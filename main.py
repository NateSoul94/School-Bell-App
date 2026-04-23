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

import sys
import os
import logging
from pathlib import Path

# Add the current directory and src directory to Python path to ensure module imports work
current_dir = Path(__file__).parent.absolute()
src_dir = current_dir / 'src'
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

def setup_application_environment():
    """
    Setup the application environment before launching.
    This includes error handling, logging, and system checks.
    """
    try:
        # Import configuration after path setup
        from src.config import setup_application_directories, config_manager, APP_NAME
        from src.logging_system import setup_logging, update_app_status
        
        print(f"Starting {APP_NAME} (Refactored Version)...")
        print(f"Working directory: {current_dir}")
        
        # Setup application directories
        print("Setting up application directories...")
        if not setup_application_directories():
            print("ERROR: Failed to create application directories")
            return False
        
        # Setup logging system
        print("Initializing logging system...")
        if not setup_logging():
            print("ERROR: Failed to initialize logging system")
            return False
        
        # Log startup
        logging.info("="*60)
        logging.info(f"{APP_NAME} - REFACTORED VERSION STARTING")
        logging.info("="*60)
        logging.info(f"Python version: {sys.version}")
        logging.info(f"Platform: {sys.platform}")
        logging.info(f"Working directory: {current_dir}")
        logging.info(f"Python path: {sys.path[:3]}...")  # Show first 3 entries
        
        # Update application status
        update_app_status('STARTING', 'Application environment setup completed')
        
        print("Application environment setup completed successfully")
        return True
        
    except ImportError as e:
        print(f"ERROR: Failed to import required modules: {e}")
        print("Please ensure all module files are present in the application directory")
        return False
    except Exception as e:
        print(f"ERROR: Critical error during environment setup: {e}")
        return False


