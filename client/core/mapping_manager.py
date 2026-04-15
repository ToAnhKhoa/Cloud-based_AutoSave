import os
import json

class MappingManager:
    def __init__(self, user_id: str):
        self.user_id = user_id
        
        # APPDATA env config routing
        appdata = os.getenv('APPDATA')
        if not appdata:
            appdata = os.path.expanduser("~")
            
        self.config_dir = os.path.join(appdata, "CloudSaveClient")
        self.config_file = os.path.join(self.config_dir, f"mapping_{self.user_id}.json")
        
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            
    def load_mappings(self):
        """Returns a dictionary of mapped apps."""
        if not os.path.exists(self.config_file):
            return {}
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
            
    def save_mappings(self, data):
        """Writes the dictionary back to the JSON config."""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
            
    def add_mapping(self, app_name: str, folder_path: str):
        """Updates the mapping mapping safely."""
        mappings = self.load_mappings()
        mappings[app_name] = folder_path
        self.save_mappings(mappings)

    def remove_mapping(self, app_name: str):
        """Removes an app from the mapping dictionary safely."""
        mappings = self.load_mappings()
        if app_name in mappings:
            del mappings[app_name]
            self.save_mappings(mappings)

