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
Logging and monitoring module for School Bell Application.
Handles comprehensive logging, crash detection, memory monitoring, and system health checks.
"""

import sys
import os
import datetime
import time
import logging
import json
import gc
import threading
from functools import wraps
from config import LOG_CONFIG, MEMORY_CONFIG, get_log_directory


# Global variables for monitoring
app_status_data = {
    'pid': os.getpid(),
    'start_time': datetime.datetime.now().isoformat(),
    'status': 'STARTING',
    'last_heartbeat': datetime.datetime.now().isoformat(),
    'expected_shutdown': False,
    'shutdown_reason': None
}

# Memory monitoring variables
_last_memory_log = 0
_last_gc_collection = 0


def setup_logging():
    """Setup comprehensive logging configuration with crash detection."""
    try:
        log_dir = get_log_directory()
        
        # Create log file paths
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(log_dir, f'{LOG_CONFIG["main_log_prefix"]}{timestamp}.log')
        crash_log = os.path.join(log_dir, f'{LOG_CONFIG["crash_log_prefix"]}{timestamp}.log')
        
        # Configure main logger with detailed formatting
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - [%(thread)d] - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Create separate crash logger
        crash_logger = logging.getLogger('crash_logger')
        crash_handler = logging.FileHandler(crash_log, encoding='utf-8')
        crash_handler.setFormatter(logging.Formatter('%(asctime)s - CRASH - %(message)s'))
        crash_logger.addHandler(crash_handler)
        crash_logger.setLevel(logging.ERROR)
        
        # Log comprehensive startup information
        log_startup_info(log_file, crash_log)
        
        # Create crash detector file
        create_crash_detector_file(log_dir)
        
        return log_file, crash_log
        
    except Exception as e:
        print(f"CRITICAL: Error setting up logging: {e}")
        return setup_fallback_logging()


def setup_fallback_logging():
    """Setup fallback logging to current directory if primary logging fails."""
    try:
        fallback_log = f'school_bell_fallback_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler(fallback_log), logging.StreamHandler(sys.stdout)]
        )
        logging.error(f"Using fallback logging to {fallback_log}")
        return fallback_log, None
    except:
        print("FATAL: Could not set up any logging")
        return None, None


def log_startup_info(log_file, crash_log):
    """Log comprehensive startup information."""
    logging.info("="*60)
    logging.info("SCHOOL BELL APPLICATION STARTUP")
    logging.info("="*60)
    logging.info(f"Application start time: {datetime.datetime.now()}")
    logging.info(f"Process ID: {os.getpid()}")
    logging.info(f"Python version: {sys.version}")
    logging.info(f"Platform: {sys.platform}")
    logging.info(f"Working directory: {os.getcwd()}")
    logging.info(f"Script location: {os.path.abspath(__file__)}")
    logging.info(f"Main log file: {log_file}")
    logging.info(f"Crash log file: {crash_log}")
    
    # Log system information
    log_system_info()
    
    # Log initial memory info
    log_memory_usage("application startup")


def log_system_info():
    """Log comprehensive system information."""
    try:
        import platform
        logging.info(f"OS: {platform.system()} {platform.release()}")
        logging.info(f"Architecture: {platform.architecture()}")
        logging.info(f"Processor: {platform.processor()}")
        logging.info(f"Machine: {platform.machine()}")
        logging.info(f"Node: {platform.node()}")
    except Exception as e:
        logging.warning(f"Could not get system info: {e}")
    
    # Log memory info
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        logging.info(f"Initial memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
        logging.info(f"Available system memory: {psutil.virtual_memory().available / 1024 / 1024:.2f} MB")
        logging.info(f"Total system memory: {psutil.virtual_memory().total / 1024 / 1024:.2f} MB")
        logging.info(f"CPU count: {psutil.cpu_count()}")
        logging.info(f"CPU usage: {psutil.cpu_percent()}%")
    except Exception as e:
        logging.warning(f"Could not get memory/CPU info: {e}")


def create_crash_detector_file(log_dir):
    """Create a crash detector file that gets updated during runtime."""
    try:
        crash_detector_file = os.path.join(log_dir, 'app_status.json')
        
        with open(crash_detector_file, 'w') as f:
            json.dump(app_status_data, f, indent=2)
            
        logging.info(f"Crash detector file created: {crash_detector_file}")
        return crash_detector_file
    except Exception as e:
        logging.error(f"Could not create crash detector file: {e}")
        return None


def update_app_status(status, reason=None):
    """Update application status for crash detection."""
    global app_status_data
    
    try:
        log_dir = get_log_directory()
        crash_detector_file = os.path.join(log_dir, 'app_status.json')
        
        app_status_data.update({
            'status': status,
            'last_heartbeat': datetime.datetime.now().isoformat(),
            'shutdown_reason': reason,
            'expected_shutdown': status == 'SHUTDOWN'
        })
        
        if os.path.exists(crash_detector_file):
            with open(crash_detector_file, 'w') as f:
                json.dump(app_status_data, f, indent=2)
        
        logging.debug(f"App status updated: {status} - {reason}")
    except Exception as e:
        logging.error(f"Could not update app status: {e}")


def log_exception(exc_type, exc_value, exc_traceback):
    """Enhanced exception logging with crash detection."""
    import traceback
    
    # Get crash logger
    crash_logger = logging.getLogger('crash_logger')
    
    # Handle KeyboardInterrupt as controlled shutdown
    if issubclass(exc_type, KeyboardInterrupt):
        logging.info("KeyboardInterrupt received - logging as controlled shutdown")
        crash_logger.info("KeyboardInterrupt - Controlled shutdown")
        update_app_status('SHUTDOWN', 'KeyboardInterrupt')
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # This is a real crash - log comprehensive details
    error_details = {
        'exception_type': exc_type.__name__,
        'exception_message': str(exc_value),
        'traceback': ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
        'time': datetime.datetime.now().isoformat(),
        'thread_id': threading.current_thread().ident,
        'thread_name': threading.current_thread().name
    }
    
    # Log to both main and crash loggers
    logging.critical("="*60)
    logging.critical("UNCAUGHT EXCEPTION - APPLICATION CRASH DETECTED")
    logging.critical("="*60)
    logging.critical(f"Exception Type: {error_details['exception_type']}")
    logging.critical(f"Exception Message: {error_details['exception_message']}")
    logging.critical(f"Thread: {error_details['thread_name']} ({error_details['thread_id']})")
    logging.critical("Full Traceback:")
    logging.critical(error_details['traceback'])
    
    crash_logger.error(f"CRASH: {error_details['exception_type']}: {error_details['exception_message']}")
    crash_logger.error(f"Thread: {error_details['thread_name']} ({error_details['thread_id']})")
    crash_logger.error(f"Traceback: {error_details['traceback']}")
    
    # Update status file
    update_app_status('CRASHED', f"{error_details['exception_type']}: {error_details['exception_message']}")
    
    # Log system state at crash
    log_system_state_at_crash()
    
    logging.critical("="*60)
    
    # Call original exception handler
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def log_system_state_at_crash():
    """Log comprehensive system state when a crash occurs."""
    try:
        logging.critical("SYSTEM STATE AT CRASH:")
        
        # Memory info
        log_memory_info_at_crash()
        
        # Thread info
        log_thread_info_at_crash()
        
        # Process info
        log_process_info_at_crash()
        
        # File system info
        log_filesystem_info_at_crash()
            
    except Exception as e:
        logging.critical(f"Error logging system state at crash: {e}")


def log_memory_info_at_crash():
    """Log memory information at crash."""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        logging.critical(f"Memory usage at crash: {memory_info.rss / 1024 / 1024:.2f} MB")
        logging.critical(f"Peak memory usage: {memory_info.peak_wset / 1024 / 1024:.2f} MB" if hasattr(memory_info, 'peak_wset') else "N/A")
        
        system_memory = psutil.virtual_memory()
        logging.critical(f"Available system memory: {system_memory.available / 1024 / 1024:.2f} MB")
        logging.critical(f"System memory usage: {system_memory.percent}%")
        
    except Exception as e:
        logging.critical(f"Could not get memory info at crash: {e}")


def log_thread_info_at_crash():
    """Log thread information at crash."""
    try:
        active_threads = threading.active_count()
        logging.critical(f"Active threads at crash: {active_threads}")
        
        for thread in threading.enumerate():
            status = 'Alive' if thread.is_alive() else 'Dead'
            daemon = 'Daemon' if thread.daemon else 'Main'
            logging.critical(f"Thread: {thread.name} (ID: {thread.ident}) - {status} - {daemon}")
            
    except Exception as e:
        logging.critical(f"Could not get thread info at crash: {e}")


def log_process_info_at_crash():
    """Log process information at crash."""
    try:
        import psutil
        process = psutil.Process()
        
        logging.critical(f"Process status: {process.status()}")
        logging.critical(f"Process CPU usage: {process.cpu_percent()}%")
        logging.critical(f"Process create time: {datetime.datetime.fromtimestamp(process.create_time())}")
        
        # Open files/connections
        try:
            open_files = len(process.open_files())
            connections = len(process.connections())
            logging.critical(f"Open files: {open_files}, Network connections: {connections}")
        except:
            pass
            
    except Exception as e:
        logging.critical(f"Could not get process info at crash: {e}")


def log_filesystem_info_at_crash():
    """Log filesystem information at crash."""
    try:
        # Check if database file exists
        from config import get_connection_string
        db_path = get_connection_string()
        if db_path:
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path)
                logging.critical(f"Database file exists: {db_path} ({db_size} bytes)")
            else:
                logging.critical(f"Database file missing: {db_path}")
        else:
            logging.critical("No database connection string available")
        
        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage(os.getcwd())
            logging.critical(f"Disk space - Total: {total//1024//1024} MB, Free: {free//1024//1024} MB")
        except:
            pass
            
    except Exception as e:
        logging.critical(f"Could not check filesystem info at crash: {e}")


def log_memory_usage(function_name="", force=False):
    """Log current memory usage with throttling."""
    global _last_memory_log
    
    current_time = time.time()
    
    # Throttle memory logging unless forced
    if not force and current_time - _last_memory_log < MEMORY_CONFIG['memory_log_interval']:
        return 0
    
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        context = f" ({function_name})" if function_name else ""
        logging.info(f"Memory usage{context}: {memory_mb:.2f} MB")
        
        # Warn about high memory usage
        if memory_mb > MEMORY_CONFIG['memory_warning_threshold']:
            level = logging.WARNING if memory_mb < MEMORY_CONFIG['memory_critical_threshold'] else logging.CRITICAL
            logging.log(level, f"High memory usage detected{context}: {memory_mb:.2f} MB")
        
        _last_memory_log = current_time
        return memory_mb
        
    except Exception as e:
        logging.error(f"Error getting memory usage: {e}")
        return 0


def memory_monitor_decorator(func):
    """Decorator to monitor memory usage of functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        
        try:
            before_mb = log_memory_usage(f"before {func_name}", force=True)
            result = func(*args, **kwargs)
            after_mb = log_memory_usage(f"after {func_name}", force=True)
            
            diff_mb = after_mb - before_mb
            if abs(diff_mb) > 1:  # Log significant memory changes (>1MB)
                logging.warning(f"Memory change in {func_name}: {diff_mb:+.2f} MB")
            
            return result
            
        except Exception as e:
            logging.error(f"Error in memory monitoring for {func_name}: {e}")
            return func(*args, **kwargs)  # Call function without monitoring
            
    return wrapper


