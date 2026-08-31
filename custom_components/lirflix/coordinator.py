"""DataUpdateCoordinator pour Lirflix.

Ce coordinateur interroge uniquement le flux de métadonnées public du site
(data/shows.json : titres, numéros d'épisodes, jours/heures de diffusion).
Il n'accède jamais aux liens de lecture/téléchargement des épisodes.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict

import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
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
    STORAGE_KEY_TEMPLATE,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class _StoredData(TypedDict, total=False):
    """Forme des données persistées entre deux démarrages de Home Assistant."""

    acknowledged: dict[str, int | None]
    last_detected: dict[str, str]


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
        entry_id: str,
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
        # Numéro d'épisode "acquitté" par émission, et date/heure locale de
        # dernière détection d'un nouvel épisode : persistés sur disque, ils
        # alimentent le capteur global "Nouveaux épisodes".
        # (Le numéro d'épisode n'étant pas comparable d'une émission à
        # l'autre, c'est la date de détection - côté Home Assistant, pas une
        # date de diffusion fournie par le site - qui sert à ordonner les
        # émissions entre elles.)
        self._store: Store[_StoredData] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_TEMPLATE.format(entry_id=entry_id)
        )
        self._acknowledged_episode: dict[str, int | None] = {}
        self._last_detected_at: dict[str, str] = {}

    async def async_load_stored_state(self) -> None:
        """Charge depuis le disque l'état acquitté par la dernière session."""
        stored = await self._store.async_load() or {}
        self._acknowledged_episode = stored.get("acknowledged", {})
        self._last_detected_at = stored.get("last_detected", {})

    async def _async_save_stored_state(self) -> None:
        await self._store.async_save(
            {
                "acknowledged": self._acknowledged_episode,
                "last_detected": self._last_detected_at,
            }
        )

    async def async_mark_all_seen(self) -> None:
        """Acquitte tous les derniers épisodes connus (remet le compteur à 0)."""
        if self.data:
            for slug, show in self.data.items():
                self._acknowledged_episode[slug] = show.get(ATTR_EPISODE_NUMBER)
            await self._async_save_stored_state()
            self.async_update_listeners()

    @property
    def pending_shows(self) -> list[dict[str, Any]]:
        """Émissions dont le dernier épisode connu n'a pas encore été acquitté."""
        if not self.data:
            return []
        pending = []
        for slug, show in self.data.items():
            episode_number = show.get(ATTR_EPISODE_NUMBER)
            if episode_number is None:
                continue
            if self._acknowledged_episode.get(slug) != episode_number:
                pending.append(show)
        # Les plus récemment détectées en premier.
        pending.sort(
            key=lambda show: self._last_detected_at.get(show[ATTR_SLUG], ""),
            reverse=True,
        )
        return pending

    @property
    def latest_show(self) -> dict[str, Any] | None:
        """Émission dont un nouvel épisode a été détecté le plus récemment.

        Basé sur l'heure à laquelle Home Assistant a constaté le changement
        (le site ne fournit pas de date de diffusion exploitable pour toutes
        les émissions) ; reste vide tant qu'aucun changement n'a encore été
        détecté depuis l'ajout de l'émission.
        """
        if not self.data or not self._last_detected_at:
            return None
        slug = max(self._last_detected_at, key=self._last_detected_at.get)
        return self.data.get(slug)

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
        state_changed = False
        for slug in self._tracked_slugs:
            show_raw = raw.get(slug)
            if show_raw is None:
                _LOGGER.warning("Émission '%s' introuvable dans %s", slug, DATA_URL)
                continue

            show = _parse_show(slug, show_raw)
            result[slug] = show

            new_number = show[ATTR_EPISODE_NUMBER]
            previous_number = self._last_seen_episode.get(slug)
            is_first_check = slug not in self._last_seen_episode
            changed = (
                previous_number is not None
                and new_number is not None
                and new_number != previous_number
            )
            if changed:
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

            if new_number is not None and (changed or is_first_check):
                self._last_detected_at[slug] = datetime.now(timezone.utc).isoformat()
                state_changed = True
            self._last_seen_episode[slug] = new_number

        if state_changed:
            await self._async_save_stored_state()

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
