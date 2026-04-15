import customtkinter as ctk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import os
from core.mapping_manager import MappingManager
from core.api_client import SessionExpiredError
from core.settings_manager import SettingsManager
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
        self.cloud_apps = []
        self.refresh_mapping_list()
        
        # Thread-safe UI queue
        self.message_queue = queue.Queue()
        self.check_queue()
        
        import threading
        threading.Thread(target=self._fetch_cloud_apps, daemon=True).start()

    def _fetch_cloud_apps(self):
        try:
            apps = self.api_client.get_cloud_apps()
            self.after(0, self._render_ghost_apps, apps)
        except SessionExpiredError:
            self.after(0, self.master.logout)

    def _render_ghost_apps(self, cloud_apps):
        self.cloud_apps = cloud_apps
        self.refresh_mapping_list()

    def map_ghost_app(self, app_name):
        folder_selected = filedialog.askdirectory(title=f"Select folder for {app_name}")
        if folder_selected:
            self.mapping_manager.add_mapping(app_name, folder_selected)
            self.refresh_mapping_list()
            self.show_toast(f"Mapped {app_name} successfully!", "#2ecc71")
            if hasattr(self.master, "sync_engine") and getattr(self.master, "sync_engine"):
                self.master.sync_engine.refresh_watchers()
                self.master.sync_engine.initial_scan(app_name, folder_selected)

    def auto_find_path(self, app_name, btn):
        import threading
        def _thread():
            btn.configure(state="disabled", text="⏳ Asking AI...")
            result = self.api_client.ask_ai_for_path(app_name)
            
            def _handle_result():
                btn.configure(state="normal", text="✨ Auto-Find (Beta)")
                
                if not result:
                    messagebox.showerror("Error", "No response from AI.")
                    return
                if result.get('status') == 'error':
                    messagebox.showerror("Error", result.get('message', 'Unknown error'))
                    return
                
                official_name = result.get('official_name', app_name)
                path = result.get('path', '')
                
                expanded_path = os.path.expandvars(path)
                expanded_path = os.path.normpath(expanded_path)
                
                if os.path.exists(expanded_path):
                    msg = f"AI identified this game as '{official_name}'.\nFound path: {expanded_path}\n\nDo you want to map this folder?"
                    if messagebox.askyesno("AI Found Path", msg):
                        self.mapping_manager.add_mapping(official_name, expanded_path)
                        self.refresh_mapping_list()
                        self.show_toast(f"Mapped {official_name} using AI!", "#8e44ad")
                        if hasattr(self.master, "sync_engine") and getattr(self.master, "sync_engine"):
                            self.master.sync_engine.refresh_watchers()
                            self.master.sync_engine.initial_scan(official_name, expanded_path)
                else:
                    parent_dir = os.path.dirname(expanded_path)
                    initial_dir = parent_dir if os.path.exists(parent_dir) else os.path.expanduser("~")
                    
                    msg = f"AI suggested the path:\n{expanded_path}\n\nHowever, this folder doesn't exist on your PC yet (you might need to launch the game first).\n\nWould you like to browse and select the folder manually?"
                    if messagebox.askyesno("Path Not Found", msg):
                        selected_folder = filedialog.askdirectory(initialdir=initial_dir, title=f"Select Save Folder for {official_name}")
                        if selected_folder:
                            self.mapping_manager.add_mapping(official_name, selected_folder)
                            self.refresh_mapping_list()
                            self.show_toast(f"Mapped {official_name} manually!", "#2ecc71")
                            if hasattr(self.master, "sync_engine") and getattr(self.master, "sync_engine"):
                                self.master.sync_engine.refresh_watchers()
                                self.master.sync_engine.initial_scan(official_name, selected_folder)
            self.after(0, _handle_result)
            
        threading.Thread(target=_thread, daemon=True).start()

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
                elif msg["type"] == "toast":
                    if hasattr(self.master, "show_toast"):
                        self.master.show_toast(msg["message"], msg["color"])
        except queue.Empty:
            pass
        self.after(100, self.check_queue)
        
    def show_toast(self, message: str, color: str = "#2ecc71"):
        """Thread-safe way to trigger a toast notification"""
        self.message_queue.put({"type": "toast", "message": message, "color": color})

    def update_app_status(self, app_name: str, status_msg: str, color: str = "orange"):
        self.message_queue.put({"type": "status", "app_name": app_name, "status_msg": status_msg, "color": color})

    def set_last_synced(self, app_name: str, timestamp_str: str):
        self.message_queue.put({"type": "timestamp", "app_name": app_name, "ts": timestamp_str})

    def handle_manual_sync(self, app_name, folder_path):
        try:
            cloud_info = self.api_client.get_save_info(app_name)
        except SessionExpiredError:
            self.master.logout()
            return
        
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
        ghost_apps = [app for app in getattr(self, "cloud_apps", []) if app not in mappings]
        
        if not mappings and not ghost_apps:
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
        idx = 0
        for app_name, path in mappings.items():
            row_frame = ctk.CTkFrame(self.mappings_frame, corner_radius=8)
            row_frame.grid(row=idx, column=0, columnspan=2, sticky="ew", pady=5, padx=5)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=1)
            row_frame.grid_columnconfigure(2, weight=0)
            row_frame.grid_columnconfigure(3, weight=0)
            row_frame.grid_columnconfigure(4, weight=0)
            
            # Stacked Layout (Card)
            info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            info_frame.grid(row=0, column=0, padx=15, pady=10, sticky="w")
            
            name_label = ctk.CTkLabel(info_frame, text=app_name, font=ctk.CTkFont(size=14, weight="bold"), cursor="hand2")
            name_label.grid(row=0, column=0, sticky="w")
            
            status_label = ctk.CTkLabel(info_frame, text="🔍 Scanning...", text_color="#3498db", font=ctk.CTkFont(size=12))
            status_label.grid(row=1, column=0, sticky="w")
            
            def _show_path(e, p=path, l=status_label):
                display_path = p if len(p) <= 65 else p[:30] + "..." + p[-30:]
                l.configure(text=display_path, text_color="gray")
                
            name_label.bind("<Enter>", _show_path)
            name_label.bind("<Leave>", lambda e, name=app_name: _on_leave(e, name))
            
            status_label.bind("<Enter>", lambda e, name=app_name: _on_enter(e, name))
            status_label.bind("<Leave>", lambda e, name=app_name: _on_leave(e, name))
            self.status_labels[app_name] = status_label
            self.current_statuses[app_name] = {"msg": "🔍 Scanning...", "color": "#3498db"}
            
            pull_btn = ctk.CTkButton(
                row_frame, 
                text="🔄 Sync", 
                width=100, 
                command=lambda a=app_name, p=path: self.handle_manual_sync(a, p)
            )
            pull_btn.grid(row=0, column=2, padx=(0, 10), pady=10, sticky="e")
            
            unmap_btn = ctk.CTkButton(
                row_frame,
                text="Unmap 🚫",
                width=100,
                fg_color="#e74c3c",
                hover_color="#c0392b",
                command=lambda a=app_name: self.unmap_app(a)
            )
            unmap_btn.grid(row=0, column=3, padx=(0, 10), pady=10, sticky="e")
            
            rollback_btn = ctk.CTkButton(
                row_frame,
                text="⏪ Rollback",
                width=100,
                fg_color="#e67e22",
                hover_color="#d35400"
            )
            rollback_btn.grid(row=0, column=4, padx=(0, 15), pady=10, sticky="e")
            rollback_btn.grid_remove() # Hide initially

            def _check_backup(a, btn, p):
                try:
                    info = self.api_client.get_save_info(a)
                    backup_date = info.get("has_backup")
                    if backup_date:
                        def _show():
                            if btn.winfo_exists():
                                btn.configure(
                                    command=lambda: self.rollback_app_ui(a, p, backup_date)
                                )
                                btn.bind("<Enter>", lambda e: btn.configure(text=f"⏪ Rollback ({backup_date})"))
                                btn.bind("<Leave>", lambda e: btn.configure(text="⏪ Rollback"))
                                btn.grid()
                        self.after(0, _show)
                except Exception:
                    pass
            threading.Thread(target=_check_backup, args=(app_name, rollback_btn, path), daemon=True).start()
            
            idx += 1

        for app_name in ghost_apps:
            row_frame = ctk.CTkFrame(self.mappings_frame, corner_radius=8)
            row_frame.grid(row=idx, column=0, columnspan=2, sticky="ew", pady=5, padx=5)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=1)
            row_frame.grid_columnconfigure(2, weight=0)
            row_frame.grid_columnconfigure(3, weight=0)
            row_frame.grid_columnconfigure(4, weight=0)
            
            info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            info_frame.grid(row=0, column=0, padx=15, pady=10, sticky="w")
            
            name_label = ctk.CTkLabel(info_frame, text=app_name, font=ctk.CTkFont(size=14, weight="bold"), cursor="hand2")
            name_label.grid(row=0, column=0, sticky="w")
            
            status_label = ctk.CTkLabel(info_frame, text="☁️ Not Mapped", text_color="#bdc3c7", font=ctk.CTkFont(size=12))
            status_label.grid(row=1, column=0, sticky="w")
            
            def _show_ghost_path(e, l=status_label):
                l.configure(text="No local folder mapped", text_color="gray")
                
            def _hide_ghost_path(e, l=status_label):
                l.configure(text="☁️ Not Mapped", text_color="#bdc3c7")
                
            name_label.bind("<Enter>", _show_ghost_path)
            name_label.bind("<Leave>", _hide_ghost_path)
            
            auto_find_btn = ctk.CTkButton(
                row_frame,
                text="✨ Auto-Find (Beta)",
                width=120,
                fg_color="#8e44ad",
                hover_color="#9b59b6",
                text_color="white"
            )
            auto_find_btn.configure(command=lambda a=app_name, b=auto_find_btn: self.auto_find_path(a, b))
            auto_find_btn.grid(row=0, column=2, padx=(0, 10), pady=10, sticky="e")
            
            pull_btn = ctk.CTkButton(
                row_frame, 
                text="Map Folder 📁", 
                width=120, 
                command=lambda a=app_name: self.map_ghost_app(a)
            )
            pull_btn.grid(row=0, column=3, padx=(0, 10), pady=10, sticky="e")
            
            delete_btn = ctk.CTkButton(
                row_frame,
                text="Delete 🗑️",
                width=100,
                fg_color="#c0392b",
                hover_color="#922b21",
                command=lambda a=app_name: self.delete_app_from_cloud(a)
            )
            delete_btn.grid(row=0, column=4, padx=(0, 15), pady=10, sticky="e")
            idx += 1
            
    def unmap_app(self, app_name):
        if messagebox.askyesno("Confirm Unmap", f"Stop syncing '{app_name}'? Your cloud backup will be kept safe."):
            if hasattr(self.master, "sync_engine") and getattr(self.master, "sync_engine"):
                self.master.sync_engine.remove_mapping(app_name)
            else:
                self.mapping_manager.remove_mapping(app_name)
            self.refresh_mapping_list()
            self.show_toast(f"Unmapped {app_name} locally.", "#f39c12")

    def delete_app_from_cloud(self, app_name):
        msg = f"WARNING: This will permanently delete the cloud backup for '{app_name}' from the server. This cannot be undone. Are you sure?"
        if messagebox.askyesno("WARNING", msg, icon="warning"):
            if self.api_client.delete_cloud_app(app_name):
                if hasattr(self, "cloud_apps") and app_name in self.cloud_apps:
                    self.cloud_apps.remove(app_name)
                messagebox.showinfo("Success", f"Successfully deleted {app_name} from the cloud.")
                self.show_toast(f"Deleted {app_name} from cloud.", "#e74c3c")
                self.refresh_mapping_list()
            else:
                messagebox.showerror("Error", f"Failed to delete {app_name} from the cloud.")

    def rollback_app_ui(self, app_name, folder_path, backup_date):
        msg = f"Are you sure you want to restore the cloud save from {backup_date}? Your current cloud and local saves will be overwritten."
        if messagebox.askyesno("WARNING", msg, icon="warning"):
            import threading
            def _thread():
                if hasattr(self.master, "sync_engine") and getattr(self.master, "sync_engine"):
                    self.update_app_status(app_name, "⏪ Rolling back...", "#e67e22")
                    
                success = self.api_client.rollback_cloud_app(app_name)
                
                def _handle_result():
                    if success:
                        messagebox.showinfo("Success", f"Successfully rolled back {app_name} on the server. Initiating download...")
                        if hasattr(self.master, "sync_engine") and getattr(self.master, "sync_engine"):
                            self.master.sync_engine.restore_from_cloud(app_name, folder_path)
                            self.refresh_mapping_list()
                    else:
                        messagebox.showerror("Error", f"Failed to rollback {app_name}.")
                        if hasattr(self.master, "sync_engine") and getattr(self.master, "sync_engine"):
                            self.update_app_status(app_name, "❌ Rollback Failed", "#e74c3c")
                self.after(0, _handle_result)
            threading.Thread(target=_thread, daemon=True).start()

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
        
        def auto_find():
            app_name = name_entry.get().strip()
            if not app_name:
                messagebox.showwarning("Missing Name", "Please enter an application name first.")
                return
            
            import threading
            def _thread():
                auto_find_btn.configure(state="disabled", text="⏳ Asking AI...")
                result = self.api_client.ask_ai_for_path(app_name)
                
                def _handle_result():
                    auto_find_btn.configure(state="normal", text="✨ Auto-Find (Beta)")
                    if not result:
                        messagebox.showerror("Error", "No response from AI.")
                        return
                    if result.get('status') == 'error':
                        messagebox.showerror("Error", result.get('message', 'Unknown error'))
                        return
                    
                    official_name = result.get('official_name', app_name)
                    path = result.get('path', '')
                    expanded_path = os.path.expandvars(path)
                    expanded_path = os.path.normpath(expanded_path)
                    
                    if os.path.exists(expanded_path):
                        name_entry.delete(0, 'end')
                        name_entry.insert(0, official_name)
                        path_var.set(expanded_path)
                        messagebox.showinfo("Success", f"Found!\n{expanded_path}")
                    else:
                        parent_dir = os.path.dirname(expanded_path)
                        initial_dir = parent_dir if os.path.exists(parent_dir) else os.path.expanduser("~")
                        
                        msg = f"AI suggested the path:\n{expanded_path}\n\nHowever, this folder doesn't exist on your PC yet (you might need to launch the game first).\n\nWould you like to browse and select the folder manually?"
                        if messagebox.askyesno("Path Not Found", msg):
                            selected_folder = filedialog.askdirectory(initialdir=initial_dir, title=f"Select Save Folder for {official_name}")
                            if selected_folder:
                                name_entry.delete(0, 'end')
                                name_entry.insert(0, official_name)
                                path_var.set(selected_folder)
                
                self.after(0, _handle_result)
            threading.Thread(target=_thread, daemon=True).start()

        auto_find_btn = ctk.CTkButton(popup, text="✨ Auto-Find (Beta)", width=130, fg_color="#8e44ad", hover_color="#9b59b6", text_color="white", command=auto_find)
        auto_find_btn.grid(row=0, column=1, padx=20, pady=(20, 5), sticky="e")
        
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
            self.show_toast(f"Mapped {app_name} successfully!", "#2ecc71")
            popup.destroy()
            
            # Safely request the sync engine to pick up the new mapped directory
            if hasattr(self.master, "sync_engine") and getattr(self.master, "sync_engine"):
                self.master.sync_engine.refresh_watchers()
                self.master.sync_engine.force_sync_if_not_empty(app_name, folder_path)
            
        save_button = ctk.CTkButton(popup, text="Save Mapping", corner_radius=8, command=save_mapping)
        save_button.grid(row=4, column=0, columnspan=2, padx=20, pady=(30, 20), sticky="ew")

