import json
with open(r'\\192.168.100.5\config\.storage\core.config_entries', encoding='utf-8') as f:
    d = json.load(f)['data']['entries']
opts = [e['options'] for e in d if e['domain']=='energy_management'][0]
class MockManager:
    def __init__(self, opts):
        self.settings = opts
    def get_setting(self, key, default=None):
        val = self.settings.get(key)
        return val if val is not None else default
    def translate_dp_mode(self, dp_mode: str) -> str:
        if not isinstance(dp_mode, str):
            dp_mode = str(dp_mode) if dp_mode is not None else "IDLE"
        if dp_mode == "GRID_CHG":
            val = self.get_setting("dp_map_grid_chg", self.get_setting("dp_map_charge", "buy"))
        elif dp_mode == "PAID_IMP":
            val = self.get_setting("dp_map_paid_imp", self.get_setting("dp_map_charge", "buy"))
        elif dp_mode == "DIS":
            val = self.get_setting("dp_map_dis", self.get_setting("dp_map_discharge", "sale_pv_bat"))
        elif dp_mode == "PV_CHG":
            val = self.get_setting("dp_map_pv_chg", self.get_setting("dp_map_solar", "sale_pv"))
        elif dp_mode == "SOL":
            val = self.get_setting("dp_map_sol", self.get_setting("dp_map_solar", "sale_pv"))
        elif dp_mode == "SELF_CON":
            val = self.get_setting("dp_map_self_con", self.get_setting("dp_map_self_consume", "stop_sale"))
        elif dp_mode == "GRID":
            val = self.get_setting("dp_map_grid_mode", self.get_setting("dp_map_grid", "no_pv_sale_no_bat"))
        elif dp_mode == "IDLE":
            val = self.get_setting("dp_map_idle", self.get_setting("dp_map_grid", "no_pv_sale_no_bat"))
        else:
            val = "sale_pv"
        if val in [0.0, 0, "0.0", "0", "None", None, ""]:
            if dp_mode in ["GRID_CHG", "PAID_IMP"]: val = "buy"
            elif dp_mode == "DIS": val = "sale_pv_bat"
            elif dp_mode in ["PV_CHG", "SOL"]: val = "sale_pv"
            elif dp_mode == "SELF_CON": val = "stop_sale"
            elif dp_mode in ["GRID", "IDLE"]: val = "no_pv_sale_no_bat"
            else: val = "sale_pv"
        return str(val).strip()

mgr = MockManager(opts)
print("SOL:", mgr.translate_dp_mode("SOL"))
print("SELF_CON:", mgr.translate_dp_mode("SELF_CON"))
print("GRID:", mgr.translate_dp_mode("GRID"))
