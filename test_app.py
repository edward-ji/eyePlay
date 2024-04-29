import threading
import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyOAuth
from pynput.keyboard import Controller, Key
from enum import Enum
import time
import random

#create a new enum class
class Command(Enum):
    PAUSE = 1
    RESUME = 2
    NEXT = 3
    PREVIOUS = 4
    VOLUME_UP = 5
    VOLUME_DOWN = 6
    QUIT = 7

# Set your Spotify username
USERNAME = 'Nhat Huy Le'

# Set your Spotify client ID and client secret
CLIENT_ID = '2b0cdf67c2da453fa658c15c7947ba42'
CLIENT_SECRET = '********************************'
REDIRECT_URI = 'http://localhost:3000'

# Scope for controlling playback
SCOPE = 'user-read-playback-state,user-modify-playback-state'

# Get OAuth token
token = util.prompt_for_user_token(USERNAME,
                                   scope=SCOPE,
                                   client_id=CLIENT_ID,
                                   client_secret=CLIENT_SECRET,
                                   redirect_uri=REDIRECT_URI)

# Create Spotify object
sp = spotipy.Spotify(auth=token)

def pause_playback():
    sp.pause_playback()

def resume_playback():
    sp.start_playback()

def next_track():
    sp.next_track()

def previous_track():
    sp.previous_track()

#volume up
def volume_up():
    current_volume = sp.current_playback()['device']['volume_percent']
    sp.volume(current_volume + 10)

#volume down
def volume_down():
    current_volume = sp.current_playback()['device']['volume_percent']
    sp.volume(current_volume - 10)

#a node class
class Node:
    def __init__(self, data, global_id):
        self.data = data
        self.next = None
        self.processed = False
        self.id = global_id

#common data
head = None
curr = None
tail = None
current_state = Command.PAUSE
current_playback = sp.current_playback()
if current_playback:
    current_state = current_playback['is_playing']
    if current_state:
        current_state = Command.RESUME
    else:
        current_state = Command.PAUSE
global_id = 0

# Lock for synchronizing access to head pointer
lock = threading.Lock()

def process_data():
    global head, curr, tail, global_id
    while True:
        # every 5 seconds, create a new node with a random command
        new_command = random.choice(list(Command))
        new_node = Node(new_command, global_id)
        with lock:
            if head is None:
                head = new_node
                curr = new_node
                tail = new_node
            else:
                tail.next = new_node
                tail = tail.next
                if curr.processed:
                    curr = curr.next
            global_id += 1
            print("New command added: ", new_command)
        time.sleep(5)

def process_command():
    global curr, current_state
    while True:
        time.sleep(1)
        with lock:
            if curr and not curr.processed:
                command = curr.data
                if command == Command.PAUSE and current_state != Command.PAUSE:
                    pause_playback()
                    current_state = Command.PAUSE
                elif command == Command.RESUME and current_state != Command.RESUME:
                    resume_playback()
                    current_state = Command.RESUME
                elif command == Command.NEXT:
                    next_track()
                elif command == Command.PREVIOUS:
                    previous_track()
                elif command == Command.VOLUME_UP:
                    volume_up()
                elif command == Command.VOLUME_DOWN:
                    volume_down()
                elif command == Command.QUIT:
                    break
                else:
                    print("Invalid command: ", command)
                curr.processed = True
                print("Processed command: ", command)
                if curr.next:
                    curr = curr.next

#a function to clean the linked list after every 10 seconds
def clean_linked_list():
    global head, curr, tail
    while True:
        time.sleep(10)
        with lock:
            #delete all processed nodes
            while head and head.processed:
                print("Deleted command: ", head.data, " with id: ", head.id)
                if head.next:
                    head = head.next
                else:
                    head = None
                    curr = None
                    tail = None

# Create threads
t1 = threading.Thread(target=process_data)
t2 = threading.Thread(target=process_command)
t3 = threading.Thread(target=clean_linked_list)

# Start threads
t1.start()
t2.start()
t3.start()

# Wait for threads to finish
t1.join()
t2.join()
t3.join()

print("Multithreading example is complete!")