def force_garbage_collection():
    """Force garbage collection and log results."""
    global _last_gc_collection
    
    current_time = time.time()
    
    # Only run GC if enough time has passed
    if current_time - _last_gc_collection < MEMORY_CONFIG['gc_interval']:
        return 0
    
    try:
        before_mb = log_memory_usage("before GC", force=True)
        collected = gc.collect()
        after_mb = log_memory_usage("after GC", force=True)
        
        if collected > 0:
            freed_mb = before_mb - after_mb
            logging.info(f"Garbage collection: freed {collected} objects, recovered {freed_mb:.2f} MB")
        
        _last_gc_collection = current_time
        return collected
        
    except Exception as e:
        logging.error(f"Error during garbage collection: {e}")
        return 0


def setup_system_exception_handling():
    """Set up system-wide exception handling."""
    sys.excepthook = log_exception
    
    # Set up threading exception handling for Python 3.8+
    if hasattr(threading, 'excepthook'):
        def thread_exception_handler(args):
            logging.error(f"Exception in thread {args.thread.name}: {args.exc_type.__name__}: {args.exc_value}")
            if args.exc_traceback:
                import traceback
                logging.error("Thread exception traceback:")
                logging.error(''.join(traceback.format_tb(args.exc_traceback)))
        
        threading.excepthook = thread_exception_handler


