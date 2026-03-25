import customtkinter as ctk

class LoginFrame(ctk.CTkFrame):
    """
    Initial view representing the login screen.
    Includes error handling and backend network synchronization.
    """
    def __init__(self, master, api_client, on_login_success):
        super().__init__(master)
        
        self.api_client = api_client
        self.on_login_success = on_login_success
        
        # Configure grid to center the login form, allocating remaining space outside the middle
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 6), weight=1)
        
        # Login Title
        self.title_label = ctk.CTkLabel(self, text="Welcome to Cloud Save", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=1, column=0, padx=20, pady=(20, 20))
        
        # Error Label (hidden by default)
        self.error_label = ctk.CTkLabel(self, text="", text_color="red")
        
        # Username Entry
        self.username_entry = ctk.CTkEntry(self, placeholder_text="Username", width=200)
        self.username_entry.grid(row=3, column=0, padx=20, pady=10)
        
        # Password Entry
        self.password_entry = ctk.CTkEntry(self, placeholder_text="Password", show="*", width=200)
        self.password_entry.grid(row=4, column=0, padx=20, pady=10)
        
        # Login Button
        self.login_button = ctk.CTkButton(self, text="Login", command=self.login_event, width=200)
        self.login_button.grid(row=5, column=0, padx=20, pady=(20, 20))
        
    def login_event(self):
        # Retrieve input text
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        # Basic validation
        if not username or not password:
            self.show_error("Please enter both username and password.")
            return

        # Hide any previous errors and visually disable button
        self.error_label.grid_forget()
        self.login_button.configure(state="disabled")
        self.update_idletasks() # Refresh UI to show disabled state immediately before network block
        
        # Attempt to authenticate
        success, error_msg = self.api_client.login(username, password)
        
        if success:
            self.show_error("") # Clear error just in case
            self.on_login_success(username)
        else:
            self.show_error(error_msg)
            self.login_button.configure(state="normal")
            
    def show_error(self, message):
        """Displays or hides the error label based on the message string."""
        if message:
            self.error_label.configure(text=message)
            self.error_label.grid(row=2, column=0, padx=20, pady=0)
        else:
            self.error_label.grid_forget()
