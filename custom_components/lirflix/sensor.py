"""Plateforme sensor pour Lirflix : un capteur par émission suivie."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_AIR_DAY,
    ATTR_AIR_TIME,
    ATTR_EPISODE_NUMBER,
    ATTR_EPISODE_TITLE,
    ATTR_IMAGE,
    ATTR_LAST_UPDATED,
    ATTR_LATEST_SHOW_TITLE,
    ATTR_PENDING_SHOWS,
    ATTR_SHOW_TITLE,
    ATTR_TOTAL_EPISODES,
    ATTR_URL,
    CONF_SHOWS,
    DOMAIN,
)
from .coordinator import LirflixCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Crée les entités capteur pour chaque émission de l'entrée de config."""
    coordinator: LirflixCoordinator = hass.data[DOMAIN][entry.entry_id]
    tracked_slugs: list[str] = entry.data.get(CONF_SHOWS, [])

    entities: list[SensorEntity] = [
        LirflixEpisodeSensor(coordinator, entry.entry_id, slug) for slug in tracked_slugs
    ]
    if len(tracked_slugs) > 1:
        # Le capteur global n'a d'intérêt que si plusieurs émissions sont suivies.
        entities.append(LirflixNewEpisodesSensor(coordinator, entry.entry_id))
    async_add_entities(entities)


class LirflixEpisodeSensor(CoordinatorEntity[LirflixCoordinator], SensorEntity):
    """Capteur exposant le dernier épisode publié pour une émission."""

    _attr_icon = "mdi:television-classic"
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: LirflixCoordinator, entry_id: str, slug: str
    ) -> None:
        super().__init__(coordinator)
        self._slug = slug
        self._attr_unique_id = f"{entry_id}_{slug}"
        self._attr_translation_key = "latest_episode"

    @property
    def _show(self) -> dict[str, Any] | None:
        return self.coordinator.data.get(self._slug) if self.coordinator.data else None

    @property
    def name(self) -> str:
        show = self._show
        return show[ATTR_SHOW_TITLE] if show else self._slug

    @property
    def native_value(self) -> int | None:
        show = self._show
        return show.get("episode_number") if show else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        return "épisode"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        show = self._show
        if not show:
            return {}
        return {
            ATTR_SHOW_TITLE: show.get(ATTR_SHOW_TITLE),
            ATTR_EPISODE_TITLE: show.get(ATTR_EPISODE_TITLE),
            ATTR_AIR_DAY: show.get(ATTR_AIR_DAY),
            ATTR_AIR_TIME: show.get(ATTR_AIR_TIME),
            ATTR_TOTAL_EPISODES: show.get(ATTR_TOTAL_EPISODES),
            ATTR_URL: show.get(ATTR_URL),
            ATTR_LAST_UPDATED: datetime.now(timezone.utc).isoformat(),
        }

    @property
    def entity_picture(self) -> str | None:
        show = self._show
        if show and show.get(ATTR_IMAGE):
            return f"https://lirflix.net/{show[ATTR_IMAGE]}"
        return None


class LirflixNewEpisodesSensor(CoordinatorEntity[LirflixCoordinator], SensorEntity):
    """Capteur global : nombre d'épisodes pas encore acquittés, tous suivis confondus.

    Le compteur se remet à zéro via le service `lirflix.mark_all_seen`.
    """

    _attr_icon = "mdi:bell-badge-outline"
    _attr_has_entity_name = True
    _attr_translation_key = "new_episodes"

    def __init__(self, coordinator: LirflixCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_new_episodes"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.pending_shows)

    @property
    def native_unit_of_measurement(self) -> str:
        return "épisodes"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        pending = self.coordinator.pending_shows
        latest = self.coordinator.latest_show
        return {
            ATTR_PENDING_SHOWS: [
                {
                    ATTR_SHOW_TITLE: show.get(ATTR_SHOW_TITLE),
                    ATTR_EPISODE_NUMBER: show.get(ATTR_EPISODE_NUMBER),
                    ATTR_EPISODE_TITLE: show.get(ATTR_EPISODE_TITLE),
                    ATTR_URL: show.get(ATTR_URL),
                }
                for show in pending
            ],
            ATTR_LATEST_SHOW_TITLE: latest.get(ATTR_SHOW_TITLE) if latest else None,
            ATTR_LAST_UPDATED: datetime.now(timezone.utc).isoformat(),
        }

    @property
    def entity_picture(self) -> str | None:
        latest = self.coordinator.latest_show
        if latest and latest.get(ATTR_IMAGE):
            return f"https://lirflix.net/{latest[ATTR_IMAGE]}"
        return None
