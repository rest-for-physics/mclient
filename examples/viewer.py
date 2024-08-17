#!/usr/bin/env python3

import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import uproot
import awkward as ak


def get_event(tree: uproot.TTree, entry: int):
    if entry >= tree.num_entries:
        raise ValueError(f"Entry {entry} is out of bounds. Tree has {tree.num_entries} entries.")

    events = tree.arrays(entry_start=entry, entry_stop=entry + 1)
    events["signal_data"] = ak.unflatten(events["signal_data"], 512, axis=1)

    signals = ak.Array({"id": events["signal_ids"], "data": events["signal_data"]}, with_name="Signals")
    events["signals"] = signals

    events = ak.without_field(events, "signal_ids")
    events = ak.without_field(events, "signal_data")

    return events[0]


class GraphApp:
    def __init__(self, _root):
        self.file = None
        self.event_tree = None
        self.run_tree = None
        self.current_entry = 0

        self.root = _root
        self.root.title("Event Viewer")

        self.file_menu_frame = tk.Frame(self.root, bd=2)
        self.file_menu_frame.pack(pady=10)

        self.open_button = tk.Button(self.file_menu_frame, text="Open File", command=self.open_file)
        self.open_button.pack(side=tk.LEFT, padx=20, pady=20)

        self.label = tk.Label(self.file_menu_frame, text="Select a ROOT file to plot signals from")
        self.label.pack(side=tk.LEFT, padx=20, pady=20)

        self.reload_file_button = tk.Button(self.file_menu_frame, text="Reload", command=self.load_file)
        self.reload_file_button.pack(side=tk.LEFT, padx=20, pady=20)

        self.button_frame = tk.Frame(self.root, bd=2)
        self.button_frame.pack(pady=10)

        self.prev_button = tk.Button(self.button_frame, text="Previous Event", command=self.prev_event)
        self.prev_button.pack(side=tk.LEFT, padx=20, pady=20)

        self.entry_textbox = tk.Entry(self.button_frame, width=10)
        self.entry_textbox.pack(side=tk.LEFT, padx=20, pady=20)
        self.entry_textbox.insert(0, "0")

        self.next_button = tk.Button(self.button_frame, text="Next Event", command=self.next_event)
        self.next_button.pack(side=tk.RIGHT, padx=20, pady=20)

        # Initialize the plot area
        self.figure = plt.Figure(figsize=(10, 4), dpi=200)
        self.ax = self.figure.add_subplot(111)

        self.ax.set_xlabel("Time bins")
        self.ax.set_ylabel("ADC")

        self.ax.set_xlim(0, 512)
        self.ax.set_ylim(0, 4096)

        self.canvas = FigureCanvasTkAgg(self.figure, self.root)
        self.canvas.get_tk_widget().pack()
        self.canvas.draw()

        self.filepath = None

    def load_file(self):
        if self.filepath is None:
            return

        self.file = uproot.open(self.filepath)

        try:
            self.event_tree = self.file["events"]
        except KeyError:
            messagebox.showerror("Error",
                                 f"The file does not contain the 'events' tree. file keys are {self.file.keys()}")
            return

        try:
            self.run_tree = self.file["run"]
        except KeyError:
            messagebox.showerror("Error", f"The file does not contain the 'run' tree. file keys are {self.file.keys()}")
            return

        self.label.config(text=f"{self.filepath} - {self.event_tree.num_entries} entries")

        self.plot_graph()

    def open_file(self):
        self.filepath = filedialog.askopenfilename(
            filetypes=[("ROOT files", "*.root")]
        )
        if not self.filepath:
            return

        self.load_file()

    def plot_graph(self):
        if self.filepath is None or self.event_tree is None or self.run_tree is None:
            messagebox.showwarning("No File", "Please select a file first!")
            return

        try:
            entry = int(self.entry_textbox.get())
            self.current_entry = entry

            event = get_event(self.event_tree, entry)

            self.ax.clear()  # Clear the previous plot
            for signal_id, data in zip(event.signals.id, event.signals.data):
                self.ax.plot(data, label=f"ID {signal_id}", alpha=0.5, linewidth=2)

            n_signals_showing = len(self.ax.lines)

            self.ax.set_xlabel("Time bins")
            self.ax.set_ylabel("ADC")

            self.ax.set_title(f"Event {entry} - Number of signals: {len(event.signals.id)}")

            self.ax.set_xlim(0, 512)
            # customize ticks in multiples of 64
            self.ax.set_xticks(range(0, 512 + 1, 64))
            # small ticks in between
            self.ax.set_xticks(range(0, 512 + 1, 16), minor=True)

            if n_signals_showing <= 10:
                self.ax.legend(loc='upper right')

            self.canvas.draw()

        except ValueError as e:
            messagebox.showerror("Error", f"Invalid entry: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while plotting: {str(e)}")

    def prev_event(self):
        if self.current_entry > 0:
            self.current_entry -= 1
            self.entry_textbox.delete(0, tk.END)
            self.entry_textbox.insert(0, str(self.current_entry))
            self.plot_graph()

    def next_event(self):
        if self.event_tree and self.current_entry < self.event_tree.num_entries - 1:
            self.current_entry += 1
            self.entry_textbox.delete(0, tk.END)
            self.entry_textbox.insert(0, str(self.current_entry))
            self.plot_graph()


if __name__ == "__main__":
    root = tk.Tk()
    app = GraphApp(root)
    root.mainloop()