def create_periodic_health_check():
    """Create a function for periodic health monitoring."""
    last_health_check = {'time': 0}
    
    def health_check():
        """Perform periodic health check."""
        current_time = time.time()
        
        # Only run health check every 5 minutes
        if current_time - last_health_check['time'] < 300:
            return
        
        try:
            # Memory check
            memory_mb = log_memory_usage("health check", force=True)
            
            # Garbage collection if needed
            if memory_mb > MEMORY_CONFIG['memory_warning_threshold']:
                collected = force_garbage_collection()
                if collected > 0:
                    logging.info(f"Health check triggered GC: freed {collected} objects")
            
            # Thread count check
            thread_count = threading.active_count()
            if thread_count > 10:  # Arbitrary threshold
                logging.warning(f"High thread count detected: {thread_count}")
            
            # Update heartbeat
            update_app_status('RUNNING', f'Health check - Memory: {memory_mb:.1f}MB, Threads: {thread_count}')
            
            last_health_check['time'] = current_time
            
        except Exception as e:
            logging.error(f"Error during health check: {e}")
    
    return health_check


def log_application_shutdown(reason="Unknown"):
    """Log comprehensive application shutdown information."""
    try:
        uptime = time.time() - (time.mktime(datetime.datetime.fromisoformat(app_status_data['start_time']).timetuple()) if app_status_data['start_time'] else time.time())
        
        logging.info("="*60)
        logging.info("APPLICATION SHUTDOWN INITIATED")
        logging.info("="*60)
        logging.info(f"Shutdown reason: {reason}")
        logging.info(f"Shutdown time: {datetime.datetime.now()}")
        logging.info(f"Application uptime: {uptime:.1f} seconds ({uptime/3600:.2f} hours)")
        logging.info(f"Process ID: {os.getpid()}")
        
        # Final memory and system state
        log_memory_usage("final shutdown", force=True)
        
        # Thread information
        active_threads = threading.active_count()
        logging.info(f"Active threads at shutdown: {active_threads}")
        
        # Final garbage collection
        collected = gc.collect()
        logging.info(f"Final garbage collection: freed {collected} objects")
        
        # Update status file
        update_app_status('SHUTDOWN', reason)
        
        logging.info("="*60)
        
    except Exception as e:
        logging.error(f"Error during shutdown logging: {e}")


