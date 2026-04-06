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
Shutdown Detective - Monitors and analyzes application shutdowns

This script analyzes the application logs to identify shutdown patterns and causes.
"""

import os
import re
import datetime
from collections import defaultdict, Counter

def analyze_shutdown_logs():
    """Analyze application logs to identify shutdown patterns"""
    
    log_dir = os.path.join(os.getenv('APPDATA', ''), 'Ali AHK Qasem', 'SchoolBellApp', 'logs')
    if not os.path.exists(log_dir):
        print("No log directory found")
        return
    
    shutdown_events = []
    error_patterns = []
    uptime_data = []
    
    for log_file in os.listdir(log_dir):
        if log_file.startswith('school_bell_') and log_file.endswith('.log'):
            log_path = os.path.join(log_dir, log_file)
            analyze_log_file(log_path, shutdown_events, error_patterns, uptime_data)
    
    print("="*60)
    print("SHUTDOWN DETECTIVE REPORT")
    print("="*60)
    
    if shutdown_events:
        print(f"\n📊 SHUTDOWN EVENTS FOUND: {len(shutdown_events)}")
        print("-" * 40)
        for event in shutdown_events[-10:]:  # Show last 10
            print(f"Date: {event['date']}")
            print(f"Reason: {event['reason']}")
            print(f"Uptime: {event['uptime']}")
            print(f"Context: {event.get('context', 'N/A')}")
            print("-" * 40)
    else:
        print("\n✅ No explicit shutdown events found in logs")
    
    if error_patterns:
        print(f"\n⚠️  ERROR PATTERNS: {len(error_patterns)}")
        error_counts = Counter(error_patterns)
        for error, count in error_counts.most_common(10):
            print(f"  {count}x: {error}")
    
    if uptime_data:
        print(f"\n⏱️  UPTIME ANALYSIS:")
        uptimes = [u for u in uptime_data if u > 0]
        if uptimes:
            avg_uptime = sum(uptimes) / len(uptimes)
            print(f"  Average uptime: {avg_uptime/3600:.1f} hours")
            print(f"  Max uptime: {max(uptimes)/3600:.1f} hours")
            print(f"  Min uptime: {min(uptimes)/3600:.1f} hours")
    
    # Look for common shutdown triggers
    print(f"\n🔍 POTENTIAL CAUSES:")
    analyze_shutdown_causes(shutdown_events, error_patterns)

def analyze_log_file(log_path, shutdown_events, error_patterns, uptime_data):
    """Analyze a single log file for shutdown information"""
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        startup_time = None
        shutdown_time = None
        
        for line in lines:
            # Look for startup
            if "School Bell Application starting up" in line:
                startup_time = extract_timestamp(line)
            
            # Look for shutdown events
            elif "APPLICATION SHUTDOWN INITIATED" in line:
                shutdown_time = extract_timestamp(line)
                reason_match = re.search(r'REASON: (.+)', line)
                reason = reason_match.group(1) if reason_match else "Unknown"
                
                uptime = 0
                if startup_time and shutdown_time:
                    uptime = (shutdown_time - startup_time).total_seconds()
                
                shutdown_events.append({
                    'date': shutdown_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'reason': reason,
                    'uptime': f"{uptime/3600:.1f} hours" if uptime > 0 else "Unknown",
                    'log_file': os.path.basename(log_path)
                })
                
                uptime_data.append(uptime)
            
            # Look for error patterns
            elif " - ERROR - " in line:
                error_match = re.search(r'ERROR - (.+)', line)
                if error_match:
                    error_patterns.append(error_match.group(1))
            
            elif " - CRITICAL - " in line:
                error_match = re.search(r'CRITICAL - (.+)', line)
                if error_match:
                    error_patterns.append(f"CRITICAL: {error_match.group(1)}")
                    
    except Exception as e:
        print(f"Error reading {log_path}: {e}")

def extract_timestamp(line):
    """Extract timestamp from log line"""
    try:
        # Format: 2025-10-20 14:23:15,025 - INFO - ...
        timestamp_str = line.split(' - ')[0]
        return datetime.datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
    except:
        return None

def analyze_shutdown_causes(shutdown_events, error_patterns):
    """Analyze potential causes based on patterns"""
    
    causes = []
    
    # Check for database issues
    db_errors = [e for e in error_patterns if 'database' in e.lower() or 'sqlite' in e.lower()]
    if db_errors:
        causes.append(f"🗃️  Database issues detected ({len(db_errors)} occurrences)")
    
    # Check for memory issues
    memory_errors = [e for e in error_patterns if 'memory' in e.lower() or 'malloc' in e.lower()]
    if memory_errors:
        causes.append(f"💾 Memory issues detected ({len(memory_errors)} occurrences)")
    
    # Check for thread issues
    thread_errors = [e for e in error_patterns if 'thread' in e.lower() or 'background' in e.lower()]
    if thread_errors:
        causes.append(f"🧵 Thread issues detected ({len(thread_errors)} occurrences)")
    
    # Check for system signals
    signal_shutdowns = [e for e in shutdown_events if 'signal' in e['reason'].lower()]
    if signal_shutdowns:
        causes.append(f"📡 System signals caused {len(signal_shutdowns)} shutdowns")
    
    # Check for unexpected shutdowns (short uptime)
    short_runs = [e for e in shutdown_events if 'hours' in e['uptime'] and float(e['uptime'].split()[0]) < 0.5]
    if short_runs:
        causes.append(f"⚡ {len(short_runs)} shutdowns occurred within 30 minutes of startup")
    
    if causes:
        for cause in causes:
            print(f"  {cause}")
    else:
        print("  No obvious patterns detected")
        print("  Possible causes:")
        print("    - Windows power management (sleep/hibernate)")
        print("    - Windows updates or system maintenance")
        print("    - User account switching")
        print("    - Remote desktop disconnection")
        print("    - Antivirus software interference")
        print("    - System resource exhaustion")

def check_windows_events():
    """Check Windows Event Logs for system events"""
    print(f"\n🪟 WINDOWS SYSTEM EVENTS:")
    print("To check Windows Event Logs manually:")
    print("1. Open Event Viewer (eventvwr.msc)")
    print("2. Navigate to Windows Logs > System")
    print("3. Look for events around shutdown times:")
    print("   - Event ID 1074: System shutdown/restart")
    print("   - Event ID 6006: Event log service stopped")
    print("   - Event ID 6008: Unexpected shutdown")
    print("   - Event ID 1001: System power events")

if __name__ == "__main__":
    print("Starting Shutdown Detective Analysis...")
    analyze_shutdown_logs()
    check_windows_events()
    
    print(f"\n💡 RECOMMENDATIONS:")
    print("1. Run with enhanced logging for 24 hours")
    print("2. Check Windows Event Viewer for system events")  
    print("3. Monitor Windows power settings")
    print("4. Disable Windows automatic updates during testing")
    print("5. Check if running on battery vs AC power makes a difference")