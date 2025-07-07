# This file will contain functions for setting up the UI.

import tkinter as tk
from tkinter import ttk
from src.constants import COLORS
from src.utils import darken_color

class UISetup:
    def __init__(self, app):
        self.app = app

    def setup_styles(self):
        """Configure modern ttk styles"""
        style = ttk.Style()
        
        # Configure button style
        style.configure(
            "Modern.TButton",
            font=("Segoe UI", 10),
            padding=(15, 8)
        )
        
        # Configure frame style
        style.configure(
            "Modern.TFrame",
            background=COLORS['surface']
        )
        
        # Configure label style
        style.configure(
            "Modern.TLabel",
            font=("Segoe UI", 10),
            background=COLORS['surface'],
            foreground=COLORS['text_primary']
        )
        
        # Configure entry style
        style.configure(
            "Modern.TEntry",
            font=("Segoe UI", 10),
            fieldbackground=COLORS['surface']
        )

    def setup_ui(self):
        # Create main container
        main_container = ttk.Frame(self.app.root, style="Modern.TFrame")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header section
        header_frame = ttk.Frame(main_container, style="Modern.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Title
        title_label = ttk.Label(header_frame, text="People Connection Visualizer", 
                               font=("Segoe UI", 20, "bold"), 
                               foreground=COLORS['primary'], 
                               style="Modern.TLabel")
        title_label.pack(side=tk.LEFT)
        
        # Toolbar with modern buttons
        toolbar = ttk.Frame(main_container, style="Modern.TFrame")
        toolbar.pack(fill=tk.X, pady=(0, 15))
          # Create modern buttons with icons        
        self.create_modern_button(toolbar, "👤 Add Person", self.app.add_person, COLORS['primary'])
        self.create_modern_button(toolbar, "❌ Delete Person", self.app.delete_person, COLORS['danger'])
        self.create_modern_button(toolbar, "💾 Save Project", self.app.save_data, COLORS['accent'])
        self.create_modern_button(toolbar, "📁 Load Project", self.app.load_data, COLORS['accent'])
        self.create_modern_button(toolbar, "🖼️ Export PNG", self.app.export_to_png, COLORS['secondary'])
        self.create_modern_button(toolbar, "🔄 Check Updates", self.app.check_for_updates, COLORS['accent'])
        self.create_modern_button(toolbar, "🗑️ Clear All", self.app.clear_all, COLORS['danger'])
        
        # Canvas container with modern styling
        canvas_frame = ttk.Frame(main_container, style="Modern.TFrame")
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
          # Modern canvas with gradient-like background
        self.app.canvas = tk.Canvas(canvas_frame, 
                               bg='#f8fafc', 
                               highlightthickness=0,
                               relief=tk.FLAT,
                               bd=0)
        self.app.canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Initialize fixed scroll region for consistent canvas size
        self.app.fixed_canvas_width = 2800
        self.app.fixed_canvas_height = 1800
          # Add subtle grid pattern to canvas
        self.app.canvas_helpers.add_grid_pattern()
        
        # Bind events
        self.app.canvas.bind("<Button-1>", self.app.events.on_canvas_click)
        self.app.canvas.bind("<B1-Motion>", self.app.events.on_canvas_drag)
        self.app.canvas.bind("<ButtonRelease-1>", self.app.events.on_canvas_release)
        self.app.canvas.bind("<Button-3>", self.app.events.on_right_click)
        self.app.canvas.bind("<Motion>", self.app.events.on_mouse_move)
        self.app.canvas.bind("<Double-Button-1>", self.app.events.on_double_click)
        self.app.canvas.bind("<Button-2>", self.app.events.on_middle_button_press)
        self.app.canvas.bind("<B2-Motion>", self.app.events.on_middle_button_motion)
        self.app.canvas.bind("<ButtonRelease-2>", self.app.events.on_middle_button_release)
        # Bind mouse wheel for zoom control
        self.app.canvas.bind("<MouseWheel>", self.app.events.on_mouse_wheel)
        # Make canvas focusable and bind keys
        self.app.canvas.configure(highlightthickness=1, highlightcolor=COLORS['primary'])
        self.app.canvas.bind("<Key-Escape>", self.app.events.on_escape_key)
        self.app.canvas.bind("<Key-Delete>", self.app.events.on_delete_key)
        self.app.canvas.bind("<Key-BackSpace>", self.app.events.on_delete_key)
        self.app.canvas.bind("<Key-c>", self.app.events.on_color_cycle_key)
        self.app.root.bind("<Key-Escape>", self.app.events.on_escape_key)
        self.app.root.bind("<Key-Delete>", self.app.events.on_delete_key)
        self.app.root.bind("<Key-BackSpace>", self.app.events.on_delete_key)
        self.app.root.bind("<Key-c>", self.app.events.on_color_cycle_key)
          # Modern instructions panel
        self.create_instructions_panel(main_container)
        
        # Status bar
        self.app.status_frame = ttk.Frame(main_container, style="Modern.TFrame")
        self.app.status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.app.status_label = ttk.Label(self.app.status_frame, 
                                    text="Ready - Right-click a person to start linking",
                                    font=("Segoe UI", 9),
                                    foreground=COLORS['text_secondary'],
                                    style="Modern.TLabel")
        self.app.status_label.pack(side=tk.LEFT)
        
        # --- Zoom slider ---
        self.app.zoom_var = tk.DoubleVar(value=1.0)
        self.app.zoom_slider = ttk.Scale(
            self.app.status_frame,
            from_=0.5, to=1.0, orient=tk.HORIZONTAL,
            variable=self.app.zoom_var,
            command=self.app.events.on_zoom,
            length=150
        )
        self.app.zoom_slider.pack(side=tk.RIGHT, padx=(0, 10))
        self.app.zoom_label = ttk.Label(self.app.status_frame, text="Zoom", style="Modern.TLabel")
        self.app.zoom_label.pack(side=tk.RIGHT)
        
        # Bind canvas resize event
        self.app.canvas.bind('<Configure>', self.app.events.on_canvas_resize)
        
        # Set the initial scroll region
        self.app.canvas.configure(scrollregion=(0, 0, self.app.fixed_canvas_width, self.app.fixed_canvas_height))

    def create_modern_button(self, parent, text, command, color):
        """Create a modern styled button"""
        btn = tk.Button(parent, 
                       text=text,
                       command=command,
                       font=("Segoe UI", 10, "bold"),
                       bg=color,
                       fg='white',
                       relief=tk.FLAT,
                       padx=20,
                       pady=10,
                       cursor='hand2',
                       border=0)
        
        def on_enter(e):
            btn.configure(bg=darken_color(color))
        
        def on_leave(e):
            btn.configure(bg=color)
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.pack(side=tk.LEFT, padx=(0, 10))
        return btn

    def create_instructions_panel(self, parent):
        """Create a modern instructions panel"""
        instructions_frame = ttk.Frame(parent, style="Modern.TFrame")
        instructions_frame.pack(fill=tk.X, pady=(10, 0))
        
        instructions = [
            "🖱️ Left-click to select and move people",
            "🔗 Right-click to link: first person, then target", 
            "✏️ Double-click on a person to edit their information",
            "⌨️ Press 'C' to cycle selected person's color",
            "❌ Press Delete to remove selected person or connection",
            "🚫 Press Escape to cancel an active connection"
        ]
        
        for i, instruction in enumerate(instructions):
            label = ttk.Label(instructions_frame, 
                            text=instruction,
                            font=("Segoe UI", 9),
                            foreground=COLORS['text_secondary'],
                            style="Modern.TLabel")
            label.pack(side=tk.LEFT, padx=(0, 20) if i < len(instructions)-1 else (0, 0))
