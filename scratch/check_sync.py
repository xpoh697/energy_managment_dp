import os
import hashlib

def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

ws_dir = r'g:\systemair\energy_mamagment\custom_components\energy_management'
ha_dir = r'\\192.168.100.5\config\custom_components\energy_management'

if os.path.exists(ha_dir):
    print("Comparing files between workspace and remote:")
    for f in os.listdir(ws_dir):
        if f.endswith('.py'):
            ws_path = os.path.join(ws_dir, f)
            ha_path = os.path.join(ha_dir, f)
            if os.path.exists(ha_path):
                ws_h = file_hash(ws_path)
                ha_h = file_hash(ha_path)
                status = "MATCH" if ws_h == ha_h else "MISMATCH !!!"
                print(f"  {f:<25} | WS: {ws_h[:8]} | HA: {ha_h[:8]} | {status}")
            else:
                print(f"  {f:<25} | Only in workspace")
else:
    print("Remote directory not accessible")
