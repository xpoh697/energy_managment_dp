import json
import os
import shutil

# Paths
storage_dir = r"\\192.168.100.5\config\.storage"
config_entries_path = os.path.join(storage_dir, "core.config_entries")
old_db_path = os.path.join(storage_dir, "energy_management_01KKCHQC1H76XNA33EYXJKFB4T")
new_db_path = os.path.join(storage_dir, "energy_management_dp_01KKCHQC1H76XNA33EYXJKFB4DP")

print("Starting migration...")

# 1. Backup core.config_entries
shutil.copy2(config_entries_path, config_entries_path + ".bak")
print("Backed up core.config_entries to core.config_entries.bak")

# 2. Copy and update the database file
if os.path.exists(old_db_path):
    with open(old_db_path, "r", encoding="utf-8") as f:
        db_data = json.load(f)
    
    # Update key inside DB data
    db_data["key"] = "energy_management_dp_01KKCHQC1H76XNA33EYXJKFB4DP"
    
    with open(new_db_path, "w", encoding="utf-8") as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)
    print(f"Copied and updated database to {new_db_path}")
else:
    print(f"Error: Old database not found at {old_db_path}")

# 3. Read core.config_entries, duplicate the entry
with open(config_entries_path, "r", encoding="utf-8") as f:
    entries_data = json.load(f)

entries = entries_data.get("data", {}).get("entries", [])
old_entry = None
for entry in entries:
    if entry.get("domain") == "energy_management" and entry.get("entry_id") == "01KKCHQC1H76XNA33EYXJKFB4T":
        old_entry = entry
        break

if old_entry:
    # Check if new entry already exists to avoid duplicates
    exists = any(e.get("domain") == "energy_management_dp" and e.get("entry_id") == "01KKCHQC1H76XNA33EYXJKFB4DP" for e in entries)
    if not exists:
        new_entry = json.loads(json.dumps(old_entry)) # deep copy
        new_entry["domain"] = "energy_management_dp"
        new_entry["entry_id"] = "01KKCHQC1H76XNA33EYXJKFB4DP"
        new_entry["title"] = "Energy Management DP"
        new_entry["data"]["name"] = "Energy Management DP"
        new_entry["options"]["name"] = "Energy Management DP"
        
        # Add to the entries list
        entries.append(new_entry)
        
        with open(config_entries_path, "w", encoding="utf-8") as f:
            json.dump(entries_data, f, ensure_ascii=False, indent=2)
        print("Successfully duplicated the config entry in core.config_entries")
    else:
        print("New config entry already exists in core.config_entries")
else:
    print("Error: Old config entry not found in core.config_entries")

print("Migration completed successfully!")
