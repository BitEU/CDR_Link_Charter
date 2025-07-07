# dialogs.py
"""
Dialog classes for the People Connection Visualizer
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import os
import webbrowser
import requests
import threading
from pathlib import Path
from .constants import COLORS

class PersonDialog:
    """
    Dialog for adding/editing person information
    """
    def __init__(self, parent, title, **kwargs):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"✏️ {title}")
        self.dialog.geometry("450x900")
        self.dialog.configure(bg=COLORS['background'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (900 // 2)
        self.dialog.geometry(f"450x900+{x}+{y}")
        
        # Main container
        main_frame = tk.Frame(self.dialog, bg=COLORS['background'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        # Title
        title_label = tk.Label(main_frame, 
                              text=title,
                              font=("Segoe UI", 18, "bold"),
                              fg=COLORS['primary'],
                              bg=COLORS['background'])
        title_label.pack(pady=(0, 25))
        
        # Form container
        form_frame = tk.Frame(main_frame, bg=COLORS['surface'], relief=tk.FLAT, bd=0)
        form_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 25))
        
        # Add padding inside form
        form_inner = tk.Frame(form_frame, bg=COLORS['surface'])
        form_inner.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        # Fields with modern styling
        fields = [
            ("👤 Full Name:", "name", True),
            ("🎂 Date of Birth:", "dob", False),
            ("🏷️ Alias/Nickname:", "alias", False),
            ("🏠 Address:", "address", False),
            ("📞 Phone Number:", "phone", False)
        ]
        
        self.entries = {}
        for i, (label, field, required) in enumerate(fields):
            # Label
            label_text = label
            if required:
                label_text += " *"
            
            field_label = tk.Label(form_inner, 
                                  text=label_text,
                                  font=("Segoe UI", 11, "bold" if required else "normal"),
                                  fg=COLORS['text_primary'],
                                  bg=COLORS['surface'],
                                  anchor="w")
            field_label.grid(row=i*2, column=0, sticky="w", pady=(8 if i > 0 else 0, 4))
            
            # Entry with modern styling
            entry = tk.Entry(form_inner, 
                           font=("Segoe UI", 12),
                           bg='white',
                           fg=COLORS['text_primary'],
                           relief=tk.FLAT,
                           bd=8,
                           highlightthickness=2,
                           highlightcolor=COLORS['primary'],
                           highlightbackground=COLORS['border'],
                           width=35)
            entry.grid(row=i*2+1, column=0, sticky="ew", pady=(0, 6))
            
            if field in kwargs:
                entry.insert(0, kwargs[field])
            
            self.entries[field] = entry
        
        # Configure grid weights
        form_inner.columnconfigure(0, weight=1)
          # Required field note
        note_label = tk.Label(form_inner,
                             text="* Required fields",
                             font=("Segoe UI", 9),
                             fg=COLORS['text_secondary'],
                             bg=COLORS['surface'])
        note_label.grid(row=len(fields)*2, column=0, sticky="w", pady=(10, 0))
        
        # File attachments section
        files_label = tk.Label(form_inner,
                              text="📎 Attached Files:",
                              font=("Segoe UI", 11, "bold"),
                              fg=COLORS['text_primary'],
                              bg=COLORS['surface'],
                              anchor="w")
        files_label.grid(row=len(fields)*2+1, column=0, sticky="w", pady=(12, 4))
        
        # Files frame
        files_frame = tk.Frame(form_inner, bg=COLORS['surface'])
        files_frame.grid(row=len(fields)*2+2, column=0, sticky="ew", pady=(0, 10))
        
        # File list and buttons
        self.files_list = tk.Listbox(files_frame, height=3, font=("Segoe UI", 10),
                                    bg='white', fg=COLORS['text_primary'],
                                    selectbackground=COLORS['primary'])
        self.files_list.pack(fill=tk.X, pady=(0, 5))
        
        files_btn_frame = tk.Frame(files_frame, bg=COLORS['surface'])
        files_btn_frame.pack(fill=tk.X)
        
        add_file_btn = tk.Button(files_btn_frame, text="+ Add File",
                                command=self.add_file, font=("Segoe UI", 9),
                                bg=COLORS['primary'], fg='white', relief=tk.FLAT,
                                padx=10, pady=4, cursor='hand2')
        add_file_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        remove_file_btn = tk.Button(files_btn_frame, text="Remove",
                                   command=self.remove_file, font=("Segoe UI", 9),
                                   bg=COLORS['text_secondary'], fg='white', relief=tk.FLAT,
                                   padx=10, pady=4, cursor='hand2')
        remove_file_btn.pack(side=tk.LEFT)
        
        # Initialize files list with existing files
        self.attached_files = kwargs.get('files', [])
        for file_path in self.attached_files:
            self.files_list.insert(tk.END, os.path.basename(file_path))
        
        # Button frame
        button_frame = tk.Frame(main_frame, bg=COLORS['background'])
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Modern buttons
        cancel_btn = tk.Button(button_frame,
                              text="Cancel",
                              command=self.cancel,
                              font=("Segoe UI", 10),
                              bg=COLORS['text_secondary'],
                              fg='white',
                              relief=tk.FLAT,
                              padx=20,
                              pady=8,
                              cursor='hand2')
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        ok_btn = tk.Button(button_frame,
                          text="Save",
                          command=self.ok,
                          font=("Segoe UI", 10, "bold"),
                          bg=COLORS['primary'],
                          fg='white',
                          relief=tk.FLAT,
                          padx=20,
                          pady=8,
                          cursor='hand2')
        ok_btn.pack(side=tk.RIGHT)
        
        # Add hover effects to buttons
        self._add_button_hover_effects(ok_btn, cancel_btn)
        
        # Focus on name entry
        self.entries["name"].focus()
        
        # Bind Enter key to OK
        self.dialog.bind('<Return>', lambda e: self.ok())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
    
    def add_file(self):
        """Handle adding a file attachment"""
        file_path = filedialog.askopenfilename(
            title="Select file to attach",
            filetypes=[("All files", "*.*"), ("Images", "*.png *.jpg *.jpeg *.gif *.bmp"),
                      ("Documents", "*.pdf *.txt *.doc *.docx"), ("Videos", "*.mp4 *.avi *.mov")]
        )
        if file_path:
            self.attached_files.append(file_path)
            self.files_list.insert(tk.END, os.path.basename(file_path))
    
    def remove_file(self):
        """Handle removing a file attachment"""
        selection = self.files_list.curselection()
        if selection:
            idx = selection[0]
            self.files_list.delete(idx)
            del self.attached_files[idx]
    
    def _add_button_hover_effects(self, ok_btn, cancel_btn):
        """Add hover effects to buttons"""
        def on_ok_enter(e):
            ok_btn.configure(bg=COLORS['primary_dark'])
        def on_ok_leave(e):
            ok_btn.configure(bg=COLORS['primary'])
        def on_cancel_enter(e):
            cancel_btn.configure(bg='#475569')
        def on_cancel_leave(e):
            cancel_btn.configure(bg=COLORS['text_secondary'])
        
        ok_btn.bind("<Enter>", on_ok_enter)
        ok_btn.bind("<Leave>", on_ok_leave)
        cancel_btn.bind("<Enter>", on_cancel_enter)
        cancel_btn.bind("<Leave>", on_cancel_leave)
        
    def ok(self):
        """Handle OK button click"""
        # Validate name is not empty
        if not self.entries["name"].get().strip():
            messagebox.showerror("Error", "Name is required!", parent=self.dialog)
            return
            
        self.result = {field: entry.get().strip() for field, entry in self.entries.items()}
        self.result['files'] = self.attached_files[:]  # Copy the files list
        self.dialog.destroy()
        
    def cancel(self):
        """Handle Cancel button click"""
        self.dialog.destroy()


class ConnectionLabelDialog:
    """
    Dialog for adding/editing a connection label
    """
    def __init__(self, parent, title, initial_value=""):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"🔗 {title}")
        self.dialog.geometry("400x300")
        self.dialog.configure(bg=COLORS['background'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (300 // 2)
        self.dialog.geometry(f"400x300+{x}+{y}")
        
        # Main container
        main_frame = tk.Frame(self.dialog, bg=COLORS['background'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        # Title
        title_label = tk.Label(main_frame, 
                              text=title,
                              font=("Segoe UI", 16, "bold"),
                              bg=COLORS['background'],
                              fg=COLORS['text_primary'])
        title_label.pack(pady=(0, 20))
        
        # Connection label input
        input_frame = tk.Frame(main_frame, bg=COLORS['background'])
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        label_text = tk.Label(input_frame,
                             text="Connection Label:",
                             font=("Segoe UI", 12, "bold"),
                             bg=COLORS['background'],
                             fg=COLORS['text_primary'])
        label_text.pack(anchor=tk.W, pady=(0, 8))
        
        # Modern entry with border
        entry_container = tk.Frame(input_frame, bg=COLORS['border'], relief=tk.SOLID, bd=1)
        entry_container.pack(fill=tk.X, pady=(0, 5))
        
        self.label_entry = tk.Entry(entry_container,
                                   font=("Segoe UI", 12),
                                   bg=COLORS['surface'],
                                   fg=COLORS['text_primary'],
                                   relief=tk.FLAT,
                                   bd=0)
        self.label_entry.pack(fill=tk.BOTH, padx=2, pady=2)
        self.label_entry.insert(0, initial_value)
        self.label_entry.focus()
        self.label_entry.select_range(0, tk.END)
        
        # Instructions
        instruction_label = tk.Label(input_frame,
                                   text="Enter a descriptive label for this connection\n(e.g., 'friend', 'dealer', 'family member')",
                                   font=("Segoe UI", 9),
                                   bg=COLORS['background'],
                                   fg=COLORS['text_secondary'],
                                   justify=tk.LEFT)
        instruction_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Button frame
        button_frame = tk.Frame(main_frame, bg=COLORS['background'])
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Cancel button
        cancel_btn = tk.Button(button_frame,
                              text="Cancel",
                              font=("Segoe UI", 11, "bold"),
                              bg=COLORS['text_secondary'],
                              fg='white',
                              relief=tk.FLAT,
                              padx=20,
                              pady=8,
                              command=self.cancel,
                              cursor='hand2')
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # OK button
        ok_btn = tk.Button(button_frame,
                          text="Save",
                          font=("Segoe UI", 11, "bold"),
                          bg=COLORS['primary'],
                          fg='white',
                          relief=tk.FLAT,
                          padx=20,
                          pady=8,
                          command=self.ok,
                          cursor='hand2')
        ok_btn.pack(side=tk.RIGHT)
        
        # Key bindings
        self.dialog.bind('<Return>', lambda e: self.ok())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)  # Handle window close
        
    def ok(self):
        """Handle OK button click"""
        label = self.label_entry.get().strip()
        if not label:
            messagebox.showerror("Error", "Connection label cannot be empty!", parent=self.dialog)
            return
        self.result = label
        self.dialog.destroy()
        
    def cancel(self):
        """Handle Cancel button click"""
        self.dialog.destroy()


class VersionUpdateDialog:
    """
    Dialog for showing version update information
    """
    def __init__(self, parent, current_version, latest_version, release_url):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("🔄 Update Available")
        self.dialog.geometry("500x400")
        self.dialog.configure(bg=COLORS['background'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"500x400+{x}+{y}")

        # Main container
        main_frame = tk.Frame(self.dialog, bg=COLORS['background'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        # Icon and title
        title_frame = tk.Frame(main_frame, bg=COLORS['background'])
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(title_frame,
                              text="🔄 Update Available",
                              font=("Segoe UI", 16, "bold"),
                              bg=COLORS['background'],
                              fg=COLORS['primary'])
        title_label.pack()
        
        # Version info frame
        info_frame = tk.Frame(main_frame, bg=COLORS['surface'], relief=tk.FLAT, bd=0)
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Add padding inside info frame
        info_inner = tk.Frame(info_frame, bg=COLORS['surface'])
        info_inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Current version
        current_label = tk.Label(info_inner,
                                text=f"Current Version: {current_version}",
                                font=("Segoe UI", 11),
                                bg=COLORS['surface'],
                                fg=COLORS['text_primary'])
        current_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Latest version
        latest_label = tk.Label(info_inner,
                               text=f"Latest Version: {latest_version}",
                               font=("Segoe UI", 11, "bold"),
                               bg=COLORS['surface'],
                               fg=COLORS['success'])
        latest_label.pack(anchor=tk.W, pady=(0, 15))
        
        # Description
        desc_label = tk.Label(info_inner,
                             text="A new version of COMRADE is available!\nClick download to get the latest version.",
                             font=("Segoe UI", 10),
                             bg=COLORS['surface'],
                             fg=COLORS['text_secondary'],
                             justify=tk.LEFT)
        desc_label.pack(anchor=tk.W)
        
        # Store release URL for later use
        self.release_url = release_url
        
        # Download progress label (initially hidden)
        self.progress_label = tk.Label(info_inner,
                                     text="",
                                     font=("Segoe UI", 9),
                                     bg=COLORS['surface'],
                                     fg=COLORS['primary'])
        self.progress_label.pack(anchor=tk.W, pady=(10, 0))
        
        # Button frame
        button_frame = tk.Frame(main_frame, bg=COLORS['background'])
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Later button
        self.later_btn = tk.Button(button_frame,
                                  text="Later",
                                  font=("Segoe UI", 11, "bold"),
                                  bg=COLORS['text_secondary'],
                                  fg='white',
                                  relief=tk.FLAT,
                                  padx=20,
                                  pady=8,
                                  command=self.later,
                                  cursor='hand2')
        self.later_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Visit GitHub button
        self.visit_btn = tk.Button(button_frame,
                                  text="Visit GitHub",
                                  font=("Segoe UI", 11),
                                  bg=COLORS['text_secondary'],
                                  fg='white',
                                  relief=tk.FLAT,
                                  padx=15,
                                  pady=8,
                                  command=self.visit_github,
                                  cursor='hand2')
        self.visit_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Download button
        self.download_btn = tk.Button(button_frame,
                                     text="⬇️ Download Update",
                                     font=("Segoe UI", 11, "bold"),
                                     bg=COLORS['primary'],
                                     fg='white',
                                     relief=tk.FLAT,
                                     padx=20,
                                     pady=8,
                                     command=self.download_update,
                                     cursor='hand2')
        self.download_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Key bindings
        self.dialog.bind('<Escape>', lambda e: self.later())
        self.dialog.protocol("WM_DELETE_WINDOW", self.later)
        
    def download_update(self):
        """Download the latest release exe file"""
        def download_thread():
            try:
                # Update UI to show loading state
                self.dialog.after(0, self.update_download_ui, "⏳ Finding latest release...", True)
                
                # Fetch latest release info from GitHub API
                response = requests.get('https://api.github.com/repos/BitEU/COMRADE/releases/latest', timeout=10)
                
                if not response.ok:
                    raise Exception('Failed to fetch release info')
                
                release_data = response.json()
                
                # Find the .exe file in the assets
                exe_asset = None
                for asset in release_data.get('assets', []):
                    if asset['name'].lower().endswith('.exe'):
                        exe_asset = asset
                        break
                
                if not exe_asset:
                    raise Exception('No executable file found in the latest release')
                
                # Update UI with download progress
                self.dialog.after(0, self.update_download_ui, f"⬇️ Downloading {exe_asset['name']}...", True)
                
                # Download the file
                download_response = requests.get(exe_asset['browser_download_url'], timeout=30)
                
                if not download_response.ok:
                    raise Exception('Failed to download the file')
                
                # Save to Downloads folder
                downloads_path = Path.home() / "Downloads"
                downloads_path.mkdir(exist_ok=True)
                file_path = downloads_path / exe_asset['name']
                
                with open(file_path, 'wb') as f:
                    f.write(download_response.content)
                
                # Success - update UI
                self.dialog.after(0, self.update_download_ui, f"✅ Downloaded to: {file_path}", False)
                
                # Show success message
                self.dialog.after(500, lambda: messagebox.showinfo(
                    "Download Complete", 
                    f"The latest version has been downloaded to:\n{file_path}\n\nYou can now install the update.",
                    parent=self.dialog
                ))
                
                # Reset button after delay
                self.dialog.after(3000, self.reset_download_ui)
                
            except requests.exceptions.Timeout:
                self.dialog.after(0, self.update_download_ui, "❌ Download timed out", False)
                self.dialog.after(0, self.show_download_error, "Download timed out. Please check your internet connection.")
            except requests.exceptions.RequestException as e:
                self.dialog.after(0, self.update_download_ui, "❌ Network error", False)
                self.dialog.after(0, self.show_download_error, f"Network error: {str(e)}")
            except Exception as e:
                self.dialog.after(0, self.update_download_ui, "❌ Download failed", False)
                self.dialog.after(0, self.show_download_error, f"Download failed: {str(e)}")
        
        # Start download in separate thread
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()
    
    def update_download_ui(self, message, disable_buttons):
        """Update the UI during download process"""
        self.progress_label.config(text=message)
        if disable_buttons:
            self.download_btn.config(state='disabled', text="⏳ Downloading...")
            self.visit_btn.config(state='disabled')
            self.later_btn.config(state='disabled')
        else:
            self.download_btn.config(state='normal')
            self.visit_btn.config(state='normal')
            self.later_btn.config(state='normal')
    
    def show_download_error(self, error_message):
        """Show error message and offer fallback"""
        result = messagebox.askquestion(
            "Download Failed",
            f"{error_message}\n\nWould you like to visit the GitHub releases page instead?",
            parent=self.dialog
        )
        if result == 'yes':
            self.visit_github()
        else:
            self.reset_download_ui()
    
    def reset_download_ui(self):
        """Reset the download UI to initial state"""
        self.progress_label.config(text="")
        self.download_btn.config(state='normal', text="⬇️ Download Update")
        self.visit_btn.config(state='normal')
        self.later_btn.config(state='normal')
    
    def visit_github(self):
        """Open the GitHub releases page in the default browser"""
        try:
            webbrowser.open(self.release_url)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open browser: {e}", parent=self.dialog)
        self.result = "visit"
        self.dialog.destroy()
        
    def later(self):
        """Close the dialog without taking action"""
        self.result = "later"
        self.dialog.destroy()


class NoUpdateDialog:
    """
    Dialog for showing that no update is available
    """
    def __init__(self, parent, current_version):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("✅ Up to Date")
        self.dialog.geometry("350x225")
        self.dialog.configure(bg=COLORS['background'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (350 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (225 // 2)
        self.dialog.geometry(f"350x225+{x}+{y}")
        
        # Main container
        main_frame = tk.Frame(self.dialog, bg=COLORS['background'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        # Icon and title
        title_label = tk.Label(main_frame,
                              text="✅ You're Up to Date!",
                              font=("Segoe UI", 16, "bold"),
                              bg=COLORS['background'],
                              fg=COLORS['success'])
        title_label.pack(pady=(0, 20))
        
        # Version info
        version_label = tk.Label(main_frame,
                                text=f"Current Version: {current_version}",
                                font=("Segoe UI", 12),
                                bg=COLORS['background'],
                                fg=COLORS['text_primary'])
        version_label.pack(pady=(0, 10))
        
        # Description
        desc_label = tk.Label(main_frame,
                             text="You have the latest version of COMRADE.",
                             font=("Segoe UI", 10),
                             bg=COLORS['background'],
                             fg=COLORS['text_secondary'])
        desc_label.pack(pady=(0, 20))
        
        # OK button
        ok_btn = tk.Button(main_frame,
                          text="OK",
                          font=("Segoe UI", 11, "bold"),
                          bg=COLORS['primary'],
                          fg='white',
                          relief=tk.FLAT,
                          padx=30,
                          pady=10,
                          command=self.ok,
                          cursor='hand2')
        ok_btn.pack()
        
        # Key bindings
        self.dialog.bind('<Return>', lambda e: self.ok())
        self.dialog.bind('<Escape>', lambda e: self.ok())
        self.dialog.protocol("WM_DELETE_WINDOW", self.ok)
        
    def ok(self):
        """Close the dialog"""
        self.result = "ok"
        self.dialog.destroy()