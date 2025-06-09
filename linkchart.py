import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import json
import os
import tempfile
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing as mp
from collections import defaultdict
import numpy as np

# Check for required packages
missing_packages = []

try:
    import pandas as pd
except ImportError:
    missing_packages.append("pandas")

try:
    import networkx as nx
except ImportError:
    missing_packages.append("networkx")

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.patches as patches
    from matplotlib.collections import LineCollection
    import matplotlib.dates as mdates
except ImportError:
    missing_packages.append("matplotlib")

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.units import inch
except ImportError:
    missing_packages.append("reportlab")

try:
    import cupy as cp
    CUDA_AVAILABLE = True
except ImportError:
    CUDA_AVAILABLE = False
    print("CuPy not installed - GPU acceleration disabled")

try:
    from numba import jit, cuda
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    print("Numba not installed - JIT compilation disabled")

try:
    from svglib.svglib import svg2rlg
except ImportError:
    missing_packages.append("svglib")

try:
    import lxml
except ImportError:
    missing_packages.append("lxml") # svglib dependency

if missing_packages:
    print("Missing required packages. Please install them using:")

if missing_packages:
    print("Missing required packages. Please install them using:")
    print(f"pip install {' '.join(missing_packages)}")
    if not CUDA_AVAILABLE:
        print("\nFor GPU acceleration, also install:")
        print("pip install cupy-cuda11x  # Replace 11x with your CUDA version")
    if not NUMBA_AVAILABLE:
        print("pip install numba")
    input("Press Enter to exit...")
    exit(1)


class Person:
    """Represents a person entity that can have multiple phone numbers"""
    def __init__(self, name, person_id=None):
        self.id = person_id or f"person_{datetime.now().timestamp()}"
        self.name = name
        self.phone_numbers = set()
        self.color = None  # Will be assigned when added to graph
        
    def add_phone(self, phone):
        self.phone_numbers.add(phone)
        
    def remove_phone(self, phone):
        self.phone_numbers.discard(phone)
        
    def __repr__(self):
        return f"Person({self.name}, phones={self.phone_numbers})"


class FilterPanel(ttk.Frame):
    """Advanced filtering panel"""
    def __init__(self, parent, on_filter_change):
        super().__init__(parent)
        self.on_filter_change = on_filter_change
        
        # Title
        ttk.Label(self, text="Filters", font=("Arial", 12, "bold")).pack(pady=5)
        
        # Date range filter
        date_frame = ttk.LabelFrame(self, text="Date Range", padding=5)
        date_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(date_frame, text="From:").grid(row=0, column=0, sticky="w")
        self.date_from = ttk.Entry(date_frame, width=15)
        self.date_from.grid(row=0, column=1, padx=5)
        self.date_from.insert(0, "YYYY-MM-DD")
        
        ttk.Label(date_frame, text="To:").grid(row=1, column=0, sticky="w")
        self.date_to = ttk.Entry(date_frame, width=15)
        self.date_to.grid(row=1, column=1, padx=5)
        self.date_to.insert(0, "YYYY-MM-DD")
        
        # Time range filter
        time_frame = ttk.LabelFrame(self, text="Time Range", padding=5)
        time_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(time_frame, text="From:").grid(row=0, column=0, sticky="w")
        self.time_from = ttk.Entry(time_frame, width=15)
        self.time_from.grid(row=0, column=1, padx=5)
        self.time_from.insert(0, "HH:MM")
        
        ttk.Label(time_frame, text="To:").grid(row=1, column=0, sticky="w")
        self.time_to = ttk.Entry(time_frame, width=15)
        self.time_to.grid(row=1, column=1, padx=5)
        self.time_to.insert(0, "HH:MM")
        
        # Node limit
        node_frame = ttk.LabelFrame(self, text="Node Limits", padding=5)
        node_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(node_frame, text="Max Nodes:").grid(row=0, column=0, sticky="w")
        self.max_nodes = ttk.Spinbox(node_frame, from_=10, to=1000, increment=10, width=10)
        self.max_nodes.set(100)
        self.max_nodes.grid(row=0, column=1, padx=5)
        
        # Minimum calls filter
        ttk.Label(node_frame, text="Min Calls:").grid(row=1, column=0, sticky="w")
        self.min_calls = ttk.Spinbox(node_frame, from_=1, to=100, increment=1, width=10)
        self.min_calls.set(1)
        self.min_calls.grid(row=1, column=1, padx=5)
        
        # Node type filter
        type_frame = ttk.LabelFrame(self, text="Show", padding=5)
        type_frame.pack(fill="x", padx=5, pady=5)
        
        self.show_phones = tk.BooleanVar(value=True)
        self.show_persons = tk.BooleanVar(value=True)
        self.show_orphan_phones = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(type_frame, text="Phones", variable=self.show_phones,
                       command=self.apply_filters).pack(anchor="w")
        ttk.Checkbutton(type_frame, text="Persons", variable=self.show_persons,
                       command=self.apply_filters).pack(anchor="w")
        ttk.Checkbutton(type_frame, text="Unassigned Phones", variable=self.show_orphan_phones,
                       command=self.apply_filters).pack(anchor="w")
        
        # Apply button
        ttk.Button(self, text="Apply Filters", command=self.apply_filters).pack(pady=10)
        
        # Reset button
        ttk.Button(self, text="Reset Filters", command=self.reset_filters).pack()
        
    def get_filters(self):
        """Return current filter settings"""
        filters = {
            'date_from': self.date_from.get(),
            'date_to': self.date_to.get(),
            'time_from': self.time_from.get(),
            'time_to': self.time_to.get(),
            'max_nodes': int(self.max_nodes.get()),
            'min_calls': int(self.min_calls.get()),
            'show_phones': self.show_phones.get(),
            'show_persons': self.show_persons.get(),
            'show_orphan_phones': self.show_orphan_phones.get()
        }
        return filters
        
    def apply_filters(self):
        """Apply current filters"""
        self.on_filter_change(self.get_filters())
        
    def reset_filters(self):
        """Reset all filters to defaults"""
        self.date_from.delete(0, tk.END)
        self.date_from.insert(0, "YYYY-MM-DD")
        self.date_to.delete(0, tk.END)
        self.date_to.insert(0, "YYYY-MM-DD")
        self.time_from.delete(0, tk.END)
        self.time_from.insert(0, "HH:MM")
        self.time_to.delete(0, tk.END)
        self.time_to.insert(0, "HH:MM")
        self.max_nodes.set(100)
        self.min_calls.set(1)
        self.show_phones.set(True)
        self.show_persons.set(True)
        self.show_orphan_phones.set(True)
        self.apply_filters()


