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
UI Components module for School Bell Application.
Contains all reusable UI components including MenuBar, AboutWindow, HelpWindow, etc.
"""

import os
import logging
from functools import partial
from PyQt6.QtWidgets import (
    QMenuBar, QMenu, QWidgetAction, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QCheckBox, QSlider, QMainWindow, QScrollArea,
    QMessageBox, QInputDialog, QLineEdit, QDialogButtonBox, QDialog,
    QTimeEdit, QFileDialog, QFontDialog
)
from PyQt6.QtGui import QPixmap, QIcon, QAction
from PyQt6.QtCore import Qt, QTime
from config import (
    SUPPORTED_LANGUAGES, SUPPORTED_THEMES, MOE_PATH, SCHOOL_LOGO_PATH,
    config_manager, APP_AUTHOR, APP_NAME, APP_VERSION
)
from database import (
    fetch_presets_from_db, save_language_to_db, save_theme_to_db,
    fetch_theme_from_db, save_font_settings_to_db, fetch_font_settings_from_db,
    fetch_colors_from_db
)


class TranslationManager:
    """Manages translations for the application."""
    
    def __init__(self):
        self.translations = {
            "English": {
                "File": "&File",
                "Refresh": "&Refresh",
                "Toggle Active Status": "Toggle Active Status",
                "Exit": "E&xit",
                "Audio": "&Audio",
                "Stop Audio": "Stop Audio",
                "Set Directory": "Set Directory",
                "Set Default Directory": "Set Default Directory",
                "Play Start": "Play Start",
                "Play End": "Play End",
                "Choose Start": "Choose Start",
                "Choose End": "Choose End",
                "Remove All Audio": "Remove All Audio",
                "Presets": "&Presets",
                "Choose Preset:": "Choose Preset:",
                "New Preset": "New Preset",
                "Delete Preset": "Delete Preset",
                "Database": "&Database",
                "Choose Database": "Choose Database",
                "Tables": "&Tables",
                "New Row": "New Row",
                "Delete Row": "Delete Row",
                "Color": "Color",
                "Choose Color:": "Color",
                "No Color": "No Color",
                "View": "&View",
                "Full Screen": "Full Screen",
                "Change Font": "Change Font",
                "Default Font": "Default Font",
                "Change Digital Height": "Change Digital Height",
                "Choose Theme:": "Choose Theme:",
                "Choose Language:": "Choose Language:",
                "About": "&About",
                "Help": "Help",
                "Lock": "&Lock",
                "Unlock": "Unlock",
                "Table Headers": ["Period", "Start Time", "End Time", "Audio Start", "Audio End", "Volume"],
                "Show Schedule Button": "Show Schedule",
                "Show Days Button": "Show Days",
                "Labels": {
                    "Preset": "Preset:",
                    "Status": "Status:",
                    "Period": "Period:",
                    "Current Day": "Current Day:"
                }
            },
            "Arabic": {
                "File": "ملف",
                "Refresh": "تحديث",
                "Toggle Active Status": "تغيير الحالة النشطة",
                "Exit": "خروج",
                "Audio": "الصوت",
                "Stop Audio": "إيقاف الصوت",
                "Set Directory": "تعيين مجلد ملفات الصوت",
                "Set Default Directory": "تعيين مجلد ملفات الصوت الافتراضي",
                "Play Start": "تشغيل البداية",
                "Play End": "تشغيل النهاية",
                "Choose Start": "اختيار البداية",
                "Choose End": "اختيار النهاية",
                "Remove All Audio": "إزالة جميع الملفات الصوتية",
                "Presets": "جدول الحصص",
                "Choose Preset:": "اختر جدول الحصص:",
                "New Preset": "إعداد جدول حصص جديد",
                "Delete Preset": "حذف جدول الحصص الحالي",
                "Database": "قاعدة البيانات",
                "Choose Database": "اختيار قاعدة البيانات",
                "Tables": "الجداول",
                "New Row": "صف جديد",
                "Delete Row": "حذف الصف",
                "Color": "اللون",
                "Choose Color:": "اللون:",
                "No Color": "بدون لون",
                "View": "عرض",
                "Full Screen": "ملء الشاشة",
                "Change Font": "تغيير الخط",
                "Default Font": "الخط الافتراضي",
                "Change Digital Height": "تغيير ارتفاع الساعة الرقمية",
                "Choose Theme:": "اختر اللون:",
                "Choose Language:": "اختر اللغة:",
                "About": "حول",
                "Help": "مساعدة",
                "Lock": "قفل",
                "Unlock": "فتح القفل",
                "Table Headers": ["الحصة", "وقت البدء", "وقت الانتهاء", "صوت البداية", "صوت النهاية", "مستوى الصوت"],
                "Show Schedule Button": "عرض الجدول",
                "Show Days Button": "عرض الأيام",
                "Labels": {
                    "Preset": "الجدول:",
                    "Status": "الحالة:",
                    "Period": "الحصة:",
                    "Current Day": "اليوم الحالي:"
                }
            }
        }
    
    def get_translation(self, language, key, default=None):
        """Get translation for a key in the specified language."""
        return self.translations.get(language, {}).get(key, default or key)
    
    def get_all_translations(self, language):
        """Get all translations for a language."""
        return self.translations.get(language, {})


class MenuBar(QMenuBar):
    """Enhanced menu bar with proper separation of concerns."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.translation_manager = TranslationManager()
        self.current_language = "English"
        
        # Initialize UI references
        self.preset_combo = None
        self.theme_combo = None
        self.language_combo = None
        self.row_color_combo = None
        self.row_color_label = None
        self.database_label = None
        self.lock_action = None
        
        # Menu references
        self.file_menu = None
        self.audio_menu = None
        self.presets_menu = None
        self.database_menu = None
        self.tables_menu = None
        self.view_menu = None
        self.about_menu = None
        self.lock_menu = None
        
        self.setup_menus()
    
    def setup_menus(self):
        """Setup all menus with default language."""
        translation = self.translation_manager.get_all_translations(self.current_language)
        
        # Create menus
        self.file_menu = QMenu(translation["File"], self)
        self.audio_menu = QMenu(translation["Audio"], self)
        self.presets_menu = QMenu(translation["Presets"], self)
        self.database_menu = QMenu(translation["Database"], self)
        self.tables_menu = QMenu(translation["Tables"], self)
        self.view_menu = QMenu(translation["View"], self)
        self.about_menu = QMenu(translation["About"], self)
        self.lock_menu = QMenu(translation["Lock"], self)
        
        # Add menus to menubar
        self.addMenu(self.file_menu)
        self.addMenu(self.audio_menu)
        self.addMenu(self.presets_menu)
        self.addMenu(self.database_menu)
        self.addMenu(self.tables_menu)
        self.addMenu(self.view_menu)
        self.addMenu(self.about_menu)
        self.addMenu(self.lock_menu)
        
        # Initialize menus
        self.init_file_menu(translation)
        self.init_audio_menu(translation)
        self.init_presets_menu(translation)
        self.init_database_menu()
        self.init_tables_menu(translation)
        self.init_view_menu(translation)
        self.init_about_menu(translation)
        self.init_lock_menu(translation)
    
    def init_file_menu(self, translation):
        """Initialize file menu."""
        refresh_action = QAction(translation["Refresh"], self)
        refresh_action.triggered.connect(self._safe_call('refresh_app'))
        self.file_menu.addAction(refresh_action)
        
        self.file_menu.addSeparator()
        
        toggle_action = QAction(translation["Toggle Active Status"], self)
        toggle_action.triggered.connect(self._safe_call('toggle_active_status'))
        self.file_menu.addAction(toggle_action)
        
        self.file_menu.addSeparator()
        
        exit_action = QAction(translation["Exit"], self)
        exit_action.triggered.connect(self._safe_call('exit_app'))
        self.file_menu.addAction(exit_action)
    
    def init_audio_menu(self, translation):
        """Initialize audio menu."""
        stop_action = QAction(translation["Stop Audio"], self)
        stop_action.triggered.connect(self._safe_call('stop_audio'))
        self.audio_menu.addAction(stop_action)
        
        self.audio_menu.addSeparator()
        
        set_dir_action = QAction(translation["Set Directory"], self)
        set_dir_action.triggered.connect(self._safe_call('set_audio_directory'))
        self.audio_menu.addAction(set_dir_action)
        
        set_default_dir_action = QAction(translation["Set Default Directory"], self)
        set_default_dir_action.triggered.connect(self._safe_call('set_default_audio_directory'))
        self.audio_menu.addAction(set_default_dir_action)
        
        self.audio_menu.addSeparator()
        
        play_start_action = QAction(translation["Play Start"], self)
        play_start_action.triggered.connect(self._safe_call('play_selected_start_audio'))
        self.audio_menu.addAction(play_start_action)
        
        play_end_action = QAction(translation["Play End"], self)
        play_end_action.triggered.connect(self._safe_call('play_selected_end_audio'))
        self.audio_menu.addAction(play_end_action)
        
        self.audio_menu.addSeparator()
        
        browse_start_action = QAction(translation["Choose Start"], self)
        browse_start_action.triggered.connect(self._safe_call('browse_selected_start_audio'))
        self.audio_menu.addAction(browse_start_action)
        
        browse_end_action = QAction(translation["Choose End"], self)
        browse_end_action.triggered.connect(self._safe_call('browse_selected_end_audio'))
        self.audio_menu.addAction(browse_end_action)
        
        self.audio_menu.addSeparator()
        
        remove_all_action = QAction(translation["Remove All Audio"], self)
        remove_all_action.triggered.connect(self._safe_call('remove_all_audio'))
        self.audio_menu.addAction(remove_all_action)
    
    def init_presets_menu(self, translation):
        """Initialize presets menu."""
        # Preset selection widget
        preset_action = QWidgetAction(self)
        preset_widget = QWidget(self)
        preset_layout = QVBoxLayout(preset_widget)
        
        preset_label = QLabel(translation["Choose Preset:"], self)
        self.preset_combo = QComboBox(self)
        
        # Load presets
        try:
            presets = fetch_presets_from_db() or []
            self.preset_combo.addItems(presets)
            self.preset_combo.currentTextChanged.connect(self._safe_call('update_schedule', pass_args=True))
        except Exception as e:
            logging.error(f"Error loading presets for menu: {e}")
        
        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(self.preset_combo)
        preset_widget.setLayout(preset_layout)
        preset_action.setDefaultWidget(preset_widget)
        self.presets_menu.addAction(preset_action)
        
        self.presets_menu.addSeparator()
        
        new_preset_action = QAction(translation["New Preset"], self)
        new_preset_action.triggered.connect(self._safe_call('create_new_preset'))
        self.presets_menu.addAction(new_preset_action)
        
        delete_preset_action = QAction(translation["Delete Preset"], self)
        delete_preset_action.triggered.connect(self._safe_call('delete_current_preset'))
        self.presets_menu.addAction(delete_preset_action)
    
    def init_database_menu(self):
        """Initialize database menu."""
        # Database status label
        self.database_label = QLabel(self)
        self.database_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_database_label()
        
        label_widget = QWidget()
        label_layout = QVBoxLayout(label_widget)
        label_layout.addWidget(self.database_label)
        label_layout.setContentsMargins(0, 0, 0, 0)
        
        label_action = QWidgetAction(self)
        label_action.setDefaultWidget(label_widget)
        self.database_menu.addAction(label_action)
        
        self.database_menu.addSeparator()
        
        browse_action = QAction("Choose Database", self)
        browse_action.triggered.connect(self._safe_call('browse_database'))
        self.database_menu.addAction(browse_action)
    
    def init_tables_menu(self, translation):
        """Initialize tables menu."""
        new_row_action = QAction(translation["New Row"], self)
        new_row_action.triggered.connect(self._safe_call('add_new_row'))
        self.tables_menu.addAction(new_row_action)
        
        delete_row_action = QAction(translation["Delete Row"], self)
        delete_row_action.triggered.connect(self._safe_call('delete_selected_row'))
        self.tables_menu.addAction(delete_row_action)

        color_action = QWidgetAction(self)
        color_widget = QWidget(self)
        color_layout = QVBoxLayout(color_widget)
        color_layout.setContentsMargins(8, 4, 8, 4)

        self.row_color_label = QLabel(translation.get("Choose Color:", "Color"), self)
        self.row_color_combo = QComboBox(self)
        self.row_color_combo.currentIndexChanged.connect(self._handle_row_color_changed)

        color_layout.addWidget(self.row_color_label)
        color_layout.addWidget(self.row_color_combo)
        color_widget.setLayout(color_layout)
        color_action.setDefaultWidget(color_widget)
        self.tables_menu.addAction(color_action)

        self.refresh_row_color_options()
    
    def init_view_menu(self, translation):
        """Initialize view menu."""
        fullscreen_action = QAction(translation["Full Screen"], self)
        fullscreen_action.triggered.connect(self._safe_call('toggle_full_screen'))
        self.view_menu.addAction(fullscreen_action)
        
        self.view_menu.addSeparator()
        
        font_action = QAction(translation["Change Font"], self)
        font_action.triggered.connect(self._safe_call('change_font'))
        self.view_menu.addAction(font_action)
        
        default_font_action = QAction(translation["Default Font"], self)
        default_font_action.triggered.connect(self._safe_call('set_default_font'))
        self.view_menu.addAction(default_font_action)
        
        self.view_menu.addSeparator()
        
        height_action = QAction(translation["Change Digital Height"], self)
        height_action.triggered.connect(self._safe_call('change_digital_height'))
        self.view_menu.addAction(height_action)
        
        self.view_menu.addSeparator()
        
        # Theme selection
        theme_action = QWidgetAction(self)
        theme_widget = QWidget(self)
        theme_layout = QVBoxLayout(theme_widget)
        
        theme_label = QLabel(translation["Choose Theme:"], self)
        self.theme_combo = QComboBox(self)
        self.theme_combo.addItems(SUPPORTED_THEMES)
        self.theme_combo.currentTextChanged.connect(self._safe_call('apply_theme', pass_args=True))
        
        # Set current theme
        try:
            current_theme = fetch_theme_from_db()
            index = self.theme_combo.findText(current_theme)
            if index >= 0:
                self.theme_combo.setCurrentIndex(index)
        except Exception as e:
            logging.error(f"Error setting current theme: {e}")
        
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_widget.setLayout(theme_layout)
        theme_action.setDefaultWidget(theme_widget)
        self.view_menu.addAction(theme_action)
        
        # Language selection
        language_action = QWidgetAction(self)
        language_widget = QWidget(self)
        language_layout = QVBoxLayout(language_widget)
        
        language_label = QLabel(translation["Choose Language:"], self)
        self.language_combo = QComboBox(self)
        self.language_combo.addItems(SUPPORTED_LANGUAGES)
        self.language_combo.currentTextChanged.connect(self._safe_call('change_language', pass_args=True))
        
        # Set current language
        current_lang_index = SUPPORTED_LANGUAGES.index(self.current_language) if self.current_language in SUPPORTED_LANGUAGES else 0
        self.language_combo.setCurrentIndex(current_lang_index)
        
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        language_widget.setLayout(language_layout)
        language_action.setDefaultWidget(language_widget)
        self.view_menu.addAction(language_action)
    
    def init_about_menu(self, translation):
        """Initialize about menu."""
        about_action = QAction(translation["About"], self)
        about_action.triggered.connect(self._safe_call('open_about_window'))
        self.about_menu.addAction(about_action)
        
        help_action = QAction(translation["Help"], self)
        help_action.triggered.connect(self._safe_call('open_help_window'))
        self.about_menu.addAction(help_action)
    
    def init_lock_menu(self, translation):
        """Initialize lock menu."""
        self.lock_action = QAction(translation["Lock"], self)
        self.lock_action.triggered.connect(self._safe_call('toggle_lock'))
        self.lock_menu.addAction(self.lock_action)
    
    def _safe_call(self, method_name, pass_args=False):
        """Safely call a method on the parent app."""
        def wrapper(*args, **kwargs):
            try:
                if self.parent_app and hasattr(self.parent_app, method_name):
                    method = getattr(self.parent_app, method_name)
                    if pass_args:
                        return method(*args, **kwargs)
                    else:
                        return method()
                else:
                    logging.warning(f"Method {method_name} not found on parent app")
            except Exception as e:
                logging.error(f"Error calling {method_name}: {e}")
        return wrapper
    
    def update_language(self, language):
        """Update menu language."""
        if language not in SUPPORTED_LANGUAGES:
            logging.error(f"Unsupported language: {language}")
            return
        
        self.current_language = language
        translation = self.translation_manager.get_all_translations(language)
        
        # Update layout direction
        if language == "Arabic":
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        
        # Update menu titles
        if self.file_menu:
            self.file_menu.setTitle(translation["File"])
        if self.audio_menu:
            self.audio_menu.setTitle(translation["Audio"])
        if self.presets_menu:
            self.presets_menu.setTitle(translation["Presets"])
        if self.database_menu:
            self.database_menu.setTitle(translation["Database"])
        if self.tables_menu:
            self.tables_menu.setTitle(translation["Tables"])
        if self.view_menu:
            self.view_menu.setTitle(translation["View"])
        if self.about_menu:
            self.about_menu.setTitle(translation["About"])
        if self.lock_menu:
            self.lock_menu.setTitle(translation["Lock"])
        
        # Update menu action texts
        self._update_menu_action_texts(translation)
        
        # Update language combo box selection without triggering change event
        if self.language_combo:
            self.language_combo.blockSignals(True)
            current_lang_index = SUPPORTED_LANGUAGES.index(language) if language in SUPPORTED_LANGUAGES else 0
            self.language_combo.setCurrentIndex(current_lang_index)
            self.language_combo.blockSignals(False)
        
        # Update widget labels inside menus
        self._update_widget_labels(translation)
        
        # Update labels in parent app if method exists
        if self.parent_app and hasattr(self.parent_app, 'update_language_labels'):
            self.parent_app.update_language_labels(language, translation)
        
        logging.info(f"Language updated to: {language}")
    
    def _update_menu_action_texts(self, translation):
        """Update individual menu action texts."""
        try:
            # Update file menu actions
            if self.file_menu:
                actions = self.file_menu.actions()
                action_index = 0
                for action in actions:
                    if not action.isSeparator():
                        if action_index == 0:
                            action.setText(translation.get("Refresh", "Refresh"))
                        elif action_index == 1:
                            action.setText(translation.get("Toggle Active Status", "Toggle Active Status"))
                        elif action_index == 2:
                            action.setText(translation.get("Exit", "Exit"))
                        action_index += 1
            
            # Update audio menu actions
            if self.audio_menu:
                actions = self.audio_menu.actions()
                action_keys = ["Stop Audio", "Set Directory", "Set Default Directory", 
                              "Play Start", "Play End", "Choose Start", "Choose End", "Remove All Audio"]
                action_index = 0
                for action in actions:
                    if not action.isSeparator() and action_index < len(action_keys):
                        action.setText(translation.get(action_keys[action_index], action_keys[action_index]))
                        action_index += 1
            
            # Update presets menu actions
            if self.presets_menu:
                actions = self.presets_menu.actions()
                action_index = 0
                for action in actions:
                    if not action.isSeparator():
                        if action_index == 1:  # Skip the combo widget action
                            action.setText(translation.get("New Preset", "New Preset"))
                        elif action_index == 2:
                            action.setText(translation.get("Delete Preset", "Delete Preset"))
                        action_index += 1
            
            # Update database menu actions
            if self.database_menu:
                actions = self.database_menu.actions()
                for action in actions:
                    if not action.isSeparator() and hasattr(action, 'text') and action.text() == "Choose Database":
                        action.setText(translation.get("Choose Database", "Choose Database"))
            
            # Update view menu actions
            if self.view_menu:
                actions = self.view_menu.actions()
                for action in actions:
                    if not action.isSeparator() and hasattr(action, 'text'):
                        action_text = action.text()
                        if action_text == "Full Screen" or "Full Screen" in action_text:
                            action.setText(translation.get("Full Screen", "Full Screen"))
                        elif action_text == "Change Font" or "Change Font" in action_text:
                            action.setText(translation.get("Change Font", "Change Font"))
                        elif action_text == "Default Font" or "Default Font" in action_text:
                            action.setText(translation.get("Default Font", "Default Font"))
                        elif action_text == "Change Digital Height" or "Change Digital Height" in action_text:
                            action.setText(translation.get("Change Digital Height", "Change Digital Height"))
            
            # Update tables menu actions
            if self.tables_menu:
                actions = self.tables_menu.actions()
                if len(actions) >= 2:
                    actions[0].setText(translation.get("New Row", "New Row"))
                    actions[1].setText(translation.get("Delete Row", "Delete Row"))
            
            # Update about menu actions
            if self.about_menu:
                actions = self.about_menu.actions()
                if len(actions) >= 2:
                    actions[0].setText(translation.get("About", "About"))
                    actions[1].setText(translation.get("Help", "Help"))
            
            # Update lock menu actions
            if self.lock_menu and self.lock_action:
                self.lock_action.setText(translation.get("Lock", "Lock"))
                
        except Exception as e:
            logging.error(f"Error updating menu action texts: {e}")
    
    def _update_widget_labels(self, translation):
        """Update labels inside widget actions (combo box labels, etc.)."""
        try:
            # Update theme selection label
            if self.view_menu:
                for action in self.view_menu.actions():
                    if isinstance(action, QWidgetAction):
                        widget = action.defaultWidget()
                        if widget:
                            # Look for theme label
                            theme_labels = widget.findChildren(QLabel)
                            for label in theme_labels:
                                if "Theme" in label.text() or "اللون" in label.text():
                                    label.setText(translation.get("Choose Theme:", "Choose Theme:"))
                                elif "Language" in label.text() or "اللغة" in label.text():
                                    label.setText(translation.get("Choose Language:", "Choose Language:"))
            
            # Update preset selection label
            if self.presets_menu:
                for action in self.presets_menu.actions():
                    if isinstance(action, QWidgetAction):
                        widget = action.defaultWidget()
                        if widget:
                            preset_labels = widget.findChildren(QLabel)
                            for label in preset_labels:
                                if "Preset" in label.text() or "الجدول" in label.text():
                                    label.setText(translation.get("Choose Preset:", "Choose Preset:"))

            # Update tables menu color label
            if self.row_color_label is not None:
                self.row_color_label.setText(translation.get("Choose Color:", "Color"))
            self.refresh_row_color_options()
                                    
        except Exception as e:
            logging.error(f"Error updating widget labels: {e}")
    
    def update_database_label(self, db_path=None):
        """Update the database connection status label."""
        if not self.database_label:
            return
        
        if not db_path:
            db_path = config_manager.get_database_path()
        
        if db_path and os.path.exists(db_path):
            db_name = os.path.basename(db_path)
            self.database_label.setText(f"Database: {db_name}")
            self.database_label.setStyleSheet("color: green;")
        else:
            self.database_label.setText("Database: Not Connected")
            self.database_label.setStyleSheet("color: red;")
    
    def update_lock_action(self, is_locked):
        """Update the lock action text."""
        if not self.lock_action:
            return
        
        if is_locked:
            self.lock_action.setText("Unlock")
        else:
            self.lock_action.setText("Lock")
    
    def refresh_presets(self):
        """Refresh the presets combo box."""
        if not self.preset_combo:
            return
        
        try:
            current_preset = self.preset_combo.currentText()
            self.preset_combo.blockSignals(True)
            
            self.preset_combo.clear()
            presets = fetch_presets_from_db() or []
            self.preset_combo.addItems(presets)
            
            # Restore selection if possible
            if current_preset in presets:
                self.preset_combo.setCurrentText(current_preset)
            
            self.preset_combo.blockSignals(False)
            
        except Exception as e:
            logging.error(f"Error refreshing presets: {e}")

    def refresh_row_color_options(self, colors=None):
        """Refresh the row color combo box from the Colors table."""
        if self.row_color_combo is None:
            return

        try:
            colors = colors if colors is not None else (fetch_colors_from_db() or [])
            current_hex = self.row_color_combo.currentData()
            no_color_label = self.translation_manager.get_translation(self.current_language, "No Color", "No Color")

            self.row_color_combo.blockSignals(True)
            self.row_color_combo.clear()
            self.row_color_combo.addItem(no_color_label, "")

            seen_names = {"no color", no_color_label.lower()}
            for color in colors:
                color_name = color.get("name", "").strip()
                color_hex = (color.get("hex", "") or "").strip()

                if not color_name:
                    continue

                dedupe_key = color_name.lower()
                if dedupe_key in seen_names:
                    continue
                seen_names.add(dedupe_key)

                if not color_hex and color_name.lower() in {"no color", no_color_label.lower()}:
                    continue

                self.row_color_combo.addItem(color_name, color_hex)

            index = self.row_color_combo.findData(current_hex)
            self.row_color_combo.setCurrentIndex(index if index >= 0 else 0)
            self.row_color_combo.blockSignals(False)

        except Exception as e:
            logging.error(f"Error refreshing row colors: {e}")

    def set_selected_row_color(self, color_hex):
        """Update the color combo to match the selected schedule row."""
        if self.row_color_combo is None:
            return

        try:
            self.row_color_combo.blockSignals(True)
            index = self.row_color_combo.findData(color_hex or "")
            self.row_color_combo.setCurrentIndex(index if index >= 0 else 0)
            self.row_color_combo.blockSignals(False)
        except Exception as e:
            logging.error(f"Error setting selected row color: {e}")

    def _handle_row_color_changed(self, index):
        """Apply the chosen row color to the selected schedule row."""
        try:
            if index < 0 or not self.parent_app or not hasattr(self.parent_app, 'apply_selected_row_color'):
                return

            color_hex = self.row_color_combo.itemData(index) if self.row_color_combo else ""
            color_name = self.row_color_combo.itemText(index) if self.row_color_combo else ""
            self.parent_app.apply_selected_row_color(color_hex, color_name)
        except Exception as e:
            logging.error(f"Error handling row color change: {e}")


