import json
import tkinter as tk
from enum import Enum
from pathlib import Path
from tkinter import ttk

import serial
from pynput.keyboard import Controller, Key
from serial.tools import list_ports

keyboard = Controller()

media_keys = [*filter(lambda attr: attr.startswith("media"), dir(Key))]


class EyeMovement(Enum):
    BLINK = "blink"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class Config:

    PORT_PATH = Path.home() / ".config/spiker_playback/port"
    KEYMAP_PATH = Path.home() / ".config/spiker_playback/keymap.json"

    port = None
    keymap = {}

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

    def set_port(self, port):
        self.port = port
        with open(self.PORT_PATH, "w") as file:
            file.write(port)

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


class App(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.pack()

        self.config = Config()
        self.serial_frame = self.create_serial_frame()
        for movement in EyeMovement:
            self.create_keymap_frame(movement)

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


root = tk.Tk()
myapp = App(root)
myapp.mainloop()
