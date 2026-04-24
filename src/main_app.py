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
Main application class for School Bell Application.
Refactored to use modular components for better maintainability and debugging.
"""

import os
import sys
import time
import datetime
import gc
import logging
from functools import partial

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QPushButton, QSlider, QFrame, QLCDNumber, QProgressBar,
    QHeaderView, QComboBox, QCheckBox, QSystemTrayIcon, QMenu, QSizePolicy,
    QStyledItemDelegate, QDialog, QFormLayout, QLineEdit, QColorDialog,
    QDialogButtonBox
)
from PyQt6.QtGui import QIcon, QGuiApplication, QPixmap, QColor, QBrush, QPalette
from PyQt6.QtCore import QTimer, Qt, QEvent, pyqtSignal

# Import our modular components
from config import (
    APP_NAME, ICON_PATH, TRAY_ICON_PATH, MOE_PATH, SCHOOL_LOGO_PATH,
    config_manager, get_audio_directory, DAY_NAMES
)
from database import (
    fetch_presets_from_db, fetch_schedule_from_db, save_current_preset_to_db,
    fetch_current_preset_from_db, fetch_active_status_from_db, update_active_status_in_db,
    fetch_language_from_db, save_language_to_db, fetch_theme_from_db, save_theme_to_db,
    save_window_to_db,
    fetch_font_settings_from_db, save_font_settings_to_db, fetch_height_from_db, save_height_to_db,
    fetch_audio_directory_from_db, save_audio_directory_to_db, fetch_lock_state_from_db,
    update_lock_state_in_db, fetch_password_from_db, save_password_to_db,
    fetch_days_from_db, update_day_status_in_db, save_day_preset_in_db,
    fetch_preset_for_day, update_schedule_in_db, insert_schedule_row, delete_schedule_row,
    create_preset, delete_preset, initialize_database, test_database_connection,
    fetch_colors_from_db, fetch_custom_theme_names_from_db,
    fetch_custom_theme_items_from_db, save_custom_theme_to_db, delete_custom_theme_from_db
)
from audio_manager import get_audio_manager, stop_audio
from schedule_manager import get_schedule_manager, get_local_time, get_day_name
from logging_system import (
    ApplicationMonitor, log_application_shutdown, memory_monitor_decorator,
    update_app_status, log_memory_usage
)
from ui_components import (
    MenuBar, AboutWindow, HelpWindow, TimePickerDialog,
    show_info_message, show_error_message, show_warning_message, show_question_dialog,
    get_text_input, get_integer_input, select_file, select_directory, select_font
)


THEME_COLOR_ITEMS = [
    "Window",
    "WindowText",
    "Base",
    "AlternateBase",
    "ToolTipBase",
    "ToolTipText",
    "Text",
    "MenuText",
    "Button",
    "ButtonText",
    "BrightText",
    "Link",
    "Highlight",
    "HighlightedText",
    "PlaceholderText",
    "DisabledText",
    "DisabledButtonText",
    "DisabledWindowText",
]


class CheckableAudioComboBox(QComboBox):
    """A combo box with checkable items for multi-select audio assignment."""

    popupClosed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setPlaceholderText("Select audio files")
        self.view().viewport().installEventFilter(self)

    def add_checkable_item(self, text, checked=False):
        self.addItem(text)
        item = self.model().item(self.count() - 1, 0)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        item.setData(
            Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked,
            Qt.ItemDataRole.CheckStateRole
        )

    def checked_items(self):
        selected = []
        for i in range(self.count()):
            item = self.model().item(i, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected.append(item.text())
        return selected

    def set_checked_items(self, selected_items):
        selected_set = {name.strip() for name in selected_items if name and name.strip()}
        for i in range(self.count()):
            item = self.model().item(i, 0)
            if not item:
                continue
            item.setCheckState(
                Qt.CheckState.Checked if item.text() in selected_set else Qt.CheckState.Unchecked
            )
        self._update_display_text()

    def eventFilter(self, obj, event):
        if obj == self.view().viewport() and event.type() == QEvent.Type.MouseButtonRelease:
            index = self.view().indexAt(event.pos())
            if index.isValid():
                item = self.model().itemFromIndex(index)
                if item:
                    new_state = Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked
                    item.setCheckState(new_state)
                    self._update_display_text()
            return True
        return super().eventFilter(obj, event)

    def hidePopup(self):
        super().hidePopup()
        self.popupClosed.emit()

    def _update_display_text(self):
        self.lineEdit().setText(','.join(self.checked_items()))


class AudioFileComboDelegate(QStyledItemDelegate):
    """Multi-select dropdown editor for audio file columns in the schedule table."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app

    def createEditor(self, parent, option, index):
        combo = CheckableAudioComboBox(parent)
        for file_name in self.app.get_available_audio_files():
            combo.add_checkable_item(file_name)

        current_value = index.data(Qt.ItemDataRole.EditRole) or ""
        selected = [f.strip() for f in current_value.split(',') if f.strip()]
        combo.set_checked_items(selected)

        combo.popupClosed.connect(lambda: self._commit_and_close_editor(combo))

        # Open the popup immediately so one click behaves like a picker.
        QTimer.singleShot(0, combo.showPopup)
        return combo

    def setEditorData(self, editor, index):
        current_value = index.data(Qt.ItemDataRole.EditRole) or ""
        selected = [f.strip() for f in current_value.split(',') if f.strip()]
        editor.set_checked_items(selected)

    def setModelData(self, editor, model, index):
        model.setData(index, ','.join(editor.checked_items()), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def _commit_and_close_editor(self, editor):
        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QStyledItemDelegate.EndEditHint.NoHint)


class CustomThemeEditorDialog(QDialog):
    """Dialog to create or edit a custom theme with live preview."""

    def __init__(self, parent_app, seed_theme_name, seed_colors, allow_delete=False):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self._delete_requested = False
        self.setWindowTitle("Custom Themes")
        self.setModal(True)
        self.resize(760, 500)

        self._colors = {item: seed_colors.get(item, "#FFFFFF") for item in THEME_COLOR_ITEMS}
        self._color_buttons = {}

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.theme_name_input = QLineEdit(self)
        self.theme_name_input.setText(seed_theme_name or "")
        self.theme_name_input.setPlaceholderText("Theme name")
        form_layout.addRow("Theme Name", self.theme_name_input)

        colors_grid = QGridLayout()
        for index, item_name in enumerate(THEME_COLOR_ITEMS):
            row = index // 2
            column_offset = (index % 2) * 2

            item_label = QLabel(item_name, self)
            button = QPushButton(self._colors[item_name], self)
            button.clicked.connect(partial(self._pick_color_for_item, item_name))
            self._set_button_preview(button, self._colors[item_name])
            self._color_buttons[item_name] = button
            colors_grid.addWidget(item_label, row, column_offset)
            colors_grid.addWidget(button, row, column_offset + 1)

        main_layout.addLayout(form_layout)
        main_layout.addLayout(colors_grid)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, self)
        if allow_delete:
            delete_button = button_box.addButton("Delete Theme", QDialogButtonBox.ButtonRole.DestructiveRole)
            delete_button.clicked.connect(self._request_delete)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        self._emit_live_preview()

    def _set_button_preview(self, button, color_hex):
        button.setText(color_hex)
        button.setStyleSheet(f"background-color: {color_hex};")

    def _pick_color_for_item(self, item_name):
        current_color = QColor(self._colors.get(item_name, "#FFFFFF"))
        picked = QColorDialog.getColor(current_color, self, f"Choose {item_name} Color")
        if not picked.isValid():
            return

        color_hex = picked.name().upper()
        self._colors[item_name] = color_hex
        self._set_button_preview(self._color_buttons[item_name], color_hex)
        self._emit_live_preview()

    def _emit_live_preview(self):
        if self.parent_app and hasattr(self.parent_app, "preview_custom_theme"):
            self.parent_app.preview_custom_theme(self._colors)

    def get_theme_payload(self):
        return (self.theme_name_input.text().strip(), dict(self._colors))

    def _request_delete(self):
        self._delete_requested = True
        self.accept()

    def delete_requested(self):
        return self._delete_requested


