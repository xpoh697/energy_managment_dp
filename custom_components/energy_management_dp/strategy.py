import logging
import math
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional

from homeassistant.util import dt as dt_util

from .const import (
    CONF_BATTERY_MAX_POWER,
    CONF_BATTERY_COST,
    CONF_BATTERY_RATED_CYCLES,
    CONF_MIN_SOC_BAT,
    CONF_ONLY_SOLAR,
    CONF_PRIORITY,
    INVERTER_MODES,
    CONF_PRICE_SELL_ONLY_PV,
    CONF_SALE_PV_NO_BAT_MAX_HOUR
)
from .utils import normalize_float, round_f, get_kwh_val

_LOGGER = logging.getLogger(__name__)

class StrategyEngine:
    """
    Consolidated Strategy Engine.
    All heuristic modules are removed, leaving only the simulation and budget logic
    needed by active UI sensors.
    """

    def __init__(self, manager):
        self.manager = manager
        self._strategy_cache = {}
        self._calculating_strategy = False

    def clear_cache(self):
        """Forcefully clears the strategy calculation cache."""
        self._strategy_cache = {}

    @staticmethod
    def _format_h(h_abs):
        if h_abs is None: return "Нет данных"
        d = "Завтра " if h_abs >= 24 else ""
        return f"{d}{h_abs % 24:02d}:00"

    def get_battery_degradation_cost(self):
        """Cost of battery wear per kWh (Cycle Cost)."""
        batt_cost = self.manager.get_setting(CONF_BATTERY_COST, 0.0)
        cycles = self.manager.get_setting(CONF_BATTERY_RATED_CYCLES, 6000)
        
        _, cap, _ = self.manager.get_battery_state()
        if cap <= 1.0: cap = 10.0 # Safety default
        
        if cycles <= 0 or batt_cost <= 0: return 0.0
        return round_f(batt_cost / (cycles * cap), 4)

    def get_efficiency_coefficient(self) -> float:
        """Calculates historical inverter efficiency (Hardcoded to stable 0.98)."""
        return 0.98

    @staticmethod
    def get_cc_cv_ratio(soc):
        """Strict CC/CV ratio based on user-provided table (v6.11)."""
        if soc >= 100: return 0.0
        if soc >= 98: return 0.125
        if soc >= 95: return 0.40
        return 1.0

    def get_gen_forecast_coefficient(self, forecast_value: float, prof_gen: dict, hour_start: int, hour_end: int) -> float:
        if not forecast_value or forecast_value <= 0.1:
            return 1.0
        p = prof_gen or {}
        avg_gen_sum = sum(float(normalize_float(p.get(str(h), 0.0))) for h in range(hour_start, hour_end))
        if avg_gen_sum <= 0.1:
            return 1.0
        return float(forecast_value / avg_gen_sum)

    def _calculate_sunrise_surplus(self, natural_morning_soc, min_soc, buffer_soc, batt_cap, eff, user_soc_limit=0.0):
        """Strictly calculates surplus above the highest floor."""
        target_mark = float(max(min_soc + buffer_soc, user_soc_limit))
        extra_soc_pct = max(0.0, natural_morning_soc - target_mark)
        return float(extra_soc_pct * batt_cap / 100.0)

    def get_hourly_accuracy_coeff(self, hour):
        """Calculates specific historical accuracy for a given hour of day."""
        man = self.manager
        sh = str(hour)
        history = man.data.get("generation", {}).get(sh, [])
        if not history:
            return 1.0, 0
            
        perf_list = []
        for rec in history[-14:]:
            if not isinstance(rec, dict): continue
            if rec.get("c"): continue
            
            v = float(rec.get("v", 0.0))
            f = float(rec.get("f", 0.0))
            if f > 0.1:
                perf_list.append(max(0.2, min(v / f, 2.0)))
        
        if not perf_list:
            return 1.0, 0
        return float(sum(perf_list) / len(perf_list)), len(perf_list)

    def _get_soc_from_log(self, log: dict, key: Any, default: Optional[float]) -> Optional[float]:
        """Safely extract SOC float from simulation log."""
        if not log: return default
        val = log.get(key)
        if val is None and isinstance(key, (int, float)):
            h_abs = int(key)
            h_rel = h_abs % 24
            is_tom = h_abs >= 24
            is_dafter = h_abs >= 48
            suffix = " (Завтра)" if is_tom else (" (Через день)" if is_dafter else "")
            str_key = f"{h_rel:02d}:59{suffix}"
            val = log.get(str_key)
        if val is None and isinstance(key, str):
            if key.isdigit():
                val = log.get(int(key))
            elif ":" in key:
                try:
                    h_rel = int(key.split(":")[0])
                    is_tom = "Завтра" in key
                    is_dafter = "Через день" in key
                    h_abs = h_rel + (24 if is_tom else (48 if is_dafter else 0))
                    val = log.get(h_abs)
                except: pass
        if isinstance(val, dict):
            res = val.get("soc", val.get("soc_end", default))
        else:
            res = val if val is not None else default
        return float(res) if res is not None else default

    def resolve_consumption_profiles(self, p_type: str, eff_period: int, day_idx: int) -> Tuple[Dict[str, float], Dict[str, float], str]:
        """Unified resolver for consumption profiles with a safe fallback of 0.3 kW."""
        man = self.manager
        def get_profile_sum(p_dict):
            if not p_dict: return 0.0
            try: return sum(max(0.0, float(v)) for v in p_dict.values() if v is not None)
            except: return 0.0

        p_today = dict(man.get_predicted_profile(p_type) or {})
        p_tom = dict(man.get_average_profile(p_type, eff_period, day_idx) or {})
        
        sum_today = get_profile_sum(p_today)
        sum_tom = get_profile_sum(p_tom)
        
        if p_type == "consumption_base" and sum_today < 0.5 and sum_tom < 0.5:
            p_today = dict(man.get_predicted_profile("consumption_total") or {})
            p_tom = dict(man.get_average_profile("consumption_total", eff_period, day_idx) or {})
            sum_today = get_profile_sum(p_today)
            sum_tom = get_profile_sum(p_tom)
            if sum_today >= 0.5 or sum_tom >= 0.5:
                _LOGGER.info("Energy Management [v12.2.0]: 'consumption_base' is empty. Falling back to 'consumption_total'.")
                return p_today, p_tom, "consumption_total"

        if sum_today < 0.5 and sum_tom < 0.5:
            _LOGGER.warning(
                "Energy Management [v12.2.0] CRITICAL: Both '%s' and 'consumption_total' profiles are EMPTY or ZERO! "
                "Forcing flat fallback load of 0.3 kW for all hours to prevent battery deep-discharge blindness.",
                p_type
            )
            flat_profile = {str(h): 0.3 for h in range(24)}
            return flat_profile, flat_profile, "fallback_0.3kw"
            
        return p_today, p_tom, p_type

    def get_survival_floor(self, start_h_abs: int, end_h_abs: int, target_at_end: float = None, ignore_solar: bool = False) -> float:
        """Proper Reverse Bridging calculation."""
        man: Any = self.manager
        _, b_cap, _ = man.get_battery_state()
        b_cap = float(b_cap or 10.0)
        eff = float(self.get_efficiency_coefficient() or 0.95)
        min_soc = float(man.get_setting(CONF_MIN_SOC_BAT, 10.0))
        
        req_soc = target_at_end if target_at_end is not None else min_soc
        
        prof_gen = dict(man.get_predicted_profile("generation") or {})
        prof_cons, _, _ = self.resolve_consumption_profiles("consumption_base", 14, man.day_type)
        
        for h_abs in range(end_h_abs - 1, start_h_abs - 1, -1):
            h_rel = str(h_abs % 24)
            l_val = float(normalize_float(prof_cons.get(h_rel, 0.4)))
            g_val = float(normalize_float(prof_gen.get(h_rel, 0.0))) if not ignore_solar else 0.0
            
            net_h_kwh = (l_val - g_val) / eff
            h_soc_pct = (net_h_kwh / b_cap * 100.0) if b_cap > 0 else 0
            req_soc += h_soc_pct
            
            base_floor = target_at_end if target_at_end is not None else min_soc
            req_soc = max(base_floor, req_soc)
            
        return round_f(req_soc, 1)

    def run_soc_simulation(self, start_soc, sim_range, now, commands=None, b_min_soc=0.0, man=None, house_profile_override=None, no_battery_charge=False, no_battery_charge_until=None, pv_curtail_hours=None, ignore_blended=False, dynamic_floors=None, no_solar=False, allow_discharge=True, attempt=0, ignore_house_in_hours=None, no_solar_to_bat=False, mode_overrides=None, current_mode=None, dynamic_ceilings=None):
        """Universal SOC simulation engine."""
        if not sim_range:
            return float(start_soc), {}, 0.0
        
        _LOGGER.debug(f"[SimStart] start_soc: {start_soc} (type: {type(start_soc)})")

        man = man or self.manager
        if b_min_soc < 0.01:
            b_min_soc = float(man.get_setting(CONF_MIN_SOC_BAT, 10.0))

        _, batt_cap, _ = man.get_battery_state()
        b_cap_f = float(batt_cap)
        if b_cap_f <= 0.1:
            return float(start_soc), {}, 0.0

        eff_period = man.custom_period
        if now.month in [3, 4, 9, 10]:
            eff_period = 7 

        day_idx_today = man.day_type
        tomorrow_dt = now + timedelta(days=1)
        day_idx_tom = (tomorrow_dt).weekday()
        
        f_today = float(man.get_forecast_value(man.forecast_today_sensor) or 0.0)
        f_tom = float(man.get_forecast_value(man.forecast_tomorrow_sensor) or 0.0)
        dist_today = man.get_forecast_hourly_distribution(man.forecast_today_hourly_sensor)
        dist_tom = man.get_forecast_hourly_distribution(man.forecast_tomorrow_sensor, tomorrow_dt.strftime("%Y-%m-%d"))

        p_type = house_profile_override or "consumption_total"
        prof_cons_today, prof_cons_tom, resolved_p_type = self.resolve_consumption_profiles(p_type, eff_period, day_idx_tom)
        
        prof_gen_today = dict(man.get_average_profile("generation", eff_period, day_idx_today))
        prof_gen_tom = dict(man.get_average_profile("generation", eff_period, day_idx_tom))
        prof_losses = dict(man.get_average_profile("losses", 7))
        
        blended_coeff = 1.0
        if not ignore_blended:
            if now.hour > 0:
                blended_coeff = float(getattr(man, "last_blended_coeff", 1.0))
            else:
                blended_coeff = 1.0
                man.last_blended_coeff = 1.0
        eff_coeff = float(self.get_efficiency_coefficient() or 1.0)
        fraction_left_h1 = float(1.0 - (now.minute / 60.0))
        max_batt_p_v = man.get_setting(CONF_BATTERY_MAX_POWER, 5.0)
        max_batt_p = float(max_batt_p_v) if max_batt_p_v is not None else 5.0
        man = self.manager
        all_prices = {}
        history_log = {}
        
        price_sell_only_pv = float(man.get_setting(CONF_PRICE_SELL_ONLY_PV, 999.0))
        sale_pv_no_bat_max_hour = float(man.get_setting(CONF_SALE_PV_NO_BAT_MAX_HOUR, 13.0))

        norm_commands = {}
        if commands:
            for k, v in commands.items():
                try:
                    clean_k = str(k).replace("h", "")
                    norm_commands[int(clean_k)] = float(v)
                except: continue
        commands = norm_commands

        try:
            today_str = now.strftime("%Y-%m-%d")
            tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
            
            p_buy = dict(man.data.get("prices_buy", {}))
            for h, p in p_buy.get(today_str, {}).items(): all_prices[int(h)] = float(normalize_float(p))
            for h, p in p_buy.get(tomorrow_str, {}).items(): all_prices[int(h) + 24] = float(normalize_float(p))
            
            all_sell_prices = {}
            p_sell = dict(man.data.get("prices_sell", {}))
            for h, p in p_sell.get(today_str, {}).items(): all_sell_prices[int(h)] = float(normalize_float(p))
            for h, p in p_sell.get(tomorrow_str, {}).items(): all_sell_prices[int(h) + 24] = float(normalize_float(p))
        except Exception:
            all_sell_prices = all_prices

        simulated_soc = float(start_soc)
        overflow_kwh = 0.0
        for i, h_abs in enumerate(sim_range):
            try:
                real_h = int(h_abs % 24)
                is_tom = bool(h_abs >= 24)
                h_str = str(real_h)
            
                step_duration = float(fraction_left_h1 if i == 0 else 1.0)
                if step_duration <= 0.001: continue

                expected_gen_kw = 0.0
                expected_cons_kw = 0.0
                tom_coeff = 1.0
                
                if is_tom:
                    h_key = str(real_h)
                    tom_coeff = 1.0 
                    if dist_tom:
                        total_dist = sum(float(normalize_float(v)) for v in dist_tom.values())
                        h_acc, _ = self.get_hourly_accuracy_coeff(real_h)
                        expected_gen_kw = float(float(normalize_float(dist_tom.get(h_key, 0.0))) / total_dist * f_tom * tom_coeff * h_acc) if total_dist > 0.1 else 0.0
                    else:
                        total_hist = sum(float(normalize_float(v)) for v in prof_gen_tom.values())
                        h_acc, _ = self.get_hourly_accuracy_coeff(real_h)
                        expected_gen_kw = float(float(normalize_float(prof_gen_tom.get(h_str, 0.0))) / total_hist * f_tom * tom_coeff * h_acc) if total_hist > 0.1 else 0.0
                else:
                    if dist_today:
                        cur_h_weight = float(dist_today.get(h_str, 0.0))
                        rem_dist = (cur_h_weight * step_duration) + sum(float(dist_today.get(str(hr), 0.0)) for hr in range(now.hour + 1, 24))
                        h_acc, _ = self.get_hourly_accuracy_coeff(int(h_abs) % 24)
                        expected_gen_kw = float(cur_h_weight / rem_dist * f_today * blended_coeff * h_acc) if rem_dist > 0.1 else 0.0
                    else:
                        cur_h_hist = float(prof_gen_today.get(h_str, 0.0))
                        rem_hist = (cur_h_hist * step_duration) + sum(float(prof_gen_today.get(str(hr), 0.0)) for hr in range(now.hour + 1, 24))
                        h_acc, _ = self.get_hourly_accuracy_coeff(int(h_abs) % 24)
                        expected_gen_kw = float(cur_h_hist / rem_hist * f_today * blended_coeff * h_acc) if rem_hist > 0.1 else 0.0
            
                p_gen_check = prof_gen_tom if is_tom else prof_gen_today
                hist_h_val = float(normalize_float(p_gen_check.get(h_str, 0.0)))
                
                if hist_h_val < 0.01 and (real_h < 6 or real_h > 21):
                    expected_gen_kw = 0.0
    
                if pv_curtail_hours is not None and int(h_abs) in pv_curtail_hours:
                    expected_gen_kw = 0.0
    
                hourly_gen_map = man.get_forecast_hourly("generation")
                if hourly_gen_map and int(h_abs) in hourly_gen_map:
                    expected_gen_kw = float(hourly_gen_map[int(h_abs)])

                p_cons = prof_cons_tom if is_tom else prof_cons_today
                occ_coeff, _, _, _, _, _, _ = man.get_occupancy_coefficient()
                occ_coeff = float(occ_coeff)
                expected_cons_kw = float(normalize_float(p_cons.get(h_str, 0.0))) * occ_coeff
                
                if (real_h >= 22 or real_h <= 6) and expected_cons_kw > 3.0:
                    expected_cons_kw = 0.5
    
                if ignore_house_in_hours is not None and int(h_abs) in ignore_house_in_hours:
                    expected_cons_kw = 0.0
    
                # Blended Anchor
                if i == 0:
                    real_load = float(getattr(man, "avg_base_load_kw" if house_profile_override == "consumption_base" else "avg_load_kw", expected_cons_kw))
                    cur_batt_p = float(man.get_sensor_float(man.battery_power_sensor) or 0.0)
                    if cur_batt_p < -0.1: 
                        p_charge = abs(cur_batt_p)
                        if real_load > (p_charge * 0.8):
                             real_load = max(0.1, real_load - p_charge)
                    anchor_weight = max(0.0, min(1.0, (now.minute / 60.0)))
                    expected_cons_kw = (real_load * anchor_weight) + (expected_cons_kw * (1.0 - anchor_weight))
            
                if i == 0:
                    real_gen_kw = float(getattr(man, "avg_gen_kw", 0.0))
                    if real_gen_kw > 0.01:
                        anchor_weight = max(0.0, min(1.0, (now.minute / 60.0)))
                        expected_gen_kw = (real_gen_kw * anchor_weight) + (expected_gen_kw * (1.0 - anchor_weight))
    
                if eff_coeff < 0.999: 
                    idle_p = float(prof_losses.get(h_str, 0.05))
                    expected_cons_kw += idle_p
    
                _h_price = float(normalize_float(all_prices.get(int(h_abs), 0.1)))
                _h_sell_price = float(normalize_float(all_sell_prices.get(int(h_abs), _h_price)))
                
                if _h_price <= 0.0:
                    expected_gen_kw = 0.0
    
                _cmd_map = commands if commands else {}
                _raw_p = _cmd_map.get(int(h_abs), 0.0)
                if isinstance(_raw_p, dict):
                    cmd_p = float(_raw_p.get("power", 0.0))
                else:
                    cmd_p = float(_raw_p)

                _prev_soc_for_log = simulated_soc
    
                _h_mode_name = (mode_overrides or {}).get(int(h_abs))
                _h_dt = (now + timedelta(hours=i)).replace(minute=0, second=0, microsecond=0)
                _h_ts_key = _h_dt.strftime("%Y-%m-%d %H:00")
                _manual_m = man.hourly_manual_overrides.get(_h_ts_key)
                _manual_soc = None
                if _manual_m:
                    _h_mode_name = _manual_m.get("mode")
                    _manual_soc = _manual_m.get("soc_limit")
                    if _h_mode_name == "buy":
                        cmd_p = max_batt_p
                    elif _h_mode_name == "sale_pv_bat":
                        cmd_p = -max_batt_p
                    elif _h_mode_name in ["stop_sale", "sale_pv_no_bat"]:
                        cmd_p = 0.0

                _h_mode_str = _h_mode_name
                if h_abs == now.hour and _h_mode_str is None:
                    _h_mode_str = current_mode
                
                if _h_mode_str is None:
                    _h_mode_str = "sale_pv"
                
                if _h_mode_str == "bat_emergency" and round(simulated_soc, 1) > b_min_soc:
                    _h_mode_str = "sale_pv"
                elif round(simulated_soc, 1) <= b_min_soc and not _manual_m and _h_mode_str != "buy":
                    _h_mode_str = "bat_emergency"
                
                _h_mode_cls = INVERTER_MODES.get(_h_mode_str)
                _mode_cfg = _h_mode_cls if _h_mode_cls else INVERTER_MODES["sale_pv"]

                _expected_gen_kw_sim = 0.0 if no_solar else expected_gen_kw
                if _h_mode_cls is not None and _h_mode_cls.curtail_pv:
                    _expected_gen_kw_sim = min(_expected_gen_kw_sim, expected_cons_kw)

                sim_p_bat = 0.0
                p_for_house = min(_expected_gen_kw_sim, expected_cons_kw)
                rem_gen = _expected_gen_kw_sim - p_for_house
                rem_cons = expected_cons_kw - p_for_house
                
                if _h_mode_cls and _h_mode_cls.is_grid_bypass:
                    rem_cons = 0.0
                
                _pv_to_bat = rem_gen if (_mode_cfg.charge_from_pv and not no_solar_to_bat) else 0.0
                _solar_charge = _pv_to_bat if (_mode_cfg.charge_from_pv and not no_solar_to_bat) else 0.0
                
                if cmd_p > 0.01:
                    total_net_kw = float(cmd_p + max(0.0, _solar_charge))
                else:
                    if _mode_cfg.discharge_to_house:
                        total_net_kw = float(_solar_charge - rem_cons + cmd_p)
                    else:
                        total_net_kw = float(_solar_charge + cmd_p)
                
                if _mode_cfg.export_pv_to_grid and not _mode_cfg.charge_from_pv:
                    total_net_kw = float(total_net_kw - _solar_charge)
                    _solar_charge = 0.0
            
                sim_eff = float(max(0.85, eff_coeff))
                sim_p_sale = 0.0
                
                h_idx_int = int(h_abs)
                h_floor_trade = b_min_soc
                h_ceiling_trade = 100.0
                if dynamic_floors and h_idx_int in dynamic_floors:
                    h_floor_trade = float(dynamic_floors[h_idx_int])
                if dynamic_ceilings and h_idx_int in dynamic_ceilings:
                    h_ceiling_trade = float(dynamic_ceilings[h_idx_int])

                if _manual_soc is not None:
                    _m_soc_f = float(_manual_soc)
                    if _h_mode_name == "buy":
                        h_ceiling_trade = min(100.0, _m_soc_f)
                    else:
                        h_floor_trade = max(15.0, _m_soc_f)

                if total_net_kw > 0.001: 
                    acc_ratio = float(self.get_cc_cv_ratio(simulated_soc))
                    actual_charge_kw = float(min(total_net_kw * eff_coeff, max_batt_p * acc_ratio))
                    
                    old_soc = simulated_soc
                    if b_cap_f > 0.1:
                        simulated_soc = float(min(h_ceiling_trade, simulated_soc + (actual_charge_kw * step_duration / b_cap_f * 100.0)))
                    
                    sim_p_bat = -actual_charge_kw / max(0.1, eff_coeff)
                    
                    actual_stored_kwh_ac = 0.0
                    if b_cap_f > 0.1:
                        actual_stored_kwh_ac = ((simulated_soc - old_soc) / 100.0 * b_cap_f) / max(0.1, eff_coeff)
                    
                    overflow_h = max(0.0, (total_net_kw * step_duration) - actual_stored_kwh_ac)
                    overflow_kwh += overflow_h
                
                if total_net_kw < -0.001 and allow_discharge: 
                    actual_discharge_kw = float(min(abs(total_net_kw) / sim_eff, max_batt_p))
                    
                    old_soc = simulated_soc
                    if b_cap_f > 0.1:
                        p_sale_ac = abs(min(0.0, cmd_p))
                        p_sale_dc = min(actual_discharge_kw, p_sale_ac / sim_eff)
                        p_house_dc = max(0.0, actual_discharge_kw - p_sale_dc)
                        
                        _h_floor_for_house = h_floor_trade if _manual_m else b_min_soc
                        house_drop_req = (p_house_dc * step_duration / b_cap_f * 100.0)
                        house_drop_act = min(house_drop_req, max(0.0, simulated_soc - _h_floor_for_house))
                        simulated_soc = float(simulated_soc - house_drop_act)
                        
                        sale_drop_req = (p_sale_dc * step_duration / b_cap_f * 100.0)
                        sale_drop_act = min(sale_drop_req, max(0.0, simulated_soc - h_floor_trade))
                        simulated_soc = float(simulated_soc - sale_drop_act)
                        
                        sim_p_sale = (sale_drop_act / 100.0 * b_cap_f) / step_duration * sim_eff
                        
                        soc_delta = old_soc - simulated_soc
                        sim_p_bat = (soc_delta / 100.0 * b_cap_f) / step_duration * sim_eff
                    else:
                        simulated_soc = 0.0
                        sim_p_bat = 0.0
                else:
                    if total_net_kw >= 0.0:
                        pass
                    else:
                        sim_p_bat = 0.0
                
                if h_abs not in history_log:
                    history_log[int(h_abs)] = {
                        "soc_start": round_f(float(_prev_soc_for_log), 1),
                        "soc_end": round_f(float(simulated_soc), 1),
                        "soc": round_f(float(simulated_soc), 1),
                        "p_bat": round_f(float(sim_p_bat), 2),
                        "p_sale": round_f(float(sim_p_sale), 2),
                        "net_p_bat": round_f(float(sim_p_bat), 2),
                        "gen_kw": round_f(float(expected_gen_kw), 2),
                        "cons_kw": round_f(float(expected_cons_kw), 2),
                        "net_kw": round_f(float(total_net_kw), 2),
                        "mode": _h_mode_str
                    }
                    if abs(cmd_p) > 0.001:
                        history_log[int(h_abs)]["req_p"] = round_f(float(abs(cmd_p)), 3)
                        history_log[int(h_abs)]["floor"] = round_f(float(h_floor_trade), 1)

            except Exception as e:
                _LOGGER.error(f"Simulation error at hour {h_abs}: {e}")
                continue

        return float(simulated_soc), history_log, float(overflow_kwh)

    def get_budget_and_permissions(self, days_for_profile=14, skip_strategy_check=False):
        """Analyze current day state and return permissions for heavy loads."""
        man: Any = self.manager
        now = dt_util.now()
        cur_hour = int(now.hour)
        
        cache_key = "budget_permissions"
        cached = self._strategy_cache.get(cache_key)
        if cached and (now - cached["time"]).total_seconds() < 30:
            return cached["res"]
        
        if self._calculating_strategy and not skip_strategy_check:
            skip_strategy_check = True

        old_calc = bool(self._calculating_strategy)
        self._calculating_strategy = True
        try:
            raw_f = man.get_forecast_value(man.forecast_today_sensor)
            forecast_val = float(raw_f) if raw_f is not None else 0.0
            
            curr_month = now.month
            eff_period = days_for_profile
            if curr_month in [3, 4, 9, 10]:
                eff_period = 7
                
            day_idx = man.day_type
            p_gen = dict(man.get_average_profile("generation", eff_period, "all"))
            
            dist = man.get_forecast_hourly_distribution(man.forecast_today_hourly_sensor)
            dist_source = "historical"
            if dist:
                dist_source = "forecast_hourly"
                past_h_gen = float(sum(float(dist.get(str(h), 0.0)) for h in range(cur_hour)))
                current_h_gen = float(dist.get(str(cur_hour), 0.0)) * (now.minute / 60.0)
                hist_gen_so_far = past_h_gen + current_h_gen
                total_hist_gen = float(sum(float(dist.get(str(h), 0.0)) for h in range(24)))
                active_dist = dist
            else:
                p_gen_norm = {h: float(normalize_float(v)) for h, v in p_gen.items()}
                past_h_gen = float(sum(p_gen_norm.get(str(h), 0.0) for h in range(cur_hour)))
                current_h_gen = float(p_gen_norm.get(str(cur_hour), 0.0)) * (now.minute / 60.0)
                hist_gen_so_far = past_h_gen + current_h_gen
                total_hist_gen = float(sum(p_gen_norm.values()))
                active_dist = p_gen
            
            dist = man.get_forecast_hourly_distribution(man.forecast_today_hourly_sensor)
            rem_hours = range(cur_hour, 24)
            
            top_h = 0.0
            bot_h = 0.0
            for h in rem_hours:
                acc, _ = self.get_hourly_accuracy_coeff(h)
                weight = float(dist.get(str(h), 0.0) if dist else 0.0)
                top_h += acc * weight
                bot_h += weight
            
            if bot_h > 0.01:
                hist_coeff = float(top_h / bot_h)
            else:
                rem_accs_data = [self.get_hourly_accuracy_coeff(h) for h in rem_hours]
                rem_accs = [d[0] for d in rem_accs_data if d[0] is not None]
                hist_coeff = float(sum(rem_accs) / len(rem_accs)) if rem_accs else 1.0
            
            actual_today = float(man.data.get("temp_daily_gen", 0.0) or 0.0)
            fraction_so_far = float(hist_gen_so_far / total_hist_gen) if total_hist_gen > 0.1 else 0.0
            predicted_total = float(actual_today + forecast_val)
            
            if predicted_total > (self.manager.data.get("temp_max_forecast", 0.0) or 0.0):
                self.manager.data["temp_max_forecast"] = float(predicted_total)
            
            expected_today_total = float(man.data.get("temp_max_forecast", 0.0) or 0.1)
            
            today_coeff = 1.0
            if hist_gen_so_far > 0.5:
                today_coeff = float(max(0.2, min(actual_today / hist_gen_so_far, 2.0)))
            
            cur_mode = getattr(man, "current_inverter_mode", "")
            is_no_pv_mode = cur_mode == "no_pv_sale_no_bat"
            
            cur_price = 0.0
            try:
                cur_price = float(man.get_price("buy", now.strftime("%Y-%m-%d"), now.hour))
            except Exception: pass
            
            is_negative_price = bool(cur_price <= 0.01)
            is_stop_sale_curtail = bool(cur_mode == "stop_sale" and man.get_sensor_float(man.battery_soc_sensor, 0.0) > 90)

            if (is_no_pv_mode or is_negative_price or is_stop_sale_curtail) and today_coeff < 1.0:
                old_today = today_coeff
                today_coeff = max(today_coeff, hist_coeff, 1.0)
                if abs(today_coeff - old_today) > 0.01:
                    _LOGGER.debug(f"[Strategy] Curtailment detected (mode={cur_mode}, price={cur_price}, SOC={man.get_sensor_float(man.battery_soc_sensor, 0.0)}%). Corrected today_coeff: {old_today:.2f} -> {today_coeff:.2f}")

            external_progress = max(0.0, min(fraction_so_far, 1.0))
            blended_coeff = float((today_coeff * external_progress) + (1.0 * (1.0 - external_progress)))
            blended_coeff = float(max(0.3, min(blended_coeff, 1.5)))
            
            man.last_blended_coeff = float(blended_coeff)
            forecast_val_adjusted = float(forecast_val * blended_coeff)
                
            batt_soc, batt_cap, batt_energy_val = man.get_battery_state()
            b_soc_f = float(batt_soc)
            b_cap_f = float(batt_cap)
            b_energy_f = float(batt_energy_val)
            
            min_soc_val = man.get_setting(CONF_MIN_SOC_BAT, 10.0)
            min_soc = float(min_soc_val) if min_soc_val is not None else 10.0
            eff_coeff = float(self.get_efficiency_coefficient() or 1.0)
                        
            occ_coeff, occ_home, occ_away, occ_cur, occ_sensors, occ_avg_home, occ_avg_away = man.get_occupancy_coefficient()
            occ_coeff = float(occ_coeff)
            
            sunrise_hour = man.get_sunrise_hour() or 6
            base_rem_today = float(man.get_expected_remaining("consumption_base", eff_period, day_idx)) * occ_coeff
            base_night = float(man.get_expected_night("consumption_base", eff_period, day_idx, until_hour=sunrise_hour)) * occ_coeff
            expected_base_consumption = float(base_rem_today + base_night)
            
            soc_buffer = 0.0
            survival_threshold = min_soc
            
            sunrise_h = 8
            prof_gen = man.get_average_profile("generation", eff_period, day_idx)
            for h in range(24):
                if float(prof_gen.get(str(h), 0.0)) > 0.05:
                    sunrise_h = h
                    break
            
            sim_end_h = 24 + sunrise_h
            sim_range = list(range(cur_hour, sim_end_h))
            
            sim_res_soc, sim_log, overflow_kwh = self.run_soc_simulation(
                start_soc=b_soc_f,
                sim_range=sim_range,
                now=now,
                b_min_soc=0.0,
                house_profile_override="consumption_base"
            )

            target_key = f"{sunrise_h:0>2}:59 (Завтра)" 
            projected_morning_soc = self._get_soc_from_log(sim_log, target_key, sim_res_soc)
            
            if projected_morning_soc < survival_threshold:
                initial_budget = float((projected_morning_soc - survival_threshold) * b_cap_f / 100.0 * eff_coeff)
                _LOGGER.debug(f"[Budget] Survival gate locked: Projected morning SOC {projected_morning_soc:.1f}% < {survival_threshold}%")
            else:
                surplus_soc = float(projected_morning_soc - survival_threshold)
                initial_budget = float(surplus_soc * b_cap_f / 100.0 * eff_coeff)
                
            available_budget = initial_budget
            essential_house_consumption = expected_base_consumption 
            
            permissions = {}
            permissions_reasons = {}
            initial_power_kw = 0.0
            batt_p_flexible = 0.0
            waste_kw = 0.0
            
            p_load_s = list(getattr(man, "power_load_sensors", []))
            p_gen_s = list(getattr(man, "power_gen_sensors", []))
            
            if p_load_s and p_gen_s:
                avg_l = float(getattr(man, "avg_load_kw", 0.0))
                avg_g = float(getattr(man, "avg_gen_kw", 0.0))
                
                if avg_l > 0.01 or avg_g > 0.01 or getattr(man, "power_history", []):
                    load_kw = avg_l
                    gen_kw = avg_g
                else:
                    load_kw = float(sum((get_kwh_val(man.hass.states.get(str(s)) or None) or 0.0) for s in p_load_s))
                    gen_kw = float(sum((get_kwh_val(man.hass.states.get(str(s)) or None) or 0.0) for s in p_gen_s))
                
                initial_power_kw = float(gen_kw - load_kw)

                f_today = float(man.get_forecast_value(man.forecast_today_sensor) or 0.0)
                dist = man.get_forecast_hourly_distribution(man.forecast_today_hourly_sensor)
                h_acc, _ = self.get_hourly_accuracy_coeff(cur_hour)

                if dist:
                    cur_h_dist = float(dist.get(str(cur_hour), 0.0))
                    rem_minutes = 60 - now.minute
                    step_duration = rem_minutes / 60.0
                    rem_dist = (cur_h_dist * step_duration) + sum(float(dist.get(str(h), 0.0)) for h in range(cur_hour + 1, 24))
                    f_potential = float(f_today * (cur_h_dist / rem_dist) * h_acc) if rem_dist > 0.01 else 0.0
                else:
                    rem_minutes = 60 - now.minute
                    step_duration = rem_minutes / 60.0
                    cur_h_hist = float(p_gen.get(str(cur_hour), 0.0))
                    rem_hist = (cur_h_hist * step_duration) + sum(float(p_gen.get(str(h), 0.0)) for h in range(cur_hour + 1, 24))
                    f_potential = float(f_today * (cur_h_hist / rem_hist) * h_acc) if rem_hist > 0.1 else 0.0
                
                potential_gen = float(max(gen_kw, f_potential))
                waste_kw = float(max(0.0, potential_gen - gen_kw))

                is_stop_sale = getattr(man, "current_inverter_mode", "") == "stop_sale"
                
                if initial_power_kw < -0.1 or not is_stop_sale:
                    waste_kw = 0.0
                
                if man.battery_power_sensor:
                    st_batt = man.hass.states.get(str(man.battery_power_sensor))
                    batt_v = get_kwh_val(st_batt) or 0.0
                    batt_p_flexible = float(max(0.0, -float(batt_v)))
                
                batt_discharge_allowed = 0.0
                if initial_budget > 0.5:
                    max_batt_p_v = man.get_setting(CONF_BATTERY_MAX_POWER, 5.0)
                    max_batt_p = float(max_batt_p_v) if max_batt_p_v is not None else 5.0
                    batt_discharge_allowed = float(max_batt_p) * float(min(1.0, initial_budget / 3.0))
                
                initial_power_kw = float(initial_power_kw + waste_kw + batt_p_flexible + batt_discharge_allowed)
                
            available_power_kw = initial_power_kw
            
            current_managed_load_kw = 0.0
            for s_id in man.deduct_settings:
                if man._is_currently_pulling_power(str(s_id)):
                    p_val = float(man.last_known_power.get(str(s_id), 0.0)) / 1000.0
                    if p_val <= 0.1:
                        p_val = float(man.learned_real_power.get(str(s_id), 0.0)) / 1000.0
                    current_managed_load_kw += min(20.0, p_val)
            
            raw_house_deficit = float(load_kw - gen_kw)
            base_house_load = max(0.0, float(load_kw - current_managed_load_kw))
            available_gen_kw = float(gen_kw - base_house_load) + waste_kw
            
            cur_price_buy = None
            if not skip_strategy_check:
                cur_price_buy = man.get_price("buy", now.strftime("%Y-%m-%d"), cur_hour)

            reserved_by = []
            sorted_items = sorted(
                man.deduct_settings.items(),
                key=lambda x: x[1].get(CONF_PRIORITY, 1) if isinstance(x[1], dict) else 1
            )
            
            for s_id, s_conf in sorted_items:
                s_id_s = str(s_id)
                s_conf = dict(s_conf if isinstance(s_conf, dict) else {})
                expected_kw, rem_kwh, is_cyclic, _ = man.get_managed_load_stats(s_id_s)
                e_kw = float(expected_kw)
                
                only_solar = bool(s_conf.get(CONF_ONLY_SOLAR, False))
                req_kwh = float(s_conf.get("required_kwh", 2.5))
                consumed = float(man.daily_deduct_consumption.get(s_id_s, 0.0))
                
                is_pulling = bool(man._is_currently_pulling_power(s_id_s))
                
                if e_kw < 0.1 and is_pulling:
                    cur_w = float(man.last_known_power.get(s_id_s, 0.0))
                    if cur_w > 100.0:
                        e_kw = cur_w / 1000.0
                    else:
                        e_kw = 2.0
                        
                is_free_price = cur_price_buy is not None and float(normalize_float(cur_price_buy)) <= 0.0

                power_bottleneck = False
                gen_bottleneck = False
                p_thresh = 0.0
                if e_kw > 0.0:
                    is_strict = bool(only_solar and not is_free_price)
                    p_thresh = float(e_kw * 0.6) if is_strict else 0.0
                    p_lim = float(-(e_kw * 0.4)) if is_strict else float(-(e_kw * 0.95))
                    
                    if is_pulling:
                        if available_power_kw < p_lim: power_bottleneck = True
                    else:
                        if available_power_kw < p_thresh: power_bottleneck = True
                            
                    if only_solar and not is_free_price:
                        if available_gen_kw < float(e_kw * 0.6): 
                            gen_bottleneck = True
                        elif is_pulling and (raw_house_deficit > 0.5) and (available_gen_kw < e_kw):
                            gen_bottleneck = True
                elif initial_power_kw > 0.5 and available_power_kw < 0:
                    power_bottleneck = True

                inverter_mode = getattr(man, "current_inverter_mode", "")
                is_emergency = inverter_mode == "bat_emergency"
                is_selling_mode = inverter_mode in ("sale_pv_no_bat", "sale_pv_bat")

                price_suffix = " (Беспл. цена)" if is_free_price else ""
                if is_emergency:
                    permissions[s_id_s] = False
                    permissions_reasons[s_id_s] = "Запрет: Аварийный стоп АКБ"
                elif is_selling_mode and not is_free_price:
                    _mode_labels = {
                        "sale_pv_no_bat": "Продажа PV (без АКБ)",
                        "sale_pv_bat": "Продажа PV+АКБ",
                    }
                    mode_label = _mode_labels.get(inverter_mode, inverter_mode)
                    if power_bottleneck:
                        _extra = f" | Дефицит мощности ({available_power_kw:.2f}кВт)"
                    elif gen_bottleneck:
                        _extra = f" | Нет генерации ({available_gen_kw:.2f}кВт)"
                    elif initial_budget < -0.1:
                        _extra = f" | Бюджет {initial_budget:.2f}кВт·ч"
                    else:
                        _extra = ""
                    permissions_reasons[s_id_s] = f"Запрет: Режим '{mode_label}'{_extra}"
                elif req_kwh > 0 and consumed >= req_kwh:
                    permissions[s_id_s] = False
                    permissions_reasons[s_id_s] = f"Норма выполнена ({consumed:.2f}/{req_kwh}{price_suffix})"
                elif power_bottleneck:
                    permissions[s_id_s] = False
                    permissions_reasons[s_id_s] = f"Дефицит мощности ({available_power_kw:.2f} < {p_thresh if not is_pulling else p_lim:.2f}{price_suffix})"
                elif gen_bottleneck:
                    permissions[s_id_s] = False
                    permissions_reasons[s_id_s] = "Недостаточно генерации (Только солнце)"
                elif only_solar and initial_budget < -0.3 and not is_free_price:
                    permissions[s_id_s] = False
                    permissions_reasons[s_id_s] = f"Заряд АКБ (бюджет {initial_budget:.2f} кВт·ч)"
                elif available_budget < 0.1 and not only_solar and not is_free_price:
                    permissions[s_id_s] = False
                    permissions_reasons[s_id_s] = f"Лимит исчерпан ({available_budget:.2f} < 0.1)"
                else:
                    permissions[s_id_s] = True
                    if only_solar and not is_free_price:
                        permissions_reasons[s_id_s] = f"Ок (Профицит солнца: {available_gen_kw:.2f} кВт)"
                    else:
                        permissions_reasons[s_id_s] = f"Ок ({available_budget:.2f} кВт·ч доступно{price_suffix})"
                    if not is_cyclic or is_pulling:
                        available_budget -= float(e_kw * (1.0 - (now.minute / 60.0)))
                        available_power_kw -= e_kw
                        available_gen_kw -= e_kw
                        reserved_by.append(s_id_s)
                    
            overflow_today = float(overflow_kwh or 0.0)
            batt_surplus = self._calculate_sunrise_surplus(projected_morning_soc, min_soc, soc_buffer, b_cap_f, eff_coeff)
            
            return_res = {
                "initial_budget": float(initial_budget or 0.0),
                "battery_capacity_kwh": float(b_cap_f or 0.0),
                "projected_morning_soc": float(round_f(projected_morning_soc, 1)),
                "survival_threshold": float(round_f(survival_threshold, 1)),
                "batt_energy_val": float(b_energy_f or 0.0),
                "expected_consumption": float(essential_house_consumption or 0.0),
                "sun_overflow_kwh": round_f(overflow_today, 3),
                "battery_surplus_kwh": round_f(batt_surplus, 3),
                "potential_export_kwh": round_f(overflow_today + batt_surplus, 3),
                "permissions": permissions or {},
                "permissions_reasons": permissions_reasons or {},
                "forecast_val": float(forecast_val_adjusted or 0.0),
                "forecast_coefficient": float(blended_coeff or 1.0),
                "forecast_today_coefficient": float(today_coeff or 1.0),
                "efficiency_coefficient": float(eff_coeff or 1.0),
                "occupancy_coefficient": float(occ_coeff or 1.0),
                "degradation_cost": float(self.get_battery_degradation_cost() or 0.0),
                "solar_actual_today": float(actual_today or 0.0),
                "solar_expected_total": float(expected_today_total),
                "solar_expected_so_far": float(hist_gen_so_far),
                "solar_fraction_so_far": float(external_progress),
                "forecast_distribution": active_dist,
                "forecast_dist_source": dist_source,
                "available_power_total_kw": float(initial_power_kw or 0.0),
                "available_gen_kw": float(available_gen_kw or 0.0),
                "reserved_by": reserved_by,
                "sunrise_hour": int(sunrise_h),
                "battery_discharge_budget_kw": float(batt_discharge_allowed or 0.0)
            }
            self._strategy_cache["budget_permissions"] = {"time": now, "res": return_res}
            return return_res
        finally:
            self._calculating_strategy = old_calc

    def run_investment_simulation(self, extra_batt_kwh=0.0, pv_multiplier=1.0):
        """Simulate last 30 days with modified system specs to predict extra savings."""
        now = dt_util.now()
        
        max_idx = 0
        for h in range(24):
            max_idx = max(max_idx, len(self.manager.data.get("consumption_total", {}).get(str(h), [])))
        
        days_to_sim = min(30, max_idx - 1)
        if days_to_sim <= 0:
            return {
                "sell_simulation": {},
                "arbitrage_buyback": {},
                "analyzed_window": "Неизвестно",
                "monthly_estimate": 0.0
            }

        man: Any = self.manager
        eff = float(self.get_efficiency_coefficient())
        
        b_soc, b_cap, _ = man.get_battery_state()
        sim_batt_cap = float(b_cap + extra_batt_kwh)
        max_batt_p = float(man.get_setting(CONF_BATTERY_MAX_POWER, 5.0))
        
        total_extra_saved = 0.0
        actual_baseline_savings = 0.0
        days_with_data = 0
        
        for d_back in range(1, days_to_sim + 1):
            sim_soc = 50.0 
            day_has_data = False
            day_sim_saved = 0.0
            
            for h_idx in range(24):
                c_h_rec = man.data.get("consumption_total", {}).get(str(h_idx), [])
                g_h_rec = man.data.get("generation", {}).get(str(h_idx), [])
                
                date_str = (now - timedelta(days=d_back)).strftime("%Y-%m-%d")
                p_buy = float(man.get_price("buy", date_str, h_idx) or 0.0)
                p_sell = float(man.get_price("sell", date_str, h_idx) or 0.0)
                
                if p_buy <= 0:
                    continue
                
                if d_back > len(c_h_rec) or d_back > len(g_h_rec):
                    continue
                
                try:
                    c_h = float(normalize_float(c_h_rec[-d_back].get("v") if isinstance(c_h_rec[-d_back], dict) else c_h_rec[-d_back]))
                    g_h = float(normalize_float(g_h_rec[-d_back].get("v") if isinstance(g_h_rec[-d_back], dict) else g_h_rec[-d_back])) * pv_multiplier
                except (IndexError, AttributeError):
                    continue
                
                net = float(g_h - c_h)
                sim_cost = 0.0
                charge_kw = 0.0
                
                if net > 0:
                    charge_kw = float(min(net * eff, max_batt_p))
                    if sim_batt_cap > 0.001:
                        sim_soc = float(min(100.0, sim_soc + (charge_kw / sim_batt_cap * 100.0)))
                else:
                    needed = float(abs(net))
                    from_batt = float(min(needed, sim_soc * sim_batt_cap / 100.0) if sim_batt_cap > 0.001 else 0.0)
                    from_batt_ac = float(from_batt * eff)
                    
                    if sim_batt_cap > 0.001:
                        sim_soc = float(max(0.0, sim_soc - (from_batt / sim_batt_cap * 100.0)))
                    
                    sim_cost = float(max(0.0, needed - from_batt_ac) * p_buy)
                
                excess = float(max(0.0, net - (charge_kw / eff if net > 0 else 0.0)))
                sell_profit = float(excess * p_sell)
                
                day_sim_saved += float((c_h * p_buy) - sim_cost + sell_profit)
                day_has_data = True

            if day_has_data:
                total_extra_saved += day_sim_saved
                days_with_data += 1
                
                day_baseline_saved = 0.0
                sim_soc_base = 50.0
                for h_idx_b in range(24):
                    try:
                        c_h_b = float(normalize_float(c_h_rec[-d_back].get("v") if isinstance(c_h_rec[-d_back], dict) else c_h_rec[-d_back]))
                        g_h_b = float(normalize_float(g_h_rec[-d_back].get("v") if isinstance(g_h_rec[-d_back], dict) else g_h_rec[-d_back])) * pv_multiplier
                        
                        net_b = g_h_b - c_h_b
                        cost_b = 0.0
                        if net_b > 0:
                            ch_b = min(net_b * eff, max_batt_p)
                            if b_cap > 0.1: sim_soc_base = min(100.0, sim_soc_base + (ch_b / b_cap * 100.0))
                            cost_b = -max(0.0, net_b - (ch_b / eff)) * p_sell
                        else:
                            nd_b = abs(net_b)
                            fb_b = min(nd_b, sim_soc_base * b_cap / 100.0) if b_cap > 0.1 else 0.0
                            if b_cap > 0.1: sim_soc_base = max(0.0, sim_soc_base - (fb_b / b_cap * 100.0))
                            cost_b = max(0.0, nd_b - (fb_b * eff)) * p_buy
                        day_baseline_saved += (c_h_b * p_buy) - cost_b
                    except: continue
                actual_baseline_savings += day_baseline_saved

        improvement = max(0.0, total_extra_saved - actual_baseline_savings)
        return {
            "days_simulated": days_with_data,
            "extra_savings": round_f(improvement, 2),
            "monthly_estimate": round_f(improvement * (30 / days_with_data), 2) if days_with_data > 0 else 0.0
        }
