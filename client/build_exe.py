import os
import sys
import subprocess

def ensure_dependencies():
    """Ensure PyInstaller and CustomTkinter are installed."""
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        
    try:
        import customtkinter
    except ImportError:
        print("customtkinter not found. Installing via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])

def main():
    ensure_dependencies()
    import customtkinter
    
    print("Starting build process...")
    
    # Find CustomTkinter installation path dynamically
    ctk_path = os.path.dirname(customtkinter.__file__)
    
    # OS-specific separator for PyInstaller --add-data (';' for Windows, ':' for Unix-like)
    separator = os.pathsep
    
    # Base PyInstaller command
    # --noconfirm: Overwrite output directory if it exists
    # --onedir: Build a one-folder bundle containing an executable
    # --noconsole: Hide the console window
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--noconsole",
        "--name", "CloudSync_Client",
    ]
    
    # 1. CustomTkinter assets
    cmd.append(f"--add-data={ctk_path}{separator}customtkinter/")
    
    # 2. Project config files (settings.json, .env)
    if os.path.exists("settings.json"):
        cmd.append(f"--add-data=settings.json{separator}.")
    if os.path.exists(".env"):
        cmd.append(f"--add-data=.env{separator}.")
        
    # 3. Project assets and Icon
    if os.path.exists("assets"):
        cmd.append(f"--add-data=assets{separator}assets/")
        icon_path = os.path.join("assets", "app_icon.ico")
        if os.path.exists(icon_path):
            cmd.append(f"--icon={icon_path}")
    
    # 4. Target script entry point
    cmd.append("main.py")
    
    print("\nRunning command:")
    print(" ".join(cmd))
    print("\n" + "="*50 + "\n")
    
    try:
        subprocess.check_call(cmd)
        print("\n" + "="*50)
        print("Success: Build Completed Successfully!")
        print("Your application is ready inside the 'dist/CloudSync_Client' folder.")
    except subprocess.CalledProcessError as e:
        print("\nFailed: Build Failed!")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
