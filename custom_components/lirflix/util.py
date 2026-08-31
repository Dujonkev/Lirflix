"""Fonctions utilitaires partagées par l'intégration Lirflix."""
from __future__ import annotations

from datetime import time

from .const import WEEKDAY_ALIASES, WEEKDAYS_KEYWORD


def parse_air_days(air_day: str | None) -> set[int]:
    """Convertit le champ 'air_day' de shows.json en jours de semaine (0=lundi).

    Gère les formats rencontrés dans data/shows.json : un seul jour en
    français ("mercredi"), une liste séparée par des virgules
    ("lundi, mardi, mercredi"), le mot-clé anglais "weekdays" (lundi à
    vendredi), ou une valeur absente/non reconnue (ensemble vide).
    """
    if not air_day or not isinstance(air_day, str):
        return set()

    normalized = air_day.strip().lower()
    if not normalized or normalized == "null":
        return set()

    if normalized == WEEKDAYS_KEYWORD:
        return {0, 1, 2, 3, 4}

    days: set[int] = set()
    for part in normalized.split(","):
        weekday = WEEKDAY_ALIASES.get(part.strip())
        if weekday is not None:
            days.add(weekday)
    return days


def parse_air_time(air_time: str | None) -> time | None:
    """Convertit le champ 'air_time' ("HH:MM") en objet time, sinon None."""
    if not air_time or not isinstance(air_time, str):
        return None
    normalized = air_time.strip().lower()
    if not normalized or normalized == "null":
        return None
    try:
        hours_str, minutes_str = normalized.split(":", 1)
        return time(hour=int(hours_str), minute=int(minutes_str))
    except (ValueError, TypeError):
        return None
