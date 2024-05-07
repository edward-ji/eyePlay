import json
import queue
import time
import threading
import tkinter as tk
from enum import Enum
from pathlib import Path
from tkinter import ttk

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import serial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from pynput.keyboard import Controller, Key
from scipy.signal import find_peaks
from serial.tools import list_ports

mpl.use("TkAgg")

keyboard = Controller()
media_keys = [*filter(lambda attr: attr.startswith("media"), dir(Key))]

SIGMA = 25
BAUDRATE = 230400
SAMPLE_FREQ = 20000  # samples per second
CHUNK_SECONDS = 0.1
CHUNK_SIZE = int(SAMPLE_FREQ * CHUNK_SECONDS)
WINDOW_SECONDS = 1.0
WINDOW_SIZE = int(SAMPLE_FREQ * WINDOW_SECONDS)
BUFFER_SECONDS = 2.5
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

    PORT_PATH = Path.home() / ".config/spiker_playback/port"
    KEYMAP_PATH = Path.home() / ".config/spiker_playback/keymap.json"

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
                "blink": "media_play_pause",
                "left": "media_previous",
                "right": "media_next",
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
event = np.zeros_like(data)
chunks = queue.Queue()
data_time = time.time()


def process():
    global data, data_time
    while True:
        if config.serial is None:
            continue
        read_bytes = iter(config.serial.read(CHUNK_SIZE))
        chunk = []
        while (raw_byte := next(read_bytes, None)) is not None:
            raw_int = int(raw_byte)
            if raw_int > 0x7F:
                chunk.append((np.bitwise_and(raw_byte, 0x7F) << 7)
                            + int(next(read_bytes)))
        if len(chunk) == 0:
            continue
        chunk = np.array(chunk)
        chunk = np.fft.fftshift(np.fft.fft(chunk))
        max_freq = len(chunk) / CHUNK_SECONDS
        freq_list = np.linspace(-max_freq / 2, max_freq / 2, len(chunk))
        gaussian_filter = np.exp(-freq_list ** 2 / SIGMA ** 2)
        chunk = np.fft.ifft(np.fft.ifftshift(chunk * gaussian_filter))
        chunks.put(chunk)
        data = np.append(data[len(chunk):], np.real(chunk))
        myapp.update_plot()


def classify():
    global event

    minimum_sec = 0.2
    minimum_size = int(10_000 * minimum_sec)
    std_threshold = 300

    while True:
        mean = np.mean(data)
        error = data - mean
        std = np.convolve(error ** 2, np.ones(WINDOW_SIZE) / WINDOW_SIZE,
                          mode="valid")
        event = std > std_threshold
        idx = np.where(np.diff(np.r_[False, event, False]))[0]
        if len(idx) < 2:
            continue
        start, end = idx[-2:]
        if end != len(event):
            continue
        if end - start < minimum_size:
            continue
        clip = data[start - WINDOW_SIZE // 2:end + WINDOW_SIZE // 2]
        high_peaks, _ = find_peaks(clip, prominence=50)
        low_peaks, _ = find_peaks(-clip, prominence=50)
        if high_peaks.size == 0 or low_peaks.size == 0:
            continue
        peaks = np.sort(np.r_[high_peaks, low_peaks])
        avg_peak_interval = np.mean(np.diff(peaks))
        if avg_peak_interval < 1000:
            movement = EyeMovement.BLINK
        else:
            if high_peaks[0] < low_peaks[0]:
                movement = EyeMovement.RIGHT
            else:
                movement = EyeMovement.LEFT
        movement *= peaks.size // 2
        action(movement)


def action(movement):
    print(f"action: {movement.value}, {config.keymap.get(movement.value)}")
    key = config.keymap.get(movement.value)
    if key:
        print("key")


class App(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.pack()

        self.serial_frame = self.create_serial_frame()
        for movement in EyeMovement:
            self.create_keymap_frame(movement)

        self.figure = plt.figure(figsize=(12, 4))
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas.get_tk_widget().pack()
        self.update_plot()

    def create_serial_frame(self):
        frame = ttk.Frame(self)
        frame.pack()

        label = ttk.Label(frame, text="Serial port")
        label.pack(side=tk.LEFT)

        combobox = ttk.Combobox(
            frame, values=[port.device for port in list_ports.comports()]
        )
        combobox.pack(side=tk.RIGHT)

        selected = config.port
        if selected:
            combobox.current(
                [port.device for port in list_ports.comports()].index(selected)
            )
        combobox.bind(
            "<<ComboboxSelected>>",
            lambda _: config.set_port(combobox.get()),
        )

        return frame

    def create_keymap_frame(self, movement):
        frame = ttk.Frame(self)
        frame.pack()

        label = ttk.Label(frame, text=movement.value)
        label.pack(side=tk.LEFT)

        combobox = ttk.Combobox(frame, values=media_keys)
        combobox.pack(side=tk.RIGHT)

        selected = config.keymap.get(movement.value)
        if selected:
            combobox.current(media_keys.index(selected))
        combobox.bind(
            "<<ComboboxSelected>>",
            lambda _: config.set_keymap(movement.value, combobox.get()),
        )

        return frame

    def update_plot(self):
        ax = self.figure.gca()
        ax.clear()
        ax.plot(data)
        ax.plot(
            np.arange(len(data) - len(event), len(data)),
            event * (np.max(data) - np.min(data)) + np.min(data), color="red"
        )
        self.canvas.draw()


root = tk.Tk()
myapp = App(root)

threading.Thread(target=process, daemon=True).start()
threading.Thread(target=classify, daemon=True).start()
myapp.mainloop()
