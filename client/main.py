import customtkinter as ctk
from core.api_client import APIClient
from gui.login import LoginFrame
from gui.app import DashboardFrame, SettingsFrame

# Set appearance mode to Dark and color theme to blue
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    """
    Main Application Window. Manages frame switching, overall layout, and centralized API Client.
    """
    def __init__(self):
        super().__init__()
        
        self.title("Cloud Save Client")
        self.geometry("900x600")
        
        # Centrally instantiate the APIClient
        self.api_client = APIClient(base_url="http://127.0.0.1:8000")
        
        # --- UI Sub-components ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid_rowconfigure(3, weight=1)  # Allow blank space at the bottom to expand
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="CloudSave UI", font=ctk.CTkFont(size=20, weight="bold"))
        self.dashboard_button = ctk.CTkButton(self.sidebar_frame, text="Dashboard", command=self.show_dashboard_view)
        self.settings_button = ctk.CTkButton(self.sidebar_frame, text="Settings", command=self.show_settings_view)
        
        # Construct Views, passing down the api_client
        self.login_frame = LoginFrame(self, api_client=self.api_client, on_login_success=self.show_main_interface)
        self.dashboard_frame = None
        self.settings_frame = None
        
        # Start the application by displaying only the login frame
        self.show_login_view()
        
    def show_login_view(self):
        """
        Configure the main layout to only display the login view.
        """
        self.sidebar_frame.grid_forget()
        if self.dashboard_frame:
            self.dashboard_frame.grid_forget()
        if self.settings_frame:
            self.settings_frame.grid_forget()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.login_frame.grid(row=0, column=0, sticky="nsew")
        
    def show_main_interface(self, username):
        """
        Transition function called upon successful login.
        """
        self.login_frame.grid_forget()
        
        # Initialize authorized frames with the authenticated username
        self.dashboard_frame = DashboardFrame(self, api_client=self.api_client, username=username)
        self.settings_frame = SettingsFrame(self, api_client=self.api_client)
        
        # Setup standard app layout
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Attach and render sidebar layout
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.dashboard_button.grid(row=1, column=0, padx=20, pady=10)
        self.settings_button.grid(row=2, column=0, padx=20, pady=10)
        
        # Show default dashboard 
        self.show_dashboard_view()
        
        # Initialize background file system watcher using mappings loaded by the dashboard
        from core.sync_engine import SyncEngine
        self.sync_engine = SyncEngine(mapping_manager=self.dashboard_frame.mapping_manager)
        self.sync_engine.start()
        
    def show_dashboard_view(self):
        self.settings_frame.grid_forget()
        self.dashboard_frame.grid(row=0, column=1, sticky="nsew")
        
    def show_settings_view(self):
        self.dashboard_frame.grid_forget()
        self.settings_frame.grid(row=0, column=1, sticky="nsew")

if __name__ == "__main__":
    app = App()
    app.mainloop()
