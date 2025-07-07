import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import csv
import math
from datetime import datetime
import os
from collections import defaultdict
import logging
import zipfile
import shutil
import tempfile
import json
import urllib.request
import urllib.error
import threading
from functools import lru_cache

# Try to import PIL for PNG export functionality
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Import from supporting modules
from src.constants import COLORS, CARD_COLORS
from src.models import Person
from src.dialogs import PersonDialog, ConnectionLabelDialog, VersionUpdateDialog, NoUpdateDialog
from src.utils import setup_logging, darken_color
from src.ui_setup import UISetup
from src.event_handlers import EventHandlers
from src.data_management import DataManagement
from src.canvas_helpers import CanvasHelpers

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)



class ConnectionApp:
    def __init__(self, root):
        logger.info("Initializing ConnectionApp")
        self.root = root
        self.root.title("COMRADE")
        self.root.geometry("1400x900")
        self.root.configure(bg=COLORS['background'])
        
        # Data structures
        self.people = {}  # {id: Person}
        self.person_widgets = {}  # {id: canvas_item_id}
        self.connection_lines = {}  # {(id1, id2): (line_id, label_id)}
        self.original_font_sizes = {}  # {canvas_item_id: original_font_size} for proper text scaling
        self.original_image_sizes = {}  # {canvas_item_id: (original_width, original_height)} for proper image scaling
        self.image_cache = {}  # {(file_path, width, height): PhotoImage} for caching resized images
        
        # Optimized image caching for zoom performance
        self.scaled_image_cache = {}  # {(image_path, scale_factor): PhotoImage}
        self.base_image_cache = {}   # {image_path: PIL.Image} - original PIL images
        self.current_scale = 1.0     # Track current zoom level
        self.max_cache_size = 50     # Limit cache size to prevent memory issues
        self.zoom_debounce_timer = None  # Timer for debouncing zoom events
        
        self.selected_person = None
        self.selected_connection = None  # Track selected connection for editing/deletion
        self.dragging = False
        self.drag_data = {"x": 0, "y": 0}
        self.connecting = False
        self.connection_start = None
        self.temp_line = None
        self.next_id = 1
        
        # Initialize helpers first, as UI setup depends on them
        self.events = EventHandlers(self)
        self.data = DataManagement(self)
        self.canvas_helpers = CanvasHelpers(self)

        logger.info("Setting up UI")
        self.ui = UISetup(self)
        self.ui.setup_styles()
        self.ui.setup_ui()
        
        # Clean up old extracted files on startup
        self.data.cleanup_old_files()
        
        # Check for updates automatically on startup (with a delay to let UI load)
        self.root.after(2000, self.data.check_for_updates_silently)  # 2 second delay
        
        logger.info("ConnectionApp initialized successfully")
    
    def refresh_person_widget(self, person_id):
        """Refresh a person's widget on the canvas"""
        # Don't refresh during zoom operations to avoid double-scaling
        if hasattr(self.events, '_zooming') and self.events._zooming:
            return
            
        logger.info(f"Refreshing widget for person {person_id}")
        
        # Remove the old widget from the canvas
        if person_id in self.person_widgets:
            for item in self.person_widgets[person_id]:
                self.canvas.delete(item)
            del self.person_widgets[person_id]
        
        # Re-create the widget with the current zoom level
        zoom = self.events.last_zoom
        self.canvas_helpers.create_person_widget(person_id, zoom)
        
        # Redraw connections to ensure they are correctly positioned
        self.canvas_helpers.update_connections()
        logger.info(f"Widget for person {person_id} refreshed")

    def add_person(self):
        logger.info("Add person button clicked")
        dialog = PersonDialog(self.root, "Add Person")
        self.root.wait_window(dialog.dialog)  # Wait for dialog to close
        logger.info(f"Dialog result: {dialog.result}")
        if dialog.result:
            # Extract files separately since Person.__init__ doesn't accept it
            files = dialog.result.pop('files', [])
            person = Person(**dialog.result)
            person.files = files  # Set files after creation
            person_id = self.next_id
            self.next_id += 1
            logger.info(f"Creating person with ID {person_id}: {person.name}")
            
            # Position using box layout
            cols = 2
            col_width = 400
            row_height = 200
            start_x = 200
            start_y = 120
            row = (len(self.people)) // cols
            col = (len(self.people)) % cols
            person.x = start_x + col * col_width
            person.y = start_y + row * row_height
            logger.info(f"Positioned person at ({person.x}, {person.y})")
            
            self.people[person_id] = person
            logger.info(f"Added person to data structure. Total people: {len(self.people)}")
            self.canvas_helpers.create_person_widget(person_id)
            logger.info(f"Created widget for person {person_id}")
        else:
            logger.info("Dialog was cancelled")
            
    def delete_person(self):
        """Delete the currently selected person"""
        if self.events.selected_person is None:
            messagebox.showwarning("No Selection", "Please select a person to delete by clicking on them first.")
            return
            
        person_id = self.events.selected_person
        person = self.people[person_id]
        
        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Deletion", 
            f"Are you sure you want to delete '{person.name}'?\n\nThis will also remove all their connections.",
            icon='warning'
        )
        
        if not result:
            return
            
        logger.info(f"Deleting person {person_id}: {person.name}")
        
        # Remove all connections involving this person
        connections_to_remove = []
        for other_id in list(person.connections.keys()):
            if other_id in self.people:
                # Remove the connection from the other person's connections
                if person_id in self.people[other_id].connections:
                    del self.people[other_id].connections[person_id]
                
                # Track connection lines to remove
                connection_key = (min(person_id, other_id), max(person_id, other_id))
                connections_to_remove.append(connection_key)
        
        # Remove connection lines from canvas
        for connection_key in connections_to_remove:
            if connection_key in self.connection_lines:
                elements = self.connection_lines[connection_key]
                for element in elements:
                    self.canvas.delete(element)
                    # Clean up font size tracking for text items
                    if element in self.original_font_sizes:
                        del self.original_font_sizes[element]
                del self.connection_lines[connection_key]
        
        # Remove person widget from canvas
        if person_id in self.person_widgets:
            widget_items = self.person_widgets[person_id]
            for item in widget_items:
                self.canvas.delete(item)
                # Clean up tracking dictionaries
                if item in self.original_font_sizes:
                    del self.original_font_sizes[item]
                if item in self.original_image_sizes:
                    del self.original_image_sizes[item]
            del self.person_widgets[person_id]
        
        # Remove from people dictionary
        del self.people[person_id]
        
        # Clear selection
        self.events.selected_person = None
        
        logger.info(f"Successfully deleted person {person_id}")
        self.update_status(f"🗑️ Deleted '{person.name}' and their connections")
        
        # Update canvas
        self.canvas.update()
            
    def clear_all(self):
        """Clear all people, connections, and reset the canvas"""
        self.data.clear_all()

    def update_status(self, message, duration=5000):
        """Update the status bar with a message that disappears after a duration"""
        self.status_label.config(text=message)
        # If a timer is already running, cancel it
        if hasattr(self, "status_timer") and self.status_timer:
            self.root.after_cancel(self.status_timer)
        # Set a new timer to clear the message
        self.status_timer = self.root.after(duration, self.clear_status)

    def clear_status(self):
        """Clear the status bar message"""
        self.status_label.config(text="Ready - Right-click a person to start linking")
        self.status_timer = None

    def draw_connection(self, id1, id2, label, zoom):
        """Delegate to canvas_helpers"""
        self.canvas_helpers.draw_connection(id1, id2, label, zoom)

    # All data management methods are now in DataManagement class
    def save_data(self):
        self.data.save_data()

    def load_data(self):
        self.data.load_data()

    def export_to_png(self):
        self.data.export_to_png()

    def check_for_updates(self, silent=False):
        self.data.check_for_updates(silent)

    def check_for_updates_silently(self):
        self.data.check_for_updates_silently()

    def cleanup_old_files(self):
        self.data.cleanup_old_files()

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = ConnectionApp(root)
        root.mainloop()
    except Exception as e:
        logger.critical(f"Unhandled exception in main loop: {e}", exc_info=True)
        messagebox.showerror("Fatal Error", f"A critical error occurred: {e}")