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

"""
Schedule management module for School Bell Application.
Handles schedule checking, time management, and background thread operations.
"""

import datetime
import time
import threading
import logging
import gc
from PyQt6.QtCore import QTimer
from config import DAY_NAMES, TIMER_INTERVALS, ERROR_CONFIG
from database import (
    fetch_schedule_from_db, fetch_active_status_from_db, 
    fetch_current_preset_from_db, fetch_preset_for_day, check_day_active
)
from audio_manager import get_audio_manager
from logging_system import memory_monitor_decorator, force_garbage_collection


class ScheduleManager:
    """Manages schedule operations and background monitoring."""
    
    def __init__(self):
        self.current_schedule = []
        self.background_thread = None
        self.is_running = False
        self.thread_errors = 0
        self.last_schedule_update = 0
        self.schedule_cache = {}
        self.cache_timeout = 60  # Cache schedules for 60 seconds
        
    def load_schedule(self, preset_name):
        """Load schedule from database with caching."""
        if not preset_name:
            return []
        
        current_time = time.time()
        cache_key = preset_name
        
        # Check cache first
        if cache_key in self.schedule_cache:
            cached_data, cache_time = self.schedule_cache[cache_key]
            if current_time - cache_time < self.cache_timeout:
                logging.debug(f"Using cached schedule for {preset_name}")
                return cached_data.copy()
        
        # Load from database
        try:
            schedule = fetch_schedule_from_db(preset_name)
            if schedule:
                # Cache the result
                self.schedule_cache[cache_key] = (schedule.copy(), current_time)
                logging.info(f"Loaded schedule for preset '{preset_name}': {len(schedule)} periods")
            else:
                logging.warning(f"No schedule found for preset '{preset_name}'")
            
            return schedule
            
        except Exception as e:
            logging.error(f"Error loading schedule for {preset_name}: {e}")
            return []
    
    def clear_schedule_cache(self):
        """Clear the schedule cache."""
        self.schedule_cache.clear()
        logging.debug("Schedule cache cleared")
    
    def update_current_schedule(self, preset_name):
        """Update the current schedule."""
        if preset_name != getattr(self, 'current_preset', None):
            self.current_schedule = self.load_schedule(preset_name)
            self.current_preset = preset_name
            self.last_schedule_update = time.time()
            logging.info(f"Schedule updated to preset: {preset_name}")
            return True
        return False
    
    def get_current_schedule(self):
        """Get the current schedule."""
        return self.current_schedule.copy()
    
    def get_active_periods(self):
        """Get periods that should be active today."""
        current_day = get_current_day()
        day_name = get_day_name()
        
        if not check_day_active(day_name):
            logging.debug(f"Day {day_name} is not active")
            return []
        
        if not fetch_active_status_from_db():
            logging.debug("System is not active")
            return []
        
        return self.current_schedule
    
    def find_current_period(self, current_time_str=None):
        """Find the currently active period."""
        if current_time_str is None:
            current_time_str = get_local_time()
        
        for period in self.current_schedule:
            period_start = period.get("start")
            period_end = period.get("end")
            
            if not period_start or not period_end:
                continue
            
            if period_start <= current_time_str <= period_end:
                return period
        
        return None
    
    def find_next_period(self, current_time_str=None):
        """Find the next upcoming period."""
        if current_time_str is None:
            current_time_str = get_local_time()
        
        upcoming_periods = []
        for period in self.current_schedule:
            period_start = period.get("start")
            if period_start and period_start > current_time_str:
                upcoming_periods.append(period)
        
        if upcoming_periods:
            # Sort by start time and return the earliest
            upcoming_periods.sort(key=lambda p: p.get("start"))
            return upcoming_periods[0]
        
        return None
    
    def get_period_status(self, current_time_str=None):
        """Get comprehensive period status information."""
        if current_time_str is None:
            current_time_str = get_local_time()
        
        current_period = self.find_current_period(current_time_str)
        next_period = self.find_next_period(current_time_str)
        
        status = {
            'current_time': current_time_str,
            'current_period': current_period,
            'next_period': next_period,
            'is_active_time': current_period is not None,
            'remaining_time': None,
            'progress': 0
        }
        
        if current_period:
            try:
                start_time = datetime.datetime.strptime(current_period["start"], "%H:%M:%S")
                end_time = datetime.datetime.strptime(current_period["end"], "%H:%M:%S")
                current_time_dt = datetime.datetime.strptime(current_time_str, "%H:%M:%S")
                
                total_duration = (end_time - start_time).total_seconds()
                elapsed_time = (current_time_dt - start_time).total_seconds()
                remaining_time = (end_time - current_time_dt).total_seconds()
                
                if total_duration > 0:
                    progress = max(0, min(100, (elapsed_time / total_duration) * 100))
                else:
                    progress = 0
                
                status.update({
                    'remaining_time': max(0, remaining_time),
                    'progress': progress,
                    'total_duration': total_duration,
                    'elapsed_time': elapsed_time
                })
                
            except ValueError as e:
                logging.error(f"Error parsing time for period status: {e}")
        
        return status
    
    def start_background_monitoring(self, app_reference):
        """Start the background schedule monitoring thread."""
        if self.background_thread and self.background_thread.is_alive():
            logging.warning("Background monitoring already running")
            return False
        
        try:
            self.is_running = True
            self.thread_errors = 0
            
            self.background_thread = threading.Thread(
                target=self._background_monitor_wrapper,
                args=(app_reference,),
                daemon=True,
                name="ScheduleMonitorThread"
            )
            
            self.background_thread.start()
            logging.info("Background schedule monitoring started")
            return True
            
        except Exception as e:
            logging.error(f"Error starting background monitoring: {e}")
            self.is_running = False
            return False
    
    def stop_background_monitoring(self):
        """Stop the background schedule monitoring thread."""
        self.is_running = False
        
        if self.background_thread and self.background_thread.is_alive():
            logging.info("Stopping background monitoring thread...")
            try:
                self.background_thread.join(timeout=ERROR_CONFIG['thread_timeout'])
                if self.background_thread.is_alive():
                    logging.warning("Background thread did not stop within timeout")
                else:
                    logging.info("Background monitoring stopped successfully")
            except Exception as e:
                logging.error(f"Error stopping background thread: {e}")
        
        self.background_thread = None
    
    def _background_monitor_wrapper(self, app_reference):
        """Wrapper for background monitoring with exception handling."""
        try:
            self._background_monitor(app_reference)
        except KeyboardInterrupt:
            logging.info("Background monitor received KeyboardInterrupt")
        except Exception as e:
            logging.error(f"Fatal error in background monitor: {e}")
            logging.error(f"Thread errors: {self.thread_errors}")
        finally:
            logging.info("Background monitor thread ending")
    
    @memory_monitor_decorator
    def _background_monitor(self, app_reference):
        """Main background monitoring loop."""
        logging.info("Background schedule monitor starting")
        
        # Initialize monitoring variables
        iteration_count = 0
        last_gc_run = time.time()
        last_error_log = 0
        consecutive_errors = 0
        last_status_log = 0
        
        try:
            while self.is_running and getattr(app_reference, 'is_running', False):
                iteration_start = time.time()
                
                try:
                    iteration_count += 1
                    current_time = get_local_time()
                    
                    # Periodic status logging
                    if iteration_count % 3600 == 0:  # Every hour
                        hours = iteration_count / 3600
                        logging.info(f"Background monitor: {hours:.1f}h runtime, {iteration_count} iterations")
                    
                    # Garbage collection
                    if iteration_start - last_gc_run > TIMER_INTERVALS['background_check'] * 60:
                        collected = force_garbage_collection()
                        if collected > 0:
                            logging.debug(f"Background GC: freed {collected} objects")
                        last_gc_run = iteration_start
                    
                    # Check if system should be active
                    if not self._should_monitor():
                        time.sleep(TIMER_INTERVALS['background_check'])
                        continue
                    
                    # Get current schedule and preset
                    current_day = get_day_name()
                    day_preset = fetch_preset_for_day(current_day)
                    active_preset = day_preset or fetch_current_preset_from_db()
                    
                    if not active_preset:
                        time.sleep(TIMER_INTERVALS['background_check'])
                        continue
                    
                    # Update schedule if needed
                    if active_preset != getattr(self, 'current_preset', None):
                        self.update_current_schedule(active_preset)
                    
                    # Process schedule for audio triggers
                    self._process_schedule_triggers(current_time)
                    
                    # Update UI if possible
                    try:
                        if hasattr(app_reference, 'update_period_status'):
                            QTimer.singleShot(0, app_reference.update_period_status)
                    except Exception as ui_error:
                        logging.debug(f"UI update error: {ui_error}")
                    
                    consecutive_errors = 0  # Reset on success
                    
                except Exception as e:
                    consecutive_errors += 1
                    current_timestamp = time.time()
                    
                    # Throttle error logging
                    if current_timestamp - last_error_log > ERROR_CONFIG['error_log_interval']:
                        logging.error(f"Error in background monitor (#{consecutive_errors}): {e}")
                        last_error_log = current_timestamp
                    
                    # Check for too many consecutive errors
                    if consecutive_errors >= ERROR_CONFIG['max_consecutive_errors']:
                        logging.critical(f"Too many consecutive errors ({consecutive_errors}) in background monitor")
                        break
                    
                    time.sleep(TIMER_INTERVALS['background_check'] * 2)  # Wait longer on errors
                    continue
                
                # Sleep for the appropriate interval
                iteration_time = time.time() - iteration_start
                sleep_time = max(0.1, TIMER_INTERVALS['background_check'] - iteration_time)
                time.sleep(sleep_time)
                
                # Log slow iterations
                if iteration_time > 2.0:
                    logging.warning(f"Slow background iteration: {iteration_time:.2f}s")
        
        finally:
            logging.info(f"Background monitor ended after {iteration_count} iterations")
    
    def _should_monitor(self):
        """Check if background monitoring should be active."""
        try:
            # Check if system is active
            if not fetch_active_status_from_db():
                return False
            
            # Check if current day is active
            current_day = get_day_name()
            if not check_day_active(current_day):
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Error checking if should monitor: {e}")
            return False
    
    def _process_schedule_triggers(self, current_time):
        """Process schedule to check for audio triggers."""
        if not self.current_schedule:
            return
        
        audio_manager = get_audio_manager()
        
        for period in self.current_schedule:
            try:
                period_start = period.get("start")
                period_end = period.get("end")
                
                # Check for start time trigger
                if current_time == period_start:
                    audio_start = period.get("audio_start", [])
                    volume = period.get("volume", 1.0)
                    
                    if audio_start:
                        period_name = period.get('period', 'Unknown')
                        logging.info(f"AUDIO TRIGGER: Start audio for '{period_name}' at {current_time}")
                        
                        try:
                            success = audio_manager.play_audio(audio_start, volume)
                            if success:
                                logging.info(f"Start audio played successfully for '{period_name}'")
                            else:
                                logging.error(f"Failed to play start audio for '{period_name}'")
                        except Exception as audio_error:
                            logging.error(f"Audio playback error for '{period_name}': {audio_error}")
                
                # Check for end time trigger
                elif current_time == period_end:
                    audio_end = period.get("audio_end", [])
                    volume = period.get("volume", 1.0)
                    
                    if audio_end:
                        period_name = period.get('period', 'Unknown')
                        logging.info(f"AUDIO TRIGGER: End audio for '{period_name}' at {current_time}")
                        
                        try:
                            success = audio_manager.play_audio(audio_end, volume)
                            if success:
                                logging.info(f"End audio played successfully for '{period_name}'")
                            else:
                                logging.error(f"Failed to play end audio for '{period_name}'")
                        except Exception as audio_error:
                            logging.error(f"Audio playback error for '{period_name}': {audio_error}")
            
            except Exception as e:
                period_name = period.get('period', 'Unknown')
                logging.error(f"Error processing period '{period_name}': {e}")
                continue
    
    def get_monitor_status(self):
        """Get status of the background monitor."""
        return {
            'is_running': self.is_running,
            'thread_alive': self.background_thread.is_alive() if self.background_thread else False,
            'thread_name': self.background_thread.name if self.background_thread else None,
            'thread_errors': self.thread_errors,
            'schedule_count': len(self.current_schedule),
            'current_preset': getattr(self, 'current_preset', None),
            'last_update': self.last_schedule_update,
            'cache_size': len(self.schedule_cache)
        }


