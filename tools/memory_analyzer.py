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
Memory Analysis Script for Jaras Application

This script analyzes memory usage patterns from the log files.
"""

import matplotlib.pyplot as plt
import pandas as pd
import os
import re
from datetime import datetime

def analyze_memory_log():
    """Analyze the continuous memory log"""
    if not os.path.exists('memory_log.txt'):
        print("memory_log.txt not found. Run the application first with memory_profile_runner.py")
        return
    
    try:
        # Read the memory log
        df = pd.read_csv('memory_log.txt')
        
        print("\n=== Memory Usage Statistics ===")
        print(f"Peak memory usage: {df['Memory(MB)'].max():.2f} MB")
        print(f"Average memory usage: {df['Memory(MB)'].mean():.2f} MB")
        print(f"Starting memory usage: {df['Memory(MB)'].iloc[0]:.2f} MB")
        print(f"Final memory usage: {df['Memory(MB)'].iloc[-1]:.2f} MB")
        print(f"Memory growth: {df['Memory(MB)'].iloc[-1] - df['Memory(MB)'].iloc[0]:.2f} MB")
        
        # Find memory spikes
        memory_diff = df['Memory(MB)'].diff()
        spikes = memory_diff[memory_diff > 10]  # Spikes > 10 MB
        
        if not spikes.empty:
            print(f"\n=== Memory Spikes (>10MB increase) ===")
            for idx in spikes.index:
                time_point = df.loc[idx, 'Time(s)']
                spike_size = spikes.loc[idx]
                print(f"Time: {time_point:.1f}s, Spike: +{spike_size:.2f} MB")
        
        # Plot memory usage over time
        plt.figure(figsize=(12, 6))
        plt.plot(df['Time(s)'], df['Memory(MB)'], label='Memory Usage', linewidth=2)
        plt.xlabel('Time (seconds)')
        plt.ylabel('Memory Usage (MB)')
        plt.title('Memory Usage Over Time - Jaras Application')
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig('memory_usage_plot.png', dpi=300, bbox_inches='tight')
        print(f"\nMemory usage plot saved as 'memory_usage_plot.png'")
        
        # Show the plot
        plt.show()
        
    except Exception as e:
        print(f"Error analyzing memory log: {e}")

def analyze_application_logs():
    """Analyze memory usage from application logs"""
    try:
        # Look for log files
        log_files = []
        appdata_dir = os.path.join(os.environ.get('APPDATA', ''), 'Ali AHK Qasem', 'SchoolBellApp', 'logs')
        
        if os.path.exists(appdata_dir):
            for file in os.listdir(appdata_dir):
                if file.startswith('school_bell_') and file.endswith('.log'):
                    log_files.append(os.path.join(appdata_dir, file))
        
        if not log_files:
            print("No application log files found.")
            return
        
        # Use the most recent log file
        latest_log = max(log_files, key=os.path.getmtime)
        print(f"\nAnalyzing log file: {latest_log}")
        
        memory_entries = []
        with open(latest_log, 'r', encoding='utf-8') as f:
            for line in f:
                # Look for memory usage entries
                if 'Memory usage' in line:
                    # Parse memory usage: "Memory usage function_name: XX.XX MB"
                    match = re.search(r'Memory usage (.+?): ([\d.]+) MB', line)
                    if match:
                        function_name = match.group(1)
                        memory_mb = float(match.group(2))
                        memory_entries.append((function_name, memory_mb))
                
                # Look for memory changes
                elif 'Memory change' in line:
                    # Parse memory change: "Memory change in function_name: +/-XX.XX MB"
                    match = re.search(r'Memory change in (.+?): ([+-]?[\d.]+) MB', line)
                    if match:
                        function_name = match.group(1)
                        change_mb = float(match.group(2))
                        print(f"Memory change in {function_name}: {change_mb:+.2f} MB")
        
        if memory_entries:
            print(f"\n=== Function Memory Usage ===")
            # Group by function name and show statistics
            from collections import defaultdict
            function_memory = defaultdict(list)
            
            for func_name, memory in memory_entries:
                function_memory[func_name].append(memory)
            
            for func_name, memories in function_memory.items():
                avg_memory = sum(memories) / len(memories)
                max_memory = max(memories)
                min_memory = min(memories)
                print(f"{func_name}:")
                print(f"  Average: {avg_memory:.2f} MB")
                print(f"  Peak: {max_memory:.2f} MB")
                print(f"  Minimum: {min_memory:.2f} MB")
                print(f"  Calls: {len(memories)}")
                print()
        
    except Exception as e:
        print(f"Error analyzing application logs: {e}")

def main():
    """Main analysis function"""
    print("=== Jaras Application Memory Analysis ===")
    
    analyze_memory_log()
    analyze_application_logs()
    
    print("\n=== Recommendations ===")
    print("1. Look for memory spikes in the plot - these indicate potential memory leaks")
    print("2. Check if memory usage grows consistently over time")
    print("3. Identify functions with high memory usage or significant memory changes")
    print("4. Run the application for longer periods to identify gradual memory leaks")

if __name__ == "__main__":
    try:
        import matplotlib.pyplot as plt
        import pandas as pd
        main()
    except ImportError as e:
        print(f"Missing required packages: {e}")
        print("Install with: pip install matplotlib pandas")