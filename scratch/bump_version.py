# Bump version to v12.0.89 in const.py
const_path = "G:/systemair/energy_mamagment/custom_components/energy_management/const.py"
with open(const_path, "r", encoding="utf-8") as f:
    const_code = f.read()

const_code = const_code.replace('VERSION = "v12.0.88"', 'VERSION = "v12.0.89"')
const_code = const_code.replace('VERSION_CODE = 1200088', 'VERSION_CODE = 1200089')

with open(const_path, "w", encoding="utf-8") as f:
    f.write(const_code)
print("CONST.PY VERSION BUMPED")

# Bump version to v12.0.89 in manifest.json
manifest_path = "G:/systemair/energy_mamagment/custom_components/energy_management/manifest.json"
with open(manifest_path, "r", encoding="utf-8") as f:
    manifest_code = f.read()

manifest_code = manifest_code.replace('"version": "v12.0.88"', '"version": "v12.0.89"')

with open(manifest_path, "w", encoding="utf-8") as f:
    f.write(manifest_code)
print("MANIFEST.JSON VERSION BUMPED")
