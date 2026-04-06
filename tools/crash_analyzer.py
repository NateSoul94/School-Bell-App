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
Enhanced Crash Analyzer - Comprehensive crash detection and analysis tool

This script analyzes logs and system state to identify application crashes and their causes.
"""

import os
import json
import datetime
import glob
from collections import defaultdict, Counter

def analyze_app_status():
    """Analyze the app status file to detect crashes"""
    log_dir = os.path.join(os.getenv('APPDATA', ''), 'Ali AHK Qasem', 'SchoolBellApp', 'logs')
    status_file = os.path.join(log_dir, 'app_status.json')
    
    print("="*60)
    print("CRASH ANALYZER - ENHANCED DIAGNOSTICS")
    print("="*60)
    
    if not os.path.exists(status_file):
        print("❌ No app status file found - cannot detect crashes")
        print(f"Expected location: {status_file}")
        return False
    
    try:
        with open(status_file, 'r') as f:
            status = json.load(f)
        
        print("📊 APPLICATION STATUS ANALYSIS:")
        print("-" * 40)
        print(f"Process ID: {status.get('pid', 'Unknown')}")
        print(f"Start Time: {status.get('start_time', 'Unknown')}")
        print(f"Current Status: {status.get('status', 'Unknown')}")
        print(f"Last Heartbeat: {status.get('last_heartbeat', 'Unknown')}")
        print(f"Expected Shutdown: {status.get('expected_shutdown', 'Unknown')}")
        print(f"Shutdown Reason: {status.get('shutdown_reason', 'Unknown')}")
        
        # Analyze status for crash indicators
        current_status = status.get('status', '').upper()
        expected_shutdown = status.get('expected_shutdown', False)
        
        if current_status == 'CRASHED':
            print("\n🚨 CRASH DETECTED!")
            print(f"Crash Reason: {status.get('shutdown_reason', 'Unknown')}")
            return True
        elif current_status == 'THREAD_CRASHED':
            print("\n⚠️  BACKGROUND THREAD CRASH DETECTED!")
            return True
        elif current_status in ['RUNNING', 'INITIALIZING'] and not is_process_running(status.get('pid')):
            print("\n💥 UNEXPECTED TERMINATION DETECTED!")
            print("Application status indicates running but process is not active")
            return True
        elif current_status == 'SHUTDOWN' and expected_shutdown:
            print("\n✅ NORMAL SHUTDOWN DETECTED")
            return False
        else:
            print(f"\n🟡 UNKNOWN STATUS: {current_status}")
            return True
            
    except Exception as e:
        print(f"❌ Error reading status file: {e}")
        return False

def is_process_running(pid):
    """Check if a process is still running"""
    if not pid:
        return False
    
    try:
        import psutil
        return psutil.pid_exists(int(pid))
    except (ImportError, ValueError, TypeError):
        # Fallback method for Windows
        try:
            import os
            os.kill(int(pid), 0)
            return True
        except (OSError, ValueError, TypeError):
            return False

def analyze_log_files():
    """Analyze log files for crash patterns"""
    log_dir = os.path.join(os.getenv('APPDATA', ''), 'Ali AHK Qasem', 'SchoolBellApp', 'logs')
    
    if not os.path.exists(log_dir):
        print(f"❌ No log directory found: {log_dir}")
        return
    
    print("\n📋 LOG FILE ANALYSIS:")
    print("-" * 40)
    
    # Find all log files
    main_logs = glob.glob(os.path.join(log_dir, 'school_bell_*.log'))
    crash_logs = glob.glob(os.path.join(log_dir, 'crashes_*.log'))
    
    print(f"Main log files found: {len(main_logs)}")
    print(f"Crash log files found: {len(crash_logs)}")
    
    # Analyze crash logs first
    if crash_logs:
        print("\n🔥 CRASH LOG ANALYSIS:")
        for crash_log in sorted(crash_logs)[-3:]:  # Last 3 crash logs
            analyze_crash_log(crash_log)
    
    # Analyze main logs
    if main_logs:
        print("\n📊 MAIN LOG ANALYSIS:")
        analyze_main_logs(main_logs[-3:])  # Last 3 main logs

def analyze_crash_log(crash_log_path):
    """Analyze a specific crash log file"""
    print(f"\nAnalyzing: {os.path.basename(crash_log_path)}")
    
    try:
        with open(crash_log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        crash_count = 0
        for line in lines:
            if "CRASH:" in line:
                crash_count += 1
                print(f"  💥 {line.strip()}")
        
        if crash_count == 0:
            print("  ✅ No crashes found in this file")
        else:
            print(f"  Total crashes: {crash_count}")
            
    except Exception as e:
        print(f"  ❌ Error reading crash log: {e}")

def analyze_main_logs(log_files):
    """Analyze main log files for patterns"""
    error_patterns = Counter()
    shutdown_reasons = Counter()
    thread_issues = 0
    memory_issues = 0
    
    for log_file in sorted(log_files):
        print(f"\nAnalyzing: {os.path.basename(log_file)}")
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count various issue patterns
            startup_count = content.count("SCHOOL BELL APPLICATION STARTUP")
            shutdown_count = content.count("APPLICATION SHUTDOWN INITIATED")
            error_count = content.count(" - ERROR - ")
            critical_count = content.count(" - CRITICAL - ")
            thread_crash_count = content.count("Background thread terminated while app is still running")
            
            print(f"  Startups: {startup_count}")
            print(f"  Shutdowns: {shutdown_count}")
            print(f"  Errors: {error_count}")
            print(f"  Critical errors: {critical_count}")
            
            if thread_crash_count > 0:
                print(f"  🚨 Thread crashes: {thread_crash_count}")
                thread_issues += thread_crash_count
            
            # Look for specific error patterns
            lines = content.split('\n')
            for line in lines:
                if " - ERROR - " in line or " - CRITICAL - " in line:
                    # Extract error message
                    parts = line.split(' - ', 3)
                    if len(parts) >= 4:
                        error_msg = parts[3]
                        # Categorize error
                        if 'database' in error_msg.lower():
                            error_patterns['Database Error'] += 1
                        elif 'memory' in error_msg.lower():
                            error_patterns['Memory Error'] += 1
                            memory_issues += 1
                        elif 'audio' in error_msg.lower():
                            error_patterns['Audio Error'] += 1
                        elif 'thread' in error_msg.lower():
                            error_patterns['Thread Error'] += 1
                        elif 'pygame' in error_msg.lower():
                            error_patterns['Pygame Error'] += 1
                        else:
                            error_patterns['Other Error'] += 1
                
                # Look for shutdown reasons
                if "SHUTDOWN REASON:" in line:
                    reason = line.split("SHUTDOWN REASON:")[1].strip()
                    shutdown_reasons[reason] += 1
        
        except Exception as e:
            print(f"  ❌ Error analyzing log file: {e}")
    
    # Summary
    print(f"\n📈 PATTERN SUMMARY:")
    print("-" * 40)
    
    if error_patterns:
        print("Error Categories:")
        for error_type, count in error_patterns.most_common():
            print(f"  {error_type}: {count}")
    
    if shutdown_reasons:
        print("\nShutdown Reasons:")
        for reason, count in shutdown_reasons.most_common():
            print(f"  {reason}: {count}")
    
    if thread_issues > 0:
        print(f"\n⚠️  Thread stability issues detected: {thread_issues} incidents")
    
    if memory_issues > 0:
        print(f"⚠️  Memory-related issues detected: {memory_issues} incidents")

def check_system_resources():
    """Check current system resources"""
    print(f"\n💻 SYSTEM RESOURCE CHECK:")
    print("-" * 40)
    
    try:
        import psutil
        
        # Memory info
        memory = psutil.virtual_memory()
        print(f"Available Memory: {memory.available / (1024**3):.2f} GB")
        print(f"Memory Usage: {memory.percent:.1f}%")
        
        # Disk space
        disk = psutil.disk_usage('/')
        print(f"Free Disk Space: {disk.free / (1024**3):.2f} GB")
        print(f"Disk Usage: {(disk.used/disk.total)*100:.1f}%")
        
        # Check if resources are critically low
        if memory.percent > 90:
            print("⚠️  WARNING: Memory usage is critically high!")
        if (disk.used/disk.total)*100 > 95:
            print("⚠️  WARNING: Disk space is critically low!")
        
    except ImportError:
        print("psutil not available - cannot check system resources")
    except Exception as e:
        print(f"Error checking system resources: {e}")

def generate_recommendations():
    """Generate recommendations based on analysis"""
    print(f"\n💡 RECOMMENDATIONS:")
    print("-" * 40)
    
    recommendations = [
        "1. Run the application with the enhanced logging for at least 24 hours",
        "2. Monitor the log files in: %APPDATA%\\Ali AHK Qasem\\SchoolBellApp\\logs",
        "3. Check Windows Event Viewer for system-level issues",
        "4. Ensure sufficient disk space (at least 1GB free)",
        "5. Verify audio files exist and are not corrupted",
        "6. Check if antivirus software is interfering with the application",
        "7. Run the application as Administrator to rule out permission issues",
        "8. Monitor memory usage during extended operation"
    ]
    
    for rec in recommendations:
        print(f"  {rec}")
    
    print(f"\n📁 Log file locations:")
    log_dir = os.path.join(os.getenv('APPDATA', ''), 'Ali AHK Qasem', 'SchoolBellApp', 'logs')
    print(f"  Main logs: {log_dir}\\school_bell_*.log")
    print(f"  Crash logs: {log_dir}\\crashes_*.log")
    print(f"  Status file: {log_dir}\\app_status.json")

def main():
    """Main analysis function"""
    # Check for crashes
    crash_detected = analyze_app_status()
    
    # Analyze log files
    analyze_log_files()
    
    # Check system resources
    check_system_resources()
    
    # Generate recommendations
    generate_recommendations()
    
    print(f"\n" + "="*60)
    if crash_detected:
        print("🚨 CRASH OR ABNORMAL TERMINATION DETECTED!")
        print("Review the analysis above and follow the recommendations.")
    else:
        print("✅ No obvious crashes detected. Application appears stable.")
    print("="*60)

if __name__ == "__main__":
    main()