# Copyright (C) 2026  Ali Qasem
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import sys
import json

def get_base_directory():
    """Get the application base directory."""
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = get_base_directory()
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
AUDIO_DIR = os.path.join(BASE_DIR, "assets", "audio_files")
ICON_PATH = os.path.join(BASE_DIR, "assets", "icons", "icon.ico")
TRAY_ICON_PATH = os.path.join(BASE_DIR, "assets", "icons", "icon.png")
MOE_PATH = os.path.join(BASE_DIR, "assets", "images", "MOE.png")
SCHOOL_LOGO_PATH = os.path.join(BASE_DIR, "assets", "images", "School.png")

APP_NAME = "School Bell App"
APP_VERSION = "2.0"
APP_AUTHOR = "Ali Qasem"

DEFAULT_CONFIG = {
    "db_file": "Jaras.db",
    "db_path": None
}

SUPPORTED_LANGUAGES = ["English", "Arabic"]

SUPPORTED_THEMES = ["Default", "Dark", "Light", "Sky Blue"]

SUPPORTED_AUDIO_FORMATS = ['.mp3', '.wav', '.ogg']

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

DATABASE_TABLES = {
    'Schedule': ['Period', 'Start_Time', 'End_Time', 'Audio_Start', 'Audio_End', 'Volume', 'Preset'],
    'Presets': ['name'],
    'Settings': ['id', 'language', 'theme', 'font', 'font_weight', 'font_size', 'height', 
                'directory', 'preset', 'active', 'password', 'lock'],
    'days': ['id', 'day_name', 'active', 'preset']
}

LOG_CONFIG = {
    'log_dir': os.path.join(os.getenv('APPDATA', ''), 'Ali AHK Qasem', 'SchoolBellApp', 'logs'),
    'main_log_prefix': 'school_bell_',
    'crash_log_prefix': 'crashes_',
    'max_log_size': 10 * 1024 * 1024,
    'backup_count': 5
}

MEMORY_CONFIG = {
    'gc_interval': 60,
    'memory_log_interval': 300,
    'memory_warning_threshold': 100,
    'memory_critical_threshold': 500
}

TIMER_INTERVALS = {
    'main_timer': 1,
    'heartbeat': 5,
    'system_monitor': 30, 
    'background_check': 1,
    'db_check': 10,
    'error_log': 30
}

ERROR_CONFIG = {
    'max_consecutive_errors': 10,
    'error_log_interval': 30,
    'thread_timeout': 5.0
}


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self):
        self.config_file = CONFIG_FILE
        self.config = {}
        self.load_config()
    
    def create_default_config(self):
        """Create default configuration file if it doesn't exist."""
        if not os.path.exists(self.config_file):
            # Set dynamic defaults
            default_config = DEFAULT_CONFIG.copy()
            default_config["db_path"] = os.path.join(BASE_DIR, default_config["db_file"])
            
            self.write_config(default_config)
            return default_config
        else:
            return {}
    
    def read_config(self):
        """Read configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as file:
                    config = json.load(file)
                    # Merge with defaults to ensure all keys exist
                    merged_config = DEFAULT_CONFIG.copy()
                    merged_config.update(config)
                    return merged_config
            else:
                return self.create_default_config()
        except json.JSONDecodeError:
            print(f"Configuration file corrupted: {self.config_file}")
            return self.create_default_config()
        except Exception as e:
            print(f"Error reading configuration: {e}")
            return self.create_default_config()
    
    def write_config(self, config=None):
        """Write configuration to file."""
        try:
            config_to_write = config if config is not None else self.config
            
            # Ensure directory exists
            config_dir = os.path.dirname(self.config_file)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            with open(self.config_file, 'w', encoding='utf-8') as file:
                json.dump(config_to_write, file, indent=2, ensure_ascii=False)
            
            if config is not None:
                self.config = config
                
        except Exception as e:
            print(f"Error writing configuration: {e}")
    
    def load_config(self):
        """Load configuration into memory."""
        self.config = self.read_config()
        return self.config
    
    def get(self, key, default=None):
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value and save."""
        self.config[key] = value
        self.write_config()
    
    def update(self, updates):
        """Update multiple configuration values."""
        self.config.update(updates)
        self.write_config()
    
    def get_database_path(self):
        """Get the current database path."""
        db_path = self.config.get("db_path")
        db_file = self.config.get("db_file", "Jaras.db")
        
        if db_path and os.path.exists(db_path):
            return db_path
        
        # Try base directory
        base_path = os.path.join(BASE_DIR, db_file)
        if os.path.exists(base_path):
            return base_path
        
        # Try current working directory
        cwd_path = os.path.join(os.getcwd(), db_file)
        if os.path.exists(cwd_path):
            return cwd_path
        
        return None
    
    def set_database_path(self, db_path):
        """Set the database path in configuration."""
        self.config["db_path"] = db_path
        self.config["db_file"] = os.path.basename(db_path)
        self.write_config()


