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
Logging Test Script - Verify the enhanced logging system works correctly
"""

import os
import sys
import datetime

# Add project root and src directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_dir = os.path.join(project_root, 'src')

for path in (project_root, src_dir, current_dir):
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    # Import the logging functions from the current modular app
    from src.logging_system import setup_logging, update_app_status, log_exception, log_memory_usage

    print("Testing enhanced logging system...")
    
    # Initialize logging
    main_log, crash_log = setup_logging()
    
    if main_log:
        print(f"✅ Logging initialized successfully!")
        print(f"Main log: {main_log}")
        if crash_log:
            print(f"Crash log: {crash_log}")
    else:
        print("❌ Logging initialization failed!")
        sys.exit(1)
    
    # Test logging functions
    import logging
    
    logging.info("="*50)
    logging.info("LOGGING SYSTEM TEST STARTED")
    logging.info("="*50)
    
    # Test different log levels
    logging.debug("This is a debug message")
    logging.info("This is an info message")
    logging.warning("This is a warning message")
    logging.error("This is an error message")
    logging.critical("This is a critical message")
    
    # Test app status updates
    update_app_status('TESTING', 'Running logging tests')
    
    # Test memory logging
    log_memory_usage("logging test")
    
    # Test exception logging (controlled)
    try:
        # This will cause a controlled exception for testing
        x = 1 / 0
    except Exception as e:
        logging.error(f"Controlled test exception: {e}")
    
    # Final status update
    update_app_status('TEST_COMPLETE', 'All logging tests completed')
    
    logging.info("="*50)
    logging.info("LOGGING SYSTEM TEST COMPLETED SUCCESSFULLY")
    logging.info("="*50)
    
    print("✅ Logging test completed successfully!")
    print(f"Check the log files in: {os.path.dirname(main_log) if main_log else 'Log directory'}")
    
except ImportError as e:
    print(f"❌ Could not import logging functions: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error during logging test: {e}")
    sys.exit(1)