class AboutWindow(QMainWindow):
    """About window with application information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setGeometry(200, 200, 500, 300)
        self.setMinimumSize(400, 250)
        
        # Create central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Application info
        app_info = f"""
        <h2>{APP_NAME}</h2>
        <p><b>Version:</b> {APP_VERSION}</p>
        <p><b>Author:</b> {APP_AUTHOR}</p>
        <br>
        <p>This application is designed to manage school bell schedules.</p>
        <br>
        <p style="direction: rtl; text-align: right;">
        <br>Codded by: Ali Qasem
        </p>
        """
        
        about_label = QLabel(app_info, self)
        about_label.setWordWrap(True)
        about_label.setStyleSheet("padding: 20px; font-size: 12px;")
        layout.addWidget(about_label)


class HelpWindow(QMainWindow):
    """Help window with usage instructions."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help")
        self.setGeometry(50, 50, 700, 600)
        self.setMinimumSize(600, 500)
        
        # Create central widget with scroll area
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        scroll_content = QWidget(scroll_area)
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        
        # Help content
        help_text = '''
        <h1>How to Use the School Bell Application</h1>
        
        <h2>First Time Setup</h2>
        <ul>
            <li>Set the audio directory where your bell sounds are stored</li>
            <li>Check that the times of the periods are correct</li>
            <li>Verify that the audio files are properly configured</li>
            <li>Set the desired preset for your schedule</li>
            <li>Ensure the correct days are active</li>
            <li>Make sure the system is set to active status</li>
        </ul>
        
        <h2>Menu Bar Overview</h2>
        
        <h3>File Menu</h3>
        <ul>
            <li><b>Refresh:</b> Reload application data from database</li>
            <li><b>Toggle Active Status:</b> Enable/disable the bell system</li>
            <li><b>Exit:</b> Close the application</li>
        </ul>
        
        <h3>Audio Menu</h3>
        <ul>
            <li><b>Stop Audio:</b> Stop any currently playing audio</li>
            <li><b>Set Directory:</b> Choose folder containing audio files</li>
            <li><b>Set Default Directory:</b> Use the default audio folder</li>
            <li><b>Play Start/End:</b> Test audio for selected period</li>
            <li><b>Choose Start/End:</b> Select audio files for period</li>
            <li><b>Remove All Audio:</b> Clear all audio assignments</li>
        </ul>
        
        <h3>Presets Menu</h3>
        <ul>
            <li><b>Choose Preset:</b> Select active schedule preset</li>
            <li><b>New Preset:</b> Create a new schedule preset</li>
            <li><b>Delete Preset:</b> Remove current preset and its data</li>
        </ul>
        
        <h3>Database Menu</h3>
        <ul>
            <li>View current database connection status</li>
            <li><b>Choose Database:</b> Select different database file</li>
        </ul>
        
        <h3>Tables Menu</h3>
        <ul>
            <li><b>New Row:</b> Add new period to schedule</li>
            <li><b>Delete Row:</b> Remove selected period</li>
        </ul>
        
        <h3>View Menu</h3>
        <ul>
            <li><b>Full Screen:</b> Toggle fullscreen mode</li>
            <li><b>Change Font:</b> Customize application font</li>
            <li><b>Default Font:</b> Reset to default font settings</li>
            <li><b>Change Digital Height:</b> Adjust clock display size</li>
            <li><b>Choose Theme:</b> Select color theme</li>
            <li><b>Choose Language:</b> Switch between English/Arabic</li>
        </ul>
        
        <h3>Lock Menu</h3>
        <ul>
            <li><b>Lock/Unlock:</b> Prevent unauthorized changes</li>
        </ul>
        
        <h2>Main Window Elements</h2>
        <ul>
            <li><b>Digital Clock:</b> Shows current time</li>
            <li><b>Current Preset:</b> Displays active schedule</li>
            <li><b>Status:</b> Shows if system is Active/Inactive</li>
            <li><b>Current Period:</b> Shows active class period</li>
            <li><b>Progress Bar:</b> Period completion progress</li>
            <li><b>Remaining Time:</b> Time left in current period</li>
            <li><b>Schedule Table:</b> Editable period schedule</li>
            <li><b>Days Table:</b> Configure active days and presets</li>
        </ul>
        
        <h2>Working with Schedules</h2>
        <ul>
            <li>Click on time cells to open time picker</li>
            <li>Use audio buttons to select bell sounds</li>
            <li>Adjust volume sliders for each period</li>
            <li>Add multiple audio files separated by commas</li>
            <li>Configure different schedules for different days</li>
        </ul>
        
        <h2>Troubleshooting</h2>
        <ul>
            <li>Check database connection status in Database menu</li>
            <li>Verify audio directory contains supported files (.mp3, .wav, .ogg)</li>
            <li>Ensure system and individual days are set to active</li>
            <li>Check application logs for detailed error information</li>
            <li>Use refresh function if data appears outdated</li>
        </ul>
        '''
        
        help_label = QLabel(help_text, self)
        help_label.setWordWrap(True)
        help_label.setStyleSheet("padding: 15px; font-size: 11px; line-height: 1.4;")
        scroll_layout.addWidget(help_label)


