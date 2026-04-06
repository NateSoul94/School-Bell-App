# School Bell App

A desktop application for **automating school bell schedules and audio playback**.

`School Bell App` is a Python-based scheduling system built with **PyQt6** and **SQLite** to help schools manage class periods, break times, and bell sounds from a simple graphical interface. It is designed for reliability, easy daily use, and straightforward customization.

---

## Overview

This project allows a school or institution to:

- create and manage bell schedules
- assign different presets for different days
- play custom audio files automatically at the correct times
- store settings and schedule data locally in a database
- run as a desktop application with tray support and persistent configuration

The app is especially useful for schools that want a lightweight, offline bell management tool without depending on online services.

---

## Features

### Core Functionality
- 🔔 **Automated bell playback** based on scheduled start and end times
- 📅 **Day-specific schedule presets** for different school days
- 🎵 **Custom audio support** for bell sounds
- 🗂️ **SQLite database storage** for schedules, presets, and settings
- 🖥️ **Desktop GUI** built with PyQt6

### Usability
- 🌍 **Arabic and English language support**
- 🎨 **Theme customization**
- 🔒 **Lock and password options** for settings protection
- 🕒 **Digital clock and remaining time display**
- 📌 **System tray integration** for background operation

### Reliability & Maintenance
- 🧾 **Enhanced logging system** for troubleshooting
- 📈 **Memory monitoring and profiling tools**
- 🛠️ **Crash and shutdown diagnostics utilities**
- 📦 **PyInstaller build support** for Windows executable packaging

---

## Tech Stack

- **Language:** Python
- **GUI Framework:** PyQt6
- **Audio:** `pygame`
- **Database:** SQLite
- **Packaging:** PyInstaller

---

## Project Structure

```text
School Bell App/
├── main.py                    # Application entry point
├── src/
│   ├── main_app.py            # Main GUI application
│   ├── config.py              # App configuration and constants
│   ├── database.py            # Database logic
│   ├── audio_manager.py       # Audio playback handling
│   ├── schedule_manager.py    # Schedule timing logic
│   ├── ui_components.py       # UI dialogs and reusable components
│   └── logging_system.py      # Logging and monitoring
├── assets/
│   ├── icons/                 # Icons
│   └── images/                # Logos and images
├── audio_files/               # Bell audio files
├── docs/                      # Project documentation
└── tools/                     # Debugging and analysis tools
```

---

## Getting Started

### Prerequisites

Make sure you have:

- **Python 3.7+**
- `pip`

### Install Dependencies

```bash
pip install PyQt6 pygame
```

### Run the Application

```bash
python main.py
```

---

## How It Works

The application monitors the current time and compares it against the active schedule stored in the database. When a scheduled period starts or ends, the selected audio file is played automatically.

Users can maintain multiple presets, assign them to specific days, and customize how the interface looks and behaves. Configuration is saved so the app can be reopened without re-entering all settings.

---

## Audio Files

You can use your own bell sounds in supported formats such as:

- `.mp3`
- `.wav`
- `.ogg`

For development use, audio files can be placed in the project's `audio_files/` or configured audio directory.
When packaged for Windows, the app is designed to support user-managed audio files separately from the executable.

---

## Build for Windows

This project includes build scripts and a PyInstaller spec file:

- `build_app.bat`
- `build_app.ps1`
- `SchoolBellApp.spec`

To build manually:

```bash
python -m pyinstaller SchoolBellApp.spec
```

See `docs/BUILD_INSTRUCTIONS.md` for full packaging details.

---

## Documentation

Additional project documentation is available in the `docs/` folder, including:

- build instructions
- logging and diagnostics notes
- memory profiling guidance
- reorganization and enhancement summaries

---

## Use Cases

This application is suitable for:

- schools and training centers
- timed class/break announcements
- offline local schedule automation
- environments needing a simple customizable bell system

---

## License

See `License.txt` for licensing information.

---

## Author

**Ali Qasem**
