import tkinter as tk
import os
from functools import lru_cache
import logging
from datetime import datetime

from src.constants import COLORS, CARD_COLORS

logger = logging.getLogger(__name__)

class CanvasHelpers:
    def __init__(self, app):
        self.app = app

    def store_text_font_size(self, item_id, font_tuple):
        """Store the original font size for a text item."""
        if item_id not in self.app.original_font_sizes:
            self.app.original_font_sizes[item_id] = font_tuple[1]

    def rescale_text(self, zoom):
        # Rescale all text items on the canvas based on their original font sizes
        text_items = [item for item in self.app.canvas.find_all() if self.app.canvas.type(item) == 'text']
        
        for item in text_items:
            if item not in self.app.original_font_sizes:
                current_font = self.app.canvas.itemcget(item, 'font')
                parts = current_font.split()
                base_size = next((int(p) for p in parts if p.isdigit()), 10)
                self.app.original_font_sizes[item] = base_size
            
            original_size = self.app.original_font_sizes[item]
            new_size = max(6, int(original_size * zoom))
            
            current_font = self.app.canvas.itemcget(item, 'font')
            parts = current_font.split()
            
            if len(parts) >= 2:
                size_index = next((i for i, p in enumerate(parts) if p.isdigit()), -1)
                if size_index != -1:
                    parts[size_index] = str(new_size)
                    new_font = ' '.join(parts)
                else:
                    new_font = f"Segoe UI {new_size}"
            else:
                new_font = f"Segoe UI {new_size}"
            
            self.app.canvas.itemconfig(item, font=new_font)

    def redraw_grid(self):
        self.app.canvas.delete("grid")
        width = self.app.fixed_canvas_width
        height = self.app.fixed_canvas_height
        grid_size = 40 * (self.app.events.last_zoom if hasattr(self.app.events, 'last_zoom') else 1)
        
        min_grid_spacing = 20
        if grid_size < min_grid_spacing:
            grid_size = min_grid_spacing
        
        x_step = max(int(grid_size), 40)
        for x in range(0, int(width + x_step), x_step):
            self.app.canvas.create_line(x, 0, x, height, fill='#e2e8f0', width=1, tags="grid")
        
        y_step = max(int(grid_size), 40)
        for y in range(0, int(height + y_step), y_step):
            self.app.canvas.create_line(0, y, width, y, fill='#e2e8f0', width=1, tags="grid")
        
        self.app.canvas.tag_lower("grid")

    def update_connections(self):
        """Redraw all connection lines based on current phone positions and zoom"""
        zoom = self.app.events.last_zoom
        
        # Clear all existing lines and labels first
        for key, elements in list(self.app.connection_lines.items()):
            for element in elements:
                self.app.canvas.delete(element)
                if element in self.app.original_font_sizes:
                    del self.app.original_font_sizes[element]

        self.app.connection_lines.clear()

        # Redraw all connections based on call data
        drawn_connections = set()
        
        for phone1, connections in self.app.call_data.items():
            for phone2, call_records in connections.items():
                if not call_records or phone1 == phone2:
                    continue
                
                # Ensure we only draw each connection once
                connection_key = tuple(sorted([phone1, phone2]))
                if connection_key in drawn_connections:
                    continue
                drawn_connections.add(connection_key)
                
                # Calculate connection statistics
                stats = self._calculate_connection_stats(call_records)
                label = self._format_connection_label(stats)
                
                # Draw the connection
                if phone1 in self.app.phone_nodes and phone2 in self.app.phone_nodes:
                    self.draw_connection(phone1, phone2, label, zoom)

    def _calculate_connection_stats(self, call_records):
        """Calculate statistics for a set of call records"""
        if not call_records:
            return None
        
        total_calls = len(call_records)
        total_duration = sum(record['duration'] for record in call_records)
        avg_duration = total_duration / total_calls if total_calls > 0 else 0
        
        # Find date range
        dates = [record['date'] for record in call_records]
        min_date = min(dates)
        max_date = max(dates)
        
        return {
            'total_calls': total_calls,
            'avg_duration': avg_duration,
            'date_range': (min_date, max_date)
        }

    def _format_connection_label(self, stats):
        """Format connection statistics into a label"""
        if not stats:
            return ""
        
        # Format average duration
        avg_mins = int(stats['avg_duration'] // 60)
        avg_secs = int(stats['avg_duration'] % 60)
        avg_duration_str = f"{avg_mins}m {avg_secs}s"
        
        # Format date range
        min_date, max_date = stats['date_range']
        if min_date == max_date:
            date_str = min_date
        else:
            # Shorten date format for readability
            min_parts = min_date.split('-')
            max_parts = max_date.split('-')
            if min_parts[0] == max_parts[0]:  # Same year
                date_str = f"{min_parts[1]}/{min_parts[2]}-{max_parts[1]}/{max_parts[2]}/{max_parts[0]}"
            else:
                date_str = f"{min_date} to {max_date}"
        
        return f"{stats['total_calls']} calls\nAvg: {avg_duration_str}\n{date_str}"

    def draw_connection(self, phone1, phone2, label, zoom=1.0):
        """Draw a single connection line and its label, scaled by zoom"""
        p1 = self.app.phone_nodes[phone1]
        p2 = self.app.phone_nodes[phone2]
        
        # Get scaled coordinates
        x1, y1 = p1.x * zoom, p1.y * zoom
        x2, y2 = p2.x * zoom, p2.y * zoom
        
        # Determine line thickness based on call volume
        if phone1 in self.app.call_data and phone2 in self.app.call_data[phone1]:
            call_count = len(self.app.call_data[phone1][phone2])
            # Scale line width: 2-8 pixels based on call volume
            line_width = min(2 + (call_count // 10), 8)
        else:
            line_width = 2
        
        # Create the main line
        line = self.app.canvas.create_line(
            x1, y1, x2, y2, 
            fill=COLORS['text_secondary'], 
            width=line_width, 
            tags=("connection", f"connection_{phone1}_{phone2}")
        )
        
        # Create a thicker, transparent line for easier clicking
        clickable_area = self.app.canvas.create_line(
            x1, y1, x2, y2, 
            fill="", 
            width=max(10, line_width + 8), 
            tags=("connection_clickable", f"connection_clickable_{phone1}_{phone2}")
        )
        
        label_id = None
        bg_rect_id = None
        if label:
            # Calculate midpoint for the label
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            
            # Create the text label
            font_size = max(8, int(9 * zoom))
            label_font = ("Segoe UI", font_size)
            
            label_id = self.app.canvas.create_text(
                mid_x, mid_y, 
                text=label, 
                font=label_font, 
                fill=COLORS['text_primary'],
                justify=tk.CENTER,
                tags=("connection_label", f"connection_label_{phone1}_{phone2}")
            )
            
            # Get bounding box of the text to create a background
            bbox = self.app.canvas.bbox(label_id)
            if bbox:
                # Create a rectangle behind the text with padding
                x1_bbox, y1_bbox, x2_bbox, y2_bbox = bbox
                padding = 5 * zoom
                bg_rect_id = self.app.canvas.create_rectangle(
                    x1_bbox - padding, y1_bbox - padding, 
                    x2_bbox + padding, y2_bbox + padding, 
                    fill=COLORS['surface'], 
                    outline='#e0e0e0', 
                    width=1,
                    tags=(f"connection_label_bg_{phone1}_{phone2}",)
                )

            # Store original font size for scaling
            if label_id:
                self.store_text_font_size(label_id, ("Segoe UI", 9))

        # Store all parts of the connection
        connection_key = tuple(sorted([phone1, phone2]))
        self.app.connection_lines[connection_key] = (line, label_id, clickable_area, bg_rect_id)
        
        # Ensure proper layering
        self.app.canvas.tag_lower("grid")
        self.app.canvas.tag_lower(line)
        if clickable_area:
            self.app.canvas.tag_lower(clickable_area)

        if bg_rect_id:
            self.app.canvas.tag_lower(bg_rect_id, line)
            self.app.canvas.tag_raise(bg_rect_id)
        if label_id:
            self.app.canvas.tag_lower(label_id, line)
            self.app.canvas.tag_raise(label_id)
        
        if bg_rect_id and label_id:
            self.app.canvas.tag_raise(label_id, bg_rect_id)

        # Ensure phone widgets are on top of lines
        self.app.canvas.tag_raise("phone")
    
    def add_grid_pattern(self):
        canvas_width = self.app.fixed_canvas_width
        canvas_height = self.app.fixed_canvas_height
        grid_size = 40
        
        for x in range(0, canvas_width, grid_size):
            self.app.canvas.create_line(x, 0, x, canvas_height, fill='#e2e8f0', width=1, tags="grid")
        
        for y in range(0, canvas_height, grid_size):
            self.app.canvas.create_line(0, y, canvas_width, y, fill='#e2e8f0', width=1, tags="grid")
        
        self.app.canvas.tag_lower("grid")

    def create_phone_widget(self, phone_number, zoom=None):
        if self.app.events.dragging:
            logger.warning(f"Attempted to create widget for phone {phone_number} during drag - skipping")
            return
            
        logger.info(f"Creating widget for phone {phone_number}")
        phone_node = self.app.phone_nodes[phone_number]
        if zoom is None:
            zoom = self.app.events.last_zoom if hasattr(self.app.events, 'last_zoom') else 1.0

        x = phone_node.x * zoom
        y = phone_node.y * zoom
        
        group = []
        
        # Calculate total calls and duration for this phone
        total_calls = 0
        total_duration = 0
        unique_contacts = set()
        
        if phone_number in self.app.call_data:
            for other_phone, records in self.app.call_data[phone_number].items():
                total_calls += len(records)
                total_duration += sum(r['duration'] for r in records)
                unique_contacts.add(other_phone)
        
        # Format duration
        hours = int(total_duration // 3600)
        minutes = int((total_duration % 3600) // 60)
        duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        
        # Prepare display text
        display_lines = [
            f"📱 {phone_number}",
            f"Alias: {phone_node.alias}" if phone_node.alias else "",
            f"Calls: {total_calls}",
            f"Duration: {duration_str}",
            f"Contacts: {len(unique_contacts)}"
        ]
        display_lines = [line for line in display_lines if line]
        
        # Calculate card dimensions
        base_width = max(max(len(line) for line in display_lines) * 8 if display_lines else 0, 180)
        card_width = base_width * zoom
        card_height = max(len(display_lines) * 20 + 40, 100) * zoom
        
        half_width = card_width // 2
        half_height = card_height // 2
        
        # Draw shadow
        shadow_offset = int(3 * zoom)
        for i in range(3, 0, -1):
            shadow_color = '#e0e0e0' if i == 3 else ('#d0d0d0' if i == 2 else '#c0c0c0')
            shadow = self.app.canvas.create_rectangle(
                x - half_width + i, y - half_height + i,
                x + half_width + i, y + half_height + i,
                fill=shadow_color, outline='', width=0,
                tags=(f"phone_{phone_number}", "phone", "shadow")
            )
            group.append(shadow)

        phone_color = CARD_COLORS[phone_node.color % len(CARD_COLORS)]
        
        # Main card
        main_card = self.app.canvas.create_rectangle(
            x - half_width, y - half_height, x + half_width, y + half_height,
            fill=COLORS['surface'], outline=phone_color, width=2,
            tags=(f"phone_{phone_number}", "phone")
        )
        group.append(main_card)
        
        # Header
        header_height = int(30 * zoom)
        header = self.app.canvas.create_rectangle(
            x - half_width, y - half_height, x + half_width, y - half_height + header_height,
            fill=phone_color, outline='', width=0,
            tags=(f"phone_{phone_number}", "phone")
        )
        group.append(header)
        
        # Phone icon and number in header
        phone_icon = self.app.canvas.create_text(
            x - half_width + int(15 * zoom), y - half_height + int(15 * zoom),
            text="📱", font=("Arial", int(12 * zoom)), fill='white',
            tags=(f"phone_{phone_number}", "phone")
        )
        self.store_text_font_size(phone_icon, ("Arial", 12))
        group.append(phone_icon)
        
        phone_text = self.app.canvas.create_text(
            x - half_width + int(35 * zoom), y - half_height + int(15 * zoom),
            text=phone_number, anchor="w", font=("Segoe UI", int(10 * zoom), "bold"), 
            fill='white',
            tags=(f"phone_{phone_number}", "phone")
        )
        self.store_text_font_size(phone_text, ("Segoe UI", 10, "bold"))
        group.append(phone_text)
        
        # Details
        details_start_y = y - half_height + header_height + int(10 * zoom)
        line_height = int(18 * zoom)
        
        current_y = details_start_y
        text_x = x - half_width + int(15 * zoom)
        
        # Skip the phone number in details since it's in the header
        for i, line in enumerate(display_lines[1:]):  # Skip first line (phone number)
            text_item = self.app.canvas.create_text(
                text_x, current_y, text=line, anchor="nw", 
                font=("Segoe UI", int(9 * zoom)),
                fill=COLORS['text_primary'], 
                tags=(f"phone_{phone_number}", "phone")
            )
            self.store_text_font_size(text_item, ("Segoe UI", 9))
            group.append(text_item)
            current_y += line_height
        
        self.app.node_widgets[phone_number] = group
        
        # Bind double-click for editing
        for item in group:
            self.app.canvas.tag_bind(item, "<Double-Button-1>", 
                lambda e, pn=phone_number: self.app.events.edit_phone(pn))
        
        self.add_hover_effects(phone_number, group)
        logger.info(f"Widget creation complete for phone {phone_number}")

    def add_hover_effects(self, phone_number, group):
        def on_enter(event):
            if self.app.events.connecting and self.app.events.connection_start == phone_number:
                return
            for item in group:
                if 'shadow' not in self.app.canvas.gettags(item):
                    if self.app.canvas.type(item) == 'rectangle':
                        self.app.canvas.itemconfig(item, outline=COLORS['primary'], width=3)
        
        def on_leave(event):
            if self.app.events.connecting and self.app.events.connection_start == phone_number:
                return
            phone_node = self.app.phone_nodes[phone_number]
            phone_color = CARD_COLORS[phone_node.color % len(CARD_COLORS)]
            for item in group:
                if 'shadow' not in self.app.canvas.gettags(item):
                    if self.app.canvas.type(item) == 'rectangle':
                        self.app.canvas.itemconfig(item, outline=phone_color, width=2)

        for item in group:
            self.app.canvas.tag_bind(item, "<Enter>", on_enter)
            self.app.canvas.tag_bind(item, "<Leave>", on_leave)

    def highlight_phone_for_connection(self, phone_number):
        group = self.app.node_widgets.get(phone_number, [])
        phone_color = CARD_COLORS[self.app.phone_nodes[phone_number].color % len(CARD_COLORS)]
        
        for item in group:
            tags = self.app.canvas.gettags(item)
            if 'shadow' in tags:
                continue
            
            item_type = self.app.canvas.type(item)
            if item_type == 'rectangle':
                # Header
                if self.app.canvas.itemcget(item, 'fill') == phone_color:
                     self.app.canvas.itemconfig(item, fill=COLORS['accent'])
                # Main card
                else:
                     self.app.canvas.itemconfig(item, fill=COLORS['surface_bright'])

    def unhighlight_phone_for_connection(self, phone_number):
        group = self.app.node_widgets.get(phone_number, [])
        phone_node = self.app.phone_nodes[phone_number]
        phone_color = CARD_COLORS[phone_node.color % len(CARD_COLORS)]

        for item in group:
            tags = self.app.canvas.gettags(item)
            if 'shadow' in tags:
                continue

            item_type = self.app.canvas.type(item)
            if item_type == 'rectangle':
                # Header
                if self.app.canvas.itemcget(item, 'fill') == COLORS['accent']:
                    self.app.canvas.itemconfig(item, fill=phone_color)
                # Main card
                else:
                    self.app.canvas.itemconfig(item, fill=COLORS['surface'])

    def rescale_images(self, zoom):
        """No images in CDR visualization, but keeping method for compatibility"""
        pass