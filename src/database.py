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
Database operations module for School Bell Application.
Handles all database connections, queries, and data management.
"""

import sqlite3
import os
import logging
from functools import wraps
from config import config_manager, DATABASE_TABLES


def database_operation(func):
    """Decorator for database operations with error handling and connection management."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        connection_string = get_connection_string()
        if not connection_string:
            logging.error(f"No database connection available for {func.__name__}")
            return None
        
        conn = None
        try:
            conn = sqlite3.connect(connection_string, timeout=10.0)
            # Pass connection as first argument if function expects it
            if 'conn' in func.__code__.co_varnames:
                result = func(conn, *args, **kwargs)
            else:
                # For functions that manage their own connections
                result = func(*args, **kwargs)
            return result
        except sqlite3.Error as e:
            logging.error(f"Database error in {func.__name__}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error in {func.__name__}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    return wrapper


def get_connection_string():
    """Get the current database connection string."""
    return config_manager.get_database_path()


def test_database_connection():
    """Test if database connection is available and working."""
    connection_string = get_connection_string()
    if not connection_string:
        return False
    
    if not os.path.exists(connection_string):
        return False
    
    try:
        conn = sqlite3.connect(connection_string, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Database connection test failed: {e}")
        return False


def ensure_tables_exist():
    """Ensure all required database tables exist with proper schema."""
    connection_string = get_connection_string()
    if not connection_string:
        logging.error("Cannot ensure tables exist - no database connection")
        return False
    
    try:
        conn = sqlite3.connect(connection_string)
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Period TEXT NOT NULL,
                Start_Time TEXT NOT NULL,
                End_Time TEXT NOT NULL,
                Audio_Start TEXT,
                Audio_End TEXT,
                Volume REAL DEFAULT 1.0,
                Preset TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Settings (
                id INTEGER PRIMARY KEY DEFAULT 1,
                language TEXT DEFAULT 'English',
                theme TEXT DEFAULT 'Default',
                font TEXT DEFAULT 'Segoe UI',
                font_weight TEXT DEFAULT 'normal',
                font_size INTEGER DEFAULT 14,
                height INTEGER DEFAULT 50,
                directory TEXT,
                preset TEXT,
                active BOOLEAN DEFAULT 1,
                password TEXT,
                lock BOOLEAN DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_name TEXT NOT NULL UNIQUE,
                active BOOLEAN DEFAULT 1,
                preset TEXT
            )
        ''')
        
        # Ensure Settings table has a default row
        cursor.execute("SELECT COUNT(*) FROM Settings WHERE id = 1")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO Settings (id) VALUES (1)")
        
        # Ensure days table is populated
        cursor.execute("SELECT COUNT(*) FROM days")
        if cursor.fetchone()[0] == 0:
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            for day in day_names:
                cursor.execute("INSERT INTO days (day_name, active) VALUES (?, 1)", (day,))
        
        conn.commit()
        conn.close()

        ensure_days_preset_column()
        ensure_schedule_color_column()
        ensure_colors_table()

        logging.info("Database tables verified and initialized")
        return True
        
    except Exception as e:
        logging.error(f"Error ensuring tables exist: {e}")
        return False


def ensure_days_preset_column():
    """Ensure the days table has a preset column."""
    connection_string = get_connection_string()
    if not connection_string:
        return False
    
    try:
        conn = sqlite3.connect(connection_string)
        cursor = conn.cursor()
        
        # Check if preset column exists
        try:
            cursor.execute("SELECT preset FROM days LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            cursor.execute("ALTER TABLE days ADD COLUMN preset TEXT")
            conn.commit()
            logging.info("Added preset column to days table")
        
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error ensuring days preset column: {e}")
        return False


def ensure_schedule_color_column():
    """Ensure the Schedule table has a Color column."""
    connection_string = get_connection_string()
    if not connection_string:
        return False

    try:
        conn = sqlite3.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(Schedule)")
        columns = {row[1] for row in cursor.fetchall()}

        if columns and "Color" not in columns:
            cursor.execute("ALTER TABLE Schedule ADD COLUMN Color TEXT DEFAULT ''")
            conn.commit()
            logging.info("Added Color column to Schedule table")

        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error ensuring schedule color column: {e}")
        return False


def ensure_colors_table():
    """Ensure the Colors table exists, is deduplicated, and has sane defaults."""
    connection_string = get_connection_string()
    if not connection_string:
        return False

    default_colors = [
        ("No Color", ""),
        ("Red", "#FFCDD2"),
        ("Orange", "#FFE0B2"),
        ("Yellow", "#FFF9C4"),
        ("Green", "#C8E6C9"),
        ("Blue", "#BBDEFB"),
        ("Purple", "#E1BEE7"),
        ("Pink", "#F8BBD0"),
        ("Gray", "#E0E0E0")
    ]

    conn = None
    try:
        conn = sqlite3.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Colors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Hex TEXT,
                Name TEXT NOT NULL
            )
        ''')

        cursor.execute("PRAGMA table_info(Colors)")
        columns = {row[1] for row in cursor.fetchall()}

        if "Hex" not in columns:
            cursor.execute("ALTER TABLE Colors ADD COLUMN Hex TEXT")
        if "Name" not in columns:
            cursor.execute("ALTER TABLE Colors ADD COLUMN Name TEXT")

        cursor.execute("DELETE FROM Colors WHERE TRIM(COALESCE(Name, '')) = ''")
        cursor.execute('''
            DELETE FROM Colors
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM Colors
                WHERE TRIM(COALESCE(Name, '')) != ''
                GROUP BY LOWER(TRIM(Name))
            )
            AND TRIM(COALESCE(Name, '')) != ''
        ''')

        try:
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_colors_name_unique ON Colors(Name COLLATE NOCASE)"
            )
        except sqlite3.Error as index_error:
            logging.warning(f"Could not create unique Colors index: {index_error}")

        cursor.execute("SELECT COUNT(*) FROM Colors")
        color_count = cursor.fetchone()[0]

        if color_count == 0:
            for name, hex_value in default_colors:
                cursor.execute(
                    "INSERT INTO Colors (Name, Hex) VALUES (?, ?)",
                    (name, hex_value)
                )

        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error ensuring Colors table: {e}")
        return False
    finally:
        if conn:
            conn.close()


