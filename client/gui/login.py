import customtkinter as ctk
import threading
import tkinter.messagebox as messagebox

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
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 8), weight=1)
        
        self.is_register_mode = False
        
        # Login Title
        self.title_label = ctk.CTkLabel(self, text="Welcome to Cloud Save", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=1, column=0, padx=20, pady=(20, 20))
        
        # Error Label (hidden by default)
        self.error_label = ctk.CTkLabel(self, text="", text_color="red")
        
        # Username Entry
        self.username_entry = ctk.CTkEntry(
            self, placeholder_text="Username", width=200,
            fg_color="#343638", text_color="white", placeholder_text_color="#a0a0a0",
            border_width=2, border_color="#3498db"
        )
        self.username_entry.grid(row=3, column=0, padx=20, pady=10)
        
        # Password Entry
        self.password_entry = ctk.CTkEntry(
            self, placeholder_text="Password", show="*", width=200,
            fg_color="#343638", text_color="white", placeholder_text_color="#a0a0a0",
            border_width=2, border_color="#3498db"
        )
        self.password_entry.grid(row=4, column=0, padx=20, pady=10)
        
        # Confirm Password Entry (Hidden initially)
        self.confirm_password_entry = ctk.CTkEntry(
            self, placeholder_text="Confirm Password", show="*", width=200,
            fg_color="#343638", text_color="white", placeholder_text_color="#a0a0a0",
            border_width=2, border_color="#3498db"
        )
        
        # Login Button
        self.login_button = ctk.CTkButton(self, text="Login", command=self.login_event, width=200)
        self.login_button.grid(row=6, column=0, padx=20, pady=(20, 10))
        
        # Toggle Mode Button
        self.toggle_mode_btn = ctk.CTkButton(
            self, text="Don't have an account? Register", 
            fg_color="transparent", text_color="#3498db", hover_color="#2c3e50", 
            command=self.toggle_mode
        )
        self.toggle_mode_btn.grid(row=7, column=0, padx=20, pady=(0, 20))
        
        # Force initial focus to bypass CustomTkinter placeholder render bug
        self.after(100, self.username_entry.focus)
        
    def toggle_mode(self):
        self.is_register_mode = not self.is_register_mode
        self.show_error("")
        if self.is_register_mode:
            self.title_label.configure(text="Create Account")
            self.login_button.configure(text="Register")
            self.toggle_mode_btn.configure(text="Already have an account? Login")
            self.confirm_password_entry.grid(row=5, column=0, padx=20, pady=10)
        else:
            self.title_label.configure(text="Welcome to Cloud Save")
            self.login_button.configure(text="Login")
            self.toggle_mode_btn.configure(text="Don't have an account? Register")
            self.confirm_password_entry.grid_forget()
            
    def reset(self):
        self.username_entry.delete(0, 'end')
        self.password_entry.delete(0, 'end')
        self.confirm_password_entry.delete(0, 'end')
        self.login_button.configure(state="normal")
        self.toggle_mode_btn.configure(state="normal")
        self.show_error("")
        
    def login_event(self):
        # Retrieve input text
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        # Basic validation
        if not username or not password:
            self.show_error("Please enter both username and password.")
            return
            
        if self.is_register_mode:
            confirm = self.confirm_password_entry.get().strip()
            if not confirm:
                self.show_error("Please confirm your password.")
                return
            if password != confirm:
                self.show_error("Passwords do not match!")
                return

        # Hide any previous errors and visually disable button
        self.error_label.grid_forget()
        self.login_button.configure(state="disabled")
        self.toggle_mode_btn.configure(state="disabled")
        self.update_idletasks() # Refresh UI to show disabled state immediately before network block
        
        # Perform network operation in background
        if self.is_register_mode:
            threading.Thread(target=self._perform_register, args=(username, password), daemon=True).start()
        else:
            threading.Thread(target=self._perform_login, args=(username, password), daemon=True).start()

    def _perform_register(self, username, password):
        success, msg = self.api_client.register(username, password)
        if success:
            self.after(0, self._on_register_success_ui, msg)
        else:
            self.after(0, self._on_register_failed_ui, msg)

    def _perform_login(self, username, password):
        # Attempt to authenticate
        success = self.api_client.login(username, password)
        
        if success:
            self.after(0, self._on_login_success_ui, username)
        else:
            self.after(0, self._on_login_failed_ui)

    def _on_login_success_ui(self, username):
        self.show_error("") # Clear error just in case
        self.on_login_success(username)

    def _on_login_failed_ui(self):
        self.show_error("Invalid credentials")
        self.login_button.configure(state="normal")
        self.toggle_mode_btn.configure(state="normal")
            
    def _on_register_success_ui(self, msg):
        messagebox.showinfo("Success", msg)
        self.reset()
        if self.is_register_mode:
            self.toggle_mode()
            
    def _on_register_failed_ui(self, msg):
        self.show_error(msg)
        self.login_button.configure(state="normal")
        self.toggle_mode_btn.configure(state="normal")
            
    def show_error(self, message):
        """Displays or hides the error label based on the message string."""
        if message:
            self.error_label.configure(text=message)
            self.error_label.grid(row=2, column=0, padx=20, pady=0)
        else:
            self.error_label.grid_forget()
