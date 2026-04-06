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
Memory profiling runner for School Bell App.

This script runs the current modular application with memory profiling enabled.
"""

import sys
import os
import time
import threading

import psutil

# Add project root and src directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_dir = os.path.join(project_root, 'src')

for path in (project_root, src_dir, current_dir):
    if path not in sys.path:
        sys.path.insert(0, path)

def monitor_memory_continuously():
    """Monitor memory usage continuously in a separate thread"""
    process = psutil.Process(os.getpid())
    start_time = time.time()
    
    with open('memory_log.txt', 'w') as f:
        f.write("Time(s),Memory(MB),CPU(%)\n")
        
        while True:
            try:
                current_time = time.time() - start_time
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                
                f.write(f"{current_time:.1f},{memory_mb:.2f},{cpu_percent:.2f}\n")
                f.flush()
                
                # Log warnings for high memory usage
                if memory_mb > 200:  # More than 200 MB
                    print(f"WARNING: High memory usage: {memory_mb:.2f} MB at {current_time:.1f}s")
                
                time.sleep(5)  # Log every 5 seconds
                
            except Exception as e:
                print(f"Error in memory monitoring: {e}")
                break

def run_with_profiling():
    """Run the application with memory profiling."""
    print("Starting memory profiling...")
    print("Memory usage will be logged to memory_log.txt")
    print("Application logs will show memory usage at key points")

    # Start continuous memory monitoring in background
    monitor_thread = threading.Thread(target=monitor_memory_continuously, daemon=True)
    monitor_thread.start()

    # Import and run the main application
    try:
        from PyQt6.QtWidgets import QApplication
        from main import setup_application_environment, check_system_requirements, initialize_database
        from src.main_app import SchoolBellApp

        if not setup_application_environment():
            print("Failed to set up application environment")
            return 1

        if not check_system_requirements():
            print("System requirements check failed")
            return 1

        if not initialize_database():
            print("Database initialization failed")
            return 1

        app = QApplication(sys.argv)
        window = SchoolBellApp()
        window.show()

        print("Application started. Monitor memory_log.txt for continuous memory usage.")
        print("Check the application logs for memory usage at key functions.")

        return app.exec()

    except ImportError as e:
        print(f"Error importing application modules: {e}")
        print("Make sure the project root and src modules are available")
        return 1
    except Exception as e:
        print(f"Error running application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_with_profiling())