# Schedule operations
@database_operation
def fetch_schedule_from_db(conn, preset):
    """Fetch schedule for a given preset from database."""
    ensure_schedule_color_column()

    try:
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT Period, Start_Time, End_Time, Audio_Start, Audio_End, Volume, Color
                FROM Schedule WHERE Preset = ?
                ORDER BY Start_Time
            """, (preset,))
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            cursor.execute("""
                SELECT Period, Start_Time, End_Time, Audio_Start, Audio_End, Volume
                FROM Schedule WHERE Preset = ?
                ORDER BY Start_Time
            """, (preset,))
            rows = cursor.fetchall()
        
        schedule = []
        for row in rows:
            schedule.append({
                "period": row[0],
                "start": row[1],
                "end": row[2],
                "audio_start": row[3].split(',') if row[3] else [],
                "audio_end": row[4].split(',') if row[4] else [],
                "volume": row[5] if row[5] is not None else 1.0,
                "color": row[6] if len(row) > 6 and row[6] else ""
            })
        return schedule
    except sqlite3.Error as e:
        logging.error(f"Database error fetching schedule: {e}")
        return []
    except Exception as e:
        logging.error(f"Error fetching schedule from database: {e}")
        return []


@database_operation
def fetch_colors_from_db(conn):
    """Fetch available row colors from the Colors table."""
    ensure_colors_table()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Name, Hex
            FROM Colors
            WHERE TRIM(COALESCE(Name, '')) != ''
            ORDER BY CASE WHEN TRIM(COALESCE(Hex, '')) = '' THEN 0 ELSE 1 END, Name
        """)

        colors = []
        seen_names = set()
        for row in cursor.fetchall():
            color_name = (row[0] or "").strip()
            color_hex = (row[1] or "").strip()

            if not color_name:
                continue

            dedupe_key = color_name.lower()
            if dedupe_key in seen_names:
                continue
            seen_names.add(dedupe_key)
            colors.append({"name": color_name, "hex": color_hex})

        return colors
    except sqlite3.Error as e:
        logging.error(f"Database error fetching colors: {e}")
        return []
    except Exception as e:
        logging.error(f"Error fetching colors from database: {e}")
        return []