# Utility functions for time and date management
def get_local_time():
    """Get current local time as HH:MM:SS string."""
    return datetime.datetime.now().strftime("%H:%M:%S")


def get_current_day():
    """Get current weekday index (0=Monday, 6=Sunday)."""
    return datetime.datetime.now().weekday()


def get_day_name():
    """Get current day name."""
    return DAY_NAMES[get_current_day()]


def parse_time_string(time_str):
    """Parse time string to datetime object."""
    try:
        return datetime.datetime.strptime(time_str, "%H:%M:%S")
    except ValueError:
        # Try without seconds
        try:
            return datetime.datetime.strptime(time_str, "%H:%M")
        except ValueError as e:
            logging.error(f"Could not parse time string '{time_str}': {e}")
            return None


def format_duration(seconds):
    """Format duration in seconds to HH:MM:SS string."""
    try:
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    except (ValueError, TypeError):
        return "00:00:00"


def calculate_time_remaining(end_time_str, current_time_str=None):
    """Calculate time remaining until end time."""
    if current_time_str is None:
        current_time_str = get_local_time()
    
    try:
        end_time = parse_time_string(end_time_str)
        current_time = parse_time_string(current_time_str)
        
        if not end_time or not current_time:
            return 0
        
        difference = end_time - current_time
        return max(0, difference.total_seconds())
        
    except Exception as e:
        logging.error(f"Error calculating time remaining: {e}")
        return 0


