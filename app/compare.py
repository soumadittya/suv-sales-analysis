"""The rows of the Compare table: what to show, grouped, as plain text."""

from __future__ import annotations

import pandas as pd

from . import fmt


def _row(group: str, label: str, values: list[str]) -> dict:
    return {"group": group, "label": label, "values": values, "kind": "text"}


def compare_rows(chosen: pd.DataFrame, only_differences: bool = False) -> list[dict]:
    """One dict per table row. `kind` is 'text' or 'verdict' (drawn as badges)."""
    v = [r for _, r in chosen.iterrows()]
    any_ev = any(r["fuel_type"] == "Electric" for r in v)
    any_ice = any(r["fuel_type"] != "Electric" for r in v)

    rows = [
        _row("Price", "Ex-showroom", [fmt.lakh(r["ex_showroom_price"]) for r in v]),
        _row("Price", f"On-road, {v[0]['on_road_city']}", [fmt.lakh(r["on_road_price"]) for r in v]),
        {"group": "Price", "label": "Verdict", "kind": "verdict",
         "values": [(r["badge"], fmt.difference_text(r["difference_pct"])) for r in v]},
        _row("Engine", "Fuel", [fmt.fuel_label(r["fuel_type"], r["hybrid_type"]) for r in v]),
        _row("Engine", "Gearbox", [fmt.GEARBOX_LABEL.get(r["gearbox_type"], r["gearbox_type"]) for r in v]),
        _row("Engine", "Power", [fmt.whole(r["power_bhp"], "bhp") for r in v]),
        _row("Engine", "Torque", [fmt.whole(r["torque_nm"], "Nm") for r in v]),
    ]
    if any_ice:
        rows += [
            _row("Engine", "Engine size", [fmt.whole(r["engine_cc"], "cc") if r["fuel_type"] != "Electric" else "Electric" for r in v]),
            _row("Engine", "Mileage (claimed)", [fmt.number(r["mileage_kmpl"], "km/l") if r["fuel_type"] != "Electric" else "Electric" for r in v]),
        ]
    if any_ev:
        rows += [
            _row("Engine", "Battery", [fmt.number(r["battery_kwh"], "kWh") if r["fuel_type"] == "Electric" else "No battery" for r in v]),
            _row("Engine", "Range (claimed)", [fmt.whole(r["range_km"], "km") if r["fuel_type"] == "Electric" else "Not electric" for r in v]),
        ]
    rows += [
        _row("Size", "Length", [fmt.whole(r["length_mm"], "mm") for r in v]),
        _row("Size", "Seats", [fmt.whole(r["seats"]) for r in v]),
        _row("Size", "Boot", [fmt.whole(r["boot_litres"], "litres") for r in v]),
        _row("Size", "Ground clearance", [fmt.whole(r["ground_clearance_mm"], "mm") for r in v]),
        _row("Safety", "Airbags", [fmt.whole(r["airbags"]) for r in v]),
        _row("Safety", "Crash rating", [fmt.crash_rating(r) for r in v]),
        _row("Safety", "ADAS", [fmt.yes_no(r["has_adas"]) for r in v]),
        _row("Safety", "360° camera", [fmt.yes_no(r["has_360_view_camera"]) for r in v]),
        _row("Features", "Touchscreen", [fmt.number(r["touchscreen_in"], "inch") if r["touchscreen_in"] != 0 else "No" for r in v]),
        _row("Features", "Speakers", [fmt.whole(r["speakers"]) for r in v]),
        _row("Features", "Sunroof", [fmt.sunroof(r["sunroof"]) for r in v]),
        _row("Features", "Seats", [r["upholstery"] if not fmt.is_missing(r["upholstery"]) else fmt.NOT_LISTED for r in v]),
        _row("Features", "Ventilated seats", [fmt.yes_no(r["has_ventilated_seats"]) for r in v]),
        _row("Features", "Cruise control", [fmt.yes_no(r["has_cruise_control"]) for r in v]),
        _row("Features", "Wireless phone charging", [fmt.yes_no(r["has_wireless_phone_charging"]) for r in v]),
        _row("Features", "Automatic climate control", [fmt.yes_no(r["has_automatic_climate_control"]) for r in v]),
        _row("Features", "Rear AC vents", [fmt.yes_no(r["has_rear_ac_vents"]) for r in v]),
    ]
    if only_differences and len(v) > 1:
        rows = [r for r in rows if len({str(x) for x in r["values"]}) > 1]
    return rows