def update_schedule_in_db(preset, period, field, value):
    """Update a specific field in the schedule."""
    connection_string = get_connection_string()
    if not connection_string:
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(connection_string)
        cursor = conn.cursor()
        
        # Map field names to database columns
        field_mapping = {
            "period": "Period",
            "start": "Start_Time", 
            "end": "End_Time",
            "audio_start": "Audio_Start",
            "audio_end": "Audio_End",
            "volume": "Volume",
            "color": "Color"
        }
        
        db_field = field_mapping.get(field, field)
        
        # Handle list fields (audio_start, audio_end)
        if field in ["audio_start", "audio_end"] and isinstance(value, list):
            value = ','.join(value)
        
        cursor.execute(f"UPDATE Schedule SET {db_field} = ? WHERE Period = ? AND Preset = ?", 
                      (value, period, preset))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error updating schedule in database: {e}")
        return False
    finally:
        if conn:
            conn.close()


def insert_schedule_row(preset, period_data):
    """Insert a new schedule row."""
    connection_string = get_connection_string()
    if not connection_string:
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(connection_string)
        cursor = conn.cursor()
        
        # Prepare audio fields
        audio_start = ','.join(period_data.get('audio_start', [])) if isinstance(period_data.get('audio_start'), list) else period_data.get('audio_start', '')
        audio_end = ','.join(period_data.get('audio_end', [])) if isinstance(period_data.get('audio_end'), list) else period_data.get('audio_end', '')
        color = period_data.get('color', '') or ''
        
        cursor.execute("""
            INSERT INTO Schedule (Period, Start_Time, End_Time, Audio_Start, Audio_End, Volume, Preset, Color) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            period_data.get('period', ''),
            period_data.get('start', '00:00:00'),
            period_data.get('end', '00:00:00'),
            audio_start,
            audio_end,
            period_data.get('volume', 1.0),
            preset,
            color
        ))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error inserting schedule row: {e}")
        return False
    finally:
        if conn:
            conn.close()


def delete_schedule_row(preset, period):
    """Delete a schedule row."""
    connection_string = get_connection_string()
    if not connection_string:
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Schedule WHERE Period = ? AND Preset = ?", (period, preset))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error deleting schedule row: {e}")
        return False
    finally:
        if conn:
            conn.close()


# Preset operations
@database_operation
def fetch_presets_from_db(conn):
    """Fetch all presets from database."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM Presets ORDER BY name")
        presets = [row[0] for row in cursor.fetchall()]
        return presets
    except sqlite3.Error as e:
        logging.error(f"Database error fetching presets: {e}")
        return []
    except Exception as e:
        logging.error(f"Error fetching presets from database: {e}")
        return []


def create_preset(preset_name):
    """Create a new preset."""
    connection_string = get_connection_string()
    if not connection_string:
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Presets (name) VALUES (?)", (preset_name,))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error creating preset: {e}")
        return False
    finally:
        if conn:
            conn.close()


def delete_preset(preset_name):
    """Delete a preset and all its associated schedule entries."""
    connection_string = get_connection_string()
    if not connection_string:
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(connection_string)
        cursor = conn.cursor()
        
        # Delete associated schedule entries first
        cursor.execute("DELETE FROM Schedule WHERE Preset = ?", (preset_name,))
        # Delete the preset
        cursor.execute("DELETE FROM Presets WHERE name = ?", (preset_name,))
        
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error deleting preset: {e}")
        return False
    finally:
        if conn:
            conn.close()


# Days operations
@database_operation
def fetch_days_from_db(conn):
    """Fetch all days configuration from database."""
    ensure_days_preset_column()
    
    try:
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id, day_name, active, preset FROM days ORDER BY id")
            rows = cursor.fetchall()
            days = [{"id": r[0], "day_name": r[1], "active": bool(r[2]), "preset": r[3]} for r in rows]
        except sqlite3.OperationalError:
            # Fallback if preset column doesn't exist
            cursor.execute("SELECT id, day_name, active FROM days ORDER BY id")
            rows = cursor.fetchall()
            days = [{"id": r[0], "day_name": r[1], "active": bool(r[2]), "preset": None} for r in rows]
        
        return days
    except sqlite3.Error as e:
        logging.error(f"Database error fetching days: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error fetching days: {e}")
        return []


