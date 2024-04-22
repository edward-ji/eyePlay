
import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyOAuth
from pynput.keyboard import Controller, Key

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

def pause_playback(sp):
    sp.pause_playback()

def resume_playback(sp):
    sp.start_playback()

def next_track(sp):
    sp.next_track()

def previous_track(sp):
    sp.previous_track()

#volume up
def volume_up(sp):
    current_volume = sp.current_playback()['device']['volume_percent']
    sp.volume(current_volume + 10)

#volume down
def volume_down(sp):
    current_volume = sp.current_playback()['device']['volume_percent']
    sp.volume(current_volume - 10)

print("Choose the input mode:")
input_mode = input()
if input_mode == 'local':
    while True:
        # clear the terminal
        print("\033c")

        keyboard= Controller()

        # based on keyboard input
        print("Local mode activated. Press the following keys to control playback:")
        print("p: Pause")
        print("r: Resume")
        print("n: Next Track")
        print("b: Previous Track")
        print("u: Volume Up")
        print("d: Volume Down")
        print("q: Quit")
        command = input()

        if command == 'p' or command == 'r':
            keyboard.press(Key.media_play_pause)
        elif command == 'n':
            keyboard.press(Key.media_next)
        elif command == 'b':
            keyboard.press(Key.media_previous)
        elif command == 'u':
            keyboard.press(Key.media_volume_up)
        elif command == 'd':
            keyboard.press(Key.media_volume_down)
        elif command == 'q':
            break
        else:
            print("Invalid command")
elif input_mode == 'server':
    # Example usage
    if token:
        sp = spotipy.Spotify(auth=token)
        # Wait for user input
        while True:
            # clear the terminal
            print("\033c")

            # based on keyboard input
            print("Local mode activated. Press the following keys to control playback:")
            print("p: Pause")
            print("r: Resume")
            print("n: Next Track")
            print("b: Previous Track")
            print("u: Volume Up")
            print("d: Volume Down")
            print("q: Quit")
            command = input()
            if command == 'p':
                pause_playback(sp)
            elif command == 'r':
                resume_playback(sp)
            elif command == 'n':
                next_track(sp)
            elif command == 'b':
                previous_track(sp)
            elif command == 'u':
                volume_up(sp)
            elif command == 'd':
                volume_down(sp)
            elif command == 'q':
                break
            else:
                print("Invalid command")
    else:
        print("Can't get token for", USERNAME)