# Global configuration instance
config_manager = ConfigManager()

# Convenient access to common paths
def get_audio_directory():
    """Get the configured audio directory."""
    audio_dir = config_manager.get("audio_directory")
    if audio_dir and os.path.exists(audio_dir):
        return audio_dir
    
    # Fallback to default
    if os.path.exists(AUDIO_DIR):
        return AUDIO_DIR
    
    # Create default if it doesn't exist
    try:
        os.makedirs(AUDIO_DIR, exist_ok=True)
        return AUDIO_DIR
    except:
        return None


def get_connection_string():
    """Get the database connection string."""
    return config_manager.get_database_path()


def ensure_directories():
    """Ensure all required directories exist."""
    directories = [
        LOG_CONFIG['log_dir'],
        get_audio_directory(),
        os.path.dirname(CONFIG_FILE)
    ]
    
    for directory in directories:
        if directory:
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                print(f"Could not create directory {directory}: {e}")


# Initialize directories on import
ensure_directories()


def setup_application_directories():
    """
    Setup application directories - alias for ensure_directories() for main.py compatibility.
    """
    try:
        ensure_directories()
        return True
    except Exception:
        return False


def validate_audio_file(file_path):
    """Validate if a file is a supported audio format."""
    if not os.path.exists(file_path):
        return False
    
    _, ext = os.path.splitext(file_path.lower())
    return ext in SUPPORTED_AUDIO_FORMATS


def get_available_audio_files(directory=None):
    """Get list of available audio files in the specified directory."""
    if directory is None:
        directory = get_audio_directory()
    
    if not directory or not os.path.exists(directory):
        return []
    
    audio_files = []
    try:
        for file in os.listdir(directory):
            if validate_audio_file(os.path.join(directory, file)):
                audio_files.append(file)
    except Exception as e:
        print(f"Error listing audio files: {e}")
    
    return sorted(audio_files)


def get_log_directory():
    """Get the logging directory, creating it if necessary."""
    log_dir = LOG_CONFIG['log_dir']
    try:
        os.makedirs(log_dir, exist_ok=True)
        return log_dir
    except Exception as e:
        print(f"Could not create log directory: {e}")
        # Fallback to current directory
        return os.getcwd()


# Validation functions
def validate_config():
    """Validate the current configuration and fix any issues."""
    config = config_manager.config
    is_valid = True
    
    # Check database path
    db_path = config.get("db_path")
    if db_path and not os.path.exists(db_path):
        print(f"Warning: Database file not found: {db_path}")
        is_valid = False
    
    # Check audio directory
    audio_dir = config.get("audio_directory")
    if audio_dir and not os.path.exists(audio_dir):
        print(f"Warning: Audio directory not found: {audio_dir}")
        # Try to create it
        try:
            os.makedirs(audio_dir, exist_ok=True)
            print(f"Created audio directory: {audio_dir}")
        except Exception as e:
            print(f"Could not create audio directory: {e}")
            is_valid = False
    
    # Validate language
    language = config.get("language", "English")
    if language not in SUPPORTED_LANGUAGES:
        print(f"Warning: Unsupported language '{language}', defaulting to English")
        config_manager.set("language", "English")
    
    # Validate theme
    theme = config.get("theme", "Default")
    if theme not in SUPPORTED_THEMES:
        print(f"Warning: Unsupported theme '{theme}', defaulting to Default")
        config_manager.set("theme", "Default")
    
    return is_valid


# Run validation on import
validate_config()