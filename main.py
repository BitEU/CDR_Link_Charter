import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import csv
import math
from datetime import datetime, timedelta
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

# Import from supporting modules
from src.constants import COLORS, CARD_COLORS
from src.models import PhoneNode
from src.dialogs import PhoneDialog, ConnectionLabelDialog, VersionUpdateDialog, NoUpdateDialog
from src.utils import setup_logging, darken_color
from src.ui_setup import UISetup
from src.event_handlers import EventHandlers
from src.data_management import DataManagement
from src.canvas_helpers import CanvasHelpers

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)


class CDRVisualizerApp:
    def __init__(self, root):
        logger.info("Initializing CDRVisualizerApp")
        self.root = root
        self.root.title("CDR Visualizer - COMRADE")
        self.root.geometry("1400x900")
        self.root.configure(bg=COLORS['background'])
        
        # Data structures
        self.phone_nodes = {}  # {phone_number: PhoneNode}
        self.node_widgets = {}  # {phone_number: canvas_item_ids}
        self.connection_lines = {}  # {(phone1, phone2): (line_id, label_id)}
        self.original_font_sizes = {}  # {canvas_item_id: original_font_size}
        self.call_data = defaultdict(lambda: defaultdict(list))  # {phone1: {phone2: [call_records]}}
        
        self.selected_phone = None
        self.selected_connection = None
        self.dragging = False
        self.drag_data = {"x": 0, "y": 0}
        self.connecting = False
        self.connection_start = None
        self.temp_line = None
        
        # Initialize helpers
        self.events = EventHandlers(self)
        self.data = DataManagement(self)
        self.canvas_helpers = CanvasHelpers(self)

        logger.info("Setting up UI")
        self.ui = UISetup(self)
        self.ui.setup_styles()
        self.ui.setup_ui()
        
        # Clean up old extracted files on startup
        self.data.cleanup_old_files()
        
        # Check for updates automatically on startup
        self.root.after(2000, self.data.check_for_updates_silently)
        
        logger.info("CDRVisualizerApp initialized successfully")
    
    def import_cdr_csv(self):
        """Import CDR data from CSV file"""
        filename = filedialog.askopenfilename(
            title="Select CDR CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not filename:
            return
            
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records_processed = 0
                new_phones = set()
                
                for row in reader:
                    # Extract data from CSV row
                    target_number = row.get('Target Number', '').strip()
                    direction = row.get('Call Direction', '').strip()
                    from_to_number = row.get('From or To Number', '').strip()
                    date = row.get('Date', '').strip()
                    start_time = row.get('Start', '').strip()
                    end_time = row.get('End', '').strip()
                    
                    if not all([target_number, from_to_number, date, start_time, end_time]):
                        continue
                    
                    # Calculate call duration
                    try:
                        start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M:%S")
                        end_dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M:%S")
                        duration = (end_dt - start_dt).total_seconds()
                    except ValueError:
                        continue
                    
                    # Create phone nodes if they don't exist
                    if target_number not in self.phone_nodes:
                        self.phone_nodes[target_number] = PhoneNode(target_number)
                        new_phones.add(target_number)
                    
                    if from_to_number not in self.phone_nodes:
                        self.phone_nodes[from_to_number] = PhoneNode(from_to_number)
                        new_phones.add(from_to_number)
                    
                    # Store call data
                    call_record = {
                        'date': date,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': duration,
                        'direction': direction
                    }
                    
                    # Store bidirectionally for easier lookup
                    self.call_data[target_number][from_to_number].append(call_record)
                    self.call_data[from_to_number][target_number].append(call_record)
                    
                    records_processed += 1
                
                # Position new nodes
                self._position_new_nodes(new_phones)
                
                # Create widgets for new nodes
                for phone in new_phones:
                    self.canvas_helpers.create_phone_widget(phone)
                
                # Update connections
                self.canvas_helpers.update_connections()
                
                messagebox.showinfo("Import Complete", 
                    f"Successfully imported {records_processed} call records\n"
                    f"Added {len(new_phones)} new phone numbers")
                
        except Exception as e:
            logger.error(f"Error importing CDR CSV: {e}")
            messagebox.showerror("Import Error", f"Failed to import CSV: {str(e)}")
    
    def _position_new_nodes(self, new_phones):
        """Position new phone nodes in a grid layout"""
        # Use existing nodes to determine starting position
        existing_count = len(self.phone_nodes) - len(new_phones)
        
        cols = 3
        col_width = 300
        row_height = 150
        start_x = 200
        start_y = 120
        
        for i, phone in enumerate(new_phones):
            index = existing_count + i
            row = index // cols
            col = index % cols
            
            self.phone_nodes[phone].x = start_x + col * col_width
            self.phone_nodes[phone].y = start_y + row * row_height
    
    def add_phone(self):
        """Manually add a phone number"""
        dialog = PhoneDialog(self.root, "Add Phone Number")
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            phone_number = dialog.result['phone_number']
            alias = dialog.result.get('alias', '')
            
            if phone_number in self.phone_nodes:
                messagebox.showwarning("Duplicate", "This phone number already exists")
                return
            
            # Create new phone node
            phone_node = PhoneNode(phone_number, alias)
            
            # Position it
            cols = 3
            col_width = 300
            row_height = 150
            start_x = 200
            start_y = 120
            index = len(self.phone_nodes)
            row = index // cols
            col = index % cols
            phone_node.x = start_x + col * col_width
            phone_node.y = start_y + row * row_height
            
            self.phone_nodes[phone_number] = phone_node
            self.canvas_helpers.create_phone_widget(phone_number)
    
    def delete_phone(self):
        """Delete the currently selected phone"""
        if self.events.selected_phone is None:
            messagebox.showwarning("No Selection", "Please select a phone to delete by clicking on it first.")
            return
            
        phone_number = self.events.selected_phone
        phone_node = self.phone_nodes[phone_number]
        
        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Deletion", 
            f"Are you sure you want to delete '{phone_number}'?\n\nThis will also remove all call records for this number.",
            icon='warning'
        )
        
        if not result:
            return
            
        logger.info(f"Deleting phone {phone_number}")
        
        # Remove all connections involving this phone
        connections_to_remove = []
        for other_phone in self.call_data[phone_number].keys():
            connection_key = tuple(sorted([phone_number, other_phone]))
            connections_to_remove.append(connection_key)
        
        # Remove connection lines from canvas
        for connection_key in connections_to_remove:
            if connection_key in self.connection_lines:
                elements = self.connection_lines[connection_key]
                for element in elements:
                    self.canvas.delete(element)
                    if element in self.original_font_sizes:
                        del self.original_font_sizes[element]
                del self.connection_lines[connection_key]
        
        # Remove phone widget from canvas
        if phone_number in self.node_widgets:
            widget_items = self.node_widgets[phone_number]
            for item in widget_items:
                self.canvas.delete(item)
                if item in self.original_font_sizes:
                    del self.original_font_sizes[item]
            del self.node_widgets[phone_number]
        
        # Remove from data structures
        del self.phone_nodes[phone_number]
        if phone_number in self.call_data:
            del self.call_data[phone_number]
        
        # Remove from other phones' call data
        for phone in self.call_data:
            if phone_number in self.call_data[phone]:
                del self.call_data[phone][phone_number]
        
        # Clear selection
        self.events.selected_phone = None
        
        logger.info(f"Successfully deleted phone {phone_number}")
        self.update_status(f"🗑️ Deleted '{phone_number}' and its call records")
        
        # Update canvas
        self.canvas.update()
    
    def clear_all(self):
        """Clear all data and reset the canvas"""
        self.data.clear_all()
    
    def update_status(self, message, duration=5000):
        """Update the status bar with a message"""
        self.status_label.config(text=message)
        if hasattr(self, "status_timer") and self.status_timer:
            self.root.after_cancel(self.status_timer)
        self.status_timer = self.root.after(duration, self.clear_status)
    
    def clear_status(self):
        """Clear the status bar message"""
        self.status_label.config(text="Ready - Import CDR data to begin")
        self.status_timer = None
    
    def refresh_phone_widget(self, phone_number):
        """Refresh a phone's widget on the canvas"""
        if hasattr(self.events, '_zooming') and self.events._zooming:
            return
            
        logger.info(f"Refreshing widget for phone {phone_number}")
        
        # Remove the old widget from the canvas
        if phone_number in self.node_widgets:
            for item in self.node_widgets[phone_number]:
                self.canvas.delete(item)
            del self.node_widgets[phone_number]
        
        # Re-create the widget with the current zoom level
        zoom = self.events.last_zoom
        self.canvas_helpers.create_phone_widget(phone_number, zoom)
        
        # Redraw connections
        self.canvas_helpers.update_connections()
        logger.info(f"Widget for phone {phone_number} refreshed")
    
    def draw_connection(self, phone1, phone2, label, zoom):
        """Delegate to canvas_helpers"""
        self.canvas_helpers.draw_connection(phone1, phone2, label, zoom)
    
    # Data management methods delegated
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
        app = CDRVisualizerApp(root)
        root.mainloop()
    except Exception as e:
        logger.critical(f"Unhandled exception in main loop: {e}", exc_info=True)
        messagebox.showerror("Fatal Error", f"A critical error occurred: {e}")