class SchoolBellApp(QMainWindow):
    """
    Refactored School Bell Application main class.
    Uses modular components for better separation of concerns and easier debugging.
    """
    
    def __init__(self):
        super().__init__()
        
        logging.info("Initializing SchoolBellApp (Refactored Version)...")
        update_app_status('INITIALIZING', 'Starting main application')
        
        # Initialize core application state
        self.is_running = True
        self._start_time = time.time()
        
        # Initialize data structures
        self.presets = []
        self.current_schedule = []
        self.current_preset = None
        self.selected_row = None
        self.locked = False
        self.is_full_screen = False
        self.digital_height = 50
        self.current_time = "00:00:00"
        self.current_language = "English"
        self.available_row_colors = []
        
        # Initialize managers
        self.audio_manager = get_audio_manager()
        self.schedule_manager = get_schedule_manager()
        self.app_monitor = ApplicationMonitor()
        
        # Initialize window references
        self.about_window = None
        self.help_window = None
        
        try:
            # Initialize database
            self._initialize_database()
            
            # Setup UI
            self._setup_application_window()
            self._setup_ui_components()
            self._setup_system_tray()
            
            # Load configuration and data
            self._load_configuration()
            self._load_application_data()
            
            # Setup timers and monitoring
            self._setup_timers()
            self._setup_monitoring()
            
            # Apply initial theme and settings
            self._apply_initial_settings()
            
            update_app_status('RUNNING', 'Application initialization completed')
            logging.info("SchoolBellApp initialization completed successfully")
            
        except Exception as e:
            logging.error(f"Critical error during initialization: {e}")
            update_app_status('CRASHED', f'Initialization error: {str(e)}')
            raise
    
    def _initialize_database(self):
        """Initialize database connection and verify schema."""
        logging.info("Initializing database connection...")
        
        if not initialize_database():
            logging.warning("Database initialization failed - some features may not work")
        elif not test_database_connection():
            logging.error("Database connection test failed")
        else:
            logging.info("Database initialized and tested successfully")
    
    def _setup_application_window(self):
        """Setup the main application window."""
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setGeometry(100, 100, 700, 530)
        self._center_window()
    
    def _setup_ui_components(self):
        """Setup all UI components."""
        logging.info("Setting up UI components...")
        
        # Create menu bar
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)
        
        # Create central widget and layout
        self._setup_central_widget()
        self._setup_header_section()
        self._setup_control_section()
        self._setup_table_section()
        
        logging.info("UI components setup completed")
    
    def _setup_central_widget(self):
        """Setup the central widget and main layout."""
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Add separator line
        self.separator_line = QFrame(self)
        self.separator_line.setFrameShape(QFrame.Shape.HLine)
        self.separator_line.setFrameShadow(QFrame.Shadow.Sunken)
        self.main_layout.addWidget(self.separator_line)
    
    def _setup_header_section(self):
        """Setup the header section with logos and time displays."""
        header_layout = QHBoxLayout()
        
        # School logo
        self.school_logo = QLabel(self)
        if os.path.exists(SCHOOL_LOGO_PATH):
            school_pixmap = QPixmap(SCHOOL_LOGO_PATH)
            self.school_logo.setPixmap(school_pixmap)
            self.school_logo.setScaledContents(True)
            self.school_logo.setMaximumSize(100, 100)
            self.school_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.school_logo)
        
        # Time and status section
        time_layout = QVBoxLayout()
        
        # Digital clock
        self.digital_clock = QLCDNumber(self)
        self.digital_clock.setDigitCount(8)
        self.digital_clock.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.digital_clock.setStyleSheet("color: green; font-weight: bold;")
        self.digital_clock.setFrameShape(QFrame.Shape.NoFrame)
        self.digital_clock.setFixedHeight(50)
        time_layout.addWidget(self.digital_clock)
        
        # Current preset label
        self.current_preset_label = QLabel("Preset: None", self)
        self.current_preset_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_layout.addWidget(self.current_preset_label)
        
        # System status label
        self.status_label = QLabel("Status: Unknown", self)
        self.status_label.setStyleSheet("font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_layout.addWidget(self.status_label)
        
        header_layout.addLayout(time_layout)
        
        # Status section
        status_layout = QVBoxLayout()
        
        # Remaining time display
        self.digital_remain = QLCDNumber(self)
        self.digital_remain.setDigitCount(8)
        self.digital_remain.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.digital_remain.setStyleSheet("color: red; font-weight: bold;")
        self.digital_remain.setFrameShape(QFrame.Shape.NoFrame)
        self.digital_remain.setFixedHeight(50)
        status_layout.addWidget(self.digital_remain)
        
        # Current day label
        self.current_day_label = QLabel(get_day_name(), self)
        self.current_day_label.setStyleSheet("font-weight: bold;")
        self.current_day_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.current_day_label)
        
        # Current period label
        self.current_period_label = QLabel("Period: None", self)
        self.current_period_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.current_period_label)
        
        header_layout.addLayout(status_layout)
        
        # MOE logo
        self.moe_logo = QLabel(self)
        if os.path.exists(MOE_PATH):
            moe_pixmap = QPixmap(MOE_PATH)
            self.moe_logo.setPixmap(moe_pixmap)
            self.moe_logo.setScaledContents(True)
            self.moe_logo.setMaximumSize(100, 100)
            self.moe_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.moe_logo)
        
        self.main_layout.addLayout(header_layout)
    
    def _setup_control_section(self):
        """Setup the control section with progress bar and buttons."""
        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMaximum(100)
        self.main_layout.addWidget(self.progress_bar)
        
        # Credit label
        self.credit_label = QLabel("Coded by: Ali Qasem", self)
        self.credit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.credit_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.main_layout.addWidget(self.credit_label)
        
        # Toggle view button
        self.toggle_view_button = QPushButton("Show Days", self)
        self.toggle_view_button.clicked.connect(self.toggle_days_schedule_view)
        self.main_layout.addWidget(self.toggle_view_button)
    
    def _setup_table_section(self):
        """Setup the table section with schedule and days tables."""
        # Schedule table
        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels([
            "Period", "Start Time", "End Time", "Audio Start", "Audio End", "Volume"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        for i in range(6):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        # Use dropdown editors for audio columns.
        self.audio_combo_delegate = AudioFileComboDelegate(self, self.table)
        self.table.setItemDelegateForColumn(3, self.audio_combo_delegate)
        self.table.setItemDelegateForColumn(4, self.audio_combo_delegate)
        
        self.table.itemChanged.connect(self.handle_item_changed)
        self.table.cellClicked.connect(self.handle_cell_clicked)
        self.table.cellDoubleClicked.connect(self.handle_cell_double_clicked)
        self.table.setVisible(True)
        self.main_layout.addWidget(self.table)
        
        # Days table
        self.days_table = QTableWidget(0, 3, self)
        self.days_table.setHorizontalHeaderLabels(["Day", "Active", "Preset"])
        self.days_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.days_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.days_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.days_table.setVisible(False)
        self.main_layout.addWidget(self.days_table)
    
    def _setup_system_tray(self):
        """Setup system tray icon and menu."""
        logging.info("Setting up system tray...")
        
        self.tray_icon = QSystemTrayIcon(QIcon(TRAY_ICON_PATH), self)
        self.tray_icon.setToolTip(APP_NAME)
        
        # Create tray menu
        tray_menu = QMenu()
        restore_action = tray_menu.addAction("Restore")
        restore_action.triggered.connect(self.show_window)
        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(lambda: self.exit_app("Tray menu exit"))
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_clicked)
        self.tray_icon.show()
        
        logging.info("System tray setup completed")
    
    def _load_configuration(self):
        """Load application configuration from database."""
        logging.info("Loading configuration...")
        
        # Load language
        self.current_language = fetch_language_from_db()
        logging.info(f"Language set to: {self.current_language}")
        
        # Load digital height
        self.digital_height = fetch_height_from_db()
        self.digital_clock.setFixedHeight(self.digital_height)
        self.digital_remain.setFixedHeight(self.digital_height)
        
        # Load lock state
        self.locked = fetch_lock_state_from_db()
        
        # Update menu bar
        self.menu_bar.update_language(self.current_language)
        self.menu_bar.update_lock_action(self.locked)
    
    def _load_application_data(self):
        """Load application data from database."""
        logging.info("Loading application data...")
        
        # Load presets
        self.load_presets()

        # Load row color options
        self.load_color_options()
        
        # Load audio directory
        self.load_audio_directory()
        
        # Load days table
        self.load_days_table()
        
        # Update status
        self.update_status_label()
        
        logging.info("Application data loaded")
    
    def _setup_timers(self):
        """Setup application timers."""
        logging.info("Setting up timers...")
        
        # Main update timer
        self.main_timer = QTimer(self)
        self.main_timer.timeout.connect(self.update_current_time)
        self.main_timer.start(1000)  # 1 second
        
        # Heartbeat timer
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(self.app_monitor.heartbeat)
        self.heartbeat_timer.start(5000)  # 5 seconds
        
        logging.info("Timers setup completed")
    
    def _setup_monitoring(self):
        """Setup background monitoring."""
        logging.info("Setting up background monitoring...")
        
        # Start schedule monitoring
        if not self.schedule_manager.start_background_monitoring(self):
            logging.error("Failed to start background monitoring")
        else:
            logging.info("Background monitoring started successfully")
    
    def _apply_initial_settings(self):
        """Apply initial theme and font settings."""
        logging.info("Applying initial settings...")
        
        # Apply theme
        saved_theme = fetch_theme_from_db()
        self.apply_theme(saved_theme)
        
        # Apply font
        font_family, font_weight, font_size = fetch_font_settings_from_db()
        self.apply_font_settings(font_family, font_weight, font_size)
        
        # Set lock state
        self.set_lock_state(self.locked)
        
        logging.info("Initial settings applied")
    
    @memory_monitor_decorator
    def load_presets(self):
        """Load presets from database."""
        try:
            self.presets = fetch_presets_from_db() or []
            
            if self.presets:
                self.menu_bar.refresh_presets()
                self.load_current_preset()
                logging.info(f"Loaded {len(self.presets)} presets")
            else:
                self.presets = []
                self.current_schedule = []
                logging.warning("No presets found in database")
                
        except Exception as e:
            logging.error(f"Error loading presets: {e}")
            show_error_message(f"Error loading presets: {e}")
    
    def load_current_preset(self):
        """Load the current active preset."""
        try:
            current_preset = fetch_current_preset_from_db()
            if current_preset and current_preset in self.presets:
                self.current_preset = current_preset
                self.current_schedule = fetch_schedule_from_db(current_preset)
                self.populate_schedule_table()
                self.current_preset_label.setText(f"Preset: {current_preset}")
                
                if self.menu_bar.preset_combo:
                    self.menu_bar.preset_combo.setCurrentText(current_preset)
                
                logging.info(f"Current preset loaded: {current_preset}")
            elif self.presets:
                # Use first available preset
                self.current_preset = self.presets[0]
                self.current_schedule = fetch_schedule_from_db(self.current_preset)
                self.populate_schedule_table()
                self.current_preset_label.setText(f"Preset: {self.current_preset}")
                logging.info(f"Using first available preset: {self.current_preset}")
            else:
                self.current_preset = None
                self.current_schedule = []
                self.current_preset_label.setText("Preset: None")

            self.sync_selected_row_color()
                
        except Exception as e:
            logging.error(f"Error loading current preset: {e}")

    def load_color_options(self):
        """Load available row colors from the database."""
        try:
            self.available_row_colors = fetch_colors_from_db() or []
            if self.menu_bar and hasattr(self.menu_bar, 'refresh_row_color_options'):
                self.menu_bar.refresh_row_color_options(self.available_row_colors)
            self.sync_selected_row_color()
            logging.info(f"Loaded {len(self.available_row_colors)} row colors")
        except Exception as e:
            logging.error(f"Error loading row colors: {e}")
    
    def load_audio_directory(self):
        """Load audio directory from database."""
        try:
            audio_dir = fetch_audio_directory_from_db()
            if audio_dir and os.path.exists(audio_dir):
                self.audio_manager.set_audio_directory(audio_dir)
                logging.info(f"Audio directory loaded: {audio_dir}")
            else:
                # Use default audio directory
                default_dir = get_audio_directory()
                if default_dir:
                    self.audio_manager.set_audio_directory(default_dir)
                    logging.info(f"Using default audio directory: {default_dir}")
                else:
                    logging.warning("No audio directory available")
        except Exception as e:
            logging.error(f"Error loading audio directory: {e}")
    
    def sync_selected_row_color(self):
        """Sync the Tables > Color combo with the selected schedule row."""
        if not self.menu_bar or not hasattr(self.menu_bar, 'set_selected_row_color'):
            return

        color_hex = ""
        if self.selected_row is not None and 0 <= self.selected_row < len(self.current_schedule):
            color_hex = self.current_schedule[self.selected_row].get("color", "") or ""

        self.menu_bar.set_selected_row_color(color_hex)

    def apply_selected_row_color(self, color_hex, color_name=None):
        """Apply the chosen color to the currently selected schedule row."""
        try:
            if self.selected_row is None or self.selected_row < 0:
                return
            if self.selected_row >= len(self.current_schedule):
                return

            color_hex = (color_hex or "").strip()
            self.current_schedule[self.selected_row]["color"] = color_hex
            self._apply_color_to_row(self.selected_row, color_hex)

            if self.current_preset:
                period_name = self.current_schedule[self.selected_row].get("period", "")
                if period_name:
                    update_schedule_in_db(self.current_preset, period_name, "color", color_hex)

            if self.schedule_manager:
                self.schedule_manager.clear_schedule_cache()

            logging.info(f"Row color updated for row {self.selected_row}: {color_name or color_hex or 'No Color'}")
        except Exception as e:
            logging.error(f"Error applying selected row color: {e}")
            show_error_message(f"Failed to apply row color: {str(e)}", "Error", self)

    def _apply_color_to_row(self, row, color_hex):
        """Apply background coloring to all visible cells in a schedule row."""
        try:
            color_hex = (color_hex or "").strip()
            use_color = bool(color_hex)
            background_color = QColor(color_hex) if use_color else QColor()

            if use_color and not background_color.isValid():
                logging.warning(f"Invalid row color skipped: {color_hex}")
                return

            brightness = (
                ((background_color.red() * 299) + (background_color.green() * 587) + (background_color.blue() * 114)) / 1000
                if use_color else 255
            )
            foreground_color = QColor("#000000" if brightness >= 186 else "#FFFFFF")

            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item:
                    if use_color:
                        item.setBackground(QBrush(background_color))
                        item.setForeground(QBrush(foreground_color))
                    else:
                        item.setData(Qt.ItemDataRole.BackgroundRole, None)
                        item.setData(Qt.ItemDataRole.ForegroundRole, None)

                widget = self.table.cellWidget(row, column)
                if widget:
                    if use_color:
                        widget.setStyleSheet(f"background-color: {color_hex}; border: none;")
                    else:
                        widget.setStyleSheet("")

        except Exception as e:
            logging.error(f"Error applying row color styling: {e}")

    def load_days_table(self):
        """Load and populate the days table."""
        try:
            days_data = fetch_days_from_db()
            if not days_data:
                logging.warning("No days data found in database")
                return
            
            self.days_table.clearContents()
            self.days_table.setRowCount(len(days_data))
            
            for row, day in enumerate(days_data):
                # Day name (read-only)
                day_item = QTableWidgetItem(day["day_name"])
                day_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                day_item.setFlags(day_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.days_table.setItem(row, 0, day_item)
                
                # Active checkbox
                checkbox = QCheckBox()
                checkbox.setChecked(bool(day["active"]))
                checkbox.stateChanged.connect(partial(self.update_day_status, day["id"]))
                
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                self.days_table.setCellWidget(row, 1, checkbox_widget)
                
                # Preset combo
                preset_combo = QComboBox()
                preset_items = ["(Default)"] + self.presets
                preset_combo.addItems(preset_items)
                
                if day.get("preset"):
                    preset_combo.setCurrentText(day["preset"])
                else:
                    preset_combo.setCurrentText("(Default)")
                
                preset_combo.currentTextChanged.connect(partial(self.update_day_preset, day["id"]))
                
                preset_widget = QWidget()
                preset_layout = QHBoxLayout(preset_widget)
                preset_layout.addWidget(preset_combo)
                preset_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                preset_layout.setContentsMargins(0, 0, 0, 0)
                self.days_table.setCellWidget(row, 2, preset_widget)
            
            logging.info(f"Days table loaded with {len(days_data)} entries")
            
        except Exception as e:
            logging.error(f"Error loading days table: {e}")
    
    @memory_monitor_decorator
    def populate_schedule_table(self):
        """Populate the schedule table with current schedule data."""
        try:
            self.table.blockSignals(True)
            
            # Clear existing content
            for row in range(self.table.rowCount()):
                widget = self.table.cellWidget(row, 5)  # Volume slider widget
                if widget:
                    slider = widget.findChild(QSlider)
                    if slider:
                        slider.valueChanged.disconnect()
                    self.table.removeCellWidget(row, 5)
                    widget.deleteLater()
            
            self.table.clearContents()
            
            if not self.current_schedule:
                self.table.setRowCount(0)
                return
            
            # Sort schedule by start time
            self.current_schedule.sort(key=lambda p: p.get("start", "00:00:00"))
            self.table.setRowCount(len(self.current_schedule))
            
            for row, period in enumerate(self.current_schedule):
                # Period name
                period_item = QTableWidgetItem(str(period.get("period", "")))
                period_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 0, period_item)
                
                # Start time
                start_item = QTableWidgetItem(str(period.get("start", "")))
                start_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 1, start_item)
                
                # End time
                end_item = QTableWidgetItem(str(period.get("end", "")))
                end_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 2, end_item)
                
                # Audio start files
                audio_start = period.get("audio_start", [])
                if isinstance(audio_start, list):
                    audio_start_text = ','.join(audio_start)
                else:
                    audio_start_text = str(audio_start)
                start_audio_item = QTableWidgetItem(audio_start_text)
                start_audio_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 3, start_audio_item)
                
                # Audio end files
                audio_end = period.get("audio_end", [])
                if isinstance(audio_end, list):
                    audio_end_text = ','.join(audio_end)
                else:
                    audio_end_text = str(audio_end)
                end_audio_item = QTableWidgetItem(audio_end_text)
                end_audio_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 4, end_audio_item)
                
                # Volume slider
                volume_slider = QSlider(Qt.Orientation.Horizontal)
                volume_slider.setRange(0, 100)
                volume_value = int(float(period.get("volume", 1.0)) * 100)
                volume_slider.setValue(max(0, min(100, volume_value)))
                volume_slider.valueChanged.connect(partial(self.update_volume, row))
                
                volume_widget = QWidget()
                volume_layout = QHBoxLayout(volume_widget)
                volume_layout.addWidget(volume_slider)
                volume_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                volume_layout.setContentsMargins(0, 0, 0, 0)
                
                # Set layout direction for volume widget to match table direction
                if self.current_language == "Arabic":
                    volume_widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                else:
                    volume_widget.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
                
                self.table.setCellWidget(row, 5, volume_widget)
                self._apply_color_to_row(row, period.get("color", ""))
            
            self.sync_selected_row_color()

            # Force garbage collection
            gc.collect()
            
        except Exception as e:
            logging.error(f"Error populating schedule table: {e}")
        finally:
            self.table.blockSignals(False)
    
    def update_current_time(self):
        """Update the current time display and period status."""
        try:
            current_time = get_local_time()
            if current_time != self.current_time:
                self.current_time = current_time
                self.digital_clock.display(self.current_time)
                self.current_day_label.setText(get_day_name())
                
                # Update period status
                self.update_period_status()
                
                # Update schedule if needed
                self._check_and_update_schedule()
        
        except Exception as e:
            logging.error(f"Error updating current time: {e}")
    
    def _check_and_update_schedule(self):
        """Check if schedule needs updating based on current day preset."""
        try:
            current_day = get_day_name()
            day_preset = fetch_preset_for_day(current_day)
            
            if day_preset:
                # Day has a specific preset, load it without saving as global
                if day_preset != self.current_preset:
                    self.update_schedule(day_preset, save_as_global=False)
            else:
                # No day-specific preset, use global preset
                global_preset = fetch_current_preset_from_db()
                if global_preset and global_preset != self.current_preset:
                    self.update_schedule(global_preset, save_as_global=False)
        except Exception as e:
            logging.debug(f"Error checking schedule update: {e}")
    
    def update_period_status(self):
        """Update the period status display."""
        try:
            if not self.current_schedule:
                self.current_period_label.setText("Period: None")
                self.digital_remain.display("00:00:00")
                self.progress_bar.setValue(0)
                return
            
            current_time_str = self.current_time
            
            # Find current active period
            for period in self.current_schedule:
                start_time = period.get("start")
                end_time = period.get("end")
                
                if not start_time or not end_time:
                    continue
                
                if start_time <= current_time_str <= end_time:
                    period_name = period.get('period', 'Unknown')
                    self.current_period_label.setText(f"Period: {period_name}")
                    
                    # Calculate remaining time and progress
                    try:
                        start_dt = datetime.datetime.strptime(start_time, "%H:%M:%S")
                        end_dt = datetime.datetime.strptime(end_time, "%H:%M:%S")
                        current_dt = datetime.datetime.strptime(current_time_str, "%H:%M:%S")
                        
                        remaining_time = end_dt - current_dt
                        total_time = end_dt - start_dt
                        
                        if remaining_time.total_seconds() <= 0:
                            self.digital_remain.display("00:00:00")
                            self.progress_bar.setValue(100)
                        else:
                            total_seconds = int(remaining_time.total_seconds())
                            hours, remainder = divmod(total_seconds, 3600)
                            minutes, seconds = divmod(remainder, 60)
                            formatted_time = f"{hours:02}:{minutes:02}:{seconds:02}"
                            
                            self.digital_remain.display(formatted_time)
                            
                            # Calculate progress
                            if total_time.total_seconds() > 0:
                                elapsed = (current_dt - start_dt).total_seconds()
                                progress = int((elapsed / total_time.total_seconds()) * 100)
                                self.progress_bar.setValue(max(0, min(100, progress)))
                            else:
                                self.progress_bar.setValue(0)
                    
                    except ValueError as e:
                        logging.error(f"Time parsing error: {e}")
                        self.digital_remain.display("ERROR")
                        self.progress_bar.setValue(0)
                    
                    return
            
            # No active period found
            self.current_period_label.setText("Period: None")
            self.digital_remain.display("00:00:00")
            self.progress_bar.setValue(0)
            
        except Exception as e:
            logging.error(f"Error updating period status: {e}")
            self.current_period_label.setText("Period: Error")
            self.digital_remain.display("00:00:00")
            self.progress_bar.setValue(0)
    
    def update_status_label(self):
        """Update the system status label."""
        try:
            is_active = fetch_active_status_from_db()
            status_text = "Active" if is_active else "Inactive"
            color = "green" if is_active else "red"
            self.status_label.setText(f"Status: {status_text}")
            self.status_label.setStyleSheet(f"font-weight: bold; color: {color};")
        except Exception as e:
            logging.error(f"Error updating status label: {e}")
            self.status_label.setText("Status: Error")
            self.status_label.setStyleSheet("font-weight: bold; color: red;")
    
    # Event handlers and UI methods
    def closeEvent(self, event):
        """Handle window close event - minimize to tray instead of closing."""
        if self.is_running:
            logging.info("Minimizing to system tray")
            event.ignore()
            self.hide()
            
            try:
                self.tray_icon.showMessage(
                    "Minimized",
                    "The app is running in the system tray.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
            except Exception as e:
                logging.error(f"Error showing tray notification: {e}")
            
            update_app_status('RUNNING', 'Minimized to system tray')
        else:
            logging.info("Application shutdown - allowing close event")
            event.accept()
    
    def show_window(self):
        """Show and activate the main window."""
        self.showNormal()
        self.activateWindow()
        self.raise_()
    
    def tray_icon_clicked(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()
    
    def exit_app(self, reason="User request"):
        """Gracefully exit the application."""
        try:
            logging.info(f"Application exit requested: {reason}")
            log_application_shutdown(reason)
            
            # Stop running flag
            self.is_running = False
            
            # Stop timers
            if hasattr(self, 'main_timer'):
                self.main_timer.stop()
            if hasattr(self, 'heartbeat_timer'):
                self.heartbeat_timer.stop()
            
            # Stop background monitoring
            if self.schedule_manager:
                self.schedule_manager.stop_background_monitoring()
            
            # Hide tray icon
            if hasattr(self, 'tray_icon'):
                self.tray_icon.hide()
            
            # Clean up audio
            if self.audio_manager:
                self.audio_manager.cleanup()
            
            # Close additional windows
            if self.about_window:
                self.about_window.close()
            if self.help_window:
                self.help_window.close()
            
            # Final garbage collection
            gc.collect()
            
            logging.info("Application cleanup completed")
            
            # Close the application
            from PyQt6.QtWidgets import QApplication
            QApplication.quit()
            
        except Exception as e:
            logging.error(f"Error during application exit: {e}")
            # Force exit if cleanup fails
            try:
                import os
                os._exit(1)
            except:
                pass
    
    # Menu action handlers
    def refresh_app(self):
        """Refresh the application data."""
        try:
            self.load_presets()
            self.load_color_options()
            self.load_audio_directory()
            self.load_days_table()
            self.update_status_label()
            show_info_message("Application refreshed successfully.")
            logging.info("Application refreshed by user")
        except Exception as e:
            logging.error(f"Error refreshing application: {e}")
            show_error_message(f"Error refreshing application: {e}")
    
    def toggle_active_status(self):
        """Toggle the system active status."""
        try:
            current_status = fetch_active_status_from_db()
            new_status = not current_status
            
            if update_active_status_in_db(new_status):
                self.update_status_label()
                status_text = "Active" if new_status else "Inactive"
                show_info_message(f"System is now {status_text}")
                logging.info(f"System status changed to: {status_text}")
            else:
                show_error_message("Failed to update system status")
        except Exception as e:
            logging.error(f"Error toggling active status: {e}")
            show_error_message(f"Error updating status: {e}")
    
    def stop_audio(self):
        """Stop any currently playing audio."""
        try:
            if self.audio_manager.stop_audio():
                logging.info("Audio stopped by user")
            else:
                logging.warning("Audio stop request failed")
        except Exception as e:
            logging.error(f"Error stopping audio: {e}")
    
    def set_audio_directory(self):
        """Set the audio directory."""
        try:
            audio_dir = select_directory("Select Audio Directory", parent=self)
            if audio_dir:
                if self.audio_manager.set_audio_directory(audio_dir):
                    save_audio_directory_to_db(audio_dir)
                    show_info_message(f"Audio directory set to:\n{audio_dir}")
                    logging.info(f"Audio directory changed to: {audio_dir}")
                else:
                    show_error_message("Failed to set audio directory")
        except Exception as e:
            logging.error(f"Error setting audio directory: {e}")
            show_error_message(f"Error setting audio directory: {e}")
    
    def set_default_audio_directory(self):
        """Set the default audio directory."""
        try:
            default_dir = os.path.join(
                os.path.expanduser('~'),
                'AppData',
                'Roaming',
                'Ali AHK Qasem',
                'SchoolBellApp',
                'audio_files'
            )
            os.makedirs(default_dir, exist_ok=True)
            
            if self.audio_manager.set_audio_directory(default_dir):
                save_audio_directory_to_db(default_dir)
                show_info_message(f"Default audio directory set to:\n{default_dir}")
                logging.info(f"Default audio directory set: {default_dir}")
            else:
                show_error_message("Failed to set default audio directory")
        except Exception as e:
            logging.error(f"Error setting default audio directory: {e}")
            show_error_message(f"Error setting default audio directory: {e}")
    
    def update_schedule(self, preset_name, save_as_global=True):
        """Update the current schedule to use the specified preset.
        
        Args:
            preset_name: Name of the preset to load
            save_as_global: If True, saves this as the global default preset.
                           If False, only displays the schedule without changing global preset.
        """
        try:
            logging.debug(f"Attempting to update schedule to preset: {preset_name}")
            logging.debug(f"Available presets: {self.presets}")
            
            if preset_name and preset_name in self.presets:
                self.current_preset = preset_name
                
                # Update schedule manager
                self.schedule_manager.update_current_schedule(preset_name)
                self.current_schedule = self.schedule_manager.get_current_schedule()
                
                # Update UI
                self.populate_schedule_table()
                self.current_preset_label.setText(f"Preset: {preset_name}")
                
                # Update menu bar combo box only if saving as global
                if save_as_global and self.menu_bar.preset_combo:
                    self.menu_bar.preset_combo.blockSignals(True)
                    self.menu_bar.preset_combo.setCurrentText(preset_name)
                    self.menu_bar.preset_combo.blockSignals(False)
                
                # Save to database only if this is a global preset change
                if save_as_global:
                    save_current_preset_to_db(preset_name)
                    logging.info(f"Schedule updated to preset: {preset_name} (saved as global)")
                else:
                    logging.info(f"Schedule updated to preset: {preset_name} (day-specific, not saved as global)")
            else:
                logging.warning(f"Invalid preset name: {preset_name} (not in available presets)")
        except Exception as e:
            logging.error(f"Error updating schedule: {e}", exc_info=True)
    
    def create_new_preset(self):
        """Create a new preset."""
        try:
            preset_name, ok = get_text_input("Enter new preset name:", "New Preset", parent=self)
            if ok and preset_name.strip():
                preset_name = preset_name.strip()
                if create_preset(preset_name):
                    self.load_presets()
                    if self.menu_bar.preset_combo:
                        self.menu_bar.preset_combo.setCurrentText(preset_name)
                    show_info_message(f"Preset '{preset_name}' created successfully")
                    logging.info(f"New preset created: {preset_name}")
                else:
                    show_error_message("Failed to create preset")
        except Exception as e:
            logging.error(f"Error creating new preset: {e}")
            show_error_message(f"Error creating preset: {e}")
    
    def delete_current_preset(self):
        """Delete the current preset."""
        try:
            if not self.current_preset:
                show_warning_message("No preset selected")
                return
            
            if show_question_dialog(
                f"Are you sure you want to delete preset '{self.current_preset}' and all its data?",
                "Delete Preset",
                self
            ):
                if delete_preset(self.current_preset):
                    self.load_presets()
                    show_info_message(f"Preset '{self.current_preset}' deleted successfully")
                    logging.info(f"Preset deleted: {self.current_preset}")
                else:
                    show_error_message("Failed to delete preset")
        except Exception as e:
            logging.error(f"Error deleting preset: {e}")
            show_error_message(f"Error deleting preset: {e}")
    
    def toggle_days_schedule_view(self):
        """Toggle between days table and schedule table view."""
        try:
            if self.table.isVisible():
                self.table.setVisible(False)
                self.days_table.setVisible(True)
                self.toggle_view_button.setText("Show Schedule")
            else:
                self.days_table.setVisible(False)
                self.table.setVisible(True)
                self.toggle_view_button.setText("Show Days")
                if self.current_preset:
                    self.populate_schedule_table()
        except Exception as e:
            logging.error(f"Error toggling view: {e}")
    
    def open_about_window(self):
        """Open the about window."""
        try:
            if self.about_window:
                self.about_window.close()
            self.about_window = AboutWindow(self)
            self.about_window.show()
        except Exception as e:
            logging.error(f"Error opening about window: {e}")
    
    def open_help_window(self):
        """Open the help window."""
        try:
            if self.help_window:
                self.help_window.close()
            self.help_window = HelpWindow(self)
            self.help_window.show()
        except Exception as e:
            logging.error(f"Error opening help window: {e}")

    def open_custom_theme_editor(self):
        """Open custom theme editor dialog with live preview support."""
        try:
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is None:
                return

            previous_theme = fetch_theme_from_db()
            current_palette_colors = self._extract_theme_items_from_palette(app.palette())

            selected_theme_name = ""
            if self.menu_bar and self.menu_bar.theme_combo:
                selected_theme_name = self.menu_bar.theme_combo.currentText().strip()

            if not selected_theme_name or selected_theme_name in ["Default", "Dark", "Light", "Sky Blue", "Navy Blue"]:
                selected_theme_name = ""

            if selected_theme_name:
                saved_items = fetch_custom_theme_items_from_db(selected_theme_name)
                if saved_items:
                    current_palette_colors = {
                        item: saved_items.get(item, current_palette_colors.get(item, "#FFFFFF"))
                        for item in THEME_COLOR_ITEMS
                    }

            dialog = CustomThemeEditorDialog(
                self,
                selected_theme_name,
                current_palette_colors,
                allow_delete=bool(selected_theme_name)
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if dialog.delete_requested():
                    if not selected_theme_name:
                        self.apply_theme(previous_theme)
                        show_warning_message("Select a saved custom theme first, then open Custom Themes to delete it.")
                        return

                    if not show_question_dialog(
                        f"Delete custom theme '{selected_theme_name}'?",
                        "Delete Custom Theme",
                        self
                    ):
                        self.apply_theme(previous_theme)
                        return

                    if not delete_custom_theme_from_db(selected_theme_name):
                        self.apply_theme(previous_theme)
                        show_error_message("Failed to delete custom theme")
                        return

                    fallback_theme = "Default" if (previous_theme or "").strip().lower() == selected_theme_name.lower() else previous_theme
                    if self.menu_bar and hasattr(self.menu_bar, "refresh_theme_options"):
                        self.menu_bar.refresh_theme_options(selected_theme=fallback_theme)
                    self.apply_theme(fallback_theme)
                    show_info_message(f"Custom theme '{selected_theme_name}' deleted")
                    return

                theme_name, item_colors = dialog.get_theme_payload()
                if not theme_name:
                    self.apply_theme(previous_theme)
                    show_warning_message("Theme name cannot be empty")
                    return

                built_in_themes = {"default", "dark", "light", "sky blue", "navy blue"}
                if theme_name.strip().lower() in built_in_themes:
                    self.apply_theme(previous_theme)
                    show_warning_message("Please choose a different name. Built-in theme names are reserved.")
                    return

                if not save_custom_theme_to_db(theme_name, item_colors):
                    self.apply_theme(previous_theme)
                    show_error_message("Failed to save custom theme")
                    return

                if self.menu_bar and hasattr(self.menu_bar, "refresh_theme_options"):
                    self.menu_bar.refresh_theme_options(selected_theme=theme_name)

                self.apply_theme(theme_name)
                show_info_message(f"Custom theme '{theme_name}' saved")
            else:
                self.apply_theme(previous_theme)

        except Exception as e:
            logging.error(f"Error opening custom theme editor: {e}")
            show_error_message(f"Error opening custom theme editor: {e}")
    
    def toggle_full_screen(self):
        """Toggle full screen mode."""
        try:
            if self.is_full_screen:
                self.showNormal()
            else:
                self.showFullScreen()
            self.is_full_screen = not self.is_full_screen
        except Exception as e:
            logging.error(f"Error toggling full screen: {e}")

    def _extract_theme_items_from_palette(self, palette):
        """Convert a QPalette into the editable custom-theme item dictionary."""
        return {
            "Window": palette.color(QPalette.ColorRole.Window).name().upper(),
            "WindowText": palette.color(QPalette.ColorRole.WindowText).name().upper(),
            "Base": palette.color(QPalette.ColorRole.Base).name().upper(),
            "AlternateBase": palette.color(QPalette.ColorRole.AlternateBase).name().upper(),
            "ToolTipBase": palette.color(QPalette.ColorRole.ToolTipBase).name().upper(),
            "ToolTipText": palette.color(QPalette.ColorRole.ToolTipText).name().upper(),
            "Text": palette.color(QPalette.ColorRole.Text).name().upper(),
            "Button": palette.color(QPalette.ColorRole.Button).name().upper(),
            "ButtonText": palette.color(QPalette.ColorRole.ButtonText).name().upper(),
            "BrightText": palette.color(QPalette.ColorRole.BrightText).name().upper(),
            "Link": palette.color(QPalette.ColorRole.Link).name().upper(),
            "Highlight": palette.color(QPalette.ColorRole.Highlight).name().upper(),
            "HighlightedText": palette.color(QPalette.ColorRole.HighlightedText).name().upper(),
            "PlaceholderText": palette.color(QPalette.ColorRole.PlaceholderText).name().upper(),
            "DisabledText": palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text).name().upper(),
            "DisabledButtonText": palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText).name().upper(),
            "DisabledWindowText": palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText).name().upper(),
        }

    def _build_palette_from_theme_items(self, item_colors):
        """Create a QPalette from custom item color mappings."""
        palette = QPalette()

        def _color_for(name, fallback):
            return QColor((item_colors or {}).get(name, fallback))

        palette.setColor(QPalette.ColorRole.Window, _color_for("Window", "#F0F0F0"))
        palette.setColor(QPalette.ColorRole.WindowText, _color_for("WindowText", "#000000"))
        palette.setColor(QPalette.ColorRole.Base, _color_for("Base", "#FFFFFF"))
        palette.setColor(QPalette.ColorRole.AlternateBase, _color_for("AlternateBase", "#F5F5F5"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, _color_for("ToolTipBase", "#FFFFFF"))
        palette.setColor(QPalette.ColorRole.ToolTipText, _color_for("ToolTipText", "#000000"))
        palette.setColor(QPalette.ColorRole.Text, _color_for("Text", "#000000"))
        palette.setColor(QPalette.ColorRole.Button, _color_for("Button", "#E9E9E9"))
        palette.setColor(QPalette.ColorRole.ButtonText, _color_for("ButtonText", "#000000"))
        palette.setColor(QPalette.ColorRole.BrightText, _color_for("BrightText", "#D00000"))
        palette.setColor(QPalette.ColorRole.Link, _color_for("Link", "#0066CC"))
        palette.setColor(QPalette.ColorRole.Highlight, _color_for("Highlight", "#0078D7"))
        palette.setColor(QPalette.ColorRole.HighlightedText, _color_for("HighlightedText", "#FFFFFF"))
        palette.setColor(QPalette.ColorRole.PlaceholderText, _color_for("PlaceholderText", "#666666"))
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.Text,
            _color_for("DisabledText", "#777777")
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.ButtonText,
            _color_for("DisabledButtonText", "#777777")
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.WindowText,
            _color_for("DisabledWindowText", "#777777")
        )
        return palette

    def preview_custom_theme(self, item_colors):
        """Apply an in-memory preview of custom theme colors without saving."""
        self.apply_theme("Custom Preview", persist=False, custom_items=item_colors)
    
    def apply_theme(self, theme_name, persist=True, custom_items=None):
        """Apply the specified theme."""
        try:
            from PyQt6.QtWidgets import QApplication

            font_family, font_weight, font_size = fetch_font_settings_from_db()

            app = QApplication.instance()
            if app is None:
                return

            theme_key = (theme_name or "Default").strip().lower()
            if not hasattr(self, '_original_system_palette'):
                # Capture the startup palette once so Default can always restore it.
                self._original_system_palette = QPalette(app.palette())

            custom_theme_names = fetch_custom_theme_names_from_db() or []
            matched_custom_theme = None
            active_custom_items = custom_items if custom_items else None
            for custom_name in custom_theme_names:
                if custom_name.strip().lower() == theme_key:
                    matched_custom_theme = custom_name
                    break

            if custom_items:
                app.setPalette(self._build_palette_from_theme_items(custom_items))
            elif theme_key == "default":
                # Restore the original app palette captured at startup.
                app.setPalette(QPalette(self._original_system_palette))
            elif theme_key == "dark":
                dark_palette = QPalette()
                dark_palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
                dark_palette.setColor(QPalette.ColorRole.WindowText, QColor("#FFFFFF"))
                dark_palette.setColor(QPalette.ColorRole.Base, QColor("#232323"))
                dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#2E2E2E"))
                dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
                dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#FFFFFF"))
                dark_palette.setColor(QPalette.ColorRole.Text, QColor("#FFFFFF"))
                dark_palette.setColor(QPalette.ColorRole.Button, QColor("#3C3C3C"))
                dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor("#FFFFFF"))
                dark_palette.setColor(QPalette.ColorRole.BrightText, QColor("#FF5555"))
                dark_palette.setColor(QPalette.ColorRole.Link, QColor("#2A82DA"))
                dark_palette.setColor(QPalette.ColorRole.Highlight, QColor("#2A82DA"))
                dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
                dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#7A7A7A"))
                dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#7A7A7A"))
                dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#7A7A7A"))
                app.setPalette(dark_palette)
            elif theme_key == "light":
                light_palette = QPalette()
                light_palette.setColor(QPalette.ColorRole.Window, QColor("#e5e5e5"))
                light_palette.setColor(QPalette.ColorRole.WindowText, QColor("#000000"))
                light_palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
                light_palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F5F5F5"))
                light_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
                light_palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#000000"))
                light_palette.setColor(QPalette.ColorRole.Text, QColor("#000000"))
                light_palette.setColor(QPalette.ColorRole.Button, QColor("#E9E9E9"))
                light_palette.setColor(QPalette.ColorRole.ButtonText, QColor("#000000"))
                light_palette.setColor(QPalette.ColorRole.BrightText, QColor("#D00000"))
                light_palette.setColor(QPalette.ColorRole.Link, QColor("#0066CC"))
                light_palette.setColor(QPalette.ColorRole.Highlight, QColor("#0078D7"))
                light_palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
                light_palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#666666"))
                light_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#777777"))
                light_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#777777"))
                light_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#777777"))
                app.setPalette(light_palette)
            elif theme_key == "sky blue":
                sky_palette = QPalette()
                sky_palette.setColor(QPalette.ColorRole.Window, QColor("#87CEEB"))
                sky_palette.setColor(QPalette.ColorRole.WindowText, QColor("#000000"))
                sky_palette.setColor(QPalette.ColorRole.Base, QColor("#EAF7FF"))
                sky_palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#DFF2FF"))
                sky_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
                sky_palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#000000"))
                sky_palette.setColor(QPalette.ColorRole.Text, QColor("#000000"))
                sky_palette.setColor(QPalette.ColorRole.Button, QColor("#B7E4F7"))
                sky_palette.setColor(QPalette.ColorRole.ButtonText, QColor("#000000"))
                sky_palette.setColor(QPalette.ColorRole.BrightText, QColor("#CC0000"))
                sky_palette.setColor(QPalette.ColorRole.Link, QColor("#005B96"))
                sky_palette.setColor(QPalette.ColorRole.Highlight, QColor("#1F7FBF"))
                sky_palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
                sky_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#555555"))
                sky_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#555555"))
                sky_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#555555"))
                app.setPalette(sky_palette)
            elif theme_key == "navy blue":
                navy_palette = QPalette()
                navy_palette.setColor(QPalette.ColorRole.Window, QColor("#14213d"))
                navy_palette.setColor(QPalette.ColorRole.WindowText, QColor("#F8FAFF"))
                navy_palette.setColor(QPalette.ColorRole.Base, QColor("#0F1B33"))
                navy_palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#182B4D"))
                navy_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#F8FAFF"))
                navy_palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#0F1B33"))
                navy_palette.setColor(QPalette.ColorRole.Text, QColor("#F8FAFF"))
                navy_palette.setColor(QPalette.ColorRole.Button, QColor("#1B2F57"))
                navy_palette.setColor(QPalette.ColorRole.ButtonText, QColor("#F8FAFF"))
                navy_palette.setColor(QPalette.ColorRole.BrightText, QColor("#FF6B6B"))
                navy_palette.setColor(QPalette.ColorRole.Link, QColor("#6FB1FF"))
                navy_palette.setColor(QPalette.ColorRole.Highlight, QColor("#2F80ED"))
                navy_palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
                navy_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#8A97AE"))
                navy_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#8A97AE"))
                navy_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#8A97AE"))
                app.setPalette(navy_palette)
            elif matched_custom_theme:
                custom_theme_items = fetch_custom_theme_items_from_db(matched_custom_theme)
                active_custom_items = custom_theme_items
                app.setPalette(self._build_palette_from_theme_items(custom_theme_items))
            else:
                app.setPalette(app.style().standardPalette())

            # Keep font settings independent of palette/theme choice.
            base_font_style = (
                f"* {{ font-size: {font_size}px; font-family: {font_family}; font-weight: {font_weight}; }}"
                f"QMenuBar, QMenuBar::item, QMenu, QMenu::item {{ "
                f"font-size: {font_size}px; font-family: {font_family}; font-weight: {font_weight}; }}"
            )

            if theme_key == "light":
                # Some widgets render low-contrast text in light palette on certain systems.
                # Force readable text color for menu/header-related controls only.
                light_contrast_overrides = """
                    QMenuBar, QMenuBar::item, QMenu, QMenu::item,
                    QHeaderView::section, QComboBox, QComboBox QAbstractItemView,
                    QPushButton {
                        color: #000000;
                    }
                    QMenu::item:disabled, QMenuBar::item:disabled, QPushButton:disabled {
                        color: #555555;
                    }
                """
                self.setStyleSheet(base_font_style + light_contrast_overrides)
            elif theme_key == "navy blue":
                navy_contrast_overrides = """
                    QMenuBar, QMenuBar::item, QMenu, QMenu::item,
                    QHeaderView::section, QComboBox, QComboBox QAbstractItemView,
                    QLabel, QTableWidget, QTableWidgetItem, QCheckBox, QPushButton {
                        color: #F8FAFF;
                    }
                    QMenu::item:disabled, QMenuBar::item:disabled,
                    QLabel:disabled, QPushButton:disabled {
                        color: #8A97AE;
                    }
                """
                self.setStyleSheet(base_font_style + navy_contrast_overrides)
            elif active_custom_items:
                menu_text_color = active_custom_items.get("MenuText") or active_custom_items.get("Text", "#000000")
                disabled_text_color = active_custom_items.get("DisabledText", "#777777")
                custom_text_overrides = f"""
                    QMenuBar, QMenuBar::item, QMenu, QMenu::item,
                    QHeaderView::section, QComboBox, QComboBox QAbstractItemView,
                    QPushButton {{
                        color: {menu_text_color};
                    }}
                    QMenu::item:disabled, QMenuBar::item:disabled,
                    QPushButton:disabled, QComboBox:disabled {{
                        color: {disabled_text_color};
                    }}
                """
                self.setStyleSheet(base_font_style + custom_text_overrides)
            else:
                self.setStyleSheet(base_font_style)

            if persist:
                save_theme_to_db(theme_name)

            if self.menu_bar and hasattr(self.menu_bar, "refresh_theme_options"):
                selected_name = theme_name if persist else self.menu_bar.theme_combo.currentText()
                self.menu_bar.refresh_theme_options(selected_theme=selected_name)

            logging.info(f"Theme applied: {theme_name}")
            
        except Exception as e:
            logging.error(f"Error applying theme: {e}")
    
    def change_language(self, language):
        """Change the application language."""
        try:
            if language in ["English", "Arabic"]:
                self.current_language = language
                save_language_to_db(language)
                self.menu_bar.update_language(language)
                logging.info(f"Language changed to: {language}")
            else:
                logging.warning(f"Unsupported language: {language}")
        except Exception as e:
            logging.error(f"Error changing language: {e}")

    def set_window_type(self, window_type):
        """Set and persist the preferred launch window mode."""
        try:
            mode = (window_type or "").strip().lower()
            if mode not in ("normal", "maximized"):
                mode = "maximized"

            if save_window_to_db(mode):
                logging.info(f"Window mode preference saved: {mode}")

                # Apply immediately so the choice is visible right away.
                if mode == "normal":
                    self.showNormal()
                else:
                    self.showMaximized()
            else:
                logging.error("Failed to save window mode preference")
        except Exception as e:
            logging.error(f"Error setting window type: {e}")
    
    def update_language_labels(self, language, translation):
        """Update UI labels with new language."""
        try:
            # Update table headers
            if self.table and "Table Headers" in translation:
                self.table.setHorizontalHeaderLabels(translation["Table Headers"])
            
            # Update days table headers
            if hasattr(self, 'days_table') and self.days_table:
                if language == "Arabic":
                    days_headers = ["اليوم", "نشط", "الجدول"]  # Day, Active, Preset in Arabic
                else:
                    days_headers = ["Day", "Active", "Preset"]
                self.days_table.setHorizontalHeaderLabels(days_headers)
            
            # Update table layout direction
            if language == "Arabic":
                if self.table:
                    self.table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                    self.table.horizontalHeader().setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                    # Update volume widgets layout direction
                    self._update_volume_widgets_direction(Qt.LayoutDirection.RightToLeft)
                if hasattr(self, 'days_table') and self.days_table:
                    self.days_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                    self.days_table.horizontalHeader().setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            else:
                if self.table:
                    self.table.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
                    self.table.horizontalHeader().setLayoutDirection(Qt.LayoutDirection.LeftToRight)
                    # Update volume widgets layout direction
                    self._update_volume_widgets_direction(Qt.LayoutDirection.LeftToRight)
                if hasattr(self, 'days_table') and self.days_table:
                    self.days_table.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
                    self.days_table.horizontalHeader().setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            
            # Update button text based on current view
            if hasattr(self, 'toggle_view_button') and self.toggle_view_button:
                # Use hidden state instead of isVisible so startup text is correct
                # even before the main window itself is shown.
                if not self.table.isHidden():
                    self.toggle_view_button.setText(translation.get("Show Days Button", "Show Days"))
                else:
                    self.toggle_view_button.setText(translation.get("Show Schedule Button", "Show Schedule"))
            
            # Update labels with translated prefixes but keep current values
            labels = translation.get("Labels", {})
            
            if hasattr(self, 'current_preset_label') and self.current_preset_label:
                current_value = self.current_preset_label.text().split(": ", 1)[-1] if ": " in self.current_preset_label.text() else "None"
                self.current_preset_label.setText(f"{labels.get('Preset', 'Preset')}: {current_value}")
            
            if hasattr(self, 'status_label') and self.status_label:
                current_value = self.status_label.text().split(": ", 1)[-1] if ": " in self.status_label.text() else "Unknown"
                self.status_label.setText(f"{labels.get('Status', 'Status')}: {current_value}")
            
            if hasattr(self, 'current_period_label') and self.current_period_label:
                current_value = self.current_period_label.text().split(": ", 1)[-1] if ": " in self.current_period_label.text() else "None"
                self.current_period_label.setText(f"{labels.get('Period', 'Period')}: {current_value}")
            
            logging.info(f"UI labels updated for language: {language}")
            
        except Exception as e:
            logging.error(f"Error updating language labels: {e}")
    
    def _update_volume_widgets_direction(self, direction):
        """Recreate all volume widgets with proper layout direction."""
        try:
            if not self.table or not hasattr(self, 'current_schedule') or not self.current_schedule:
                return
            
            for row in range(self.table.rowCount()):
                # Get current volume value from the existing slider
                current_volume = 100  # default
                existing_widget = self.table.cellWidget(row, 5)
                if existing_widget:
                    existing_slider = existing_widget.findChild(QSlider)
                    if existing_slider:
                        current_volume = existing_slider.value()
                
                # Recreate volume slider with proper direction
                volume_slider = QSlider(Qt.Orientation.Horizontal)
                volume_slider.setRange(0, 100)
                volume_slider.setValue(current_volume)
                volume_slider.valueChanged.connect(partial(self.update_volume, row))
                
                volume_widget = QWidget()
                volume_layout = QHBoxLayout(volume_widget)
                volume_layout.addWidget(volume_slider)
                volume_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                volume_layout.setContentsMargins(0, 0, 0, 0)
                
                # Set proper layout direction
                volume_widget.setLayoutDirection(direction)
                
                # Replace the widget in the table
                self.table.setCellWidget(row, 5, volume_widget)
                    
        except Exception as e:
            logging.error(f"Error updating volume widgets direction: {e}")
    
    def apply_font_settings(self, font_family, font_weight, font_size):
        """Apply font settings to the application."""
        try:
            from PyQt6.QtGui import QFont

            current_theme = fetch_theme_from_db()
            self.apply_theme(current_theme)  # This will use the new font settings

            # Native menu rendering can ignore stylesheet font-size on some systems,
            # so set menu fonts explicitly.
            ui_font = QFont(font_family, int(font_size))
            ui_font.setBold(str(font_weight).lower() == "bold")

            if self.menu_bar:
                self.menu_bar.setFont(ui_font)

                menus = [
                    self.menu_bar.file_menu,
                    self.menu_bar.audio_menu,
                    self.menu_bar.presets_menu,
                    self.menu_bar.database_menu,
                    self.menu_bar.tables_menu,
                    self.menu_bar.view_menu,
                    self.menu_bar.about_menu,
                    self.menu_bar.lock_menu,
                ]

                for menu in menus:
                    if not menu:
                        continue
                    menu.setFont(ui_font)
                    for action in menu.actions():
                        try:
                            action.setFont(ui_font)
                        except Exception:
                            pass

            logging.info(f"Font settings applied: {font_family}, {font_weight}, {font_size}")
        except Exception as e:
            logging.error(f"Error applying font settings: {e}")
    
    def change_digital_height(self):
        """Change the digital clock height."""
        try:
            current_height = self.digital_height
            height, ok = get_integer_input(
                "Enter new height:", "Change Digital Height",
                current_height, 20, 200, self
            )
            
            if ok:
                self.digital_height = height
                self.digital_clock.setFixedHeight(height)
                self.digital_remain.setFixedHeight(height)
                save_height_to_db(height)
                logging.info(f"Digital height changed to: {height}")
        except Exception as e:
            logging.error(f"Error changing digital height: {e}")
    
    def set_lock_state(self, locked):
        """Set the application lock state."""
        try:
            self.table.setEnabled(not locked)
            self.days_table.setEnabled(not locked)
            self.toggle_view_button.setEnabled(not locked)
            
            # Disable menu items when locked
            if self.menu_bar:
                for menu in [self.menu_bar.file_menu, self.menu_bar.audio_menu,
                           self.menu_bar.presets_menu, self.menu_bar.database_menu,
                           self.menu_bar.tables_menu, self.menu_bar.view_menu,
                           self.menu_bar.about_menu]:
                    if menu:
                        menu.setEnabled(not locked)
            
            logging.info(f"Lock state set to: {locked}")
        except Exception as e:
            logging.error(f"Error setting lock state: {e}")
    
    def toggle_lock(self):
        """Toggle the application lock state."""
        try:
            if self.locked:
                # Unlock
                password, ok = get_text_input(
                    "Enter password:", "Unlock Application",
                    password=True, parent=self
                )
                if ok:
                    stored_password = fetch_password_from_db()
                    print(f"DEBUG: Entered password length: {len(password) if password else 0}")
                    print(f"DEBUG: Stored password length: {len(stored_password) if stored_password else 0}")
                    print(f"DEBUG: Passwords match: {password == stored_password}")
                    
                    if password == stored_password:
                        self.locked = False
                        self.set_lock_state(False)
                        result = update_lock_state_in_db(False)
                        print(f"DEBUG: Lock state updated in DB: {result}")
                        self.menu_bar.update_lock_action(False)
                        show_info_message("Application unlocked")
                        logging.info("Application unlocked")
                    else:
                        show_error_message("Incorrect password")
                        print(f"DEBUG: Password mismatch!")
            else:
                # Lock
                password, ok = get_text_input(
                    "Enter a password:", "Set Password",
                    password=True, parent=self
                )
                if ok and password:
                    print(f"DEBUG: Setting password length: {len(password)}")
                    result = save_password_to_db(password)
                    print(f"DEBUG: Password saved to DB: {result}")
                    self.locked = True
                    self.set_lock_state(True)
                    result = update_lock_state_in_db(True)
                    print(f"DEBUG: Lock state updated in DB: {result}")
                    self.menu_bar.update_lock_action(True)
                    show_info_message("Application locked")
                    logging.info("Application locked")
        except Exception as e:
            logging.error(f"Error toggling lock: {e}")
            print(f"DEBUG ERROR: {e}")
    
    # Table event handlers
    def handle_cell_clicked(self, row, column):
        """Handle table cell click events."""
        try:
            self.selected_row = row
            self.sync_selected_row_color()
            
            # Handle time picker for time columns
            if column in [1, 2]:  # Start time or end time
                current_time = self.table.item(row, column).text() if self.table.item(row, column) else "00:00:00"
                new_time, ok = TimePickerDialog.get_time_from_user(current_time, self)
                
                if ok:
                    self.table.item(row, column).setText(new_time)
                    
                    # Update database
                    field = "start" if column == 1 else "end"
                    self.current_schedule[row][field] = new_time
                    
                    if self.current_preset:
                        period_name = self.current_schedule[row].get("period", "")
                        update_schedule_in_db(self.current_preset, period_name, field, new_time)
            elif column in [3, 4]:  # Audio start/end files
                item = self.table.item(row, column)
                if item:
                    self.table.editItem(item)
        except Exception as e:
            logging.error(f"Error handling cell click: {e}")

    def handle_cell_double_clicked(self, row, column):
        """Open file picker for audio cells on double click."""
        try:
            self.selected_row = row
            self.sync_selected_row_color()

            if column == 3:
                self.browse_file(row, "audio_start", replace_existing=True)
            elif column == 4:
                self.browse_file(row, "audio_end", replace_existing=True)
        except Exception as e:
            logging.error(f"Error handling cell double click: {e}")

    def get_available_audio_files(self):
        """Return available audio file names from configured audio directory."""
        try:
            directory = fetch_audio_directory_from_db()
            if directory and os.path.isdir(directory):
                self.audio_manager.set_audio_directory(directory)
            else:
                directory = self.audio_manager.get_audio_directory()

            if not directory or not os.path.isdir(directory):
                return []

            audio_extensions = (".mp3", ".wav")
            files = [
                name for name in os.listdir(directory)
                if os.path.isfile(os.path.join(directory, name)) and name.lower().endswith(audio_extensions)
            ]
            return sorted(files, key=str.lower)
        except Exception as e:
            logging.error(f"Error getting available audio files: {e}")
            return []
    
    def handle_item_changed(self, item):
        """Handle table item changes."""
        try:
            row = item.row()
            column = item.column()
            value = item.text()
            
            if row >= len(self.current_schedule):
                return
            
            # Update schedule data
            field_map = {0: "period", 1: "start", 2: "end", 3: "audio_start", 4: "audio_end"}
            
            if column in field_map:
                field = field_map[column]
                
                if field == "period":
                    # Handle period name change
                    old_period = self.current_schedule[row]["period"]
                    self.current_schedule[row][field] = value
                    self.update_period_in_db(old_period, value)
                else:
                    # Update field in current schedule
                    if field in ["audio_start", "audio_end"]:
                        # Split comma-separated audio files
                        self.current_schedule[row][field] = [f.strip() for f in value.split(',') if f.strip()]
                    else:
                        self.current_schedule[row][field] = value
                    
                    # Update entire row in database
                    self.update_row_in_db(row)
        except Exception as e:
            logging.error(f"Error handling item change: {e}")
    
    def update_period_in_db(self, old_period, new_period):
        """Update period name in database."""
        try:
            from src.config import get_connection_string
            import sqlite3
            
            conn = sqlite3.connect(get_connection_string())
            cursor = conn.cursor()
            cursor.execute("UPDATE Schedule SET Period = ? WHERE Period = ? AND Preset = ?", 
                         (new_period, old_period, self.current_preset))
            conn.commit()
            conn.close()

            if self.schedule_manager:
                self.schedule_manager.clear_schedule_cache()
        except Exception as e:
            logging.error(f"Error updating period in database: {e}")
            show_error_message(f"Error updating period in database: {e}", "Error", self)
    
    def update_row_in_db(self, row):
        """Update entire row in database."""
        try:
            from src.config import get_connection_string
            import sqlite3
            
            period = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
            start = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
            end = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
            audio_start = self.table.item(row, 3).text() if self.table.item(row, 3) else ""
            audio_end = self.table.item(row, 4).text() if self.table.item(row, 4) else ""
            color = self.current_schedule[row].get("color", "") if row < len(self.current_schedule) else ""

            # Get volume from slider
            volume_widget = self.table.cellWidget(row, 5)
            if volume_widget:
                volume_slider = volume_widget.findChild(QSlider)
                volume = volume_slider.value() / 100.0 if volume_slider else 1.0
            else:
                volume = 1.0

            conn = sqlite3.connect(get_connection_string())
            cursor = conn.cursor()
            
            # Check if row exists
            cursor.execute("SELECT COUNT(*) FROM Schedule WHERE Period = ? AND Preset = ?", 
                         (period, self.current_preset))
            exists = cursor.fetchone()[0]
            
            if exists:
                # Update existing row
                cursor.execute("""UPDATE Schedule SET Start_Time = ?, End_Time = ?, Audio_Start = ?, 
                                 Audio_End = ?, Volume = ?, Color = ? WHERE Period = ? AND Preset = ?""",
                             (start, end, audio_start, audio_end, volume, color, period, self.current_preset))
            else:
                # Insert new row
                cursor.execute("""INSERT INTO Schedule (Period, Start_Time, End_Time, Audio_Start, 
                                 Audio_End, Volume, Preset, Color) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", 
                             (period, start, end, audio_start, audio_end, volume, self.current_preset, color))
            
            conn.commit()
            conn.close()

            if self.schedule_manager:
                self.schedule_manager.clear_schedule_cache()
            
        except Exception as e:
            logging.error(f"Error updating row in database: {e}")
            show_error_message(f"Error updating row in database: {e}", "Error", self)
    
    def update_volume(self, row, value):
        """Update volume for a schedule row."""
        try:
            if row < len(self.current_schedule):
                volume = value / 100.0
                self.current_schedule[row]["volume"] = volume
                
                # Update database
                if self.current_preset:
                    period_name = self.current_schedule[row].get("period", "")
                    update_schedule_in_db(self.current_preset, period_name, "volume", volume)
                
                # Apply volume change to currently playing audio
                self.audio_manager.set_volume(volume)
                logging.debug(f"Volume applied to audio: {volume}")
        except Exception as e:
            logging.error(f"Error updating volume: {e}")
    
    def update_day_status(self, day_id, state):
        """Update day status in database."""
        try:
            status = state == Qt.CheckState.Checked.value
            update_day_status_in_db(day_id, status)
            logging.debug(f"Day {day_id} status updated to {status}")
        except Exception as e:
            logging.error(f"Error updating day status: {e}")
    
    def update_day_preset(self, day_id, preset_text):
        """Update day preset in database."""
        print(f"DEBUG: update_day_preset called with day_id={day_id}, preset_text={preset_text}")
        try:
            preset = None if preset_text == "(Default)" else preset_text
            save_day_preset_in_db(day_id, preset)
            logging.info(f"Day ID {day_id} preset updated to: {preset if preset else 'Default (None)'}")
            print(f"DEBUG: Saved to database, preset={preset}")
            
            # Get the day name for this day_id
            days_data = fetch_days_from_db()
            current_day_id = None
            updated_day_name = None
            
            # Find the day name for the updated day_id
            for day in days_data:
                if day["id"] == day_id:
                    updated_day_name = day["day_name"]
                    break
            
            # Get current day name
            current_day_name = get_day_name()
            print(f"DEBUG: Current day: {current_day_name}, Updated day: {updated_day_name}")
            logging.debug(f"Current day: {current_day_name}, Updated day: {updated_day_name}")
            
            # If updating today's preset, refresh the schedule
            if updated_day_name == current_day_name:
                print(f"DEBUG: Days match! Updating schedule...")
                if preset:
                    # Load the specific preset for this day (don't save as global)
                    logging.info(f"Loading day-specific preset: {preset}")
                    print(f"DEBUG: Loading day-specific preset: {preset}")
                    self.update_schedule(preset, save_as_global=False)
                else:
                    # Load the global default preset (don't save as global since it already is)
                    global_preset = fetch_current_preset_from_db()
                    logging.info(f"Reverting to global preset: {global_preset}")
                    print(f"DEBUG: Reverting to global preset: {global_preset}")
                    if global_preset:
                        self.update_schedule(global_preset, save_as_global=False)
                    else:
                        logging.warning("No global preset found to revert to")
                        print("DEBUG: No global preset found")
            else:
                print(f"DEBUG: Days don't match, not updating schedule")
                        
        except Exception as e:
            logging.error(f"Error updating day preset: {e}", exc_info=True)
            print(f"DEBUG ERROR: {e}")
    
    # Additional functionality placeholders
    def play_selected_start_audio(self):
        """Play start audio for selected row."""
        try:
            if self.selected_row is None or self.selected_row >= len(self.current_schedule):
                show_warning_message("Please select a row first.")
                return
            
            period = self.current_schedule[self.selected_row]
            audio_files = period.get("audio_start", [])
            
            if not audio_files:
                show_info_message("No start audio files configured for this period.")
                return
            
            # Get volume from slider
            volume = 1.0
            try:
                volume_widget = self.table.cellWidget(self.selected_row, 5)
                if volume_widget:
                    volume_slider = volume_widget.findChild(QSlider)
                    if volume_slider:
                        volume = volume_slider.value() / 100.0
            except Exception as e:
                logging.warning(f"Could not get volume from slider: {e}")
            
            # Play the audio file(s) with selected volume
            if self.audio_manager.play_audio(audio_files, volume=volume):
                logging.info(f"Playing start audio: {audio_files} at volume {volume}")
            else:
                show_error_message(f"Failed to play audio file(s): {audio_files}")
        except Exception as e:
            logging.error(f"Error playing start audio: {e}")
            show_error_message(f"Error playing start audio: {e}")
    
    def play_selected_end_audio(self):
        """Play end audio for selected row."""
        try:
            if self.selected_row is None or self.selected_row >= len(self.current_schedule):
                show_warning_message("Please select a row first.")
                return
            
            period = self.current_schedule[self.selected_row]
            audio_files = period.get("audio_end", [])
            
            if not audio_files:
                show_info_message("No end audio files configured for this period.")
                return
            
            # Get volume from slider
            volume = 1.0
            try:
                volume_widget = self.table.cellWidget(self.selected_row, 5)
                if volume_widget:
                    volume_slider = volume_widget.findChild(QSlider)
                    if volume_slider:
                        volume = volume_slider.value() / 100.0
            except Exception as e:
                logging.warning(f"Could not get volume from slider: {e}")
            
            # Play the audio file(s) with selected volume
            if self.audio_manager.play_audio(audio_files, volume=volume):
                logging.info(f"Playing end audio: {audio_files} at volume {volume}")
            else:
                show_error_message(f"Failed to play audio file(s): {audio_files}")
        except Exception as e:
            logging.error(f"Error playing end audio: {e}")
            show_error_message(f"Error playing end audio: {e}")
    
    def browse_selected_start_audio(self):
        """Browse for start audio files."""
        if self.selected_row is not None:
            self.browse_file(self.selected_row, "audio_start")
    
    def browse_selected_end_audio(self):
        """Browse for end audio files."""
        if self.selected_row is not None:
            self.browse_file(self.selected_row, "audio_end")
    
    def browse_file(self, row, audio_type, replace_existing=False):
        """Browse for audio file and add to schedule."""
        try:
            from PyQt6.QtWidgets import QFileDialog
            import os
            
            # Always prefer the directory saved in Settings.
            directory = fetch_audio_directory_from_db()
            if directory and os.path.isdir(directory):
                self.audio_manager.set_audio_directory(directory)
            else:
                directory = self.audio_manager.get_audio_directory()

            if not directory or not os.path.isdir(directory):
                show_warning_message("Audio directory is not set or does not exist.")
                return
            
            file_name, _ = QFileDialog.getOpenFileName(self, "Select Audio File", directory, "Audio Files (*.mp3 *.wav)")
            if file_name:
                # Check if file is in audio directory
                if os.path.commonpath([file_name, directory]) == directory:
                    display_name = os.path.basename(file_name)
                else:
                    display_name = file_name

                # Update table cell
                column = 3 if audio_type == "audio_start" else 4
                cell = self.table.item(row, column)
                current_text = cell.text() if cell else ""
                
                if replace_existing:
                    updated_text = display_name
                elif current_text.strip():
                    updated_text = f"{current_text},{display_name}"
                else:
                    updated_text = display_name

                if cell:
                    cell.setText(updated_text)
                else:
                    new_item = QTableWidgetItem(updated_text)
                    self.table.setItem(row, column, new_item)

                # Update current schedule
                self.current_schedule[row][audio_type] = updated_text.split(',')
                
                # Update database
                self.update_row_in_db(row)
                
        except Exception as e:
            logging.error(f"Error browsing audio file: {e}")
            show_error_message(f"Error selecting audio file: {str(e)}", "Error", self)
    
    def add_new_row(self):
        """Add a new row to the schedule."""
        try:
            row_count = self.table.rowCount()
            self.table.blockSignals(True)
            self.table.insertRow(row_count)
            
            period_value = f"Period {row_count + 1}"
            period_item = QTableWidgetItem(period_value)
            period_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_count, 0, period_item)
            
            start_item = QTableWidgetItem("00:00:00")
            start_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_count, 1, start_item)
            
            end_item = QTableWidgetItem("00:00:00")
            end_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_count, 2, end_item)
            
            audio_start_item = QTableWidgetItem("")
            audio_start_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_count, 3, audio_start_item)
            
            audio_end_item = QTableWidgetItem("")
            audio_end_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_count, 4, audio_end_item)

            volume_slider = QSlider(Qt.Orientation.Horizontal)
            volume_slider.setRange(0, 100)
            volume_slider.setValue(100)
            volume_slider.valueChanged.connect(partial(self.update_volume, row_count))
            volume_widget = QWidget()
            volume_layout = QHBoxLayout(volume_widget)
            volume_layout.addWidget(volume_slider)
            volume_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            volume_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row_count, 5, volume_widget)

            self.current_schedule.append({
                "period": period_value,
                "start": "00:00:00",
                "end": "00:00:00",
                "audio_start": [],
                "audio_end": [],
                "volume": 1.0,
                "color": ""
            })
            self.table.blockSignals(False)

            self.selected_row = row_count
            self.table.selectRow(row_count)
            self.sync_selected_row_color()

            # Insert into database
            from src.config import get_connection_string
            import sqlite3
            
            conn = sqlite3.connect(get_connection_string())
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Schedule (Period, Start_Time, End_Time, Audio_Start, Audio_End, Volume, Preset, Color) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                        (period_value, "00:00:00", "00:00:00", "", "", 1.0, self.current_preset, ""))
            conn.commit()
            conn.close()

            if self.schedule_manager:
                self.schedule_manager.clear_schedule_cache()
            
            logging.info(f"Added new row: {period_value}")
                
        except Exception as e:
            logging.error(f"Error adding new row: {e}")
            show_error_message(f"Failed to add new row: {str(e)}", "Error", self)
    
    def delete_selected_row(self):
        """Delete the selected schedule row."""
        try:
            from src.database import delete_schedule_row
            
            # Get selected row
            current_row = self.table.currentRow()
            
            if current_row < 0:
                show_warning_message("Please select a row to delete", "No Selection", self)
                return
            
            # Get period from selected row
            period_item = self.table.item(current_row, 0)
            if not period_item:
                show_error_message("Could not identify the selected row", "Error", self)
                return
            
            period = period_item.text()
            
            # Confirm deletion
            reply = show_question_dialog(
                f"Are you sure you want to delete Period {period}?",
                "Confirm Deletion",
                self
            )
            
            if reply:
                # Delete from database
                if delete_schedule_row(self.current_preset, period):
                    # Remove from current schedule
                    self.current_schedule = [p for p in self.current_schedule if p.get('period') != period]
                    self.selected_row = None
                    self.sync_selected_row_color()

                    if self.schedule_manager:
                        self.schedule_manager.clear_schedule_cache()

                    # Refresh table
                    self.populate_schedule_table()
                    logging.info(f"Deleted row: Period {period}")
                else:
                    show_error_message("Failed to delete row from database", "Error", self)
                    
        except Exception as e:
            logging.error(f"Error deleting row: {e}")
            show_error_message(f"Failed to delete row: {str(e)}", "Error", self)
    
    def remove_all_audio(self):
        """Remove all audio assignments from schedule."""
        try:
            reply = show_question_dialog(
                "Are you sure you want to remove all audio files from the schedule?",
                "Remove All Audio Files",
                self
            )
            
            if reply:
                for row in range(self.table.rowCount()):
                    # Clear audio start
                    start_item = self.table.item(row, 3)
                    if start_item:
                        start_item.setText("")
                    
                    # Clear audio end
                    end_item = self.table.item(row, 4)
                    if end_item:
                        end_item.setText("")
                    
                    # Update current schedule
                    if row < len(self.current_schedule):
                        self.current_schedule[row]["audio_start"] = []
                        self.current_schedule[row]["audio_end"] = []
                    
                    # Update database
                    self.update_row_in_db(row)
                
                show_info_message("All audio files have been removed from the schedule.", "Audio Removed", self)
                logging.info("All audio files removed from schedule")
                
        except Exception as e:
            logging.error(f"Error removing all audio: {e}")
            show_error_message(f"Error removing audio files: {str(e)}", "Error", self)
    
    def browse_database(self):
        """Browse for a different database file."""
        try:
            from PyQt6.QtWidgets import QFileDialog
            from src.config import config_manager
            import os
            
            # Get current database path
            current_db = config_manager.get_database_path()
            start_dir = os.path.dirname(current_db) if current_db else os.getcwd()
            
            # Open file dialog
            db_path, _ = QFileDialog.getOpenFileName(
                self,
                "Choose Database File",
                start_dir,
                "Database Files (*.db);;All Files (*.*)"
            )
            
            if db_path:
                # Update configuration
                config_manager.set_database_path(db_path)
                
                # Update database label
                if hasattr(self, 'menu_bar') and hasattr(self.menu_bar, 'update_database_label'):
                    self.menu_bar.update_database_label()
                
                # Reload the application with new database
                show_info_message(
                    "Database changed successfully!\nPlease restart the application for changes to take effect.",
                    "Database Changed",
                    self
                )
                
                logging.info(f"Database changed to: {db_path}")
                
        except Exception as e:
            logging.error(f"Error browsing database: {e}")
            show_error_message(f"Failed to change database: {str(e)}", "Database Error", self)
    
    def change_font(self):
        """Change application font."""
        try:
            current_family, current_weight, current_size = fetch_font_settings_from_db()
            
            # Create a QFont object from current settings
            from PyQt6.QtGui import QFont
            current_font = QFont(current_family, current_size)
            if current_weight == "bold":
                current_font.setBold(True)
            
            # Use the font selection dialog from ui_components
            selected_font, ok = select_font(current_font, self)
            
            if ok and selected_font:
                # Extract font properties
                font_family = selected_font.family()
                font_size = selected_font.pointSize()
                font_weight = "bold" if selected_font.bold() else "normal"
                
                # Save to database
                save_font_settings_to_db(font_family, font_weight, font_size)
                
                # Apply the new font settings
                self.apply_font_settings(font_family, font_weight, font_size)
                
                logging.info(f"Font changed to: {font_family}, {font_weight}, {font_size}")
                show_info_message("Font settings updated successfully!", "Font Changed", self)
                
        except Exception as e:
            logging.error(f"Error changing font: {e}")
            show_error_message(f"Failed to change font: {str(e)}", "Font Error", self)
    
    def set_default_font(self):
        """Set default font settings."""
        try:
            # Default font settings
            default_family = "Segoe UI"
            default_weight = "normal"
            default_size = 14
            default_height = 50
            
            # Save to database
            save_font_settings_to_db(default_family, default_weight, default_size)
            save_height_to_db(default_height)
            
            # Apply the default font settings
            self.apply_font_settings(default_family, default_weight, default_size)
            
            # Reset digital height to default
            self.digital_height = default_height
            self.digital_clock.setFixedHeight(default_height)
            self.digital_remain.setFixedHeight(default_height)
            
            logging.info("Font and digital height reset to default settings")
            show_info_message("Font and digital height reset to default settings!", "Default Font", self)
            
        except Exception as e:
            logging.error(f"Error setting default font: {e}")
            show_error_message(f"Failed to reset font: {str(e)}", "Font Error", self)
    
    def _center_window(self):
        """Center the window on screen."""
        try:
            screen = QGuiApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            window_geometry.moveCenter(screen_geometry.center())
            self.move(window_geometry.topLeft())
        except Exception as e:
            logging.error(f"Error centering window: {e}")


# Module initialization
logging.info("Main application module initialized")