def get_crash_detector_status():
    """Get the current crash detector status."""
    try:
        log_dir = get_log_directory()
        crash_detector_file = os.path.join(log_dir, 'app_status.json')
        
        if os.path.exists(crash_detector_file):
            with open(crash_detector_file, 'r') as f:
                return json.load(f)
        else:
            return None
            
    except Exception as e:
        logging.error(f"Error reading crash detector status: {e}")
        return None


def analyze_previous_crashes():
    """Analyze previous application crashes from log files."""
    try:
        log_dir = get_log_directory()
        crash_info = []
        
        # Look for crash detector files
        status_file = os.path.join(log_dir, 'app_status.json')
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                status_data = json.load(f)
                
            if status_data.get('status') == 'CRASHED' and not status_data.get('expected_shutdown'):
                crash_info.append({
                    'type': 'unexpected_termination',
                    'time': status_data.get('last_heartbeat', 'Unknown'),
                    'reason': status_data.get('shutdown_reason', 'Unknown crash')
                })
        
        # Look for crash log files
        crash_logs = []
        for file in os.listdir(log_dir):
            if file.startswith(LOG_CONFIG['crash_log_prefix']) and file.endswith('.log'):
                crash_logs.append(os.path.join(log_dir, file))
        
        # Analyze recent crash logs (last 7 days)
        recent_crashes = 0
        cutoff_time = time.time() - (7 * 24 * 3600)  # 7 days ago
        
        for log_file in crash_logs:
            try:
                if os.path.getmtime(log_file) > cutoff_time:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        recent_crashes += content.count('CRASH:')
            except:
                continue
        
        if recent_crashes > 0:
            logging.warning(f"Found {recent_crashes} crashes in recent logs")
        
        return {
            'crash_info': crash_info,
            'recent_crashes': recent_crashes,
            'log_directory': log_dir
        }
        
    except Exception as e:
        logging.error(f"Error analyzing previous crashes: {e}")
        return {'error': str(e)}


