"""Child-process transcription progress window.

The menu-bar process can't create Tk windows (see main.py), so it spawns this to
show transcription progress. Reads one number per line from stdin:

* ``0.0``–``1.0`` — set the determinate bar to that fraction
* ``-1``          — switch to an indeterminate "working…" animation

Closes itself when stdin reaches EOF (the parent finished or failed).

Run: ``python progress.py "<name shown in the window>"``
"""

import sys
import threading
import tkinter as tk
from tkinter import ttk


def main(name: str = "audio") -> None:
    state = {"frac": 0.0, "indeterminate": True, "done": False}

    def reader():
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                value = float(line)
            except ValueError:
                continue
            if value < 0:
                state["indeterminate"] = True
            else:
                state["frac"] = max(0.0, min(1.0, value))
                state["indeterminate"] = False
        state["done"] = True  # stdin closed → parent done

    root = tk.Tk()
    root.title("xRapture")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    x = (root.winfo_screenwidth() - 340) // 2
    root.geometry(f"340x96+{x}+80")

    tk.Label(root, text=f"Transcribing {name}", anchor="w").pack(fill="x", padx=14, pady=(14, 4))
    bar = ttk.Progressbar(root, mode="indeterminate", maximum=100, length=312)
    bar.pack(padx=14)
    bar.start(12)
    pct = tk.Label(root, text="working…", anchor="e", fg="#6a6a6a")
    pct.pack(fill="x", padx=14, pady=(4, 0))

    mode = {"v": "indeterminate"}

    def poll():
        if state["done"]:
            root.destroy()
            return
        if state["indeterminate"]:
            if mode["v"] != "indeterminate":
                bar.configure(mode="indeterminate")
                bar.start(12)
                mode["v"] = "indeterminate"
            pct.configure(text="working…")
        else:
            if mode["v"] != "determinate":
                bar.stop()
                bar.configure(mode="determinate")
                mode["v"] = "determinate"
            bar["value"] = state["frac"] * 100
            pct.configure(text=f"{int(state['frac'] * 100)}%")
        root.after(50, poll)

    threading.Thread(target=reader, daemon=True).start()
    poll()
    root.mainloop()


if __name__ == "__main__":
    main()
