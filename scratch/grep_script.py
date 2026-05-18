with open("custom_components/energy_management/sensor.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "translate_dp_mode" in line or "def translate" in line:
            print(f"{i}: {line.strip()}")
