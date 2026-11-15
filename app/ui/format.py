"""Formats d'affichage à la française (copie autonome : le frontend ne dépend pas du package backend)."""
from __future__ import annotations

import math


def _ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def fmt_int(x) -> str:
    return f"{x:,.0f}".replace(",", "\u202f") if _ok(x) else "n.d."


def fmt_num(x, digits: int = 1) -> str:
    return f"{x:,.{digits}f}".replace(",", "\u202f").replace(".", ",") if _ok(x) else "n.d."


def fmt_pct(x, digits: int = 1) -> str:
    """x est déjà en pourcentage (7.3 -> « 7,3 % »)."""
    return f"{fmt_num(x, digits)} %" if _ok(x) else "n.d."


def fmt_ratio_pct(x, digits: int = 1) -> str:
    """x est une proportion (0.073 -> « 7,3 % »)."""
    return fmt_pct(x * 100, digits) if _ok(x) else "n.d."


def fmt_days(x, digits: int = 1) -> str:
    return f"{fmt_num(x, digits)} j" if _ok(x) else "n.d."


def fmt_brl(x, digits: int = 0) -> str:
    return f"R$ {fmt_num(x, digits)}" if _ok(x) else "n.d."


def signed(x, digits: int = 1, unit: str = "") -> str:
    if not _ok(x):
        return "n.d."
    sign = "+" if x > 0 else ("−" if x < 0 else "")
    return f"{sign}{fmt_num(abs(x), digits)}{unit}"