def check_system_requirements():
    """
    Check system requirements and dependencies.
    """
    try:
        import logging
        logging.info("Checking system requirements...")
        
        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 7):
            logging.error(f"Python 3.7+ required, found {python_version.major}.{python_version.minor}")
            return False
        
        logging.info(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # Check required modules
        required_modules = [
            ('PyQt6', 'PyQt6.QtWidgets'),
            ('pygame', 'pygame'),
            ('sqlite3', 'sqlite3')
        ]
        
        missing_modules = []
        for module_name, import_name in required_modules:
            try:
                __import__(import_name)
                logging.info(f"✓ {module_name} available")
            except ImportError:
                logging.error(f"✗ {module_name} not available")
                missing_modules.append(module_name)
        
        if missing_modules:
            logging.error(f"Missing required modules: {missing_modules}")
            return False
        
        logging.info("All system requirements satisfied")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to check system requirements: {e}")
        return False


def initialize_database():
    """
    Initialize and verify database connection.
    """
    try:
        import logging
        from src.database import initialize_database, test_database_connection
        
        logging.info("Initializing database...")
        
        if not initialize_database():
            logging.error("Database initialization failed")
            return False
        
        if not test_database_connection():
            logging.error("Database connection test failed")
            return False
        
        logging.info("Database initialized and verified successfully")
        return True
        
    except Exception as e:
        logging.error(f"Database initialization error: {e}")
        return False


def launch_application():
    """
    Launch the main application with error handling and cleanup.
    """
    app = None
    main_window = None
    
    try:
        import logging
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from src.main_app import SchoolBellApp
        from src.database import fetch_window_from_db
        from src.logging_system import update_app_status, log_memory_usage
        
        logging.info("Creating Qt application...")
        
        # Enable high DPI scaling
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
        # Create Qt application
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # Keep running when window is closed
        
        # Log initial memory usage
        log_memory_usage("Application startup")
        
        logging.info("Creating main application window...")
        update_app_status('LAUNCHING', 'Creating main window')
        
        # Create and show main window
        main_window = SchoolBellApp()
        saved_window_mode = fetch_window_from_db()
        if saved_window_mode == "normal":
            main_window.show()
        else:
            main_window.showMaximized()
        
        logging.info("Application launched successfully")
        update_app_status('RUNNING', 'Application fully operational')
        
        # Start event loop
        logging.info("Starting Qt event loop...")
        exit_code = app.exec()
        
        logging.info(f"Application event loop ended with code: {exit_code}")
        return exit_code
        
    except KeyboardInterrupt:
        logging.info("Application interrupted by user (Ctrl+C)")
        return 0
    except SystemExit as e:
        logging.info(f"Application exit requested with code: {e.code}")
        return e.code or 0
    except Exception as e:
        logging.error(f"Critical error in main application: {e}")
        logging.exception("Full traceback:")
        update_app_status('CRASHED', f'Critical error: {str(e)}')
        
        # Show error dialog if possible
        try:
            if app and main_window:
                from src.ui_components import show_error_message
                show_error_message(f"Critical application error:\n{e}")
        except:
            print(f"CRITICAL ERROR: {e}")
        
        return 1
    finally:
        # Cleanup
        try:
            if main_window:
                main_window.close()
            if app:
                app.quit()
                
            # Final logging
            logging.info("Application cleanup completed")
            update_app_status('SHUTDOWN', 'Application terminated')
            
        except Exception as cleanup_error:
            logging.error(f"Error during cleanup: {cleanup_error}")


def handle_startup_error(error_message, show_dialog=True):
    """
    Handle startup errors with user notification.
    """
    try:
        from src.config import APP_NAME
        app_name = APP_NAME
    except ImportError:
        app_name = 'School Bell Application'
    
    error_text = f"Failed to start {app_name}:\n\n{error_message}"
    
    print(f"STARTUP ERROR: {error_message}")
    
    # Try to show GUI error dialog
    if show_dialog:
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            from PyQt6.QtGui import QIcon
            
            # Create minimal app for error dialog
            temp_app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Startup Error")
            msg.setText(error_text)
            msg.setInformativeText("Please check the console output for more details.")
            msg.exec()
            
        except Exception:
            # Fallback to console output
            print("\n" + "="*60)
            print("STARTUP ERROR")
            print("="*60)
            print(error_text)
            print("="*60)


def reset_language_to_english():
    """Reset the language setting to English in the database."""
    try:
        from src.database import save_language_to_db
        from src.config import setup_application_directories
        
        print("Resetting language to English...")
        setup_application_directories()
        save_language_to_db("English")
        print("Language successfully reset to English!")
        return True
    except Exception as e:
        print(f"Error resetting language: {e}")
        return False


def main():
    """
    Main entry point for the School Bell Application.
    Handles all initialization, error checking, and application launch.
    """
    try:
        # Check for special command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1] == "--reset-language" or sys.argv[1] == "-r":
                return 0 if reset_language_to_english() else 1
            elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
                print("School Bell Application - Refactored Version")
                print("Usage:")
                print("  python main.py              Start the application normally")
                print("  python main.py --reset-language  Reset language to English")
                print("  python main.py -r               Reset language to English (short)")
                print("  python main.py --help           Show this help message")
                return 0
        
        print("School Bell Application - Refactored Version")
        print("Initializing...")
        
        # Step 1: Setup environment
        if not setup_application_environment():
            handle_startup_error("Failed to setup application environment")
            return 1
        
        # Step 2: Check system requirements  
        if not check_system_requirements():
            handle_startup_error("System requirements not met")
            return 1
        
        # Step 3: Initialize database
        if not initialize_database():
            handle_startup_error("Database initialization failed")
            return 1
        
        # Step 4: Launch application
        exit_code = launch_application()
        
        print(f"Application exited with code: {exit_code}")
        return exit_code
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 0
    except Exception as e:
        error_message = f"Unexpected error during startup: {e}"
        handle_startup_error(error_message)
        return 1


if __name__ == "__main__":
    """
    Entry point when script is run directly.
    Ensures proper exit handling and return codes.
    """
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(1)