def update_day_status_in_db(day_id, status):
    """Update day active status in database."""
    connection_string = get_connection_string()
    if not connection_string:
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute("UPDATE days SET active = ? WHERE id = ?", (int(status), day_id))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error updating day status in database: {e}")
        return False
    finally:
        if conn:
            conn.close()


@database_operation
def save_day_preset_in_db(conn, day_id, preset):
    """Save day-specific preset in database."""
    ensure_days_preset_column()
    
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE days SET preset = ? WHERE id = ?", (preset, day_id))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error saving day preset to database: {e}")
        return False


@database_operation
def fetch_preset_for_day(conn, day_name):
    """Fetch preset for a specific day."""
    ensure_days_preset_column()
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT preset FROM days WHERE LOWER(day_name) = ?", (day_name.lower(),))
        row = cursor.fetchone()
        return row[0] if row and row[0] else None
    except Exception:
        return None


# Settings operations
@database_operation
def fetch_language_from_db(conn):
    """Fetch language setting from database."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT language FROM Settings WHERE id = 1")
        row = cursor.fetchone()
        return row[0] if row and row[0] else "English"
    except Exception as e:
        logging.error(f"Error fetching language from database: {e}")
        return "English"


@database_operation
def save_language_to_db(conn, language):
    """Save language setting to database."""
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Settings SET language = ? WHERE id = 1", (language,))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error saving language to database: {e}")
        return False


@database_operation
def fetch_theme_from_db(conn):
    """Fetch theme setting from database."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT theme FROM Settings WHERE id = 1")
        row = cursor.fetchone()
        return row[0] if row and row[0] else "Default"
    except Exception as e:
        logging.error(f"Error fetching theme from database: {e}")
        return "Default"


@database_operation
def save_theme_to_db(conn, theme):
    """Save theme setting to database."""
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Settings SET theme = ? WHERE id = 1", (theme,))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error saving theme to database: {e}")
        return False


@database_operation
def fetch_current_preset_from_db(conn):
    """Fetch current preset from database."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT preset FROM Settings WHERE id = 1")
        row = cursor.fetchone()
        return row[0] if row and row[0] else None
    except Exception as e:
        logging.error(f"Error fetching current preset from database: {e}")
        return None


@database_operation
def save_current_preset_to_db(conn, preset):
    """Save current preset to database."""
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Settings SET preset = ? WHERE id = 1", (preset,))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error saving current preset to database: {e}")
        return False


@database_operation
def fetch_active_status_from_db(conn):
    """Fetch active status from database."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT active FROM Settings WHERE id = 1")
        row = cursor.fetchone()
        return bool(row[0]) if row and row[0] is not None else True
    except Exception as e:
        logging.error(f"Error fetching active status from database: {e}")
        return True


def update_active_status_in_db(status):
    """Update active status in database."""
    connection_string = get_connection_string()
    if not connection_string:
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute("UPDATE Settings SET active = ? WHERE id = 1", (int(status),))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error updating active status in database: {e}")
        return False
    finally:
        if conn:
            conn.close()


@database_operation
def fetch_audio_directory_from_db(conn):
    """Fetch audio directory from database."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT directory FROM Settings WHERE id = 1")
        row = cursor.fetchone()
        return row[0] if row and row[0] else None
    except Exception as e:
        logging.error(f"Error fetching audio directory from database: {e}")
        return None


@database_operation
def save_audio_directory_to_db(conn, directory):
    """Save audio directory to database."""
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Settings SET directory = ? WHERE id = 1", (directory,))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error saving audio directory to database: {e}")
        return False


@database_operation
def fetch_font_settings_from_db(conn):
    """Fetch font settings from database."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT font, font_weight, font_size FROM Settings WHERE id = 1")
        row = cursor.fetchone()
        
        if row:
            font_family = row[0] if row[0] else "Segoe UI"
            font_weight = row[1] if row[1] else "normal"
            font_size = row[2] if row[2] else 14
            return font_family, font_weight, font_size
        else:
            return "Segoe UI", "normal", 14
    except Exception as e:
        logging.error(f"Error fetching font settings from database: {e}")
        return "Segoe UI", "normal", 14