def is_time_in_range(time_str, start_str, end_str):
    """Check if a time falls within a given range."""
    try:
        return start_str <= time_str <= end_str
    except (TypeError, ValueError):
        return False


def get_schedule_summary(schedule):
    """Get a summary of a schedule."""
    if not schedule:
        return "No schedule available"
    
    total_periods = len(schedule)
    periods_with_audio = sum(1 for p in schedule if p.get('audio_start') or p.get('audio_end'))
    
    try:
        start_times = [p.get('start') for p in schedule if p.get('start')]
        end_times = [p.get('end') for p in schedule if p.get('end')]
        
        earliest_start = min(start_times) if start_times else "N/A"
        latest_end = max(end_times) if end_times else "N/A"
        
        return (f"Schedule: {total_periods} periods, "
                f"{periods_with_audio} with audio, "
                f"runs from {earliest_start} to {latest_end}")
    except Exception as e:
        return f"Schedule: {total_periods} periods (error analyzing: {e})"


# Global schedule manager instance
_global_schedule_manager = None


def get_schedule_manager():
    """Get the global schedule manager instance."""
    global _global_schedule_manager
    
    if _global_schedule_manager is None:
        _global_schedule_manager = ScheduleManager()
    
    return _global_schedule_manager


def initialize_schedule_manager():
    """Initialize the global schedule manager."""
    global _global_schedule_manager
    _global_schedule_manager = ScheduleManager()
    return _global_schedule_manager


# Initialize when module is imported
logging.info("Schedule manager module initialized")