class ApplicationMonitor:
    """Comprehensive application monitoring class."""
    
    def __init__(self):
        self.start_time = time.time()
        self.heartbeat_count = 0
        self.last_heartbeat = time.time()
        self.health_check_function = create_periodic_health_check()
        
    def heartbeat(self):
        """Application heartbeat - call this periodically."""
        self.heartbeat_count += 1
        current_time = time.time()
        
        # Update app status
        update_app_status('RUNNING', f'Heartbeat #{self.heartbeat_count}')
        
        # Log detailed heartbeat every 12th beat (1 minute if called every 5 seconds)
        if self.heartbeat_count % 12 == 0:
            uptime = current_time - self.start_time
            logging.info(f"HEARTBEAT #{self.heartbeat_count}: Uptime {uptime/3600:.1f}h")
        
        # Perform health check
        self.health_check_function()
        
        self.last_heartbeat = current_time
    
    def check_thread_health(self, expected_threads=None):
        """Check the health of application threads."""
        active_threads = threading.active_count()
        thread_names = [t.name for t in threading.enumerate()]
        
        if expected_threads:
            missing_threads = []
            for expected in expected_threads:
                if expected not in thread_names:
                    missing_threads.append(expected)
            
            if missing_threads:
                logging.error(f"Missing expected threads: {missing_threads}")
                return False
        
        logging.debug(f"Thread health check: {active_threads} active threads")
        return True
    
    def get_uptime(self):
        """Get application uptime in seconds."""
        return time.time() - self.start_time
    
    def get_status_summary(self):
        """Get a comprehensive status summary."""
        return {
            'uptime_seconds': self.get_uptime(),
            'uptime_hours': self.get_uptime() / 3600,
            'heartbeat_count': self.heartbeat_count,
            'last_heartbeat': self.last_heartbeat,
            'memory_mb': log_memory_usage("status check", force=True),
            'thread_count': threading.active_count(),
            'process_id': os.getpid()
        }


# Initialize logging when module is imported
main_log, crash_log = setup_logging()
setup_system_exception_handling()

# Log successful initialization
if main_log:
    logging.info("Logging system initialized successfully")
    logging.info(f"Main log: {main_log}")
    if crash_log:
        logging.info(f"Crash log: {crash_log}")
else:
    print("WARNING: Logging system initialization failed!")