@database_operation
def save_font_settings_to_db(conn, font_family, font_weight, font_size):
    """Save font settings to database."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Settings 
            SET font = ?, font_weight = ?, font_size = ? 
            WHERE id = 1
        """, (font_family, font_weight, font_size))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error saving font settings to database: {e}")
        return False


@database_operation
def fetch_height_from_db(conn):
    """Fetch digital height setting from database."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT height FROM Settings WHERE id = 1")
        row = cursor.fetchone()
        return row[0] if row and row[0] else 50
    except Exception as e:
        logging.error(f"Error fetching height from database: {e}")
        return 50


@database_operation
def save_height_to_db(conn, height):
    """Save digital height setting to database."""
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Settings SET height = ? WHERE id = 1", (height,))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error saving height to database: {e}")
        return False


def fetch_password_from_db():
    """Fetch password from database."""
    connection_string = get_connection_string()
    if not connection_string:
        return None
    
    conn = None
    try:
        conn = sqlite3.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM Settings WHERE id = 1")
        row = cursor.fetchone()
        return row[0] if row and row[0] else None
    except Exception as e:
        logging.error(f"Error fetching password from database: {e}")
        return None
    finally:
        if conn:
            conn.close()


def save_password_to_db(password):
    """Save password to database."""
    connection_string = get_connection_string()
    if not connection_string:
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute("UPDATE Settings SET password = ? WHERE id = 1", (password,))
        conn.commit()
        logging.info(f"Password saved successfully")
        return True
    except Exception as e:
        logging.error(f"Error saving password to database: {e}")
        return False
    finally:
        if conn:
            conn.close()


@database_operation
def fetch_lock_state_from_db(conn):
    """Fetch lock state from database."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT lock FROM Settings WHERE id = 1")
        row = cursor.fetchone()
        return bool(row[0]) if row and row[0] is not None else False
    except Exception as e:
        logging.error(f"Error fetching lock state from database: {e}")
        return False


def update_lock_state_in_db(state):
    """Update lock state in database."""
    connection_string = get_connection_string()
    if not connection_string:
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute("UPDATE Settings SET lock = ? WHERE id = 1", (int(state),))
        conn.commit()
        logging.info(f"Lock state updated to {state}")
        return True
    except Exception as e:
        logging.error(f"Error updating lock state in database: {e}")
        return False
    finally:
        if conn:
            conn.close()


# Utility functions
def check_day_active(day_name):
    """Check if a specific day is active."""
    days = fetch_days_from_db()
    for day in days:
        if day["day_name"].lower() == day_name.lower():
            return day["active"]
    return False


def get_database_info():
    """Get comprehensive database information for debugging."""
    connection_string = get_connection_string()
    if not connection_string:
        return {"status": "No connection", "path": None}
    
    info = {
        "status": "Connected" if test_database_connection() else "Connection failed",
        "path": connection_string,
        "exists": os.path.exists(connection_string),
        "size": 0,
        "tables": {},
        "presets_count": 0,
        "schedule_count": 0
    }
    
    try:
        info["size"] = os.path.getsize(connection_string)
        
        conn = sqlite3.connect(connection_string, timeout=5.0)
        cursor = conn.cursor()
        
        # Get table information
        for table_name in DATABASE_TABLES.keys():
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                info["tables"][table_name] = count
                
                if table_name == "Presets":
                    info["presets_count"] = count
                elif table_name == "Schedule":
                    info["schedule_count"] = count
            except sqlite3.Error:
                info["tables"][table_name] = "Error"
        
        conn.close()
        
    except Exception as e:
        info["error"] = str(e)
    
    return info


def initialize_database():
    """Initialize database with proper schema and default data."""
    if not test_database_connection():
        logging.error("Cannot initialize database - no connection available")
        return False
    
    try:
        success = ensure_tables_exist()
        if success:
            ensure_days_preset_column()
            ensure_schedule_color_column()
            ensure_colors_table()
            logging.info("Database initialized successfully")
        return success
    except Exception as e:
        logging.error(f"Error initializing database: {e}")
        return False


# Initialize database on module import
if get_connection_string():
    initialize_database()