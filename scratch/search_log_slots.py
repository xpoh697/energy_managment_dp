import sys
sys.stdout.reconfigure(encoding='utf-8')

log_path = r"\\192.168.100.5\config\energy_management.log"
try:
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "Global Plan updated" in line or "DIAG: get_mode_at" in line or "DIAG: Hour 30 blocked" in line or "DIAG: Hour 31 blocked" in line or "DIAG: Hour 32 blocked" in line or "DIAG: Hour 33 blocked" in line:
                if "18:3" in line or "18:2" in line or "18:4" in line:
                    print(line.strip())
except Exception as e:
    print(f"Error reading log: {e}")