class PersonManagementDialog(tk.Toplevel):
    """Dialog for managing persons and their phone associations"""
    def __init__(self, parent, persons, phones):
        super().__init__(parent)
        self.title("Person Management")
        self.geometry("600x500")
        
        self.persons = persons  # Dictionary of person_id -> Person
        self.phones = phones    # Set of all phone numbers
        self.result = None
        
        # Main container
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Person list
        list_frame = ttk.LabelFrame(main_frame, text="Persons", padding=5)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Listbox with scrollbar
        scroll = ttk.Scrollbar(list_frame)
        scroll.pack(side="right", fill="y")
        
        self.person_listbox = tk.Listbox(list_frame, yscrollcommand=scroll.set)
        self.person_listbox.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.person_listbox.yview)
        
        # Populate person list
        self.refresh_person_list()
        
        # Bind selection event
        self.person_listbox.bind('<<ListboxSelect>>', self.on_person_select)
        
        # Right panel
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True)
        
        # Add person section
        add_frame = ttk.LabelFrame(right_frame, text="Add Person", padding=5)
        add_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(add_frame, text="Name:").grid(row=0, column=0, sticky="w")
        self.name_entry = ttk.Entry(add_frame, width=25)
        self.name_entry.grid(row=0, column=1, padx=5)
        
        ttk.Button(add_frame, text="Add Person", 
                  command=self.add_person).grid(row=0, column=2, padx=5)
        
        # Phone assignment section
        phone_frame = ttk.LabelFrame(right_frame, text="Phone Assignment", padding=5)
        phone_frame.pack(fill="both", expand=True)
        
        # Selected person info
        self.selected_person_label = ttk.Label(phone_frame, text="Select a person", 
                                              font=("Arial", 10, "bold"))
        self.selected_person_label.pack()
        
        # Assigned phones
        ttk.Label(phone_frame, text="Assigned Phones:").pack(anchor="w", pady=(10, 0))
        
        self.assigned_listbox = tk.Listbox(phone_frame, height=6)
        self.assigned_listbox.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(phone_frame, text="Remove Selected Phone", 
                  command=self.remove_phone).pack()
        
        # Available phones
        ttk.Label(phone_frame, text="Available Phones:").pack(anchor="w", pady=(10, 0))
        
        # Search box
        search_frame = ttk.Frame(phone_frame)
        search_frame.pack(fill="x", padx=5)
        
        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.phone_search = ttk.Entry(search_frame)
        self.phone_search.pack(side="left", fill="x", expand=True, padx=5)
        self.phone_search.bind('<KeyRelease>', self.filter_phones)
        
        # This is the corrected code
        self.available_listbox = tk.Listbox(phone_frame, height=8)

        # The "Assign" button is packed last, but told to stick to the bottom.
        ttk.Button(phone_frame, text="Assign Selected Phone", 
                  command=self.assign_phone).pack(side="bottom", pady=5)

        # The listbox is now packed to fill the remaining space above the button.
        self.available_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Populate available phones
        self.refresh_available_phones()
        
        # Bottom buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(button_frame, text="Delete Person", 
                  command=self.delete_person).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Close", 
                  command=self.destroy).pack(side="right", padx=5)
        
    def refresh_person_list(self):
        """Refresh the person listbox"""
        self.person_listbox.delete(0, tk.END)
        for person_id, person in sorted(self.persons.items(), key=lambda x: x[1].name):
            phone_count = len(person.phone_numbers)
            self.person_listbox.insert(tk.END, f"{person.name} ({phone_count} phones)")
            
    def on_person_select(self, event):
        """Handle person selection"""
        selection = self.person_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        person_id = list(sorted(self.persons.items(), key=lambda x: x[1].name))[index][0]
        person = self.persons[person_id]
        
        self.selected_person_label.config(text=f"Selected: {person.name}")
        self.current_person_id = person_id
        
        # Update assigned phones
        self.assigned_listbox.delete(0, tk.END)
        for phone in sorted(person.phone_numbers):
            self.assigned_listbox.insert(tk.END, phone)
            
        # Update available phones
        self.refresh_available_phones()
        
    def refresh_available_phones(self):
        """Refresh available phones list"""
        self.available_listbox.delete(0, tk.END)
        
        # Get all assigned phones
        assigned = set()
        for person in self.persons.values():
            assigned.update(person.phone_numbers)
            
        # Show unassigned phones
        search_term = self.phone_search.get().lower()
        for phone in sorted(self.phones - assigned):
            if search_term in phone.lower():
                self.available_listbox.insert(tk.END, phone)
                
    def filter_phones(self, event):
        """Filter phone list based on search"""
        self.refresh_available_phones()
        
    def add_person(self):
        """Add a new person"""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Please enter a person name")
            return
            
        person = Person(name)
        self.persons[person.id] = person
        
        self.name_entry.delete(0, tk.END)
        self.refresh_person_list()
        
        messagebox.showinfo("Success", f"Added person: {name}")
        
    def delete_person(self):
        """Delete selected person"""
        if not hasattr(self, 'current_person_id'):
            messagebox.showwarning("Warning", "Please select a person")
            return
            
        person = self.persons[self.current_person_id]
        if messagebox.askyesno("Confirm", f"Delete {person.name}?"):
            del self.persons[self.current_person_id]
            self.refresh_person_list()
            self.selected_person_label.config(text="Select a person")
            self.assigned_listbox.delete(0, tk.END)
            self.refresh_available_phones()
            
    def assign_phone(self):
        """Assign selected phone to current person"""
        if not hasattr(self, 'current_person_id'):
            messagebox.showwarning("Warning", "Please select a person")
            return
            
        selection = self.available_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a phone to assign")
            return
            
        phone = self.available_listbox.get(selection[0])
        person = self.persons[self.current_person_id]
        person.add_phone(phone)
        
        self.assigned_listbox.insert(tk.END, phone)
        self.refresh_available_phones()
        self.refresh_person_list()
        
    def remove_phone(self):
        """Remove selected phone from current person"""
        if not hasattr(self, 'current_person_id'):
            return
            
        selection = self.assigned_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a phone to remove")
            return
            
        phone = self.assigned_listbox.get(selection[0])
        person = self.persons[self.current_person_id]
        person.remove_phone(phone)
        
        self.assigned_listbox.delete(selection[0])
        self.refresh_available_phones()
        self.refresh_person_list()

