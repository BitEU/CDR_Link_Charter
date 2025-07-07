from datetime import datetime
from src.constants import COLORS, CARD_COLORS
from src.dialogs import ConnectionLabelDialog, PhoneDialog
from tkinter import messagebox

# This file will contain event handling logic.

class EventHandlers:
    def __init__(self, app):
        self.app = app
        self.dragging = False
        self.drag_data = {"x": 0, "y": 0}
        self.connecting = False
        self.connection_start = None
        self.temp_line = None
        self.selected_phone = None
        self.selected_connection = None
        self.last_zoom = 1.0
        self.zoom_debounce_timer = None
        self._panning = False
        self.current_hover = None
        self._last_mouse_move_time = 0
        self._pending_color_refresh = None

    def on_zoom(self, value):
        # Scale the canvas content based on the zoom value
        try:
            zoom = float(value)
        except ValueError:
            zoom = 1.0
        
        # Avoid unnecessary work if zoom hasn't changed significantly
        if abs(zoom - self.last_zoom) < 0.01:
            return
        
        # Store previous zoom for efficient scaling
        prev_zoom = self.last_zoom
        
        # Use single canvas.scale operation for better performance
        scale_factor = zoom / prev_zoom
        self.app.canvas.scale("all", 0, 0, scale_factor, scale_factor)
        self.last_zoom = zoom
        
        # Keep the scroll region fixed to maintain consistent canvas size
        self.app.canvas.configure(scrollregion=(0, 0, self.app.fixed_canvas_width, self.app.fixed_canvas_height))
        
        # Batch UI updates for better performance
        self.debounced_zoom_update(zoom)

    def debounced_zoom_update(self, zoom):
        """Perform expensive zoom operations with debouncing"""
        # Cancel previous timer if it exists
        if self.zoom_debounce_timer:
            self.app.root.after_cancel(self.zoom_debounce_timer)
        
        # Schedule the expensive operations after a short delay
        self.zoom_debounce_timer = self.app.root.after(50, lambda: self._perform_zoom_update(zoom))
    
    def _perform_zoom_update(self, zoom):
        """Perform the actual expensive zoom update operations"""
        self.app.canvas_helpers.rescale_text(zoom)
        self.app.canvas_helpers.update_connections()
        self.app.canvas_helpers.redraw_grid()
        self.zoom_debounce_timer = None

    def on_canvas_resize(self, event):
        self.app.canvas_helpers.redraw_grid()

    def on_canvas_click(self, event):
        # Account for zoom in hit detection
        zoom = self.last_zoom
        # Make tolerance proportional to zoom level
        tolerance = max(3, int(10 * (1/zoom))) # Increase tolerance as we zoom out
        
        # Convert screen coordinates to canvas coordinates to handle scrolled content
        canvas_x = self.app.canvas.canvasx(event.x)
        canvas_y = self.app.canvas.canvasy(event.y)
        
        # Use canvas coordinates for hit detection
        items = self.app.canvas.find_overlapping(canvas_x - tolerance, canvas_y - tolerance, canvas_x + tolerance, canvas_y + tolerance)
        
        # Always clear selections on a new click
        self.clear_connection_selection()
        self.selected_phone = None
        self.dragging = False

        if not items:
            return

        # Iterate from topmost to bottommost item
        for item in reversed(items):
            tags = self.app.canvas.gettags(item)

            # Check for connection label first
            if any(t.startswith("connection_label_") or t.startswith("connection_clickable_") for t in tags):
                for tag in tags:
                    if tag.startswith("connection_label_") or tag.startswith("connection_clickable_"):
                        parts = tag.split("_")
                        if len(parts) >= 4:
                            try:
                                phone1 = "_".join(parts[2:-1])  # Handle phone numbers with underscores
                                phone2 = parts[-1]
                                self.selected_connection = tuple(sorted([phone1, phone2]))
                                self.highlight_connection_selection()
                                self.app.canvas.focus_set()
                                return  # Exit after handling the click
                            except ValueError:
                                continue
            
            # If not a connection, check for a phone
            if any("phone" in tag for tag in tags):
                for tag in tags:
                    if tag.startswith("phone_") and tag != "phone":
                        phone_number = tag[6:]  # Remove "phone_" prefix
                        self.selected_phone = phone_number
                        self.drag_data = {"x": canvas_x, "y": canvas_y}
                        self.dragging = True
                        return # Exit after handling the click

    def on_canvas_drag(self, event):
        if self.dragging and self.selected_phone:
            zoom = self.last_zoom
            
            # Convert screen coordinates to canvas coordinates
            canvas_x = self.app.canvas.canvasx(event.x)
            canvas_y = self.app.canvas.canvasy(event.y)
            
            # Calculate the movement delta in canvas coordinates
            dx_canvas = canvas_x - self.drag_data["x"]
            dy_canvas = canvas_y - self.drag_data["y"]
            
            # Convert canvas delta to world delta (compensate for zoom)
            dx_world = dx_canvas / zoom
            dy_world = dy_canvas / zoom
            
            # Update logical (unscaled) position using world delta
            self.app.phone_nodes[self.selected_phone].x += dx_world
            self.app.phone_nodes[self.selected_phone].y += dy_world

            # Move existing canvas items directly during drag (much more efficient)
            phone_items = self.app.node_widgets[self.selected_phone]
            for item in phone_items:
                self.app.canvas.move(item, dx_canvas, dy_canvas)

            # Update connections immediately (but efficiently)
            self.app.canvas_helpers.update_connections()
            # Update drag data for next movement
            self.drag_data = {"x": canvas_x, "y": canvas_y}

    def on_canvas_release(self, event):
        if self.dragging and self.selected_phone:
            self.dragging = False
            
            # Don't refresh the widget - it's already at the correct position and scale
            # Only refresh if there was a pending color change
            if self._pending_color_refresh:
                self.app.root.after(50, lambda: self.app.refresh_phone_widget(self._pending_color_refresh))
                self._pending_color_refresh = None
        else:
            self.dragging = False
    
    def on_double_click(self, event):
        """Handle double-click events for editing connections"""
        # Convert screen coordinates to canvas coordinates
        canvas_x = self.app.canvas.canvasx(event.x)
        canvas_y = self.app.canvas.canvasy(event.y)
        
        items = self.app.canvas.find_closest(canvas_x, canvas_y)
        if not items:
            return
             
        clicked = items[0]
        tags = self.app.canvas.gettags(clicked)
        
        # Check if double-clicked on a connection label
        for tag in tags:
            if tag.startswith("connection_label_") or tag.startswith("connection_clickable_"):
                # Extract connection IDs from tag
                parts = tag.split("_")
                if len(parts) >= 4:
                    try:
                        phone1 = "_".join(parts[2:-1])  # Handle phone numbers with underscores
                        phone2 = parts[-1]
                        self.selected_connection = tuple(sorted([phone1, phone2]))
                        self.edit_connection_label()
                        break
                    except ValueError:
                        # Not a valid connection tag, skip
                        continue
    
    def on_mouse_move(self, event):
        if self.dragging:
            return
             
        current_time = datetime.now().timestamp()
        if self._last_mouse_move_time:
            if current_time - self._last_mouse_move_time < 0.02:  # 50 FPS max
                return
        self._last_mouse_move_time = current_time
        
        tolerance = 5  # pixels
        
        canvas_x = self.app.canvas.canvasx(event.x)
        canvas_y = self.app.canvas.canvasy(event.y)
        
        items = self.app.canvas.find_overlapping(canvas_x - tolerance, canvas_y - tolerance, 
                                           canvas_x + tolerance, canvas_y + tolerance)
        
        phone_number = None
        for item in items:
            tags = self.app.canvas.gettags(item)
            if any("phone" in tag for tag in tags):
                for tag in tags:
                    if tag.startswith("phone_") and tag != "phone":
                        phone_number = tag[6:]  # Remove "phone_" prefix
                        break
                if phone_number is not None:
                    break
        
        if phone_number is not None:
            if not self.connecting or (self.connecting and phone_number != self.connection_start):
                if self.current_hover != phone_number:
                    pass
                if self.current_hover != phone_number:
                    self.app.canvas.configure(cursor="hand2")
                    self.current_hover = phone_number
        else:
            if self.current_hover:
                self.app.canvas.configure(cursor="")
                self.current_hover = None
        
        if self.connecting and self.temp_line and self.connection_start:
            p = self.app.phone_nodes[self.connection_start]
            zoom = self.last_zoom
            start_x, start_y = p.x * zoom, p.y * zoom
            canvas_x = self.app.canvas.canvasx(event.x)
            canvas_y = self.app.canvas.canvasy(event.y)
            self.app.canvas.coords(self.temp_line, start_x, start_y, canvas_x, canvas_y)
            
            if phone_number is not None and phone_number != self.connection_start:
                self.app.canvas.itemconfig(self.temp_line, fill=COLORS['success'], width=4)
            else:
                self.app.canvas.itemconfig(self.temp_line, fill=COLORS['accent'], width=3)
    
    def on_right_click(self, event):
        """Improved right-click linking with more forgiving detection"""
        tolerance = 10
        
        canvas_x = self.app.canvas.canvasx(event.x)
        canvas_y = self.app.canvas.canvasy(event.y)
        
        items = self.app.canvas.find_overlapping(canvas_x - tolerance, canvas_y - tolerance, 
                                           canvas_x + tolerance, canvas_y + tolerance)
        phone_number = None
        for item in items:
            tags = self.app.canvas.gettags(item)
            if any("phone" in tag for tag in tags):
                for tag in tags:
                    if tag.startswith("phone_") and tag != "phone":
                        phone_number = tag[6:]  # Remove "phone_" prefix
                        break
                if phone_number is not None:
                    break
        if phone_number is None:
            self.cancel_connection()
            return

        if not self.connecting:
            self.start_connection(phone_number, canvas_x, canvas_y)
        elif self.connection_start == phone_number:
            self.cancel_connection()
        else:
            self.complete_connection(phone_number)
    
    def on_escape_key(self, event):
        """Handle escape key to cancel connections"""
        if self.connecting:
            self.cancel_connection()
            self.app.update_status("Action cancelled with Escape key")
    
    def on_delete_key(self, event):
        """Handle delete key to remove selected connection or phone"""
        if self.selected_connection:
            self.delete_connection()
        elif self.selected_phone:
            self.app.delete_phone()
    
    def on_color_cycle_key(self, event):
        """Handle 'c' key to cycle colors of selected phone"""
        if self.selected_phone:
            phone_node = self.app.phone_nodes[self.selected_phone]
            phone_node.color = (phone_node.color + 1) % len(CARD_COLORS)
            
            if not self.dragging:
                self.app.refresh_phone_widget(self.selected_phone)
                self.app.update_status(f"Changed {phone_node.phone_number}'s color")
            else:
                self.app.update_status(f"Color will be updated for {phone_node.phone_number} after drag")
                self._pending_color_refresh = self.selected_phone

    def on_middle_button_press(self, event):
        self.app.canvas.scan_mark(event.x, event.y)
        self._panning = True

    def on_middle_button_motion(self, event):
        if self._panning:
            self.app.canvas.scan_dragto(event.x, event.y, gain=1)

    def on_middle_button_release(self, event):
        self._panning = False

    def on_mouse_wheel(self, event):
        """Handle mouse wheel events to change the zoom slider"""
        current_zoom = self.app.zoom_var.get()
        zoom_step = 0.05
        new_zoom = min(current_zoom + zoom_step, 1.0) if event.delta > 0 else max(current_zoom - zoom_step, 0.5)
        self.app.zoom_var.set(new_zoom)
        self.on_zoom(new_zoom)

    def start_connection(self, phone_number, x, y):
        """Start drawing a connection line from a phone"""
        self.connecting = True
        self.connection_start = phone_number
        p1 = self.app.phone_nodes[phone_number]
        zoom = self.last_zoom
        start_x, start_y = p1.x * zoom, p1.y * zoom
        self.temp_line = self.app.canvas.create_line(start_x, start_y, x, y, fill=COLORS['accent'], width=3, dash=(4, 4))
        self.app.update_status(f"🔗 Adding note from {p1.phone_number}... Right-click another phone to link, or right-click again to cancel.")
        self.app.canvas_helpers.highlight_phone_for_connection(phone_number)

    def complete_connection(self, phone_number):
        """Complete a connection between two phones with optional notes"""
        if not self.connecting or self.connection_start is None:
            return
            
        phone1 = self.connection_start
        phone2 = phone_number
        
        # Avoid self-connection
        if phone1 == phone2:
            self.cancel_connection()
            return
        
        # Ask for a label/note for the connection (optional)
        dialog = ConnectionLabelDialog(self.app.root, "Add Connection Note (Optional)")
        self.app.root.wait_window(dialog.dialog)
        
        # If there's no call data between these phones, create empty structure
        if phone1 not in self.app.call_data:
            self.app.call_data[phone1] = {}
        if phone2 not in self.app.call_data[phone1]:
            self.app.call_data[phone1][phone2] = []
        
        if phone2 not in self.app.call_data:
            self.app.call_data[phone2] = {}
        if phone1 not in self.app.call_data[phone2]:
            self.app.call_data[phone2][phone1] = []
        
        # Add manual note if provided
        if dialog.result:
            # Store as a special "manual note" entry
            manual_note = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'start_time': '',
                'end_time': '',
                'duration': 0,
                'direction': 'Manual Note',
                'note': dialog.result
            }
            self.app.call_data[phone1][phone2].append(manual_note)
            self.app.call_data[phone2][phone1].append(manual_note)
        
        # Update connections
        self.app.canvas_helpers.update_connections()
        
        # Clean up
        self.cancel_connection()
        self.app.update_status(f"✅ Connection updated between {phone1} and {phone2}")

    def cancel_connection(self):
        """Cancel the connection drawing process"""
        if self.temp_line:
            self.app.canvas.delete(self.temp_line)
            self.temp_line = None
        if self.connection_start:
            self.app.canvas_helpers.unhighlight_phone_for_connection(self.connection_start)
        self.connecting = False
        self.connection_start = None
        self.app.update_status("Ready")

    def edit_phone(self, phone_number):
        """Handle editing a phone's alias via a dialog."""
        if phone_number in self.app.phone_nodes:
            phone_node = self.app.phone_nodes[phone_number]
            
            # Use a dialog to get updated information
            dialog = PhoneDialog(self.app.root, 
                                "Edit Phone Alias", 
                                phone_number=phone_node.phone_number,
                                alias=phone_node.alias)
            self.app.root.wait_window(dialog.dialog)
            
            if dialog.result:
                # Update phone data (only alias can be changed)
                phone_node.alias = dialog.result['alias']
                
                # Refresh the specific phone's widget on the canvas
                self.app.refresh_phone_widget(phone_number)
                self.app.update_status(f"Updated alias for {phone_node.phone_number}")

    def edit_connection_label(self):
        """Edit the note of the selected connection"""
        if not self.selected_connection:
            return
            
        phone1, phone2 = self.selected_connection
        
        # Find existing manual note if any
        current_note = ""
        if phone1 in self.app.call_data and phone2 in self.app.call_data[phone1]:
            for record in self.app.call_data[phone1][phone2]:
                if record.get('direction') == 'Manual Note':
                    current_note = record.get('note', '')
                    break
        
        dialog = ConnectionLabelDialog(self.app.root, "Edit Connection Note", initial_value=current_note)
        self.app.root.wait_window(dialog.dialog)
        
        if dialog.result is not None:
            # Remove old manual note if exists
            if phone1 in self.app.call_data and phone2 in self.app.call_data[phone1]:
                self.app.call_data[phone1][phone2] = [r for r in self.app.call_data[phone1][phone2] if r.get('direction') != 'Manual Note']
                self.app.call_data[phone2][phone1] = [r for r in self.app.call_data[phone2][phone1] if r.get('direction') != 'Manual Note']
            
            # Add new manual note if not empty
            if dialog.result:
                manual_note = {
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'start_time': '',
                    'end_time': '',
                    'duration': 0,
                    'direction': 'Manual Note',
                    'note': dialog.result
                }
                
                if phone1 not in self.app.call_data:
                    self.app.call_data[phone1] = {}
                if phone2 not in self.app.call_data[phone1]:
                    self.app.call_data[phone1][phone2] = []
                
                if phone2 not in self.app.call_data:
                    self.app.call_data[phone2] = {}
                if phone1 not in self.app.call_data[phone2]:
                    self.app.call_data[phone2][phone1] = []
                
                self.app.call_data[phone1][phone2].append(manual_note)
                self.app.call_data[phone2][phone1].append(manual_note)
            
            self.app.canvas_helpers.update_connections()
            self.app.update_status(f"Connection note updated for {phone1} and {phone2}")
        
        self.clear_connection_selection()

    def delete_connection(self):
        """Delete the currently selected connection"""
        if not self.selected_connection:
            messagebox.showwarning("No Selection", "Please select a connection to delete.")
            return
            
        phone1, phone2 = self.selected_connection
        
        result = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete the connection between {phone1} and {phone2}?\n\nThis will remove all call records and notes between these numbers.",
            icon='warning'
        )
        
        if result:
            # Remove from data structures
            if phone1 in self.app.call_data and phone2 in self.app.call_data[phone1]:
                del self.app.call_data[phone1][phone2]
            if phone2 in self.app.call_data and phone1 in self.app.call_data[phone2]:
                del self.app.call_data[phone2][phone1]
            
            # Remove from canvas
            connection_key = tuple(sorted([phone1, phone2]))
            if connection_key in self.app.connection_lines:
                line_id, label_id, clickable_area_id, bg_rect_id = self.app.connection_lines.pop(connection_key)
                self.app.canvas.delete(line_id)
                if label_id:
                    self.app.canvas.delete(label_id)
                if bg_rect_id:
                    self.app.canvas.delete(bg_rect_id)
                self.app.canvas.delete(clickable_area_id)
            
            self.selected_connection = None
            self.app.update_status(f"🗑️ Connection between {phone1} and {phone2} deleted")

    def highlight_connection_selection(self):
        """Highlight the selected connection on the canvas"""
        if not self.selected_connection:
            return
        
        if self.selected_connection in self.app.connection_lines:
            line_id, label_id, _, bg_rect_id = self.app.connection_lines[self.selected_connection]
            self.app.canvas.itemconfig(line_id, fill=COLORS['primary'], width=4)
            if label_id and bg_rect_id:
                self.app.canvas.itemconfig(bg_rect_id, outline=COLORS['primary'], width=2)

    def clear_connection_selection(self):
        """Clear any existing connection selection highlight"""
        if not self.selected_connection:
            return
            
        if self.selected_connection in self.app.connection_lines:
            line_id, label_id, _, bg_rect_id = self.app.connection_lines[self.selected_connection]
            self.app.canvas.itemconfig(line_id, fill=COLORS['text_secondary'], width=2)
            if label_id and bg_rect_id:
                self.app.canvas.itemconfig(bg_rect_id, outline=COLORS['border'])

        self.selected_connection = None