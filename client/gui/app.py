import customtkinter as ctk
import tkinter.filedialog as filedialog
from core.mapping_manager import MappingManager

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
        
    def refresh_mapping_list(self):
        # Clear existing children
        for child in self.mappings_frame.winfo_children():
            child.destroy()
            
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

        # Draw rows dynamically
        for idx, (app_name, path) in enumerate(mappings.items()):
            row_frame = ctk.CTkFrame(self.mappings_frame, corner_radius=8)
            row_frame.grid(row=idx, column=0, columnspan=2, sticky="ew", pady=5, padx=5)
            row_frame.grid_columnconfigure(1, weight=1)
            
            name_label = ctk.CTkLabel(row_frame, text=app_name, font=ctk.CTkFont(size=14, weight="bold"))
            name_label.grid(row=0, column=0, padx=15, pady=10, sticky="w")
            
            path_label = ctk.CTkLabel(row_frame, text=path, text_color="gray", font=ctk.CTkFont(size=12))
            path_label.grid(row=0, column=1, padx=15, pady=10, sticky="w")

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
