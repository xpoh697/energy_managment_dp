import sys
sys.stdout.reconfigure(encoding='utf-8')

log_path = r"\\192.168.100.5\config\energy_management.log"
try:
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "Battery SOC:" in line or "DIAG: Battery" in line or "inverter_battery" in line or "Global Plan progress" in line:
                if "18:3" in line or "18:2" in line or "18:4" in line:
                    print(line.strip())
except Exception as e:
    print(f"Error reading log: {e}")
