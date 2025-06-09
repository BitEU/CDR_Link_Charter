import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import json
import os
import tempfile

# Check for required packages and provide helpful error messages
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
    try:
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg as FigureCanvasTkinter
    except ImportError:
        from matplotlib.backends.backend_tkagg import FigureCanvasTkinter
    from matplotlib.figure import Figure
    import matplotlib.patches as patches
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

if missing_packages:
    print("Missing required packages. Please install them using:")
    print(f"pip install {' '.join(missing_packages)}")
    input("Press Enter to exit...")
    exit(1)

class PhoneLinkChartApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Phone Call Link Chart Analyzer")
        self.root.geometry("1200x800")
        
        # Data storage
        self.call_data = pd.DataFrame()
        self.graph = nx.Graph()
        self.people = {}  # phone -> person name mapping
        self.edge_notes = {}  # edge -> note mapping
        self.pos = {}  # node positions
        self.dragging = None
        self.drag_offset = (0, 0)
        
        # GUI Setup
        self.setup_gui()
        
        # Load sample data if available
        self.load_sample_data()
        
    def setup_gui(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top button bar - simple and clean
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Left side buttons
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side=tk.LEFT)
        
        ttk.Button(left_buttons, text="📁 Load CSV", 
                  command=self.load_csv_file).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(left_buttons, text="👤 Add Person", 
                  command=self.add_person_mode).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(left_buttons, text="📝 Add Description", 
                  command=self.add_description_mode).pack(side=tk.LEFT, padx=(0, 5))
        
        # Right side buttons
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side=tk.RIGHT)
        
        ttk.Button(right_buttons, text="🔄 Reset Layout", 
                  command=self.reset_layout).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(right_buttons, text="📄 Export PDF", 
                  command=self.export_to_pdf).pack(side=tk.LEFT)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready - Load CSV data to begin")
        status_label = ttk.Label(button_frame, textvariable=self.status_var, 
                                foreground="blue", font=("Arial", 9))
        status_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Graph area
        graph_frame = ttk.Frame(main_frame)
        graph_frame.pack(fill=tk.BOTH, expand=True)
        
        # Matplotlib figure
        self.fig = Figure(figsize=(12, 8), dpi=100, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        self.canvas = FigureCanvasTkinter(self.fig, graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Bind mouse events for interaction
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        
        # Mode tracking
        self.mode = "normal"  # normal, add_person, add_description
        
    def load_sample_data(self):
        """Load the sample CSV data"""
        try:
            self.call_data = pd.read_csv('cdr_sample.csv')
            self.call_data['timestamp'] = pd.to_datetime(self.call_data['timestamp'])
            self.process_call_data()
            self.update_graph()
            self.status_var.set(f"Loaded {len(self.call_data)} call records from sample data")
        except Exception as e:
            print(f"Could not load sample data: {e}")
    
    def load_csv_file(self):
        """Load CSV file with call data"""
        file_path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.call_data = pd.read_csv(file_path)
                
                # Validate required columns
                required_cols = ['caller', 'receiver', 'timestamp']
                if not all(col in self.call_data.columns for col in required_cols):
                    messagebox.showerror("Error", f"CSV must contain columns: {', '.join(required_cols)}")
                    return
                
                self.call_data['timestamp'] = pd.to_datetime(self.call_data['timestamp'])
                self.process_call_data()
                self.update_graph()
                self.status_var.set(f"Loaded {len(self.call_data)} call records")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load CSV: {str(e)}")
    
    def process_call_data(self):
        """Process call data to create graph"""
        if self.call_data.empty:
            return
        
        self.graph.clear()
        
        # Add all unique phone numbers as nodes
        phones = set(self.call_data['caller'].unique()) | set(self.call_data['receiver'].unique())
        self.graph.add_nodes_from(phones)
        
        # Calculate call statistics for each phone pair
        call_stats = {}
        
        for _, row in self.call_data.iterrows():
            caller, receiver = row['caller'], row['receiver']
            
            # Create undirected edge key (sort to avoid duplicates)
            edge_key = tuple(sorted([caller, receiver]))
            
            if edge_key not in call_stats:
                call_stats[edge_key] = {
                    'count': 0,
                    'dates': []
                }
            
            call_stats[edge_key]['count'] += 1
            call_stats[edge_key]['dates'].append(row['timestamp'])
        
        # Add edges with weights and labels
        for (phone1, phone2), stats in call_stats.items():
            dates = sorted(stats['dates'])
            date_range = f"{dates[0].strftime('%m/%d/%y')} - {dates[-1].strftime('%m/%d/%y')}"
            
            self.graph.add_edge(
                phone1, phone2,
                weight=stats['count'],
                call_count=stats['count'],
                date_range=date_range
            )
    
    def add_person_mode(self):
        """Switch to add person mode"""
        self.mode = "add_person"
        self.status_var.set("Click on a phone number to assign a person name")
    
    def add_description_mode(self):
        """Switch to add description mode"""
        self.mode = "add_description"
        self.status_var.set("Click on a connection line to add a description")
    
    def on_click(self, event):
        """Handle mouse clicks"""
        if event.inaxes != self.ax:
            return
        
        if self.mode == "add_person":
            self.handle_person_click(event)
        elif self.mode == "add_description":
            self.handle_description_click(event)
        else:
            self.handle_drag_start(event)
    
    def handle_person_click(self, event):
        """Handle clicking on a node to add person name"""
        if not self.pos:
            return
        
        # Find closest node
        click_pos = (event.xdata, event.ydata)
        closest_node = None
        min_dist = float('inf')
        
        for node, pos in self.pos.items():
            dist = ((pos[0] - click_pos[0])**2 + (pos[1] - click_pos[1])**2)**0.5
            if dist < 0.1 and dist < min_dist:  # Within reasonable click distance
                min_dist = dist
                closest_node = node
        
        if closest_node:
            # Prompt for person name
            current_name = self.people.get(closest_node, "")
            name = tk.simpledialog.askstring(
                "Person Name", 
                f"Enter name for phone {closest_node}:",
                initialvalue=current_name
            )
            
            if name is not None:  # User didn't cancel
                if name.strip():
                    self.people[closest_node] = name.strip()
                else:
                    # Remove person if name is empty
                    if closest_node in self.people:
                        del self.people[closest_node]
                
                self.update_graph()
                self.status_var.set(f"Updated person name for {closest_node}")
        
        self.mode = "normal"
        self.status_var.set("Ready")
    
    def handle_description_click(self, event):
        """Handle clicking on an edge to add description"""
        if not self.pos:
            return
        
        click_pos = (event.xdata, event.ydata)
        closest_edge = None
        min_dist = float('inf')
        
        # Check distance to each edge
        for u, v in self.graph.edges():
            pos1, pos2 = self.pos[u], self.pos[v]
            # Calculate distance from point to line segment
            dist = self.point_to_line_distance(click_pos, pos1, pos2)
            if dist < 0.05 and dist < min_dist:  # Within reasonable click distance
                min_dist = dist
                closest_edge = (u, v)
        
        if closest_edge:
            edge_key = f"{closest_edge[0]} ↔ {closest_edge[1]}"
            current_note = self.edge_notes.get(edge_key, "")
            
            note = tk.simpledialog.askstring(
                "Connection Description",
                f"Enter description for connection {edge_key}:",
                initialvalue=current_note
            )
            
            if note is not None:  # User didn't cancel
                if note.strip():
                    self.edge_notes[edge_key] = note.strip()
                else:
                    # Remove note if empty
                    if edge_key in self.edge_notes:
                        del self.edge_notes[edge_key]
                
                self.update_graph()
                self.status_var.set(f"Updated description for {edge_key}")
        
        self.mode = "normal"
        self.status_var.set("Ready")
    
    def point_to_line_distance(self, point, line_start, line_end):
        """Calculate distance from point to line segment"""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        # Vector from line start to line end
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            # Line is actually a point
            return ((x0 - x1)**2 + (y0 - y1)**2)**0.5
        
        # Parameter t for the closest point on the line
        t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / (dx**2 + dy**2)))
        
        # Closest point on the line
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        # Distance from point to closest point on line
        return ((x0 - closest_x)**2 + (y0 - closest_y)**2)**0.5
    
    def handle_drag_start(self, event):
        """Start dragging a node"""
        if not self.pos:
            return
        
        click_pos = (event.xdata, event.ydata)
        
        # Find closest node
        for node, pos in self.pos.items():
            dist = ((pos[0] - click_pos[0])**2 + (pos[1] - click_pos[1])**2)**0.5
            if dist < 0.1:  # Within reasonable click distance
                self.dragging = node
                self.drag_offset = (pos[0] - click_pos[0], pos[1] - click_pos[1])
                break
    
    def on_motion(self, event):
        """Handle mouse motion for dragging"""
        if self.dragging and event.inaxes == self.ax:
            # Update node position
            new_x = event.xdata + self.drag_offset[0]
            new_y = event.ydata + self.drag_offset[1]
            self.pos[self.dragging] = (new_x, new_y)
            self.update_graph()
    
    def on_release(self, event):
        """Handle mouse release to stop dragging"""
        self.dragging = None
        self.drag_offset = (0, 0)
    
    def update_graph(self):
        """Update the graph visualization with clean, non-overlapping text"""
        if self.graph.number_of_nodes() == 0:
            self.ax.clear()
            self.ax.text(0.5, 0.5, 'Load CSV data to see graph', 
                        ha='center', va='center', transform=self.ax.transAxes,
                        fontsize=14, color='gray')
            self.canvas.draw()
            return
        
        self.ax.clear()
        
        # Calculate layout if not exists or reset
        if not self.pos or len(self.pos) != self.graph.number_of_nodes():
            self.pos = nx.spring_layout(self.graph, k=2, iterations=50)
        
        # Draw edges first (so they appear behind nodes)
        edge_weights = [self.graph[u][v].get('weight', 1) for u, v in self.graph.edges()]
        max_weight = max(edge_weights) if edge_weights else 1
        
        for u, v, data in self.graph.edges(data=True):
            x1, y1 = self.pos[u]
            x2, y2 = self.pos[v]
            
            # Draw edge with thickness based on call count
            weight = data.get('weight', 1)
            line_width = 1 + (weight / max_weight) * 4  # Scale from 1 to 5
            
            self.ax.plot([x1, x2], [y1, y2], 'gray', alpha=0.6, linewidth=line_width)
        
        # Draw nodes
        for node in self.graph.nodes():
            x, y = self.pos[node]
            
            if node in self.people:
                # Person node - larger and blue
                self.ax.scatter(x, y, s=800, c='lightblue', alpha=0.8, edgecolors='navy', linewidth=2)
            else:
                # Phone-only node - smaller and gray
                self.ax.scatter(x, y, s=600, c='lightgray', alpha=0.8, edgecolors='black', linewidth=1)
        
        # Add node labels - clean and readable
        for node in self.graph.nodes():
            x, y = self.pos[node]
            
            if node in self.people:
                # Show person name and phone
                label = f"{self.people[node]}\n{node}"
                self.ax.text(x, y, label, ha='center', va='center', 
                           fontsize=8, fontweight='bold', color='navy',
                           bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
            else:
                # Show just phone number
                self.ax.text(x, y, node, ha='center', va='center', 
                           fontsize=8, color='black',
                           bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
        
        # Add edge labels - strategically placed to avoid overlap
        self.add_edge_labels()
        
        # Set title and clean up axes
        self.ax.set_title("Phone Call Relationship Network", fontsize=16, fontweight='bold', pad=20)
        self.ax.axis('off')
        
        # Add legend
        legend_elements = [
            patches.Patch(color='lightblue', label='Phone with Person'),
            patches.Patch(color='lightgray', label='Phone Only')
        ]
        self.ax.legend(handles=legend_elements, loc='upper right')
        
        # Ensure proper margins
        self.ax.margins(0.1)
        
        self.canvas.draw()
    
    def add_edge_labels(self):
        """Add edge labels with smart positioning to avoid overlap"""
        label_positions = []
        
        for u, v, data in self.graph.edges(data=True):
            x1, y1 = self.pos[u]
            x2, y2 = self.pos[v]
            
            # Calculate midpoint with slight offset
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            
            # Create label
            call_count = data.get('call_count', 0)
            date_range = data.get('date_range', '')
            
            # Short, clean label
            label = f"{call_count} calls\n{date_range}"
            
            # Add note if exists
            edge_key = f"{u} ↔ {v}"
            if edge_key in self.edge_notes:
                note = self.edge_notes[edge_key]
                if len(note) > 15:
                    note = note[:15] + "..."
                label += f"\n{note}"
            
            # Find best position to avoid overlap
            best_x, best_y = self.find_best_label_position(mid_x, mid_y, label_positions)
            
            # Add label
            self.ax.text(best_x, best_y, label, ha='center', va='center',
                        fontsize=7, color='darkred',
                        bbox=dict(boxstyle="round,pad=0.2", facecolor='yellow', alpha=0.7))
            
            # Track this label position
            label_positions.append((best_x, best_y))
    
    def find_best_label_position(self, mid_x, mid_y, existing_positions):
        """Find the best position for a label to avoid overlap"""
        if not existing_positions:
            return mid_x, mid_y
        
        # Try the original position first
        min_dist = min([((mid_x - ex)**2 + (mid_y - ey)**2)**0.5 for ex, ey in existing_positions])
        
        if min_dist > 0.15:  # Sufficient distance
            return mid_x, mid_y
        
        # Try offsets around the midpoint
        offsets = [(0.05, 0.05), (-0.05, 0.05), (0.05, -0.05), (-0.05, -0.05),
                  (0.1, 0), (-0.1, 0), (0, 0.1), (0, -0.1)]
        
        for dx, dy in offsets:
            new_x, new_y = mid_x + dx, mid_y + dy
            min_dist = min([((new_x - ex)**2 + (new_y - ey)**2)**0.5 for ex, ey in existing_positions])
            
            if min_dist > 0.15:
                return new_x, new_y
        
        # If all else fails, use original position
        return mid_x, mid_y
    
    def reset_layout(self):
        """Reset the graph layout"""
        if self.graph.number_of_nodes() > 0:
            self.pos = nx.spring_layout(self.graph, k=2, iterations=50)
            self.update_graph()
            self.status_var.set("Layout reset")
    
    def export_to_pdf(self):
        """Export the chart and data to PDF"""
        if self.graph.number_of_nodes() == 0:
            messagebox.showwarning("Warning", "No data to export")
            return
        
        file_path = filedialog.asksavename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Save PDF Report"
        )
        
        if not file_path:
            return
        
        try:
            # Create PDF document
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title = Paragraph("Phone Call Relationship Analysis Report", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Summary statistics
            people_count = len(set(self.people.values())) if self.people else 0
            summary_data = [
                ['Metric', 'Value'],
                ['Total Phone Numbers', str(self.graph.number_of_nodes())],
                ['Total Call Relationships', str(self.graph.number_of_edges())],
                ['Total Call Records', str(len(self.call_data))],
                ['People Identified', str(people_count)],
                ['Date Range', f"{self.call_data['timestamp'].min().strftime('%Y-%m-%d')} to {self.call_data['timestamp'].max().strftime('%Y-%m-%d')}"]
            ]
            
            summary_table = Table(summary_data)
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 12))
            
            # Save graph image
            temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            self.fig.savefig(temp_img.name, dpi=300, bbox_inches='tight', facecolor='white')
            temp_img.close()
            
            # Add graph image
            img = Image(temp_img.name, width=7*inch, height=5*inch)
            story.append(img)
            
            # Build PDF
            doc.build(story)
            
            # Clean up
            os.unlink(temp_img.name)
            
            messagebox.showinfo("Success", f"PDF report exported to {file_path}")
            self.status_var.set("PDF exported successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")

def main():
    try:
        root = tk.Tk()
        app = PhoneLinkChartApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()