class TimePickerDialog(QDialog):
    """Custom time picker dialog."""
    
    def __init__(self, current_time="00:00:00", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Time")
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Parse current time
        try:
            hours, minutes, seconds = map(int, current_time.split(":"))
        except (ValueError, AttributeError):
            hours, minutes, seconds = 0, 0, 0
        
        # Time edit widget
        self.time_edit = QTimeEdit(QTime(hours, minutes, seconds), self)
        self.time_edit.setDisplayFormat("HH:mm:ss")
        layout.addWidget(self.time_edit)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_time(self):
        """Get the selected time as string."""
        return self.time_edit.time().toString("HH:mm:ss")
    
    @staticmethod
    def get_time_from_user(current_time="00:00:00", parent=None):
        """Static method to get time from user."""
        dialog = TimePickerDialog(current_time, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_time(), True
        return current_time, False


def show_info_message(message, title="Information", parent=None):
    """Show information message box."""
    try:
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText(message)
        msg_box.setWindowTitle(title)
        msg_box.exec()
    except Exception as e:
        logging.error(f"Error showing info message: {e}")


def show_error_message(message, title="Error", parent=None):
    """Show error message box."""
    try:
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setText(message)
        msg_box.setWindowTitle(title)
        msg_box.exec()
    except Exception as e:
        logging.error(f"Error showing error message: {e}")


def show_warning_message(message, title="Warning", parent=None):
    """Show warning message box."""
    try:
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText(message)
        msg_box.setWindowTitle(title)
        msg_box.exec()
    except Exception as e:
        logging.error(f"Error showing warning message: {e}")


def show_question_dialog(message, title="Question", parent=None):
    """Show question dialog and return user response."""
    try:
        reply = QMessageBox.question(
            parent, title, message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes
    except Exception as e:
        logging.error(f"Error showing question dialog: {e}")
        return False


def get_text_input(prompt, title="Input", default="", password=False, parent=None):
    """Get text input from user."""
    try:
        echo_mode = QLineEdit.EchoMode.Password if password else QLineEdit.EchoMode.Normal
        text, ok = QInputDialog.getText(parent, title, prompt, echo_mode, default)
        return text, ok
    except Exception as e:
        logging.error(f"Error getting text input: {e}")
        return "", False


def get_integer_input(prompt, title="Input", value=0, min_val=0, max_val=1000, parent=None):
    """Get integer input from user."""
    try:
        number, ok = QInputDialog.getInt(parent, title, prompt, value, min_val, max_val)
        return number, ok
    except Exception as e:
        logging.error(f"Error getting integer input: {e}")
        return value, False


def select_file(title="Select File", directory="", file_filter="All Files (*)", parent=None):
    """Show file selection dialog."""
    try:
        file_path, _ = QFileDialog.getOpenFileName(parent, title, directory, file_filter)
        return file_path
    except Exception as e:
        logging.error(f"Error selecting file: {e}")
        return ""


def select_directory(title="Select Directory", directory="", parent=None):
    """Show directory selection dialog."""
    try:
        dir_path = QFileDialog.getExistingDirectory(parent, title, directory)
        return dir_path
    except Exception as e:
        logging.error(f"Error selecting directory: {e}")
        return ""


def select_font(current_font=None, parent=None):
    """Show font selection dialog."""
    try:
        font, ok = QFontDialog.getFont(current_font, parent)
        if ok:
            return font, True
        return current_font, False
    except Exception as e:
        logging.error(f"Error selecting font: {e}")
        return current_font, False


# Module initialization
logging.info("UI Components module initialized successfully")