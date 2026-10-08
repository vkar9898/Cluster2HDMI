# panel_slider.py  -  runs on your PC (Windows), not on the Pico.
# Steps through the panel's data pins one at a time over USB and says the
# label number out loud, so you can watch the panel from under the desk.
#
# Before running:
#   1. In Thonny, with the Pico connected, open audi_panel_test_v3.py and
#      File > Save as... > Raspberry Pi Pico > main_v3.py
#      (change PICO_MODULE below if you use a different name).
#   2. In Thonny: Run > Configure interpreter > "Local Python 3"
#      (this frees the Pico's USB port for this program).
#   3. Open this file in Thonny and press Run.
#      If it says pyserial is missing: Tools > Manage packages > pyserial.
#
# Keys: Left / Right arrows step through the pins, W = all white, B = all black,
#       D = colour demo.

import tkinter as tk
from tkinter import ttk, messagebox
import threading, time, ast, subprocess, sys

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("pyserial is missing: in Thonny use Tools > Manage packages > pyserial")
    raise

PICO_VID = 0x2E8A
PICO_MODULE = "main_v3"   # file name on the Pico, without .py


def find_port():
    for p in serial.tools.list_ports.comports():
        if p.vid == PICO_VID:
            return p.device
    return None


def speak(text):
    if sys.platform != "win32":
        return
    cmd = ("Add-Type -AssemblyName System.Speech; "
           "(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('%s')" % text)
    subprocess.Popen(["powershell", "-NoProfile", "-Command", cmd],
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


class Pico:
    def __init__(self, port):
        self.s = serial.Serial(port, 115200, timeout=0.1)
        self.lock = threading.Lock()
        self.buf = ""
        threading.Thread(target=self._reader, daemon=True).start()
        time.sleep(0.3)
        self.send("")

    def _reader(self):
        while True:
            try:
                data = self.s.read(256)
            except Exception:
                return
            if data:
                self.buf = (self.buf + data.decode(errors="ignore"))[-4000:]

    def send(self, line):
        with self.lock:
            self.s.write((line + "\r").encode())

    def ask_labels(self):
        self.buf = ""
        self.send("print('LABELS', [l for g, l in DATA], [g for g, l in DATA])")
        end = time.time() + 3
        while time.time() < end:
            for row in self.buf.splitlines():
                if row.startswith("LABELS "):
                    parts = row[len("LABELS "):]
                    split = parts.index("] [") + 1
                    return ast.literal_eval(parts[:split]), ast.literal_eval(parts[split + 1:])
            time.sleep(0.05)
        return None, None


class App:
    def __init__(self, root):
        self.root = root
        root.title("Panel pin slider")
        port = find_port()
        if not port:
            messagebox.showerror("No Pico", "Couldn't find the Pico on USB.\n"
                                 "Is Thonny still connected to it? Switch Thonny to 'Local Python 3'.")
            root.destroy()
            return
        try:
            self.pico = Pico(port)
        except Exception as e:
            messagebox.showerror("Port busy", "Couldn't open %s:\n%s\n\nClose Thonny's "
                                 "connection to the Pico first." % (port, e))
            root.destroy()
            return
        self.pico.send("from %s import *" % PICO_MODULE)
        time.sleep(2)
        self.labels, self.gps = self.pico.ask_labels()
        if not self.labels:
            messagebox.showerror("No answer", "The Pico didn't answer.\nIs %s.py saved on it, " % PICO_MODULE +
                                 "and did it finish starting? Try unplugging and replugging the Pico.")
            root.destroy()
            return

        self.speak_on = tk.BooleanVar(value=True)
        self.idx = tk.IntVar(value=0)

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Connected on %s" % port).pack(side="left")
        ttk.Checkbutton(top, text="Speak label", variable=self.speak_on).pack(side="right")

        self.big = tk.Label(root, text="", font=("Segoe UI", 40, "bold"))
        self.big.pack(pady=10)

        self.scale = tk.Scale(root, from_=0, to=len(self.labels) - 1, orient="horizontal",
                              length=600, showvalue=False, variable=self.idx,
                              command=lambda v: self.show(int(float(v))))
        self.scale.pack(padx=20)

        btns = ttk.Frame(root, padding=10)
        btns.pack()
        ttk.Button(btns, text="< Prev", command=lambda: self.step(-1)).pack(side="left", padx=4)
        ttk.Button(btns, text="Next >", command=lambda: self.step(1)).pack(side="left", padx=4)
        ttk.Button(btns, text="All white", command=self.white).pack(side="left", padx=4)
        ttk.Button(btns, text="All black", command=self.black).pack(side="left", padx=4)
        ttk.Button(btns, text="Resend setup", command=lambda: self.pico.send("send_setup()")).pack(side="left", padx=4)

        cols = ttk.Frame(root, padding=(10, 0))
        cols.pack()
        for name in ("red", "green", "blue", "yellow", "cyan", "magenta", "grey"):
            ttk.Button(cols, text=name.capitalize(),
                       command=lambda n=name: self.colour(n)).pack(side="left", padx=3)
        ttk.Button(cols, text="Demo", command=self.demo).pack(side="left", padx=3)

        notes = ttk.LabelFrame(root, text="Notes per pin (colour + brightness)", padding=10)
        notes.pack(fill="both", expand=True, padx=10, pady=10)
        self.entries = []
        for i, (lab, gp) in enumerate(zip(self.labels, self.gps)):
            r, c = i % 9, (i // 9) * 2
            ttk.Label(notes, text="Label %d (GP%d)" % (lab, gp)).grid(row=r, column=c, sticky="w", padx=4)
            e = ttk.Entry(notes, width=18)
            e.grid(row=r, column=c + 1, padx=4, pady=1)
            self.entries.append(e)
        ttk.Button(root, text="Copy notes to clipboard", command=self.copy_notes).pack(pady=(0, 10))

        root.bind("<Left>", lambda e: self.step(-1))
        root.bind("<Right>", lambda e: self.step(1))
        root.bind("<Key-w>", lambda e: self.white())
        root.bind("<Key-b>", lambda e: self.black())
        root.bind("<Key-d>", lambda e: self.demo())
        self.show(0)

    def show(self, i):
        lab, gp = self.labels[i], self.gps[i]
        self.idx.set(i)
        self.big.config(text="Label %d   (GP%d)   %d/%d" % (lab, gp, i + 1, len(self.labels)))
        self.pico.send("only(%d)" % lab)
        if self.speak_on.get():
            speak("label %d" % lab)

    def step(self, d):
        i = max(0, min(len(self.labels) - 1, self.idx.get() + d))
        self.show(i)

    def white(self):
        self.big.config(text="ALL WHITE")
        self.pico.send("white()")
        if self.speak_on.get():
            speak("white")

    def black(self):
        self.big.config(text="ALL BLACK")
        self.pico.send("black()")
        if self.speak_on.get():
            speak("black")

    def colour(self, name):
        self.big.config(text=name.upper())
        self.pico.send("%s()" % name)
        if self.speak_on.get():
            speak(name)

    def demo(self):
        self.big.config(text="DEMO")
        self.pico.send("demo()")

    def copy_notes(self):
        text = "\n".join("Label %d (GP%d): %s" % (lab, gp, e.get())
                         for lab, gp, e in zip(self.labels, self.gps, self.entries))
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Copied", "Notes copied - paste them into the chat.")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
