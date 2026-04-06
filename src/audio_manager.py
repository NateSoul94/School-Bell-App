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
import random
import logging
import pygame
import time
from config import get_audio_directory, validate_audio_file, get_available_audio_files, SUPPORTED_AUDIO_FORMATS
from logging_system import memory_monitor_decorator


class AudioManager:
    
    def __init__(self, audio_directory=None):
        self.audio_directory = audio_directory or get_audio_directory()
        self.is_initialized = False
        self.current_volume = 1.0
        self.last_played_file = None
        self.playback_errors = 0
        self.max_errors = 5
        
        self.initialize_audio_system()
    
    def initialize_audio_system(self):
        try:
            if not pygame.get_init():
                pygame.init()
            
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                logging.info("Pygame mixer initialized successfully")
            
            self.is_initialized = True
            self.playback_errors = 0
            
        except Exception as e:
            logging.error(f"Error initializing audio system: {e}")
            self.is_initialized = False
    
    def check_audio_system(self):
        try:
            if not pygame.mixer.get_init():
                logging.warning("Pygame mixer not initialized, attempting to reinitialize")
                self.initialize_audio_system()
                return self.is_initialized
            return True
        except Exception as e:
            logging.error(f"Error checking audio system: {e}")
            return False
    
    def set_audio_directory(self, directory):
        if directory and os.path.exists(directory):
            self.audio_directory = directory
            logging.info(f"Audio directory set to: {directory}")
            return True
        else:
            logging.error(f"Invalid audio directory: {directory}")
            return False
    
    def get_audio_directory(self):
        return self.audio_directory
    
    def validate_audio_directory(self):
        if not self.audio_directory:
            logging.error("No audio directory set")
            return False
        
        if not os.path.exists(self.audio_directory):
            logging.error(f"Audio directory does not exist: {self.audio_directory}")
            return False
        
        return True
    
    def get_available_files(self):
        if not self.validate_audio_directory():
            return []
        
        return get_available_audio_files(self.audio_directory)
    
    def validate_file(self, file_name):
        if not file_name:
            return False
        
        file_path = os.path.join(self.audio_directory, file_name.strip())
        return validate_audio_file(file_path)
    
    def get_file_info(self, file_name):
        if not self.validate_file(file_name):
            return None
        
        file_path = os.path.join(self.audio_directory, file_name.strip())
        
        try:
            file_stats = os.stat(file_path)
            return {
                'name': file_name,
                'path': file_path,
                'size': file_stats.st_size,
                'size_mb': file_stats.st_size / 1024 / 1024,
                'modified': file_stats.st_mtime,
                'exists': True,
                'valid': True
            }
        except Exception as e:
            logging.error(f"Error getting file info for {file_name}: {e}")
            return {
                'name': file_name,
                'path': file_path,
                'exists': False,
                'valid': False,
                'error': str(e)
            }
    
    @memory_monitor_decorator
    def play_audio(self, file_names, volume=None):
        try:
            if not file_names:
                logging.warning("play_audio called with empty file_names")
                return False
            
            if isinstance(file_names, str):
                file_names = [file_names]
            elif not isinstance(file_names, (list, tuple)):
                logging.error(f"Invalid file_names type: {type(file_names)}")
                return False
            
            file_names = [f.strip() for f in file_names if f and f.strip()]
            if not file_names:
                logging.warning("No valid file names after filtering")
                return False
            
            if volume is not None:
                self.current_volume = max(0.0, min(1.0, float(volume)))
            
            if not self.check_audio_system():
                logging.error("Audio system not available")
                return False

            if not self.validate_audio_directory():
                logging.error(f"Audio directory not accessible: {self.audio_directory}")
                return False
            
            file_name = random.choice(file_names)
            file_path = os.path.join(self.audio_directory, file_name)
            
            logging.info(f"Attempting to play audio: {file_name}")
            logging.debug(f"Full path: {file_path}")
            logging.debug(f"Volume: {self.current_volume}")
            
            if not os.path.exists(file_path):
                logging.error(f"Audio file not found: {file_path}")
                self._log_available_files()
                return False
            
            try:
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    logging.error(f"Audio file is empty: {file_path}")
                    return False
                logging.debug(f"File size: {file_size} bytes")
            except Exception as e:
                logging.error(f"Could not check file size: {e}")
                return False
            
            if not validate_audio_file(file_path):
                logging.error(f"Unsupported audio format: {file_path}")
                return False
            
            self.stop_audio()
            
            time.sleep(0.05)
            
            return self._load_and_play_file(file_path, file_name)
            
        except Exception as e:
            logging.error(f"Critical error in play_audio: {e}")
            logging.error(f"Parameters - files: {file_names}, volume: {volume}")
            self.playback_errors += 1
            
            if self.playback_errors >= self.max_errors:
                logging.critical(f"Too many playback errors ({self.playback_errors}), reinitializing audio system")
                self.initialize_audio_system()
                self.playback_errors = 0
            
            return False
    
    def _load_and_play_file(self, file_path, file_name):
        try:
            logging.debug(f"Loading audio file: {file_path}")

            pygame.mixer.music.load(file_path)
            
            pygame.mixer.music.set_volume(self.current_volume)
            logging.debug(f"Volume set to: {self.current_volume}")
            
            pygame.mixer.music.play()
            
            if not pygame.mixer.music.get_busy():
                logging.warning("Audio playback may not have started (mixer not busy)")
                return False
            
            logging.info(f"Audio playback started successfully: {file_name}")
            self.last_played_file = file_name
            self.playback_errors = 0
            
            return True
            
        except pygame.error as e:
            logging.error(f"Pygame audio error with {file_path}: {e}")
            self._log_pygame_state()
            return False
            
        except Exception as e:
            logging.error(f"Unexpected error playing {file_path}: {e}")
            return False
    
    def _log_available_files(self):
        try:
            available_files = self.get_available_files()
            if available_files:
                logging.info(f"Available audio files ({len(available_files)}): {available_files[:10]}...")
            else:
                logging.warning("No audio files found in directory")
        except Exception as e:
            logging.error(f"Could not list available files: {e}")
    
    def _log_pygame_state(self):
        try:
            mixer_info = pygame.mixer.get_init()
            if mixer_info:
                logging.debug(f"Pygame mixer info: {mixer_info}")
            else:
                logging.warning("Pygame mixer not initialized")
            
            logging.debug(f"Pygame mixer channels: {pygame.mixer.get_num_channels()}")
            logging.debug(f"Currently playing: {pygame.mixer.music.get_busy()}")
            
        except Exception as e:
            logging.debug(f"Could not get pygame state: {e}")
    
    def stop_audio(self):
        try:
            if self.check_audio_system():
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                    logging.debug("Audio playback stopped")
                return True
            return False
        except Exception as e:
            logging.error(f"Error stopping audio: {e}")
            return False
    
    def pause_audio(self):
        try:
            if self.check_audio_system() and pygame.mixer.music.get_busy():
                pygame.mixer.music.pause()
                logging.debug("Audio playback paused")
                return True
            return False
        except Exception as e:
            logging.error(f"Error pausing audio: {e}")
            return False
    
    def unpause_audio(self):
        try:
            if self.check_audio_system():
                pygame.mixer.music.unpause()
                logging.debug("Audio playback unpaused")
                return True
            return False
        except Exception as e:
            logging.error(f"Error unpausing audio: {e}")
            return False
    
    def set_volume(self, volume):
        try:
            self.current_volume = max(0.0, min(1.0, float(volume)))
            
            if self.check_audio_system():
                pygame.mixer.music.set_volume(self.current_volume)
                logging.debug(f"Volume set to: {self.current_volume}")
                return True
            return False
        except Exception as e:
            logging.error(f"Error setting volume: {e}")
            return False
    
    def get_volume(self):
        return self.current_volume
    
    def is_playing(self):
        try:
            return self.check_audio_system() and pygame.mixer.music.get_busy()
        except Exception as e:
            logging.error(f"Error checking playback status: {e}")
            return False
    
    def get_playback_position(self):
        try:
            if self.check_audio_system() and pygame.mixer.music.get_busy():
                return pygame.mixer.music.get_pos()
            return -1
        except Exception as e:
            logging.debug(f"Could not get playback position: {e}")
            return -1
    
    def test_audio_file(self, file_name):
        if not file_name:
            return False, "No file name provided"
        
        file_path = os.path.join(self.audio_directory, file_name.strip())

        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"

        if not validate_audio_file(file_path):
            return False, f"Unsupported audio format"

        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False, "File is empty"
        except Exception as e:
            return False, f"Could not access file: {e}"

        try:
            if not self.check_audio_system():
                return False, "Audio system not available"

            was_playing = self.is_playing()
            current_pos = self.get_playback_position()

            pygame.mixer.music.load(file_path)

            if was_playing:

                pass
            
            return True, "File test successful"
            
        except Exception as e:
            return False, f"Could not load file: {e}"
    
    def get_audio_stats(self):
        stats = {
            'audio_system_initialized': self.is_initialized,
            'audio_directory': self.audio_directory,
            'directory_exists': os.path.exists(self.audio_directory) if self.audio_directory else False,
            'current_volume': self.current_volume,
            'is_playing': self.is_playing(),
            'last_played_file': self.last_played_file,
            'playback_errors': self.playback_errors,
            'available_files_count': 0,
            'supported_formats': SUPPORTED_AUDIO_FORMATS
        }
        
        try:
            available_files = self.get_available_files()
            stats['available_files_count'] = len(available_files)
            stats['available_files'] = available_files[:10]
        except Exception as e:
            stats['file_listing_error'] = str(e)
        
        try:
            if self.check_audio_system():
                mixer_info = pygame.mixer.get_init()
                if mixer_info:
                    stats['mixer_frequency'] = mixer_info[0]
                    stats['mixer_size'] = mixer_info[1]
                    stats['mixer_channels'] = mixer_info[2]
                
                stats['pygame_channels'] = pygame.mixer.get_num_channels()
        except Exception as e:
            stats['pygame_error'] = str(e)
        
        return stats
    
    def cleanup(self):
        try:
            self.stop_audio()
            
            if pygame.mixer.get_init():
                pygame.mixer.quit()
                logging.info("Pygame mixer shut down")
            
            self.is_initialized = False
            
        except Exception as e:
            logging.error(f"Error during audio cleanup: {e}")


_global_audio_manager = None


def get_audio_manager():
    global _global_audio_manager
    
    if _global_audio_manager is None:
        _global_audio_manager = AudioManager()
    
    return _global_audio_manager


def initialize_audio():
    global _global_audio_manager
    _global_audio_manager = AudioManager()
    return _global_audio_manager

def play_audio(file_names, volume=1.0, audio_dir=None):
    manager = get_audio_manager()

    if audio_dir and audio_dir != manager.get_audio_directory():
        manager.set_audio_directory(audio_dir)
    
    return manager.play_audio(file_names, volume)


def stop_audio():
    manager = get_audio_manager()
    return manager.stop_audio()


def set_audio_volume(volume):
    manager = get_audio_manager()
    return manager.set_volume(volume)


def is_audio_playing():
    manager = get_audio_manager()
    return manager.is_playing()


def get_audio_stats():
    manager = get_audio_manager()
    return manager.get_audio_stats()


def cleanup_audio():
    global _global_audio_manager
    
    if _global_audio_manager:
        _global_audio_manager.cleanup()
        _global_audio_manager = None

try:
    if not pygame.get_init():
        pygame.init()
    logging.info("Audio module initialized successfully")
except Exception as e:
    logging.error(f"Error initializing audio module: {e}")