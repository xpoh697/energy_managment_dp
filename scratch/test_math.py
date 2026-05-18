import json
import math

min_soc = 13.0
soc_buffer = 5.0
user_limit = 15.0

t_morning = max(user_limit, min_soc + soc_buffer)

print(f"t_morning = {t_morning}")

# Let's say house_until_sunrise_pct is 19.2
# Let's mock get_survival_floor
req_soc = t_morning
for i in range(12):
    req_soc += (19.2 / 12)
    
print(f"req_soc = {req_soc}")
