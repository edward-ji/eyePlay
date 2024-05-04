import json
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
from serial.tools import list_ports

mpl.use("TkAgg")
plt.ion()

keyboard = Controller()
media_keys = [*filter(lambda attr: attr.startswith("media"), dir(Key))]

SIGMA = 25
BAUDRATE = 230400
SAMPLE_FREQ = 20000  # samples per second
WINDOW_SECONDS = 0.1
WINDOW_SIZE = int(SAMPLE_FREQ * WINDOW_SECONDS)
BUFFER_SECONDS = 10.0
BUFFER_SIZE = int(BUFFER_SECONDS * WINDOW_SIZE)


class EyeMovement(Enum):
    BLINK = "blink"
    LEFT = "left"
    RIGHT = "right"
    DOUBLE_BLINK = "double_blink"
    DOUBLE_LEFT = "double_left"
    DOUBLE_RIGHT = "double_right"


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
            self.serial = serial.Serial(self.port, BAUDRATE, timeout=WINDOW_SECONDS)
            if self.port not in (port.device for port in list_ports.comports()):
                self.port = None
        except FileNotFoundError:
            self.port = None

    def set_port(self, port):
        self.port = port
        with open(self.PORT_PATH, "w") as file:
            file.write(port)
        self.serial = serial.Serial(port, BAUDRATE, timeout=WINDOW_SECONDS)

    def load_keymap(self):
        try:
            with open(self.KEYMAP_PATH) as file:
                self.keymap = json.load(file)
        except FileNotFoundError:
            self.keymap = {
                "blink": "media_play_pause",
                "up": "media_volume_up",
                "down": "media_volume_down",
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


def process(app):
    while True:
        read_bytes = iter(app.config.serial.read(WINDOW_SIZE))
        data = []
        while (raw_byte := next(read_bytes, None)) is not None:
            raw_int = int(raw_byte)
            if raw_int > 0x7F:
                data.append((np.bitwise_and(raw_byte, 0x7F) << 7)
                            + int(next(read_bytes)))
        if len(data) < WINDOW_SIZE:
            continue
        data = np.array(data)
        data = np.fft.fftshift(np.fft.fft(data))
        time = np.linspace(-WINDOW_SECONDS/2, WINDOW_SECONDS/2, WINDOW_SIZE)
        gaussian_filter = np.exp(-time ** 2 / SIGMA ** 2)
        data = np.fft.ifft(np.fft.ifftshift(data * gaussian_filter))
        app.data = np.append(app.data[len(data):], data)


class App(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.pack()

        self.config = Config()
        self.serial_frame = self.create_serial_frame()
        for movement in EyeMovement:
            self.create_keymap_frame(movement)

        self.figure = plt.figure(figsize=(12, 4))
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas.get_tk_widget().pack()

        self.data = np.zeros(BUFFER_SIZE)
        threading.Thread(target=process, args=(self,), daemon=True).start()
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

        selected = self.config.port
        if selected:
            combobox.current(
                [port.device for port in list_ports.comports()].index(selected)
            )
        combobox.bind(
            "<<ComboboxSelected>>",
            lambda _: self.config.set_port(combobox.get()),
        )

        return frame

    def create_keymap_frame(self, movement):
        frame = ttk.Frame(self)
        frame.pack()

        label = ttk.Label(frame, text=movement.value)
        label.pack(side=tk.LEFT)

        combobox = ttk.Combobox(frame, values=media_keys)
        combobox.pack(side=tk.RIGHT)

        selected = self.config.keymap.get(movement.value)
        if selected:
            combobox.current(media_keys.index(selected))
        combobox.bind(
            "<<ComboboxSelected>>",
            lambda _: self.config.set_keymap(movement.value, combobox.get()),
        )

        return frame

    def update_plot(self):
        ax = self.figure.gca()
        ax.clear()
        ax.plot(self.data)
        ax.set_xlim(0, BUFFER_SIZE)
        ax.set_axis_off()
        self.canvas.draw()

        root.after(int(WINDOW_SECONDS * 1_000), self.update_plot)

root = tk.Tk()
myapp = App(root)
myapp.mainloop()
