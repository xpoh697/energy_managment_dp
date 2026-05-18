with open(r'\\192.168.100.5\config\custom_components\energy_management\sensor.py', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(244, 285):
    if i < len(lines):
        line = lines[i].strip()
        # Clean non-ascii characters
        clean_line = "".join([c if ord(c) < 128 else '?' for c in line])
        print(f"{i+1}: {clean_line}")
