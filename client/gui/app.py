import customtkinter as ctk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import os
from core.mapping_manager import MappingManager
import queue

class DashboardFrame(ctk.CTkFrame):
    """
    Main content view representing the Dashboard.
    """
    def __init__(self, master, api_client, username):
        super().__init__(master, corner_radius=0)
        
        self.api_client = api_client
        self.mapping_manager = MappingManager(user_id=username)
        
        # Grid config
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Header frame
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Your Cloud Saves", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, sticky="w")
        
        self.add_app_button = ctk.CTkButton(self.header_frame, text="+ Add New App", command=self.open_add_app_popup)
        self.add_app_button.grid(row=0, column=1, sticky="e")
        
        # Scrollable mapping list
        self.mappings_frame = ctk.CTkScrollableFrame(self)
        self.mappings_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(10, 20))
        self.mappings_frame.grid_columnconfigure(1, weight=1)
        
        # Initialize
        self.refresh_mapping_list()
        
        # Thread-safe UI queue
        self.message_queue = queue.Queue()
        self.check_queue()
        
    def check_queue(self):
        try:
            while True:
                msg = self.message_queue.get_nowait()
                if msg["type"] == "status":
                    app_name = msg["app_name"]
                    status_msg = msg["status_msg"]
                    color = msg["color"]
                    if hasattr(self, 'status_labels') and app_name in self.status_labels:
                        self.current_statuses[app_name] = {"msg": status_msg, "color": color}
                        self.status_labels[app_name].configure(text=status_msg, text_color=color)
                elif msg["type"] == "timestamp":
                    app_name = msg["app_name"]
                    ts = msg["ts"]
                    self.last_synced_times[app_name] = ts
        except queue.Empty:
            pass
        self.after(100, self.check_queue)
        
    def update_app_status(self, app_name: str, status_msg: str, color: str = "orange"):
        self.message_queue.put({"type": "status", "app_name": app_name, "status_msg": status_msg, "color": color})

    def set_last_synced(self, app_name: str, timestamp_str: str):
        self.message_queue.put({"type": "timestamp", "app_name": app_name, "ts": timestamp_str})

    def handle_manual_sync(self, app_name, folder_path):
        cloud_info = self.api_client.get_save_info(app_name)
        
        newest_mtime = 0
        if os.path.exists(folder_path):
            for root, dirs, files in os.walk(folder_path):
                for f in files:
                    file_path = os.path.join(root, f)
                    if os.path.exists(file_path):
                        mtime = os.path.getmtime(file_path)
                        if mtime > newest_mtime:
                            newest_mtime = mtime
                            
        from datetime import datetime
        local_time_dt = None
        if newest_mtime > 0:
            local_time_dt = datetime.fromtimestamp(newest_mtime)
            
        cloud_time_dt = None
        if cloud_info.get("exists"):
            cloud_time_str = cloud_info.get("last_modified")
            try:
                cloud_time_dt = datetime.strptime(cloud_time_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
                
        local_newer = False
        cloud_newer = False
        
        if local_time_dt and cloud_time_dt:
            if local_time_dt > cloud_time_dt:
                local_newer = True
            elif cloud_time_dt > local_time_dt:
                cloud_newer = True
        elif cloud_time_dt and not local_time_dt:
            cloud_newer = True
        elif local_time_dt and not cloud_time_dt:
            local_newer = True
            
        if local_newer or (local_time_dt and not cloud_info.get("exists")):
            msg = "Your LOCAL files are newer (or cloud is empty).\nDo you want to UPLOAD and overwrite the Cloud?"
            if messagebox.askyesno("Confirm Upload", msg):
                if hasattr(self.master, "sync_engine") and getattr(self.master, "sync_engine"):
                    self.update_app_status(app_name, "☁️ Syncing to Cloud...", "#3498db")
                    self.master.sync_engine.force_sync_if_not_empty(app_name, folder_path)
        elif cloud_newer or (not local_time_dt and cloud_info.get("exists")):
            msg = "The CLOUD save is newer (or local folder is empty).\nDo you want to PULL from the Cloud and overwrite local files?"
            if messagebox.askyesno("Confirm Download", msg):
                if hasattr(self.master, "sync_engine") and getattr(self.master, "sync_engine"):
                    self.master.sync_engine.restore_from_cloud(app_name, folder_path)
        else:
            messagebox.showinfo("In Sync", f"{app_name} is already fully synchronized!")

    def refresh_mapping_list(self):
        # Clear existing children
        for child in self.mappings_frame.winfo_children():
            child.destroy()
            
        self.status_labels = {}
        self.current_statuses = {}
        self.last_synced_times = {}
            
        mappings = self.mapping_manager.load_mappings()
        
        if not mappings:
            # Show friendly message
            no_data_label = ctk.CTkLabel(self.mappings_frame, text="No applications mapped yet. Add one to get started!", text_color="gray")
            no_data_label.grid(row=0, column=0, columnspan=2, pady=20)
            self.mappings_frame.grid_columnconfigure(0, weight=1)
            return

        # Setup columns for rows
        self.mappings_frame.grid_columnconfigure(0, weight=0)
        self.mappings_frame.grid_columnconfigure(1, weight=1)

        def _on_enter(event, a_name):
            if a_name in self.last_synced_times and self.last_synced_times[a_name]:
                self.status_labels[a_name].configure(
                    text=f"🕒 Last Synced: {self.last_synced_times[a_name]}",
                    text_color="gray"
                )
                
        def _on_leave(event, a_name):
            if a_name in self.current_statuses:
                status = self.current_statuses[a_name]
                self.status_labels[a_name].configure(
                    text=status.get("msg", "🟢 Monitoring..."),
                    text_color=status.get("color", "#2ecc71")
                )
            else:
                self.status_labels[a_name].configure(text="🟢 Monitoring...", text_color="#2ecc71")

        import threading
        # Draw rows dynamically
        for idx, (app_name, path) in enumerate(mappings.items()):
            row_frame = ctk.CTkFrame(self.mappings_frame, corner_radius=8)
            row_frame.grid(row=idx, column=0, columnspan=2, sticky="ew", pady=5, padx=5)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=1)
            row_frame.grid_columnconfigure(2, weight=0)
            
            # Stacked Layout (Card)
            info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            info_frame.grid(row=0, column=0, padx=15, pady=10, sticky="w")
            
            name_label = ctk.CTkLabel(info_frame, text=app_name, font=ctk.CTkFont(size=14, weight="bold"))
            name_label.grid(row=0, column=0, sticky="w")
            
            path_label = ctk.CTkLabel(info_frame, text=path, text_color="gray", font=ctk.CTkFont(size=12))
            path_label.grid(row=1, column=0, sticky="w")
            
            status_label = ctk.CTkLabel(row_frame, text="🔍 Scanning...", text_color="#3498db", font=ctk.CTkFont(size=12))
            status_label.grid(row=0, column=1, padx=15, pady=10, sticky="e")
            status_label.bind("<Enter>", lambda e, name=app_name: _on_enter(e, name))
            status_label.bind("<Leave>", lambda e, name=app_name: _on_leave(e, name))
            self.status_labels[app_name] = status_label
            self.current_statuses[app_name] = {"msg": "🔍 Scanning...", "color": "#3498db"}
            
            pull_btn = ctk.CTkButton(
                row_frame, 
                text="🔄 Sync", 
                width=120, 
                command=lambda a=app_name, p=path: self.handle_manual_sync(a, p)
            )
            pull_btn.grid(row=0, column=2, padx=(0, 15), pady=10, sticky="e")
            
    def open_add_app_popup(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Add New App Mapping")
        popup.geometry("450x300")
        
        # Make the popup transient to master and grab focus
        popup.transient(self.winfo_toplevel())
        popup.grab_set()
        
        # Position popup relative to main window center
        popup.update_idletasks()
        main_x = self.winfo_toplevel().winfo_x()
        main_y = self.winfo_toplevel().winfo_y()
        popup.geometry(f"+{main_x + 200}+{main_y + 150}")
        
        # Form layout configuration
        popup.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(popup, text="Application Name:").grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        name_entry = ctk.CTkEntry(popup, placeholder_text="e.g. mario_game_save")
        name_entry.grid(row=1, column=0, columnspan=2, padx=20, pady=5, sticky="ew")
        
        ctk.CTkLabel(popup, text="Folder Path:").grid(row=2, column=0, padx=20, pady=(15, 5), sticky="w")
        
        path_var = ctk.StringVar(value="No folder selected")
        path_label = ctk.CTkLabel(popup, textvariable=path_var, text_color="gray", wraplength=250)
        path_label.grid(row=3, column=0, padx=20, pady=5, sticky="w")
        
        def browse_folder():
            folder_selected = filedialog.askdirectory()
            if folder_selected:
                path_var.set(folder_selected)
                
        browse_button = ctk.CTkButton(popup, text="Browse", width=100, command=browse_folder)
        browse_button.grid(row=3, column=1, padx=20, pady=5, sticky="e")
        
        def save_mapping():
            app_name = name_entry.get().strip()
            folder_path = path_var.get()
            
            # Simple validation check
            if not app_name or folder_path == "No folder selected":
                return
                
            self.mapping_manager.add_mapping(app_name, folder_path)
            self.refresh_mapping_list()
            popup.destroy()
            
            # Safely request the sync engine to pick up the new mapped directory
            if hasattr(self.master, "sync_engine") and getattr(self.master, "sync_engine"):
                self.master.sync_engine.refresh_watchers()
                self.master.sync_engine.force_sync_if_not_empty(app_name, folder_path)
            
        save_button = ctk.CTkButton(popup, text="Save Mapping", corner_radius=8, command=save_mapping)
        save_button.grid(row=4, column=0, columnspan=2, padx=20, pady=(30, 20), sticky="ew")

class SettingsFrame(ctk.CTkFrame):
    """
    Settings view placeholder
    """
    def __init__(self, master, api_client):
        super().__init__(master, corner_radius=0)
        self.api_client = api_client
        self.title_label = ctk.CTkLabel(self, text="Settings", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=20, sticky="nw")
