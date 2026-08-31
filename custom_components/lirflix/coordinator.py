"""DataUpdateCoordinator pour Lirflix.

Ce coordinateur interroge uniquement le flux de métadonnées public du site
(data/shows.json : titres, numéros d'épisodes, jours/heures de diffusion).
Il n'accède jamais aux liens de lecture/téléchargement des épisodes.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    ATTR_AIR_DAY,
    ATTR_AIR_TIME,
    ATTR_EPISODE_NUMBER,
    ATTR_EPISODE_TITLE,
    ATTR_IMAGE,
    ATTR_LAST_UPDATED,
    ATTR_SHOW_TITLE,
    ATTR_SLUG,
    ATTR_TOTAL_EPISODES,
    ATTR_URL,
    DATA_URL,
    EVENT_NEW_EPISODE,
    SHOW_PAGE_URL,
)

_LOGGER = logging.getLogger(__name__)


def _parse_show(slug: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Réduit un objet 'show' du JSON source aux seules métadonnées utiles.

    On ignore volontairement les clés 'players' et 'downloads' (liens de
    lecture/téléchargement) : seules les informations d'annonce d'épisode
    (numéro, titre, planning) sont conservées.
    """
    episodes = raw.get("episodes") or []
    last_episode = episodes[-1] if episodes else None

    episode_number = None
    episode_title = None
    if last_episode:
        episode_number = last_episode.get("number")
        parts = last_episode.get("parts") or []
        if parts:
            episode_title = " / ".join(
                p.get("title", "") for p in parts if p.get("title")
            )

    return {
        ATTR_SLUG: slug,
        ATTR_SHOW_TITLE: raw.get("title", slug),
        ATTR_EPISODE_NUMBER: episode_number,
        ATTR_EPISODE_TITLE: episode_title,
        ATTR_AIR_DAY: raw.get("air_day"),
        ATTR_AIR_TIME: raw.get("air_time"),
        ATTR_URL: SHOW_PAGE_URL.format(slug=slug),
        ATTR_IMAGE: raw.get("image"),
        ATTR_TOTAL_EPISODES: len(episodes),
    }


class LirflixCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Récupère périodiquement data/shows.json et suit les nouveaux épisodes."""

    def __init__(
        self,
        hass: HomeAssistant,
        tracked_slugs: list[str],
        scan_interval_minutes: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Lirflix",
            update_interval=timedelta(minutes=scan_interval_minutes),
        )
        self._tracked_slugs = tracked_slugs
        # Mémorise le dernier numéro d'épisode connu par émission, pour
        # détecter les nouvelles parutions d'une itération à l'autre.
        self._last_seen_episode: dict[str, int | None] = {}

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(20):
                resp = await session.get(DATA_URL)
                resp.raise_for_status()
                raw = await resp.json(content_type=None)
        except Exception as err:  # pylint: disable=broad-except
            raise UpdateFailed(f"Erreur lors de la récupération de {DATA_URL} : {err}") from err

        result: dict[str, dict[str, Any]] = {}
        for slug in self._tracked_slugs:
            show_raw = raw.get(slug)
            if show_raw is None:
                _LOGGER.warning("Émission '%s' introuvable dans %s", slug, DATA_URL)
                continue

            show = _parse_show(slug, show_raw)
            result[slug] = show

            new_number = show[ATTR_EPISODE_NUMBER]
            previous_number = self._last_seen_episode.get(slug)
            if (
                previous_number is not None
                and new_number is not None
                and new_number != previous_number
            ):
                self.hass.bus.async_fire(
                    EVENT_NEW_EPISODE,
                    {
                        ATTR_SLUG: slug,
                        ATTR_SHOW_TITLE: show[ATTR_SHOW_TITLE],
                        ATTR_EPISODE_NUMBER: new_number,
                        ATTR_EPISODE_TITLE: show[ATTR_EPISODE_TITLE],
                        ATTR_URL: show[ATTR_URL],
                    },
                )
                _LOGGER.info(
                    "Nouvel épisode détecté pour '%s' : épisode %s",
                    show[ATTR_SHOW_TITLE],
                    new_number,
                )

            self._last_seen_episode[slug] = new_number

        return result

    async def async_fetch_available_shows(self) -> dict[str, str]:
        """Retourne {slug: titre} pour toutes les émissions disponibles.

        Utilisé uniquement par le config_flow pour construire la liste de
        sélection ; ne stocke rien de plus que le titre affiché.
        """
        session = async_get_clientsession(self.hass)
        async with async_timeout.timeout(20):
            resp = await session.get(DATA_URL)
            resp.raise_for_status()
            raw = await resp.json(content_type=None)
        return {slug: show.get("title", slug) for slug, show in raw.items()}
