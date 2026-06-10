"""Tiny helper: show a native "open audio file" dialog and print the chosen path.

Run as a subprocess so the menu-bar process never has to create a Tk root itself
(on macOS pystray and tkinter can't share one process). Prints nothing if the user
cancels.
"""

import tkinter as tk
from tkinter import filedialog

AUDIO_TYPES = [
    ("Audio files", "*.wav *.mp3 *.m4a *.flac *.ogg *.aac *.mp4 *.wma *.aiff"),
    ("All files", "*.*"),
]


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(title="Choose an audio file to transcribe",
                                      filetypes=AUDIO_TYPES)
    root.destroy()
    if path:
        print(path)


if __name__ == "__main__":
    main()