class SettingsFrame(ctk.CTkFrame):
    """
    Settings interface governing client configurations like 'Start with Windows'
    """
    def __init__(self, master, api_client):
        super().__init__(master, corner_radius=0)
        self.api_client = api_client
        self.settings_manager = SettingsManager()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Settings", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, sticky="w")
        
        # Settings Content
        self.content_frame = ctk.CTkFrame(self, corner_radius=8)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # Load user settings
        self.current_settings = self.settings_manager.load()
        
        # Start with windows switch
        self.startup_var = ctk.BooleanVar(value=self.current_settings.get("start_with_windows", False))
        self.startup_switch = ctk.CTkSwitch(
            self.content_frame, 
            text="Launch App on System Startup", 
            variable=self.startup_var,
            command=self.toggle_startup_setting,
            font=ctk.CTkFont(size=14)
        )
        self.startup_switch.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Start Minimized switch
        self.minimized_var = ctk.BooleanVar(value=self.current_settings.get("start_minimized", False))
        self.minimized_switch = ctk.CTkSwitch(
            self.content_frame, 
            text="Start Minimized to Tray", 
            variable=self.minimized_var,
            command=self.toggle_minimized_setting,
            font=ctk.CTkFont(size=14)
        )
        self.minimized_switch.grid(row=0, column=1, padx=20, pady=20, sticky="w")
        
        # Debounce Settings
        self.debounce_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.debounce_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.debounce_frame, text="Watchdog Backup Delay (seconds):", font=ctk.CTkFont(size=14)).grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        self.debounce_var = ctk.StringVar(value=str(self.current_settings.get("debounce_time", 3.0)))
        
        self.debounce_entry = ctk.CTkEntry(self.debounce_frame, textvariable=self.debounce_var, width=100)
        self.debounce_entry.grid(row=1, column=0, sticky="w")
        
        self.debounce_save_btn = ctk.CTkButton(self.debounce_frame, text="Save Delay", width=120, command=self.save_debounce)
        self.debounce_save_btn.grid(row=1, column=1, padx=15, sticky="w")
        
        # Theme Settings
        self.theme_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.theme_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.theme_frame, text="Appearance Theme:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        initial_theme = self.current_settings.get("theme", "Dark")
        self.theme_var = ctk.StringVar(value=initial_theme)
        
        self.theme_menu = ctk.CTkOptionMenu(
            self.theme_frame,
            values=["Light", "Dark", "System"],
            variable=self.theme_var,
            command=self.change_theme
        )
        self.theme_menu.grid(row=1, column=0, sticky="w")
        
        # Mute Notifications switch
        self.mute_var = ctk.BooleanVar(value=self.current_settings.get("mute_notifications", False))
        self.mute_switch = ctk.CTkSwitch(
            self.content_frame, 
            text="Mute OS Notifications", 
            variable=self.mute_var,
            command=self.toggle_mute_setting,
            font=ctk.CTkFont(size=14)
        )
        self.mute_switch.grid(row=2, column=1, padx=20, pady=10, sticky="w")
        
        # Bandwidth Limit Settings
        self.bw_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.bw_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.bw_frame, text="Max Bandwidth (KB/s, 0=Uncapped):", font=ctk.CTkFont(size=14)).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.bw_var = ctk.StringVar(value=str(self.current_settings.get("bandwidth_limit_kbps", 0.0)))
        
        self.bw_entry = ctk.CTkEntry(self.bw_frame, textvariable=self.bw_var, width=100)
        self.bw_entry.grid(row=1, column=0, sticky="w")
        
        self.bw_save_btn = ctk.CTkButton(self.bw_frame, text="Save Limit", width=120, command=self.save_bandwidth)
        self.bw_save_btn.grid(row=1, column=1, padx=15, sticky="w")
        
    def change_theme(self, new_theme: str):
        ctk.set_appearance_mode(new_theme)
        self.current_settings["theme"] = new_theme
        self.settings_manager.save(self.current_settings)
        
    def save_debounce(self):
        try:
            val = float(self.debounce_var.get())
            if val < 0.5: val = 0.5
            if val > 3600.0: val = 3600.0
            
            self.current_settings["debounce_time"] = val
            self.settings_manager.save(self.current_settings)
            
            # Apply dynamically to running watchers without interrupting them
            if hasattr(self.master, "sync_engine") and getattr(self.master, "sync_engine"):
                self.master.sync_engine.update_debounce_time(val)
                
            if hasattr(self.master, "show_toast"):
                self.master.show_toast(f"Saved sync delay: {val}s", "#3498db")
        except ValueError:
            self.debounce_var.set(str(self.current_settings.get("debounce_time", 3.0)))
            if hasattr(self.master, "show_toast"):
                self.master.show_toast("Invalid number entered", "#e74c3c")
                
    def toggle_startup_setting(self):
        new_state = self.startup_var.get()
        self.current_settings["start_with_windows"] = new_state
        self.settings_manager.save(self.current_settings)
        self.settings_manager.toggle_startup(new_state)
        if hasattr(self.master, "show_toast"):
            state_text = "Enabled" if new_state else "Disabled"
            color = "#2ecc71" if new_state else "#f39c12"
            self.master.show_toast(f"Startup on boot: {state_text}", color)
            
    def toggle_minimized_setting(self):
        new_state = self.minimized_var.get()
        self.current_settings["start_minimized"] = new_state
        self.settings_manager.save(self.current_settings)
        if hasattr(self.master, "show_toast"):
            state_text = "Enabled" if new_state else "Disabled"
            self.master.show_toast(f"Start Minimized: {state_text}", "#3498db")
            
    def toggle_mute_setting(self):
        new_state = self.mute_var.get()
        self.current_settings["mute_notifications"] = new_state
        self.settings_manager.save(self.current_settings)
        
    def save_bandwidth(self):
        try:
            val = float(self.bw_var.get())
            if val < 0.0: val = 0.0
            
            self.current_settings["bandwidth_limit_kbps"] = val
            self.settings_manager.save(self.current_settings)
            
            if hasattr(self.master, "show_toast"):
                self.master.show_toast(f"Saved Limit: {val} KB/s", "#3498db")
        except ValueError:
            self.bw_var.set(str(self.current_settings.get("bandwidth_limit_kbps", 0.0)))
            if hasattr(self.master, "show_toast"):
                self.master.show_toast("Invalid number entered", "#e74c3c")
