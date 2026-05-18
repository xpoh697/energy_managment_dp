import sys
sys.stdout.reconfigure(encoding='utf-8')

log_path = r"\\192.168.100.5\config\energy_management.log"
try:
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "DIAG: Forecast Sensors" in line or "DIAG: Gen Profile" in line:
                print(line.strip())
except Exception as e:
    print(f"Error reading log: {e}")
