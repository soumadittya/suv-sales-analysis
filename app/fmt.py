"""How numbers and words are written on the pages.

The rules come from the design system's README: prices in lakh with two
decimals, full rupees with Indian digit grouping in the on-road breakdown,
percentages cut toward zero, and "Not listed" for anything CarDekho doesn't give.
"""

from __future__ import annotations

import math
import re
from datetime import date

NOT_LISTED = "Not listed"

BADGE_CLASS = {
    "Good value": "good",
    "Fair": "fair",
    "Overpriced": "over",
    "Not enough data": "unknown",
}


def is_missing(value) -> bool:
    """True for None, NaN and empty text."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return isinstance(value, str) and value.strip() == ""


def lakh(rupees) -> str:
    """1534000 -> '₹15.34 lakh'."""
    if is_missing(rupees):
        return NOT_LISTED
    return f"₹{rupees / 1e5:.2f} lakh"


def lakh_amount(rupees) -> str:
    """A difference in lakh without the sign: 237300 -> '₹2.37 lakh'."""
    return lakh(abs(rupees))


def rupees(value) -> str:
    """1669184 -> '₹16,69,184' (Indian grouping: last three digits, then pairs)."""
    if is_missing(value):
        return NOT_LISTED
    digits = str(int(round(value)))
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return "₹" + ",".join(groups + [tail]) if groups else "₹" + tail


def difference_text(difference_pct) -> str:
    """How far a price is from its fair price, in whole percent cut toward zero.

    0.183 -> '18% above', -0.1115 -> '11% below', 0.009 -> 'at fair price'.
    Cutting toward zero keeps the number from contradicting the badge near the
    15% line (a Fair car at 14.8% above reads '14% above', not '15% above').
    """
    if is_missing(difference_pct):
        return ""
    whole = int(abs(difference_pct) * 100)
    if whole < 1:
        return "at fair price"
    return f"{whole}% {'above' if difference_pct > 0 else 'below'}"


def number(value, unit: str = "", decimals: int = 2) -> str:
    """142.0 -> '142', 10.25 -> '10.25', with an optional unit."""
    if is_missing(value):
        return NOT_LISTED
    text = f"{value:,.{decimals}f}".rstrip("0").rstrip(".")
    return f"{text} {unit}".strip()


def whole(value, unit: str = "") -> str:
    """128.73 -> '129' (for bhp, where decimals mean nothing to a buyer)."""
    if is_missing(value):
        return NOT_LISTED
    return f"{round(value):,} {unit}".strip()


def yes_no(value) -> str:
    """The 1 / 0 / empty has_ columns."""
    if is_missing(value):
        return NOT_LISTED
    return "Yes" if float(value) >= 1 else "No"


def long_date(iso: str) -> str:
    """'2026-11-20' -> '20 Nov 2026'."""
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b %Y')}"


GEARBOX_LABEL = {
    "Manual": "Manual",
    "Automatic, type not listed": "Automatic",
    "Torque-converter AT": "Torque-converter automatic",
    "DCT": "DCT automatic",
    "CVT": "CVT automatic",
    "AMT": "AMT automatic",
    "Hybrid": "Hybrid automatic",
    "Single-speed (EV)": "Automatic",
}


def fuel_label(fuel: str, hybrid_type) -> str:
    """'Petrol' plus the hybrid kind when there is one."""
    if is_missing(hybrid_type):
        return fuel
    if hybrid_type == "Plug-in":
        return f"{fuel} plug-in hybrid"
    return f"{fuel} {str(hybrid_type).lower()} hybrid"


def meta_line(row) -> str:
    """'Petrol · DCT automatic · 118 bhp' for lists of variants."""
    parts = [fuel_label(row["fuel_type"], row.get("hybrid_type"))]
    parts.append(GEARBOX_LABEL.get(row["gearbox_type"], row["gearbox_type"]))
    if not is_missing(row.get("power_bhp")):
        parts.append(whole(row["power_bhp"], "bhp"))
    return " · ".join(parts)


def crash_rating(row) -> str:
    """Bharat NCAP first, then Global NCAP."""
    for column, body in (("bharat_ncap_stars", "Bharat NCAP"), ("global_ncap_stars", "Global NCAP")):
        stars = row.get(column)
        if not is_missing(stars):
            n = int(stars)
            return f"{n} star{'s' if n != 1 else ''} ({body})"
    return NOT_LISTED


SUNROOF_LABEL = {"None": "No", "Single": "Single", "Panoramic": "Panoramic", "Yes, type not listed": "Yes"}


def sunroof(value) -> str:
    if is_missing(value):
        return NOT_LISTED
    return SUNROOF_LABEL.get(value, value)


_STANDS_FOR = re.compile(r"\s*\(stands for [^)]*\)")


def clean_feature(text: str) -> str:
    """'front fog lamps (stands for the fog-lamp group)' -> 'front fog lamps'."""
    text = _STANDS_FOR.sub("", text).strip()
    return "ADAS" if text == "ADAS package" else text


def split_list(text) -> list[str]:
    """'a; b; c' -> ['a', 'b', 'c']."""
    if is_missing(text):
        return []
    return [clean_feature(part) for part in str(text).split(";") if part.strip()]


def short_list(items: list[str], keep: int = 3) -> str:
    """['a', 'b', 'c', 'd', 'e'] -> 'a, b, c and 2 more'."""
    if not items:
        return ""
    if len(items) <= keep + 1:
        text = ", ".join(items[:-1]) + (" and " if len(items) > 1 else "") + items[-1]
    else:
        text = ", ".join(items[:keep]) + f" and {len(items) - keep} more"
    return text[0].upper() + text[1:]
