import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw
import threading
from tkinter import messagebox
from core.api_client import APIClient
from gui.login import LoginFrame
from gui.app import DashboardFrame, SettingsFrame

from core.settings_manager import SettingsManager

# Set color theme to blue
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    """
    Main Application Window. Manages frame switching, overall layout, and centralized API Client.
    """
    def __init__(self):
        super().__init__()
        
        sm = SettingsManager()
        self.settings_manager = sm # Store globally
        theme = sm.load().get("theme", "Dark")
        ctk.set_appearance_mode(theme)
        
        self.title("Cloud Save Client")
        self.geometry("900x600")
        
        # Intercept window close event
        self.protocol('WM_DELETE_WINDOW', self.hide_to_tray)
        
        # Centrally instantiate the APIClient
        self.api_client = APIClient(base_url="http://127.0.0.1:8000")
        
        # --- UI Sub-components ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid_rowconfigure(3, weight=1)  # Allow blank space at the bottom to expand
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="CloudSave UI", font=ctk.CTkFont(size=20, weight="bold"))
        self.dashboard_button = ctk.CTkButton(self.sidebar_frame, text="Dashboard", command=self.show_dashboard_view)
        self.settings_button = ctk.CTkButton(self.sidebar_frame, text="Settings", command=self.show_settings_view)
        
        self.logout_button = ctk.CTkButton(
            self.sidebar_frame, text="Logout", 
            command=lambda: self.logout("You have successfully logged out."),
            fg_color="#c0392b", hover_color="#e74c3c"
        )
        
        # Construct Views, passing down the api_client
        self.login_frame = LoginFrame(self, api_client=self.api_client, on_login_success=self.on_login_success)
        self.dashboard_frame = None
        self.settings_frame = None
        
        self.is_logging_out = False
        
        # Minimized logic
        if self.settings_manager.load().get("start_minimized", False):
            self.after(100, self.hide_to_tray)
        
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
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)
        
        self.login_frame.grid(row=0, column=0, sticky="nsew")
        if hasattr(self.login_frame, 'reset'):
            self.login_frame.reset()
        
    def on_login_success(self, username):
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
        self.logout_button.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="s")
        
        # Show default dashboard 
        self.show_dashboard_view()
        
        # Initialize background file system watcher using mappings loaded by the dashboard
        from core.sync_engine import SyncEngine
        self.sync_engine = SyncEngine(
            mapping_manager=self.dashboard_frame.mapping_manager,
            user_id=username,
            api_client=self.api_client,
            status_callback=self.dashboard_frame.update_app_status,
            timestamp_callback=self.dashboard_frame.set_last_synced,
            on_auth_error=self.logout,
            toast_callback=self.dashboard_frame.show_toast
        )
        self.sync_engine.run_startup_scan()
        
    def show_dashboard_view(self):
        self.settings_frame.grid_forget()
        self.dashboard_frame.grid(row=0, column=1, sticky="nsew")
        
    def show_settings_view(self):
        self.dashboard_frame.grid_forget()
        self.settings_frame.grid(row=0, column=1, sticky="nsew")

    def show_toast(self, message, color="#2ecc71"):
        """Displays a small temporary rectangle box at the bottom right corner of the SCREEN."""
        if self.settings_manager.load().get("mute_notifications", False):
            return
        
        toast = ctk.CTkToplevel(self)
        toast.withdraw()
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        
        frame = ctk.CTkFrame(toast, fg_color=color, corner_radius=8, border_width=1, border_color="#1a1a1a")
        frame.pack(fill="both", expand=True)
        
        prefix = "☁️ " if color == "#2ecc71" else "⚠️ "
        label = ctk.CTkLabel(frame, text=prefix + message, text_color="white", font=ctk.CTkFont(weight="bold", size=13))
        label.pack(padx=20, pady=12)
        
        toast.update_idletasks()
        width = frame.winfo_reqwidth()
        height = frame.winfo_reqheight()
        
        screen_width = toast.winfo_screenwidth()
        screen_height = toast.winfo_screenheight()
        
        x = screen_width - width - 25
        y = screen_height - height - 70
        
        toast.geometry(f"{width}x{height}+{x}+{y}")
        toast.deiconify()
        
        self.after(4000, toast.destroy)

    def logout(self, message="Your session has expired. Please log in again."):
        """Tears down local state safely and navigates back to login view."""
        if self.is_logging_out:
            return
            
        self.is_logging_out = True
        
        # Stop file watchers and destroy dependent components
        if hasattr(self, "sync_engine") and getattr(self, "sync_engine"):
            self.sync_engine.stop()
            self.sync_engine = None
            
        if getattr(self, "api_client", None):
            self.api_client.token = None # Clear token logic

        if self.dashboard_frame:
            self.dashboard_frame.destroy()
            self.dashboard_frame = None
            
        if self.settings_frame:
            self.settings_frame.destroy()
            self.settings_frame = None
            
        self.show_login_view()
        
        # Display the message in main thread async to prevent blocking the teardown
        self.after(500, lambda: messagebox.showwarning("Session Ended", message))
        
        self.after(1000, lambda: setattr(self, 'is_logging_out', False))

    def create_default_icon(self):
        # Create a simple 64x64 blue square with a white C
        image = Image.new('RGB', (64, 64), color=(52, 152, 219))
        dc = ImageDraw.Draw(image)
        dc.text((20, 15), "C", fill=(255, 255, 255), font=None)
        return image

    def hide_to_tray(self):
        self.withdraw()
        menu = pystray.Menu(
            pystray.MenuItem('Show App', self.show_from_tray, default=True),
            pystray.MenuItem('Quit', self.quit_app)
        )
        self.tray_icon = pystray.Icon("CloudSave", self.create_default_icon(), "CloudSave Sync", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_from_tray(self, icon, item):
        icon.stop()
        self.after(0, self.deiconify)

    def quit_app(self, icon, item):
        icon.stop()
        if hasattr(self, 'sync_engine') and self.sync_engine:
            self.sync_engine.stop()
        self.after(0, self.destroy)

if __name__ == "__main__":
    app = App()
    app.mainloop()
