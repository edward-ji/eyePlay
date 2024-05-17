import json
import queue
import threading
import time
import tkinter as tk
from enum import Enum
from functools import partial
from pathlib import Path
from tkinter import ttk

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import serial
import spotipy
import spotipy.util as util
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from pynput.keyboard import Controller, Key
from scipy.signal import find_peaks
from serial.tools import list_ports


# Spotify API configuration
USERNAME = 'Nhat Huy Le'
CLIENT_ID = '2b0cdf67c2da453fa658c15c7947ba42'
CLIENT_SECRET = '********************************'
REDIRECT_URI = 'http://localhost:3000'
SCOPE = 'user-read-playback-state,user-modify-playback-state'

# Get OAuth token
token = util.prompt_for_user_token(USERNAME,
                                   scope=SCOPE,
                                   client_id=CLIENT_ID,
                                   client_secret=CLIENT_SECRET,
                                   redirect_uri=REDIRECT_URI)

# Create Spotify object
sp = spotipy.Spotify(auth=token)

def playpause_playback():
    playback = sp.current_playback()
    if playback is not None:
        if playback['is_playing']:
            sp.pause_playback()
        else:
            sp.start_playback()
    else:
        sp.start_playback()

def next_track():
    sp.next_track()

def previous_track():
    sp.previous_track()

def volume_up():
    playback = sp.current_playback()
    if playback is None:
        return
    current_volume = playback['device']['volume_percent']
    sp.volume(current_volume + 10)

def volume_down():
    playback = sp.current_playback()
    if playback is None:
        return
    current_volume = playback['device']['volume_percent']
    sp.volume(current_volume - 10)

def mute():
    sp.volume(0)

mpl.use("TkAgg")

keyboard = Controller()

media_keys = {
    "None": lambda: None,
    "Play/Pause": partial(keyboard.press, Key.media_play_pause),
    "Previous": partial(keyboard.press, Key.media_previous),
    "Next": partial(keyboard.press, Key.media_next),
    "Volume Up": partial(keyboard.press, Key.media_volume_up),
    "Volume Down": partial(keyboard.press, Key.media_volume_down),
    "Mute": partial(keyboard.press, Key.media_volume_mute),
    "Spotify Play/Pause": playpause_playback,
    "Spotify Previous": previous_track,
    "Spotify Next": next_track,
    "Spotify Volume Up": volume_up,
    "Spotify Volume Down": volume_down,
    "Spotify Mute": mute,
    }

SIGMA = 25
BAUDRATE = 230400
SAMPLE_FREQ = 20000  # samples per second
CHUNK_SECONDS = 0.1
CHUNK_SIZE = int(SAMPLE_FREQ * CHUNK_SECONDS)
WINDOW_SECONDS = 0.8
WINDOW_SIZE = int(SAMPLE_FREQ * WINDOW_SECONDS)
BUFFER_SECONDS = 10.0
BUFFER_SIZE = int(SAMPLE_FREQ * BUFFER_SECONDS)


class EyeMovement(Enum):
    BLINK = "blink"
    LEFT = "left"
    RIGHT = "right"
    DOUBLE_BLINK = "double_blink"
    DOUBLE_LEFT = "double_left"
    DOUBLE_RIGHT = "double_right"

    def __mul__(self, other):
        if not isinstance(other, int):
            raise ValueError("Multiplier must be an integer")
        elif other <= 0:
            raise ValueError("Multiplier must be a positive integer")
        if other == 1:
            return self
        match self:
            case EyeMovement.BLINK:
                return EyeMovement.DOUBLE_BLINK
            case EyeMovement.LEFT:
                return EyeMovement.DOUBLE_LEFT
            case EyeMovement.RIGHT:
                return EyeMovement.DOUBLE_RIGHT
            case _:
                return self


class Config:

    PORT_PATH = ".config/spiker_playback/port"
    KEYMAP_PATH = ".config/spiker_playback/keymap.json"

    def __init__(self):
        self.load_port()
        self.load_keymap()

    def load_port(self):
        try:
            with open(self.PORT_PATH) as file:
                self.port = file.read()
            if self.port not in (port.device for port in list_ports.comports()):
                self.port = None
        except FileNotFoundError:
            self.port = None
        if self.port is not None:
            self.serial = serial.Serial(self.port, BAUDRATE)
        else:
            self.serial = None

    def set_port(self, port):
        self.port = port
        with open(self.PORT_PATH, "w") as file:
            file.write(port)
        self.serial = serial.Serial(port, BAUDRATE)

    def load_keymap(self):
        try:
            with open(self.KEYMAP_PATH) as file:
                self.keymap = json.load(file)
        except FileNotFoundError:
            self.keymap = {
                "blink": "Play/Pause",
                "left": "Previous",
                "right": "Next",
            }
            self.dump_keymap()

    def dump_keymap(self):
        parent = Path(self.KEYMAP_PATH).parent
        if not parent.exists():
            parent.mkdir(parents=True)
        with open(self.KEYMAP_PATH, "w") as file:
            json.dump(self.keymap, file)

    def set_keymap(self, movement, key):
        self.keymap[movement] = key
        self.dump_keymap()


config = Config()
data = np.full(BUFFER_SIZE, 500.0)
chunks = queue.Queue()


