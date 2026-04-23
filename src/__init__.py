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
School Bell Application - Source Module

This module contains the core application components for the School Bell Application.

Components:
- config: Configuration management
- database: Database operations and management
- logging_system: Enhanced logging and monitoring
- audio_manager: Audio playback and management
- schedule_manager: Schedule management and monitoring
- ui_components: User interface components
- main_app: Main application class

Author: Ali Qasem
Version: 2.3.0
"""

__version__ = "2.3.0"
__author__ = "Ali Qasem"

# Core modules
from .config import *
from .database import *
from .logging_system import *
from .audio_manager import *
from .schedule_manager import *
from .ui_components import *
from .main_app import *