import json
import tkinter as tk
from tkinter import ttk
from enum import Enum

from pynput.keyboard import Key, Controller


keyboard = Controller()

media_keys = [*filter(lambda attr: attr.startswith("media"), dir(Key))]


class EyeMovement(Enum):
    BLINK = "blink"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class App(tk.Frame):

    keymap = {}

    def __init__(self, parent):
        super().__init__(parent)
        self.pack()

        self.load_keymap()
        for movement in EyeMovement:
            self.create_keymap_frame(movement)

    def create_keymap_frame(self, movement):
        frame = ttk.Frame(self)
        frame.pack()

        label = ttk.Label(frame, text=movement.value)
        label.pack(side=tk.LEFT)

        combobox = ttk.Combobox(frame, values=media_keys)
        combobox.pack(side=tk.RIGHT)
        
        selected = self.keymap.get(movement.value)
        if selected:
            combobox.current(media_keys.index(selected))
        combobox.bind("<<ComboboxSelected>>",
                      lambda _: self.set_keymap(movement.value, combobox.get()))

        return frame

    def load_keymap(self):
        try:
            with open("keymap.json") as file:
                self.keymap = json.load(file)
        except FileNotFoundError:
            self.keymap = {
                "blink": "media_play_pause",
                "up": "media_volume_up",
                "down": "media_volume_down",
                "left": "media_previous",
                "right": "media_next"
                }
            self.dump_keymap()

    def dump_keymap(self):
        with open("keymap.json", "w") as file:
            json.dump(self.keymap, file)

    def set_keymap(self, movement, key):
        self.keymap[movement] = key
        self.dump_keymap()

root = tk.Tk()
myapp = App(root)
myapp.mainloop()