def process():
    global data, data_time
    while True:
        if config.serial is None:
            continue
        try:
            read_bytes = iter(config.serial.read(CHUNK_SIZE))
        except serial.SerialException:
            config.load_port()
            continue
        chunk = []
        while (raw_byte := next(read_bytes, None)) is not None:
            raw_int = int(raw_byte)
            if raw_int > 0x7F:
                next_byte = next(read_bytes, None)
                if next_byte is None:
                    break
                chunk.append((np.bitwise_and(raw_byte, 0x7F) << 7)
                             + int(next_byte))
        if len(chunk) == 0:
            continue
        chunk = np.array(chunk)
        chunk = np.fft.fftshift(np.fft.fft(chunk))
        max_freq = len(chunk) / CHUNK_SECONDS
        freq_list = np.linspace(-max_freq / 2, max_freq / 2, len(chunk))
        gaussian_filter = np.exp(-freq_list ** 2 / SIGMA ** 2)
        chunk = np.fft.ifft(np.fft.ifftshift(chunk * gaussian_filter))
        chunks.put(np.real(chunk))
        data = np.append(data[len(chunk):], np.real(chunk))
        app.update_plot()


def classify():
    SMOOTH_WINDOW_SEC = 0.025
    SMOOTH_WINDOW_SIZE = int(SMOOTH_WINDOW_SEC * SAMPLE_FREQ)

    window = np.zeros(WINDOW_SIZE)
    event = None

    while (chunk := chunks.get()) is not None:
        window = np.append(window[len(chunk):], chunk)

        if np.var(window) > 250:
            # print("window event detected")
            if event is None:
                event = window
            else:
                event = np.append(event, chunk)
                # print("event continue")
            continue
        elif event is None:
            # print("window has no event")
            continue

        # event classification
        event = event[WINDOW_SIZE // 2:-WINDOW_SIZE // 2]
        if len(event) <= int(SAMPLE_FREQ * 0.2):
            event = None
            continue
        
        high_peaks, _ = find_peaks(event, prominence=50)
        low_peaks, _ = find_peaks(-event, prominence=50)
        if len(high_peaks) == 0 or len(low_peaks) == 0:
            movement = EyeMovement.BLINK
        else:
            peaks = np.sort(np.concatenate((high_peaks, low_peaks)))
            min_diff_peak = np.min(np.diff(peaks))
            if min_diff_peak < 2065:
                movement = EyeMovement.BLINK
            else:
                if np.mean(high_peaks) < np.mean(low_peaks):
                    movement = EyeMovement.LEFT
                else:
                    movement = EyeMovement.RIGHT

        smooth_filter = np.ones(SMOOTH_WINDOW_SIZE) / SMOOTH_WINDOW_SIZE
        smoothed = np.convolve(event, smooth_filter, mode="valid")
        smoothed_peaks, _ = find_peaks(smoothed, prominence=50)
        if len(smoothed_peaks) >= 2:
            movement *= 2
        action(movement)

        # reset
        event = None


action_toggle = False


def action(movement):
    global action_toggle
    print(f"{time.time()}: {movement.value}")
    key = config.keymap.get(movement.value)
    if movement == EyeMovement.DOUBLE_BLINK:
        action_toggle = not action_toggle
        app.popup("Action " + ("enabled" if action_toggle else "disabled"))
    if key is not None and action_toggle:
        media_keys[key]()


class App(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.pack()

        self.serial_frame = self.create_serial_frame()
        self.keymap_frames = ttk.Frame(self)
        self.keymap_frames.pack()
        for i, movement in enumerate([
            EyeMovement.BLINK,
            EyeMovement.LEFT,
            EyeMovement.RIGHT,
            EyeMovement.DOUBLE_LEFT,
            EyeMovement.DOUBLE_RIGHT
            ]):
            self.create_keymap_frame(i, movement)

        self.figure = plt.figure(figsize=(12, 4))
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas.get_tk_widget().pack()
        self.update_plot()

        self.popup_frame = ttk.Frame(self)
        self.popup_frame.place(relx=1, rely=0, anchor=tk.NE)
        self.popup("Double blink to active/deactivate actions")


    def popup(self, message):
        label = tk.Label(self.popup_frame,
                         text=message,
                         bg="lightgrey",
                         fg="black",
                         )
        label.pack(anchor=tk.E, pady=(0, 5))
        self.after(5_000, label.destroy)

    def create_serial_frame(self):
        frame = ttk.Frame(self)
        frame.pack(anchor=tk.W, padx=5, pady=5)

        label = ttk.Label(frame, text="Device")
        label.pack(side=tk.LEFT)

        devices = [port.device for port in list_ports.comports()]
        combobox = ttk.Combobox(frame, values=devices)
        combobox.pack(side=tk.RIGHT)

        selected = config.port
        if selected and selected in devices:
            combobox.current(devices.index(selected))
        else:
            self.after(100, partial(self.popup,
                                    "Device not found, please select one"))
        combobox.bind(
            "<<ComboboxSelected>>",
            lambda _: config.set_port(combobox.get()),
        )

        return frame

    def create_keymap_frame(self, i, movement):
        frame = ttk.Frame(self.keymap_frames)
        frame.grid(row=i // 3, column=i % 3, padx=5, pady=5)

        text = movement.value.replace("_", " ").capitalize()
        label = ttk.Label(frame, text=text, width=9, anchor=tk.W)
        label.pack(side=tk.LEFT)

        combobox = ttk.Combobox(frame, values=[*media_keys.keys()])
        combobox.pack(side=tk.RIGHT)

        selected = config.keymap.get(movement.value)
        if selected:
            combobox.current(list(media_keys).index(selected))
        else:
            combobox.current(0)
        combobox.bind(
            "<<ComboboxSelected>>",
            lambda _: config.set_keymap(movement.value, combobox.get()),
        )

        return frame

    def update_plot(self):
        ax = self.figure.gca()
        ax.clear()
        ax.plot(data)
        self.canvas.draw()


root = tk.Tk()
app = App(root)

threading.Thread(target=process, daemon=True).start()
threading.Thread(target=classify, daemon=True).start()
app.mainloop()
