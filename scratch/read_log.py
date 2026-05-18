import os

paths = [
    r"\\192.168.100.5\config\energy_management.log",
    r"\\192.168.100.5\config\home-assistant.log",
]

for p in paths:
    print(f"Checking path: {p}")
    if os.path.exists(p):
        print(f"File exists: {p}")
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                print(f"Last 50 lines of {p}:")
                for line in lines[-50:]:
                    print(line.strip())
        except Exception as e:
            print(f"Error reading file: {e}")
    else:
        print(f"File does not exist: {p}")
