import json
import tkinter as tk
from enum import Enum
from pathlib import Path
from tkinter import ttk

from pynput.keyboard import Controller, Key

KEYMAP_PATH = Path.home() / ".config/spiker_playback/keymap.json"


keyboard = Controller()

media_keys = [*filter(lambda attr: attr.startswith("media"), dir(Key))]


class EyeMovement(Enum):
    BLINK = "blink"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class Config:

    keymap = {}

    def __init__(self):
        self.load_keymap()

    def load_keymap(self):
        try:
            with open(KEYMAP_PATH) as file:
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
        parent = Path(KEYMAP_PATH).parent
        if not parent.exists():
            parent.mkdir(parents=True)
        with open(KEYMAP_PATH, "w") as file:
            json.dump(self.keymap, file)

    def set_keymap(self, movement, key):
        self.keymap[movement] = key
        self.dump_keymap()


class App(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.pack()

        self.config = Config()
        for movement in EyeMovement:
            self.create_keymap_frame(movement)

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
