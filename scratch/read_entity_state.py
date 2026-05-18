import sqlite3

db_path = r"\\192.168.100.5\config\home-assistant_v2.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT entity_id FROM states_meta ORDER BY entity_id ASC")
rows = cursor.fetchall()
print("ALL HA ENTITIES:")
for row in rows:
    if "inverter" in row[0] or "energy" in row[0] or "trader" in row[0]:
        print(f"  {row[0]}")

conn.close()
