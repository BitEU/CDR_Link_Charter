"""

- Say I have different phones that have called each other.
- I want to create a link chart that shows the relationships between these phones based on the call data.
- There should be a button the lefthand side of the chart that allows me to add people to the chart and let me link one or more phones to that person. There should be a field to enter the person's name.
- The lines linking the phones should have text labels that show the number of calls made between the phones and the date range of those calls.
- There should be a field on each linking lione too that allows me to add a note about the call relationship.
- There should be a button in the top left that allows me to export the chart as a PDF file.

"""

import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict
from datetime import datetime

class LinkChartApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Phone Link Chart")
        self.people = {}  # person_name -> set of phones
        self.notes = {}   # (caller, receiver) -> note

        # Load call data
        self.df = pd.read_csv("CDR_Link_Charter/cdr_sample.csv")
        self.graph, self.edge_labels = self.build_graph(self.df)

        # Layout
        self.left_frame = tk.Frame(master)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.add_person_btn = tk.Button(self.left_frame, text="Add Person", command=self.add_person)
        self.add_person_btn.pack(pady=10)
        self.export_btn = tk.Button(self.left_frame, text="Export as PDF", command=self.export_pdf)
        self.export_btn.pack(pady=10)

        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=master)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)
        self.draw_graph()

    def build_graph(self, df):
        G = nx.Graph()
        edge_labels = {}
        call_data = defaultdict(list)
        for _, row in df.iterrows():
            a, b = str(row['caller']), str(row['receiver'])
            t = datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S")
            key = tuple(sorted([a, b]))
            call_data[key].append(t)
            G.add_node(a)
            G.add_node(b)
            G.add_edge(a, b)
        for (a, b), times in call_data.items():
            count = len(times)
            date_range = f"{min(times).date()} - {max(times).date()}"
            edge_labels[(a, b)] = f"{count} calls\n{date_range}"
        return G, edge_labels

    def draw_graph(self):
        self.ax.clear()
        pos = nx.spring_layout(self.graph)
        nx.draw(self.graph, pos, ax=self.ax, with_labels=True, node_color='lightblue')
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=self.edge_labels, ax=self.ax)
        # Draw notes if any
        for (a, b), note in self.notes.items():
            if note:
                x = (pos[a][0] + pos[b][0]) / 2
                y = (pos[a][1] + pos[b][1]) / 2
                self.ax.text(x, y, f"Note: {note}", color='red', fontsize=8, bbox=dict(facecolor='white', alpha=0.5))
        self.canvas.draw()

    def add_person(self):
        name = simpledialog.askstring("Add Person", "Enter person's name:")
        if not name:
            return
        phones = simpledialog.askstring("Link Phones", "Enter phone numbers (comma separated):")
        if not phones:
            return
        phone_list = [p.strip() for p in phones.split(",")]
        self.people[name] = set(phone_list)
        messagebox.showinfo("Person Added", f"{name} linked to {', '.join(phone_list)}")

    def export_pdf(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if file_path:
            self.fig.savefig(file_path)
            messagebox.showinfo("Exported", f"Chart exported to {file_path}")

    # Optional: Add a method to add/edit notes on links
    def add_note_to_link(self, a, b):
        note = simpledialog.askstring("Add Note", f"Add note for link {a} - {b}:")
        if note is not None:
            self.notes[(a, b)] = note
            self.draw_graph()

if __name__ == "__main__":
    root = tk.Tk()
    app = LinkChartApp(root)
    root.mainloop()