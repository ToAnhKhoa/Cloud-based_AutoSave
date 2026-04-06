import time
import threading
import os
import shutil
import tempfile
import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FolderWatcher(FileSystemEventHandler):
    """
    Monitors a single folder for file modifications, creations, and deletions.
    Uses a threading.Timer to debounce rapid successive events.
    """
    def __init__(self, app_name, folder_path, callback, status_callback=None, debounce_seconds=3.0):
        super().__init__()
        self.app_name = app_name
        self.folder_path = folder_path
        self.callback = callback
        self.status_callback = status_callback
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

    def _notify_change(self):
        if self.status_callback:
            self.status_callback(self.app_name, "⏳ Sync Pending...", "#f39c12")

    def on_modified(self, event):
        if not event.is_directory:
            self._notify_change()
            self._debounce()

    def on_created(self, event):
        if not event.is_directory:
            self._notify_change()
            self._debounce()

    def on_deleted(self, event):
        if not event.is_directory:
            self._notify_change()
            self._debounce()

class SyncEngine:
    """
    Manages background file observation spanning across multiple user mappings.
    """
    def __init__(self, mapping_manager, user_id: str, api_client, status_callback=None, timestamp_callback=None):
        self.mapping_manager = mapping_manager
        self.user_id = user_id
        self.api_client = api_client
        self.status_callback = status_callback
        self.timestamp_callback = timestamp_callback
        self.observer = Observer()
        self.watchers = []
        self.ignored_apps_for_watchdog = set()
        self.sync_states = {}

    def _revert_status(self, app_name):
        if self.status_callback:
            self.status_callback(app_name, "🟢 Monitoring...", "#2ecc71")

    def _perform_upload(self, app_name, folder_path):
        if not os.path.exists(folder_path) or len(os.listdir(folder_path)) == 0:
            if self.status_callback:
                self.status_callback(app_name, "⚠️ Sync Aborted (Directory Empty)", "#f39c12")
                threading.Timer(5.0, lambda: self._revert_status(app_name)).start()
            return

        print(f"[SyncEngine] Zipping {app_name}...")
        if self.status_callback:
            self.status_callback(app_name, "☁️ Syncing to Cloud...", "#3498db")
        
        try:
            temp_dir = tempfile.gettempdir()
            temp_base_name = os.path.join(temp_dir, f"{app_name}_sync")
            
            # Make a zip file
            zip_path = shutil.make_archive(temp_base_name, 'zip', root_dir=folder_path)
            
            # Upload via API
            success = self.api_client.upload_save(app_name, zip_path)
            
            if success:
                print("[SyncEngine] Upload successful to Backend!")
                now = datetime.datetime.now().strftime("%H:%M:%S")
                if self.timestamp_callback:
                    self.timestamp_callback(app_name, now)
                
                self.sync_states[app_name] = 'in_sync'
                self.start_watching(app_name, folder_path)
                
                if self.status_callback:
                    self.status_callback(app_name, "✅ Sync Complete!", "#2ecc71")
                    threading.Timer(3.0, lambda: self._revert_status(app_name)).start()
            else:
                print("[SyncEngine] Upload failed.")
                if self.status_callback:
                    self.status_callback(app_name, "❌ Sync Failed!", "#e74c3c")
                    threading.Timer(5.0, lambda: self._revert_status(app_name)).start()
                    
            # Cleanup temp file
            if os.path.exists(zip_path):
                os.remove(zip_path)
        except Exception as e:
            print(f"[SyncEngine] Exception during sync: {e}")
            if self.status_callback:
                self.status_callback(app_name, "❌ Sync Failed!", "#e74c3c")
                threading.Timer(5.0, lambda: self._revert_status(app_name)).start()

    def sync_callback(self, app_name, folder_path):
        if app_name in self.ignored_apps_for_watchdog:
            return
        self._perform_upload(app_name, folder_path)

    def force_sync_if_not_empty(self, app_name, folder_path):
        if os.path.exists(folder_path) and os.listdir(folder_path):
            threading.Thread(target=self._perform_upload, args=(app_name, folder_path)).start()
        else:
            print("[SyncEngine] Folder is empty, skipping initial sync.")

    def restore_from_cloud(self, app_name: str, folder_path: str):
        def _restore_thread():
            self.ignored_apps_for_watchdog.add(app_name)
            if self.status_callback:
                self.status_callback(app_name, "⬇️ Downloading from Cloud...", "#3498db")
            
            success = self.api_client.download_save(app_name, folder_path)
            
            if success:
                self.sync_states[app_name] = 'in_sync'
                self.start_watching(app_name, folder_path)
                if self.status_callback:
                    self.status_callback(app_name, "✅ Restoration Complete!", "#2ecc71")
            else:
                if self.status_callback:
                    self.status_callback(app_name, "❌ Restoration Failed", "#e74c3c")
            
            time.sleep(2)
            if app_name in self.ignored_apps_for_watchdog:
                self.ignored_apps_for_watchdog.remove(app_name)
            
            if self.status_callback:
                self.status_callback(app_name, "🟢 Monitoring...", "#2ecc71")
                
        threading.Thread(target=_restore_thread).start()

    def initial_scan(self, app_name, folder_path):
        try:
            self.sync_states[app_name] = 'scanning'
            
            cloud_info = self.api_client.get_save_info(app_name)
            cloud_exists = cloud_info.get("exists", False)
            
            local_time = None
            if os.path.exists(folder_path):
                newest_mtime = 0
                has_files = False
                for root, dirs, files in os.walk(folder_path):
                    for f in files:
                        file_path = os.path.join(root, f)
                        if os.path.exists(file_path):
                            mtime = os.path.getmtime(file_path)
                            if mtime > newest_mtime:
                                newest_mtime = mtime
                                has_files = True
                if has_files:
                    local_time = newest_mtime

            cloud_time = None
            if cloud_exists:
                cloud_time_str = cloud_info.get("last_modified")
                if cloud_time_str:
                    try:
                        dt = datetime.datetime.strptime(cloud_time_str, '%Y-%m-%d %H:%M:%S')
                        cloud_time = dt.timestamp()
                    except ValueError:
                        cloud_exists = False
                else:
                    cloud_exists = False
            
            self.sync_states[app_name] = 'out_of_sync'
            if not cloud_exists and not local_time:
                if self.status_callback:
                    self.status_callback(app_name, "🟡 Awaiting First Save", "#f39c12")
            elif not cloud_exists and local_time:
                if self.status_callback:
                    self.status_callback(app_name, "🟡 Pending Initial Upload", "#f39c12")
            elif cloud_exists and not local_time:
                if self.status_callback:
                    self.status_callback(app_name, "🟡 Cloud Data Available", "#f39c12")
            else:
                if local_time > cloud_time + 2.0:
                    if self.status_callback:
                        self.status_callback(app_name, "🟡 Out of Sync (Local Ahead)", "#f39c12")
                elif cloud_time > local_time + 2.0:
                    if self.status_callback:
                        self.status_callback(app_name, "🟡 Out of Sync (Cloud Ahead)", "#f39c12")
                else:
                    self.sync_states[app_name] = 'in_sync'
                    if self.status_callback:
                        self.status_callback(app_name, "🟢 Monitoring...", "#2ecc71")
                    self.start_watching(app_name, folder_path)
        except Exception as e:
            print(f"[Scan Error] {app_name}: {e}")
            if self.status_callback:
                self.status_callback(app_name, "🔴 Initialization Failed", "#e74c3c")

    def start_watching(self, app_name, folder_path):
        for watcher in self.watchers:
            if watcher.app_name == app_name and watcher.folder_path == folder_path:
                return
                
        if os.path.exists(folder_path):
            watcher = FolderWatcher(app_name, folder_path, self.sync_callback, status_callback=self.status_callback)
            self.watchers.append(watcher)
            self.observer.schedule(watcher, folder_path, recursive=True)
            print(f"[SyncEngine] Scheduled background watch for {app_name} at {folder_path}")

    def refresh_watchers(self):
        """Clear existing watchers and re-schedule from current mappings."""
        self.observer.unschedule_all()
        self.watchers.clear()
        
        print(f"[SyncEngine] Watchers cleared! Currently watching 0 folders.")

    def start(self):
        """
        Reads mappings, attaches FolderWatchers, and spawns the background thread execution.
        """
        self.refresh_watchers()
        
        mappings = self.mapping_manager.load_mappings()
        if mappings:
            for app_name, folder_path in mappings.items():
                threading.Thread(target=self.initial_scan, args=(app_name, folder_path)).start()

        # The watchdog.Observer internally spawns a daemon thread, so it won't block CustomTkinter UI.
        self.observer.start()
        print("[SyncEngine] Hardware Event Observer started in background.")

    def stop(self):
        """Gracefully shutdown the observer on exit."""
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
