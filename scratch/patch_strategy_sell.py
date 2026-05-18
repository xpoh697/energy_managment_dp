import os

file_path = "G:/systemair/energy_mamagment/custom_components/energy_management/strategy_sell.py"

with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Distribution Cap Patch
old_target = """                        # v11.9.687: Restore strict price priority. 
                        # Do NOT cap the distribution here, or Jackals will steal the budget.
                        p_export = min(max_batt_p, rem_budget / duration)
                        
                        sell_commands[h] = round_f(p_export, 3) if p_export > 0.05 else 0.0
                        rem_budget -= p_export * duration"""

new_target = """                        # Cap distribution by hour's power cap from previous feedback loop
                        p_cap = h_power_caps.get(h, max_batt_p)
                        p_export = min(p_cap, rem_budget / duration)
                        
                        sell_commands[h] = round_f(p_export, 3) if p_export > 0.05 else 0.0
                        rem_budget -= p_export * duration"""

if old_target in code:
    code = code.replace(old_target, new_target)
    print("PATCH 1 SUCCESS")
else:
    # Try direct variant (with slightly different whitespace/indentation)
    print("PATCH 1 FAILED - TARGET NOT FOUND")

# 2. Epsilon Creep Patch
old_cap_update = """                            # If hour is limited by floor, cap it for the next iteration
                            if h_soc < h_floor + 0.1:
                                old_cap = h_power_caps.get(h_cmd, max_batt_p)
                                new_cap = max(0.0, p_real_dc + 0.01) # Small epsilon
                                if new_cap < old_cap:
                                    h_power_caps[h_cmd] = new_cap"""

new_cap_update = """                            # If hour is limited by floor, cap it for the next iteration
                            if h_soc < h_floor + 0.1:
                                old_cap = h_power_caps.get(h_cmd, max_batt_p)
                                new_cap = max(0.0, p_real_dc + 0.01) # Small epsilon
                                # Avoid epsilon creep / tiny phantom loads
                                if new_cap < 0.05:
                                    new_cap = 0.0
                                if new_cap < old_cap:
                                    h_power_caps[h_cmd] = new_cap"""

if old_cap_update in code:
    code = code.replace(old_cap_update, new_cap_update)
    print("PATCH 2 SUCCESS")
else:
    print("PATCH 2 FAILED")

# 3. Loop Start Patch
old_loop_start = """                for attempt in range(20): # v11.9.315: Increased iterations for complex cases
                    # --- Stage 2: Distribution Loop (TS 107) ---
                    rem_budget = float(target_budget_ac)"""

new_loop_start = """                prev_commands = {}
                for attempt in range(20): # v11.9.315: Increased iterations for complex cases
                    # --- Stage 2: Distribution Loop (TS 107) ---
                    rem_budget = float(target_budget_ac)"""

if old_loop_start in code:
    code = code.replace(old_loop_start, new_loop_start)
    print("PATCH 3 SUCCESS")
else:
    print("PATCH 3 FAILED")

# 4. Convergence Guard
old_distribution = """                        sell_commands[h] = round_f(p_export, 3) if p_export > 0.05 else 0.0
                        rem_budget -= p_export * duration"""

new_distribution = """                        sell_commands[h] = round_f(p_export, 3) if p_export > 0.05 else 0.0
                        rem_budget -= p_export * duration
                    
                    # v12.0.89: Convergence optimization - break if commands are stable
                    if attempt > 0 and sell_commands == prev_commands:
                        break
                    prev_commands = dict(sell_commands)"""

if old_distribution in code:
    code = code.replace(old_distribution, new_distribution)
    print("PATCH 4 SUCCESS")
else:
    print("PATCH 4 FAILED")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code)
print("WRITE COMPLETE")