class PageSizeDialog(tk.Toplevel):
    """A modal dialog to ask for PDF page size using radio buttons."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Select Page Size")
        self.result = None
        self.choice_var = tk.StringVar(value='a4')  # Default to A4

        # Adjust geometry for new layout
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        self.geometry(f"350x180+{parent_x + (parent_width // 2) - 175}+{parent_y + (parent_height // 2) - 90}")

        self.transient(parent)
        self.grab_set()

        # Main content frame
        main_frame = ttk.Frame(self, padding="10 10 10 10")
        main_frame.pack(fill="both", expand=True)

        # Label
        ttk.Label(main_frame, text="Please select the desired PDF page size:").pack(pady=5, anchor="w")

        # Radio buttons
        radio_frame = ttk.Frame(main_frame, padding="10 0 0 0")
        radio_frame.pack(pady=5, fill="x")
        ttk.Radiobutton(radio_frame, text="Letter (Landscape)", variable=self.choice_var, value='letter').pack(anchor="w")
        ttk.Radiobutton(radio_frame, text="A4 (Landscape)", variable=self.choice_var, value='a4').pack(anchor="w")
        ttk.Radiobutton(radio_frame, text="Native (Fit to Chart)", variable=self.choice_var, value='native').pack(anchor="w")

        # --- CORRECTED BUTTON LAYOUT ---
        # A frame to hold the buttons, packed to the bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side="bottom", fill="x", pady=(20, 0))

        # Pack buttons to the right side of the button_frame
        ttk.Button(button_frame, text="Cancel", command=self.on_close, width=10).pack(side="right", padx=5)
        ttk.Button(button_frame, text="OK", command=self.on_ok, width=10).pack(side="right")
        # --- END OF CORRECTION ---

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Return>", lambda event: self.on_ok())
        self.bind("<Escape>", lambda event: self.on_close())
        
    def on_ok(self):
        self.result = self.choice_var.get()
        self.destroy()

    def on_close(self):
        # This is the corrected method where the syntax error was
        self.result = None
        self.destroy()

class EnhancedPhoneLinkChartApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Phone Call Link Chart Analyzer - Enhanced Edition")
        self.root.geometry("1400x900")

        # Data storage
        self.call_data = pd.DataFrame()
        # No longer need self.filtered_data here, it will be returned by the worker
        self.graph = nx.Graph()
        self.persons = {}  # person_id -> Person object
        self.pos = {}
        self.current_filters = {}
        self.person_manager_window = None

        # Add a queue for thread communication
        self.result_queue = queue.Queue()

        # Performance settings
        self.use_gpu = CUDA_AVAILABLE
        self.thread_pool = ThreadPoolExecutor(max_workers=mp.cpu_count())

        # GUI Setup
        self.setup_gui()

        # Try to load sample data
        self.root.after(100, self.load_sample_data)
        
    def setup_gui(self):
        """Setup the main GUI"""
        # Main container with paned window
        main_paned = ttk.PanedWindow(self.root, orient="horizontal")
        main_paned.pack(fill="both", expand=True)
        
        # Left panel - filters
        left_frame = ttk.Frame(main_paned, width=250)
        self.filter_panel = FilterPanel(left_frame, self.on_filter_change)
        self.filter_panel.pack(fill="both", expand=True)
        main_paned.add(left_frame, weight=0)
        
        # Right panel - main content
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)
        
        # Top toolbar
        toolbar = ttk.Frame(right_frame)
        toolbar.pack(fill="x", padx=5, pady=5)
        
        # Toolbar buttons
        ttk.Button(toolbar, text="📁 Load CSV", 
                  command=self.load_csv_file).pack(side="left", padx=2)
        ttk.Button(toolbar, text="👥 Manage Persons", 
                  command=self.open_person_manager).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🔄 Reset Layout", 
                  command=self.reset_layout).pack(side="left", padx=2)
        ttk.Button(toolbar, text="📊 Statistics", 
                  command=self.show_statistics).pack(side="left", padx=2)
        ttk.Button(toolbar, text="📄 Export PDF", 
                  command=self.export_to_pdf).pack(side="left", padx=2)
        
        # GPU indicator
        gpu_text = "🚀 GPU Enabled" if self.use_gpu else "💻 CPU Mode"
        self.gpu_label = ttk.Label(toolbar, text=gpu_text, 
                                  foreground="green" if self.use_gpu else "orange")
        self.gpu_label.pack(side="right", padx=10)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready - Load CSV data to begin")
        self.progress_var = tk.DoubleVar()
        
        status_frame = ttk.Frame(right_frame)
        status_frame.pack(fill="x", padx=5)
        
        ttk.Label(status_frame, textvariable=self.status_var).pack(side="left")
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, 
                                           length=200, mode='determinate')
        self.progress_bar.pack(side="right", padx=5)
        
        # Graph canvas with tabs
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Network view tab
        network_frame = ttk.Frame(self.notebook)
        self.notebook.add(network_frame, text="Network View")
        
        self.fig = Figure(figsize=(12, 8), dpi=100, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        self.canvas = FigureCanvasTkAgg(self.fig, network_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Detail view tab
        detail_frame = ttk.Frame(self.notebook)
        self.notebook.add(detail_frame, text="Detail View")
        
        # Create treeview for detailed data
        tree_scroll = ttk.Scrollbar(detail_frame)
        tree_scroll.pack(side="right", fill="y")
        
        self.detail_tree = ttk.Treeview(detail_frame, 
                                       columns=("Caller", "Receiver", "Count", "First", "Last", "Avg Duration"),
                                       yscrollcommand=tree_scroll.set)
        self.detail_tree.pack(fill="both", expand=True)
        tree_scroll.config(command=self.detail_tree.yview)
        
        # Configure columns
        self.detail_tree.heading("#0", text="Connection")
        self.detail_tree.heading("Caller", text="Caller")
        self.detail_tree.heading("Receiver", text="Receiver")
        self.detail_tree.heading("Count", text="Calls")
        self.detail_tree.heading("First", text="First Call")
        self.detail_tree.heading("Last", text="Last Call")
        self.detail_tree.heading("Avg Duration", text="Avg Duration")
        
        # Bind events
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        
        # Initialize zoom/pan
        self.zoom_factor = 1.0
        self.pan_offset = [0, 0]
        self.dragging = None
        
    def load_sample_data(self):
        """Try to load sample data"""
        try:
            if os.path.exists('cdr_sample.csv'):
                self.load_csv_data('cdr_sample.csv')
        except Exception as e:
            print(f"Could not load sample data: {e}")
            
    def load_csv_file(self):
        """Load CSV file dialog"""
        file_path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            self.load_csv_data(file_path)
            
    def load_csv_data(self, file_path):
        """Load and process CSV data with multithreading"""
        try:
            # Show progress
            self.status_var.set("Loading CSV file...")
            self.progress_var.set(10)
            self.root.update()
            
            # Load CSV in chunks for large files
            chunk_size = 10000
            chunks = []
            
            for chunk in pd.read_csv(file_path, chunksize=chunk_size):
                chunks.append(chunk)
                self.progress_var.set(min(50, 10 + len(chunks) * 5))
                self.root.update()
                
            self.call_data = pd.concat(chunks, ignore_index=True)
            
            # Normalize format
            self.normalize_csv_format()
            
            # Process data in parallel
            self.status_var.set("Processing call data...")
            self.process_call_data_parallel()
            
            # Update display
            self.apply_current_filters()
            
            self.status_var.set(f"Loaded {len(self.call_data):,} call records")
            self.progress_var.set(0)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV: {str(e)}")
            self.progress_var.set(0)
            
    def normalize_csv_format(self):
        """Normalize CSV format - same as original but optimized"""
        # Similar to original implementation but with progress updates
        self.progress_var.set(60)
        
        if 'Target Number' in self.call_data.columns:
            self.process_new_format_optimized()
        elif 'caller' in self.call_data.columns:
            self.process_old_format()
        else:
            self.auto_detect_format()
            
    def process_new_format_optimized(self):
        """Process new format with vectorized operations"""
        # Ensure string types for all relevant columns
        self.call_data['Target Number'] = self.call_data['Target Number'].astype(str)
        self.call_data['From or To Number'] = self.call_data['From or To Number'].astype(str)
        self.call_data['Call Direction'] = self.call_data['Call Direction'].astype(str)
        
        # Use vectorized operations for better performance
        direction_lower = self.call_data['Call Direction'].str.lower()
        is_outbound = direction_lower.isin(['outbound', 'outgoing', 'out'])
        
        self.call_data['caller'] = pd.Series(
            self.call_data['Target Number'].where(is_outbound, self.call_data['From or To Number']),
            dtype=str
        )
        
        self.call_data['receiver'] = pd.Series(
            self.call_data['From or To Number'].where(is_outbound, self.call_data['Target Number']),
            dtype=str
        )
        
        # Parse timestamps with proper format
        try:
            # Convert date and time columns to string first
            date_str = self.call_data['Date'].astype(str)
            start_str = self.call_data['Start'].astype(str)
            
            # Combine date and time
            datetime_str = date_str + ' ' + start_str
            
            # Try to parse with common formats
            self.call_data['timestamp'] = pd.to_datetime(
                datetime_str,
                format='%m/%d/%Y %H:%M:%S',
                errors='coerce'
            )
            
            # If many failed, try without format
            if self.call_data['timestamp'].isna().sum() > len(self.call_data) * 0.5:
                self.call_data['timestamp'] = pd.to_datetime(datetime_str, errors='coerce')
                
        except Exception as e:
            print(f"Timestamp parsing error: {e}")
            self.call_data['timestamp'] = pd.Timestamp.now()
        
        # Calculate duration if possible
        if 'Start' in self.call_data.columns and 'End' in self.call_data.columns:
            try:
                date_str = self.call_data['Date'].astype(str)
                start_str = self.call_data['Start'].astype(str)
                end_str = self.call_data['End'].astype(str)
                
                start_datetime = pd.to_datetime(date_str + ' ' + start_str, errors='coerce')
                end_datetime = pd.to_datetime(date_str + ' ' + end_str, errors='coerce')
                
                self.call_data['duration'] = (end_datetime - start_datetime).dt.total_seconds()
                # Clean up negative or invalid durations
                self.call_data.loc[self.call_data['duration'] < 0, 'duration'] = pd.NA
            except Exception as e:
                print(f"Duration calculation error: {e}")
                self.call_data['duration'] = pd.NA
            
    def process_old_format(self):
        """Process old format"""
        if 'timestamp' not in self.call_data.columns:
            time_cols = [col for col in self.call_data.columns 
                        if any(word in col.lower() for word in ['time', 'date', 'when'])]
            if time_cols:
                self.call_data['timestamp'] = pd.to_datetime(self.call_data[time_cols[0]])
            else:
                self.call_data['timestamp'] = pd.Timestamp.now()
        else:
            self.call_data['timestamp'] = pd.to_datetime(self.call_data['timestamp'])
            
    def auto_detect_format(self):
        """Auto-detect CSV format"""
        # Similar to original but with progress updates
        self.progress_var.set(70)
        
        # Implementation similar to original
        cols = self.call_data.columns
        caller_patterns = ['caller', 'from', 'source', 'originator', 'a_number']
        receiver_patterns = ['receiver', 'to', 'destination', 'called', 'b_number']
        
        caller_col = None
        receiver_col = None
        
        for col in cols:
            col_lower = col.lower()
            if any(pattern in col_lower for pattern in caller_patterns):
                caller_col = col
            elif any(pattern in col_lower for pattern in receiver_patterns):
                receiver_col = col
                
        if caller_col and receiver_col:
            self.call_data['caller'] = self.call_data[caller_col]
            self.call_data['receiver'] = self.call_data[receiver_col]
            
            # Find timestamp
            time_cols = [col for col in cols 
                        if any(word in col.lower() for word in ['time', 'date', 'when', 'start'])]
            if time_cols:
                self.call_data['timestamp'] = pd.to_datetime(self.call_data[time_cols[0]])
            else:
                self.call_data['timestamp'] = pd.Timestamp.now()
        else:
            raise ValueError("Could not auto-detect caller and receiver columns")
            
    def process_call_data_parallel(self):
        """Process call data using parallel processing"""
        if self.call_data.empty:
            return
            
        self.progress_var.set(80)
        
        # Ensure string types for phone numbers
        self.call_data['caller'] = self.call_data['caller'].astype(str)
        self.call_data['receiver'] = self.call_data['receiver'].astype(str)
        
        # Get unique phones
        all_phones = set(self.call_data['caller'].unique()) | set(self.call_data['receiver'].unique())
        
        # Group by caller-receiver pairs
        grouped = self.call_data.groupby(['caller', 'receiver'])
        
        # Process in parallel
        futures = []
        chunk_size = max(1, len(grouped) // mp.cpu_count())
        
        group_keys = list(grouped.groups.keys())
        for i in range(0, len(group_keys), chunk_size):
            chunk = group_keys[i:i+chunk_size]
            future = self.thread_pool.submit(self.process_call_chunk, chunk, grouped)
            futures.append(future)
            
        # Collect results
        call_stats = {}
        for future in as_completed(futures):
            result = future.result()
            call_stats.update(result)
            
        # Build graph
        self.graph.clear()
        self.graph.add_nodes_from(all_phones)
        
        # Add edges
        for (phone1, phone2), stats in call_stats.items():
            self.graph.add_edge(
                phone1, phone2,
                weight=stats['count'],
                call_count=stats['count'],
                date_range=stats['date_range'],
                avg_duration=stats.get('avg_duration', ''),
                first_call=stats['first_call'],
                last_call=stats['last_call']
            )
            
        self.progress_var.set(100)
        
    def process_call_chunk(self, chunk_keys, grouped):
        """Process a chunk of call data"""
        result = {}
        
        for key in chunk_keys:
            try:
                group = grouped.get_group(key)
                caller, receiver = key
                
                # Ensure string types
                caller = str(caller)
                receiver = str(receiver)
                
                # Calculate statistics
                dates = pd.to_datetime(group['timestamp'])
                first_call = dates.min()
                last_call = dates.max()
                
                date_range = f"{first_call.strftime('%m/%d/%y')} - {last_call.strftime('%m/%d/%y')}"
                
                # Average duration
                avg_duration = ""
                if 'duration' in group.columns:
                    durations = group['duration'].dropna()
                    if len(durations) > 0 and durations.dtype in ['float64', 'int64']:
                        avg_sec = float(durations.mean())
                        if avg_sec >= 60:
                            avg_duration = f" ({avg_sec/60:.1f}m avg)"
                        else:
                            avg_duration = f" ({avg_sec:.0f}s avg)"
                            
                # Store results with sorted tuple key
                edge_key = tuple(sorted([caller, receiver]))
                result[edge_key] = {
                    'count': len(group),
                    'date_range': date_range,
                    'avg_duration': avg_duration,
                    'first_call': first_call,
                    'last_call': last_call
                }
            except Exception as e:
                print(f"Error processing chunk key {key}: {e}")
                continue
                
        return result
        
    def on_filter_change(self, filters):
        """Handle filter changes"""
        self.current_filters = filters
        self.apply_current_filters()
        
    def apply_current_filters(self):
        """Starts the filtering process in a background thread to keep the GUI responsive."""
        if self.call_data.empty:
            return

        self.status_var.set("Applying filters...")
        self.progress_bar.start()  # Use indeterminate progress bar for responsiveness

        # Submit the worker function to the thread pool with the necessary data
        self.thread_pool.submit(self._worker_apply_filters, self.current_filters, self.call_data.copy())

        # Start checking for the result from the queue
        self.root.after(100, self._check_filter_results)

    def _worker_apply_filters(self, filters, data):
        """
        This function runs in the background. It performs all slow filtering and graph building.
        It combines the logic from the old apply_current_filters and build_filtered_graph methods.
        """
        # --- Filtering Stage ---
        # Apply date filter
        if filters.get('date_from', 'YYYY-MM-DD') != 'YYYY-MM-DD':
            try:
                date_from = pd.to_datetime(filters['date_from'])
                data = data[data['timestamp'] >= date_from]
            except: pass

        if filters.get('date_to', 'YYYY-MM-DD') != 'YYYY-MM-DD':
            try:
                date_to = pd.to_datetime(filters['date_to'])
                data = data[data['timestamp'] <= date_to]
            except: pass

        # Apply time filter
        if filters.get('time_from', 'HH:MM') != 'HH:MM':
            try:
                time_from = pd.to_datetime(filters['time_from']).time()
                data = data[data['timestamp'].dt.time >= time_from]
            except: pass

        if filters.get('time_to', 'HH:MM') != 'HH:MM':
            try:
                time_to = pd.to_datetime(filters['time_to']).time()
                data = data[data['timestamp'].dt.time <= time_to]
            except: pass

        # --- Graph Building Stage ---
        filtered_graph = nx.Graph()
        if data.empty:
            self.result_queue.put(filtered_graph) # Put empty graph in queue and exit
            return

        # Count calls and gather details
        call_details = defaultdict(lambda: {'dates': [], 'durations': []})
        for _, row in data.iterrows():
            edge_key = tuple(sorted([row['caller'], row['receiver']]))
            call_details[edge_key]['dates'].append(row['timestamp'])
            if 'duration' in row and pd.notna(row['duration']):
                call_details[edge_key]['durations'].append(row['duration'])

        # Filter by minimum calls
        min_calls = filters.get('min_calls', 1)
        filtered_edges = {k: len(v['dates']) for k, v in call_details.items() if len(v['dates']) >= min_calls}

        # Get all phones involved in the filtered edges
        all_phones = set()
        for (p1, p2) in filtered_edges.keys():
            all_phones.add(p1)
            all_phones.add(p2)

        # Apply node limit by selecting most active phones
        max_nodes = filters.get('max_nodes', 100)
        if len(all_phones) > max_nodes:
            phone_activity = defaultdict(int)
            for (p1, p2), count in filtered_edges.items():
                phone_activity[p1] += count
                phone_activity[p2] += count

            top_phones = set(sorted(phone_activity, key=phone_activity.get, reverse=True)[:max_nodes])

            # Further filter edges to only include top phones
            filtered_edges = {k: v for k, v in filtered_edges.items() if k[0] in top_phones and k[1] in top_phones}
            all_phones = top_phones

        # Build the final graph
        filtered_graph.add_nodes_from(all_phones)
        for (phone1, phone2), count in filtered_edges.items():
            details = call_details[(phone1, phone2)]
            dates = sorted(details['dates'])
            date_range = f"{dates[0].strftime('%m/%d/%y')} - {dates[-1].strftime('%m/%d/%y')}"

            avg_duration = ""
            if details['durations']:
                avg_sec = sum(details['durations']) / len(details['durations'])
                avg_duration = f" ({avg_sec/60:.1f}m avg)" if avg_sec >= 60 else f" ({avg_sec:.0f}s avg)"

            filtered_graph.add_edge(
                phone1, phone2, weight=count, call_count=count, date_range=date_range,
                avg_duration=avg_duration, first_call=dates[0], last_call=dates[-1]
            )

        # Put the final result onto the queue for the main thread
        self.result_queue.put(filtered_graph)

    def _check_filter_results(self):
        """Checks the queue for a result from the worker thread and updates the GUI."""
        try:
            self.filtered_graph = self.result_queue.get_nowait()

            # Stop the progress bar and update status
            self.progress_bar.stop()
            self.progress_var.set(0) # Reset determinate progress bar if needed
            self.status_var.set(f"Showing {len(self.filtered_graph.nodes())} nodes, {len(self.filtered_graph.edges())} connections")

            # We have a result, so update the visualization
            self.reset_layout() # reset_layout is better here as it recalculates positions
            self.update_detail_view()

        except queue.Empty:
            # Result is not ready yet, check again in 100ms
            self.root.after(100, self._check_filter_results)
        
    def build_filtered_graph(self):
        """Build graph from filtered data with node limits"""
        self.filtered_graph = nx.Graph()
        
        if self.filtered_data.empty:
            return
            
        # Count calls per phone pair
        call_counts = defaultdict(int)
        call_details = defaultdict(lambda: {'dates': [], 'durations': []})
        
        for _, row in self.filtered_data.iterrows():
            edge_key = tuple(sorted([row['caller'], row['receiver']]))
            call_counts[edge_key] += 1
            call_details[edge_key]['dates'].append(row['timestamp'])
            if 'duration' in row and pd.notna(row['duration']):
                call_details[edge_key]['durations'].append(row['duration'])
                
        # Filter by minimum calls
        min_calls = self.current_filters.get('min_calls', 1)
        filtered_edges = {k: v for k, v in call_counts.items() if v >= min_calls}
        
        # Get all phones involved
        all_phones = set()
        for (p1, p2) in filtered_edges.keys():
            all_phones.add(p1)
            all_phones.add(p2)
            
        # Apply node limit by selecting most active phones
        max_nodes = self.current_filters.get('max_nodes', 100)
        if len(all_phones) > max_nodes:
            # Calculate activity score for each phone
            phone_activity = defaultdict(int)
            for (p1, p2), count in filtered_edges.items():
                phone_activity[p1] += count
                phone_activity[p2] += count
                
            # Select top phones
            top_phones = set(sorted(phone_activity.keys(), 
                                  key=lambda x: phone_activity[x], 
                                  reverse=True)[:max_nodes])
            
            # Filter edges to only include top phones
            filtered_edges = {k: v for k, v in filtered_edges.items() 
                            if k[0] in top_phones and k[1] in top_phones}
            all_phones = top_phones
            
        self.progress_var.set(60)
        
        # Build the graph
        self.filtered_graph.add_nodes_from(all_phones)
        
        # Add edges with attributes
        for (phone1, phone2), count in filtered_edges.items():
            details = call_details[(phone1, phone2)]
            dates = sorted(details['dates'])
            
            date_range = f"{dates[0].strftime('%m/%d/%y')} - {dates[-1].strftime('%m/%d/%y')}"
            
            avg_duration = ""
            if details['durations']:
                avg_sec = sum(details['durations']) / len(details['durations'])
                if avg_sec >= 60:
                    avg_duration = f" ({avg_sec/60:.1f}m avg)"
                else:
                    avg_duration = f" ({avg_sec:.0f}s avg)"
                    
            self.filtered_graph.add_edge(
                phone1, phone2,
                weight=count,
                call_count=count,
                date_range=date_range,
                avg_duration=avg_duration,
                first_call=dates[0],
                last_call=dates[-1]
            )
            
        self.progress_var.set(80)
        
    def update_graph(self):
        """Update graph visualization with enhanced layout"""
        self.ax.clear()
        
        if not hasattr(self, 'filtered_graph') or self.filtered_graph.number_of_nodes() == 0:
            self.ax.text(0.5, 0.5, 'No data to display\nAdjust filters or load data', 
                        ha='center', va='center', transform=self.ax.transAxes,
                        fontsize=14, color='gray')
            self.canvas.draw()
            return
            
        # Calculate layout using GPU if available
        if self.use_gpu and CUDA_AVAILABLE and self.filtered_graph.number_of_nodes() > 100:
            self.pos = self.calculate_layout_gpu()
        else:
            # Use force-directed layout
            self.pos = nx.spring_layout(self.filtered_graph, k=3, iterations=50, seed=42)
            
        # Apply zoom and pan
        self.apply_zoom_pan()
        
        # Prepare edge collection for better performance
        edge_pos = []
        edge_colors = []
        edge_widths = []
        
        if self.filtered_graph.number_of_edges() > 0:
            weights = [data['weight'] for _, _, data in self.filtered_graph.edges(data=True)]
            max_weight = max(weights)
            
            for u, v, data in self.filtered_graph.edges(data=True):
                x1, y1 = self.pos[u]
                x2, y2 = self.pos[v]
                edge_pos.append([(x1, y1), (x2, y2)])
                
                # Color based on call frequency
                normalized_weight = data['weight'] / max_weight
                edge_colors.append((0.7, 0.7, 0.7, 0.3 + 0.5 * normalized_weight))
                edge_widths.append(0.5 + 4 * normalized_weight)
                
            # Draw all edges at once
            edge_collection = LineCollection(edge_pos, colors=edge_colors, 
                                           linewidths=edge_widths, zorder=1)
            self.ax.add_collection(edge_collection)
            
        # Draw nodes
        self.draw_nodes()
        
        # Add labels for significant connections
        self.add_smart_labels()
        
        # Set title and clean up
        title = f"Phone Network - {len(self.filtered_graph.nodes())} nodes, {len(self.filtered_graph.edges())} connections"
        self.ax.set_title(title, fontsize=14, pad=10)
        self.ax.axis('off')
        
        # Add legend
        self.add_legend()
        
        # Set margins
        self.ax.set_xlim(-1.2, 1.2)
        self.ax.set_ylim(-1.2, 1.2)
        
        self.canvas.draw()
        
    def calculate_layout_gpu(self):
        """Calculate graph layout using GPU acceleration"""
        try:
            import cupy as cp
            
            n_nodes = self.filtered_graph.number_of_nodes()
            node_list = list(self.filtered_graph.nodes())
            node_idx = {node: i for i, node in enumerate(node_list)}
            
            # Initialize positions randomly
            pos_array = cp.random.rand(n_nodes, 2) * 2 - 1
            
            # Create adjacency matrix
            adj_matrix = cp.zeros((n_nodes, n_nodes))
            for u, v in self.filtered_graph.edges():
                i, j = node_idx[u], node_idx[v]
                adj_matrix[i, j] = 1
                adj_matrix[j, i] = 1
                
            # Force-directed layout on GPU
            for _ in range(50):
                forces = cp.zeros_like(pos_array)
                
                # Repulsive forces
                for i in range(n_nodes):
                    diff = pos_array[i] - pos_array
                    dist = cp.sqrt(cp.sum(diff ** 2, axis=1))
                    dist[dist == 0] = 1
                    repulsion = diff / (dist[:, cp.newaxis] ** 2)
                    forces[i] = cp.sum(repulsion, axis=0)
                    
                # Attractive forces
                for i in range(n_nodes):
                    neighbors = cp.where(adj_matrix[i] > 0)[0]
                    if len(neighbors) > 0:
                        diff = pos_array[neighbors] - pos_array[i]
                        attraction = cp.sum(diff, axis=0) * 0.1
                        forces[i] += attraction
                        
                # Update positions
                pos_array += forces * 0.01
                
                # Keep within bounds
                pos_array = cp.clip(pos_array, -1, 1)
                
            # Convert back to CPU and dictionary
            pos_cpu = pos_array.get()
            return {node: pos_cpu[i] for node, i in node_idx.items()}
            
        except Exception as e:
            print(f"GPU layout failed, falling back to CPU: {e}")
            return nx.spring_layout(self.filtered_graph, k=3, iterations=50)
            
    def draw_nodes(self):
        """Draw nodes with different styles for phones and persons"""
        # Separate nodes by type
        person_nodes = []
        phone_nodes = []
        orphan_phones = []
        
        # Get all phones assigned to persons
        assigned_phones = set()
        for person in self.persons.values():
            assigned_phones.update(person.phone_numbers)
            
        for node in self.filtered_graph.nodes():
            if node in assigned_phones:
                # Find which person(s) this phone belongs to
                for person_id, person in self.persons.items():
                    if node in person.phone_numbers:
                        person_nodes.append((node, person))
                        break
            else:
                orphan_phones.append(node)
                
        # Draw person-associated phones
        if person_nodes and self.current_filters.get('show_persons', True):
            x_coords = [self.pos[node][0] for node, _ in person_nodes]
            y_coords = [self.pos[node][1] for node, _ in person_nodes]
            
            scatter = self.ax.scatter(x_coords, y_coords, s=300, c='lightblue', 
                                    alpha=0.8, edgecolors='navy', linewidth=2, zorder=3)
                                    
            # Add person labels
            for (node, person) in person_nodes:
                x, y = self.pos[node]
                self.ax.annotate(f"{person.name}\n{node}", (x, y), 
                               ha='center', va='center', fontsize=8,
                               bbox=dict(boxstyle="round,pad=0.3", 
                                       facecolor='white', alpha=0.8))
                                       
        # Draw orphan phones
        if orphan_phones and self.current_filters.get('show_orphan_phones', True):
            x_coords = [self.pos[node][0] for node in orphan_phones]
            y_coords = [self.pos[node][1] for node in orphan_phones]
            
            self.ax.scatter(x_coords, y_coords, s=200, c='lightgray', 
                          alpha=0.6, edgecolors='black', linewidth=1, zorder=2)
                          
            # Add labels for top orphan phones
            node_degrees = [(node, self.filtered_graph.degree(node)) for node in orphan_phones]
            top_orphans = sorted(node_degrees, key=lambda x: x[1], reverse=True)[:20]
            
            for node, degree in top_orphans:
                if degree > 2:  # Only label well-connected nodes
                    x, y = self.pos[node]
                    self.ax.annotate(node, (x, y), ha='center', va='center', 
                                   fontsize=7, alpha=0.7)
                                   
    def add_smart_labels(self):
        """Add labels for significant connections only"""
        if self.filtered_graph.number_of_edges() == 0:
            return
            
        # Get top edges by weight
        edges_by_weight = sorted(self.filtered_graph.edges(data=True), 
                               key=lambda x: x[2]['weight'], reverse=True)
                               
        # Limit labels to prevent clutter
        max_labels = min(20, len(edges_by_weight) // 5)
        
        for i, (u, v, data) in enumerate(edges_by_weight[:max_labels]):
            # Calculate label position
            x1, y1 = self.pos[u]
            x2, y2 = self.pos[v]
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            
            # Create compact label
            label = f"{data['call_count']} calls"
            if data.get('avg_duration'):
                label += f"\n{data['avg_duration']}"
                
            self.ax.annotate(label, (mid_x, mid_y), ha='center', va='center',
                           fontsize=7, color='darkred',
                           bbox=dict(boxstyle="round,pad=0.2", 
                                   facecolor='yellow', alpha=0.6))
                                   
    def add_legend(self):
        """Add a legend to the graph"""
        legend_elements = []
        
        if self.current_filters.get('show_persons', True):
            legend_elements.append(patches.Patch(color='lightblue', label='Person-linked Phone'))
            
        if self.current_filters.get('show_orphan_phones', True):
            legend_elements.append(patches.Patch(color='lightgray', label='Unassigned Phone'))
            
        if legend_elements:
            self.ax.legend(handles=legend_elements, loc='upper right', fontsize=9)
            
    def apply_zoom_pan(self):
        """Apply zoom and pan to node positions"""
        for node in self.pos:
            x, y = self.pos[node]
            # Apply zoom
            x *= self.zoom_factor
            y *= self.zoom_factor
            # Apply pan
            x += self.pan_offset[0]
            y += self.pan_offset[1]
            self.pos[node] = (x, y)
            
    def on_scroll(self, event):
        """Handle mouse scroll for zooming"""
        if event.inaxes != self.ax:
            return
            
        # Zoom in or out
        zoom_speed = 0.1
        if event.button == 'up':
            self.zoom_factor *= (1 + zoom_speed)
        else:
            self.zoom_factor *= (1 - zoom_speed)
            
        # Limit zoom
        self.zoom_factor = max(0.1, min(10, self.zoom_factor))
        
        self.update_graph()
        
    def on_click(self, event):
        """Handle mouse clicks"""
        if event.inaxes != self.ax:
            return
            
        if event.button == 1:  # Left click
            # Start dragging for pan
            self.drag_start = (event.xdata, event.ydata)
            self.drag_start_offset = self.pan_offset.copy()
            
    def on_motion(self, event):
        """Handle mouse motion"""
        if hasattr(self, 'drag_start') and event.inaxes == self.ax:
            # Calculate pan offset
            dx = event.xdata - self.drag_start[0]
            dy = event.ydata - self.drag_start[1]
            self.pan_offset[0] = self.drag_start_offset[0] + dx
            self.pan_offset[1] = self.drag_start_offset[1] + dy
            self.update_graph()
            
    def on_release(self, event):
        """Handle mouse release"""
        if hasattr(self, 'drag_start'):
            del self.drag_start
            del self.drag_start_offset
            
    def reset_layout(self):
        """Reset zoom and layout"""
        self.zoom_factor = 1.0
        self.pan_offset = [0, 0]
        
        if hasattr(self, 'filtered_graph') and self.filtered_graph.number_of_nodes() > 0:
            # Recalculate layout
            if self.use_gpu and CUDA_AVAILABLE and self.filtered_graph.number_of_nodes() > 100:
                self.pos = self.calculate_layout_gpu()
            else:
                self.pos = nx.spring_layout(self.filtered_graph, k=3, iterations=50, seed=42)
                
            self.update_graph()
            
    def update_detail_view(self):
        """Update the detail view treeview"""
        # Clear existing items
        for item in self.detail_tree.get_children():
            self.detail_tree.delete(item)
            
        if not hasattr(self, 'filtered_graph') or self.filtered_graph.number_of_edges() == 0:
            return
            
        # Add edge information
        edges_info = []
        for u, v, data in self.filtered_graph.edges(data=True):
            # Get person names if available
            u_display = u
            v_display = v
            
            for person in self.persons.values():
                if u in person.phone_numbers:
                    u_display = f"{person.name} ({u})"
                if v in person.phone_numbers:
                    v_display = f"{person.name} ({v})"
                    
            edges_info.append({
                'connection': f"{u_display} ↔ {v_display}",
                'caller': u_display,
                'receiver': v_display,
                'count': data['call_count'],
                'first': data.get('first_call', data['date_range'].split(' - ')[0]),
                'last': data.get('last_call', data['date_range'].split(' - ')[1]),
                'avg_duration': data.get('avg_duration', 'N/A')
            })
            
        # Sort by call count
        edges_info.sort(key=lambda x: x['count'], reverse=True)
        
        # Add to treeview
        for info in edges_info:
            self.detail_tree.insert('', 'end', text=info['connection'],
                                  values=(info['caller'], info['receiver'], 
                                         info['count'], info['first'], 
                                         info['last'], info['avg_duration']))
                                         
    def open_person_manager(self):
        """Open the person management dialog, ensuring only one instance is open."""
        # Check if the window already exists and is open
        if self.person_manager_window and self.person_manager_window.winfo_exists():
            self.person_manager_window.lift()  # Bring the existing window to the front
            return

        # Get all unique phones
        all_phones = set()
        if not self.call_data.empty:
            all_phones = set(self.call_data['caller'].unique()) | set(self.call_data['receiver'].unique())

        # Create the new dialog
        dialog = PersonManagementDialog(self.root, self.persons, all_phones)
        self.person_manager_window = dialog  # Store the reference

        # Make the dialog modal and always on top
        dialog.transient(self.root)  # Associate with the main window
        dialog.grab_set()            # Direct all events to this window

        # The wait_window call will pause execution here until the dialog is closed
        self.root.wait_window(dialog)

        # After the window is closed, refresh the main graph display
        if hasattr(self, 'filtered_graph'):
            self.update_graph()
            self.update_detail_view()
            
    def show_statistics(self):
        """Show detailed statistics"""
        if self.call_data.empty:
            messagebox.showinfo("Statistics", "No data loaded")
            return
            
        # Calculate statistics
        total_calls = len(self.call_data)
        unique_phones = len(set(self.call_data['caller'].unique()) | set(self.call_data['receiver'].unique()))
        
        if hasattr(self, 'filtered_data') and not self.filtered_data.empty:
            filtered_calls = len(self.filtered_data)
            date_range = f"{self.filtered_data['timestamp'].min()} to {self.filtered_data['timestamp'].max()}"
        else:
            filtered_calls = total_calls
            date_range = f"{self.call_data['timestamp'].min()} to {self.call_data['timestamp'].max()}"
            
        persons_count = len(self.persons)
        assigned_phones = sum(len(p.phone_numbers) for p in self.persons.values())
        
        stats_text = f"""Call Data Statistics:

