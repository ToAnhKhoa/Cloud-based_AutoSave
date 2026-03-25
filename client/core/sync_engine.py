import time
import threading
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FolderWatcher(FileSystemEventHandler):
    """
    Monitors a single folder for file modifications, creations, and deletions.
    Uses a threading.Timer to debounce rapid successive events.
    """
    def __init__(self, app_name, folder_path, callback, debounce_seconds=3.0):
        super().__init__()
        self.app_name = app_name
        self.folder_path = folder_path
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        
        # Debounce timer thread
        self.timer = None

    def _trigger_callback(self):
        """Called automatically after the debounce period elapses."""
        self.callback(self.app_name, self.folder_path)

    def _debounce(self):
        """Cancels any pending timer and starts a fresh one."""
        if self.timer is not None:
            self.timer.cancel()
        self.timer = threading.Timer(self.debounce_seconds, self._trigger_callback)
        self.timer.start()

    def on_modified(self, event):
        if not event.is_directory:
            self._debounce()

    def on_created(self, event):
        if not event.is_directory:
            self._debounce()

    def on_deleted(self, event):
        if not event.is_directory:
            self._debounce()

class SyncEngine:
    """
    Manages background file observation spanning across multiple user mappings.
    """
    def __init__(self, mapping_manager):
        self.mapping_manager = mapping_manager
        self.observer = Observer()
        self.watchers = []

    def sync_callback(self, app_name, folder_path):
        # We print to console until the actual ZIP and upload service is implemented
        print(f"[SyncEngine] Action detected and debounced! Ready to zip and upload: {app_name} at {folder_path}")

    def start(self):
        """
        Reads mappings, attaches FolderWatchers, and spawns the background thread execution.
        """
        mappings = self.mapping_manager.load_mappings()
        if not mappings:
            print("[SyncEngine] No valid mappings found to watch.")
            return

        for app_name, folder_path in mappings.items():
            if os.path.exists(folder_path):
                watcher = FolderWatcher(app_name, folder_path, self.sync_callback)
                self.watchers.append(watcher)
                
                # Attaching the watcher safely
                self.observer.schedule(watcher, folder_path, recursive=True)
                print(f"[SyncEngine] Scheduled background watch for {app_name} at {folder_path}")
            else:
                print(f"[SyncEngine] Warning: Path for {app_name} does not exist on disk: {folder_path}")

        # The watchdog.Observer internally spawns a daemon thread, so it won't block CustomTkinter UI.
        self.observer.start()
        print("[SyncEngine] Hardware Event Observer started in background.")

    def stop(self):
        """Gracefully shutdown the observer on exit."""
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
