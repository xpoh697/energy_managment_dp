import sys
sys.stdout.reconfigure(encoding='utf-8')

log_path = r"\\192.168.100.5\config\energy_management.log"
try:
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        print(f"Total lines in log: {len(lines)}")
        print("Last 30 lines:")
        for line in lines[-30:]:
            print(line.strip())
except Exception as e:
    print(f"Error reading log: {e}")
