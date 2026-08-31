"""Plateforme calendar pour Lirflix : planning de diffusion des émissions suivies.

Construit uniquement à partir des champs publics 'air_day' et 'air_time' de
data/shows.json (jour et heure de diffusion habituels). Il s'agit d'un
planning théorique et récurrent, pas d'une confirmation qu'un épisode précis
sera diffusé à une date donnée : lirflix.net ne fournit pas de date de
diffusion fiable pour la majorité des émissions suivies.
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta

import homeassistant.util.dt as dt_util
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_AIR_DAY, ATTR_AIR_TIME, ATTR_SHOW_TITLE, ATTR_SLUG, ATTR_URL, DOMAIN
from .coordinator import LirflixCoordinator
from .util import parse_air_days, parse_air_time

# Le site ne publie pas la durée réelle des épisodes : on affiche un
# créneau de 30 minutes par défaut, purement indicatif.
EVENT_DURATION = timedelta(minutes=30)
# Fenêtre utilisée pour déterminer le "prochain" événement (propriété `event`).
NEXT_EVENT_WINDOW = timedelta(days=14)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Crée l'entité calendrier unique de l'entrée de configuration."""
    coordinator: LirflixCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LirflixCalendar(coordinator, entry.entry_id)])


class LirflixCalendar(CoordinatorEntity[LirflixCoordinator], CalendarEntity):
    """Planning de diffusion (jour/heure habituels) des émissions suivies."""

    _attr_icon = "mdi:calendar-clock"
    _attr_has_entity_name = True
    _attr_translation_key = "schedule"

    def __init__(self, coordinator: LirflixCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_schedule"

    def _iter_show_events(
        self, start: datetime, end: datetime
    ) -> Iterator[CalendarEvent]:
        """Génère les occurrences de toutes les émissions suivies entre start et end."""
        if not self.coordinator.data:
            return
        for show in self.coordinator.data.values():
            weekdays = parse_air_days(show.get(ATTR_AIR_DAY))
            air_time = parse_air_time(show.get(ATTR_AIR_TIME))
            if not weekdays or air_time is None:
                continue

            day = start.date()
            last_day = end.date()
            while day <= last_day:
                if day.weekday() in weekdays:
                    event_start = datetime.combine(
                        day, air_time, tzinfo=dt_util.DEFAULT_TIME_ZONE
                    )
                    event_end = event_start + EVENT_DURATION
                    if event_start < end and event_end > start:
                        yield CalendarEvent(
                            start=event_start,
                            end=event_end,
                            summary=show.get(ATTR_SHOW_TITLE, show.get(ATTR_SLUG)),
                            description=show.get(ATTR_URL),
                        )
                day += timedelta(days=1)

    @property
    def event(self) -> CalendarEvent | None:
        """Prochain épisode planifié, tous suivis confondus."""
        now = dt_util.now()
        upcoming = sorted(
            self._iter_show_events(now, now + NEXT_EVENT_WINDOW),
            key=lambda evt: evt.start,
        )
        return upcoming[0] if upcoming else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Retourne les occurrences planifiées entre start_date et end_date."""
        return sorted(
            self._iter_show_events(start_date, end_date), key=lambda evt: evt.start
        )