Total Records: {total_calls:,}
Filtered Records: {filtered_calls:,}
Unique Phone Numbers: {unique_phones:,}
Date Range: {date_range}

Person Management:
Total Persons: {persons_count}
Assigned Phones: {assigned_phones}
Unassigned Phones: {unique_phones - assigned_phones}

Graph Statistics:
Current Nodes: {len(self.filtered_graph.nodes()) if hasattr(self, 'filtered_graph') else 0}
Current Edges: {len(self.filtered_graph.edges()) if hasattr(self, 'filtered_graph') else 0}
"""
        
        messagebox.showinfo("Statistics", stats_text)
        
    def export_to_pdf(self):
        """Prompts for page size and exports the current view to PDF."""
        if not hasattr(self, 'filtered_graph') or self.filtered_graph.number_of_nodes() == 0:
            messagebox.showwarning("Warning", "No data to export")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Save PDF Report"
        )
        
        if not file_path:
            return

        # --- Prompt for Page Size ---
        dialog = PageSizeDialog(self.root)
        self.root.wait_window(dialog)
        choice = dialog.result

        if not choice:
            return # User cancelled the dialog

        # Import necessary libraries here
        from reportlab.lib.pagesizes import letter, A4, landscape
        from svglib.svglib import svg2rlg

        try:
            # --- Create Drawing Object (needed for all options) ---
            temp_svg = tempfile.NamedTemporaryFile(suffix='.svg', delete=False, mode='w', encoding='utf-8')
            self.fig.savefig(temp_svg.name, format='svg', bbox_inches='tight')
            temp_svg.close()
            drawing = svg2rlg(temp_svg.name)
            
            # --- Determine Page Size Based on Choice ---
            pagesize = None
            if choice == 'letter':
                pagesize = landscape(letter)
            elif choice == 'a4':
                pagesize = landscape(A4)
            elif choice == 'native':
                # For native, size the page to the chart plus margins
                native_width = drawing.width + (2 * inch)
                # Increased vertical space to 3.5 inches to ensure header fits
                native_height = drawing.height + (3.5 * inch)
                pagesize = (native_width, native_height)

            # Create the PDF document with the chosen page size
            doc = SimpleDocTemplate(file_path, pagesize=pagesize)
            story = []

            # --- Add Title and Stats ---
            styles = getSampleStyleSheet()
            story.append(Paragraph("Phone Call Network Analysis Report", styles['Title']))
            story.append(Spacer(1, 12))
            story.append(Paragraph(f"""
            <para>
            <b>Analysis Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>
            <b>Total Nodes:</b> {len(self.filtered_graph.nodes())}<br/>
            <b>Total Connections:</b> {len(self.filtered_graph.edges())}<br/>
            <b>Filter Applied:</b> {self.status_var.get()}<br/>
            </para>
            """, styles['Normal']))
            story.append(Spacer(1, 24))

            # --- Scale Drawing (if not native) ---
            if choice != 'native':
                available_width = doc.width
                available_height = doc.height
                if drawing.width > 0 and drawing.height > 0:
                    scale_factor = min(available_width / drawing.width, available_height / drawing.height)
                    drawing.scale(scale_factor, scale_factor)
                    drawing.width = drawing.width * scale_factor
                    drawing.height = drawing.height * scale_factor
            
            story.append(drawing)
            doc.build(story)
            os.unlink(temp_svg.name) # Clean up
            
            messagebox.showinfo("Success", f"PDF exported to {file_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")
            
    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown()


def main():
    """Main entry point"""
    try:
        # Enable high DPI support on Windows
        if os.name == 'nt':
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    root = tk.Tk()
    
    # Set icon if available
    try:
        if os.path.exists('icon.ico'):
            root.iconbitmap('icon.ico')
    except:
        pass
        
    app = EnhancedPhoneLinkChartApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()