import re, sys, json
sys.stdout.reconfigure(encoding='utf-8')

# Bump version in manifest.json
with open('custom_components/energy_management_dp/manifest.json', encoding='utf-8') as f:
    manifest = json.load(f)

old_v = manifest.get("version", "1.0.0")
parts = old_v.split(".")
parts[-1] = str(int(parts[-1]) + 1)
new_v = ".".join(parts)
manifest["version"] = new_v

with open('custom_components/energy_management_dp/manifest.json', 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

print(f"manifest.json: {old_v} -> {new_v}")

# Bump version in const.py
with open('custom_components/energy_management_dp/const.py', encoding='utf-8') as f:
    content = f.read()

cur = re.search(r'VERSION = "([^"]+)"', content)
cur_code = re.search(r'VERSION_CODE = (\d+)', content)
if cur: print(f"const.py VERSION: {cur.group(1)}")
if cur_code: print(f"const.py VERSION_CODE: {cur_code.group(1)}")

def bump_version(m):
    v = m.group(1).split(".")
    v[-1] = str(int(v[-1]) + 1)
    return f'VERSION = "{".".join(v)}"'

new = re.sub(r'VERSION = "([^"]+)"', bump_version, content)
new = re.sub(r'VERSION_CODE = (\d+)', lambda m: f'VERSION_CODE = {int(m.group(1))+1}', new)

with open('custom_components/energy_management_dp/const.py', 'w', encoding='utf-8') as f:
    f.write(new)

cur2 = re.search(r'VERSION = "([^"]+)"', new)
cur_code2 = re.search(r'VERSION_CODE = (\d+)', new)
if cur2: print(f"New VERSION: {cur2.group(1)}")
if cur_code2: print(f"New VERSION_CODE: {cur_code2.group(1)}")
