"""Intégration Lirflix - notifications de nouveaux épisodes.

Cette intégration interroge périodiquement le flux public de métadonnées
du site (liste des émissions, numéro du dernier épisode publié, jour et
heure de diffusion) et crée un capteur par émission suivie. Un événement
`lirflix_new_episode` est déclenché dès qu'un nouvel épisode est détecté,
ce qui permet de construire des automatisations (notification mobile,
annonce vocale, etc.).

Volontairement, cette intégration n'expose ni ne suit les liens de lecture
ou de téléchargement des épisodes : seules les métadonnées d'annonce sont
utilisées.
"""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SHOWS,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    SERVICE_MARK_ALL_SEEN,
)
from .coordinator import LirflixCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]

_MARK_ALL_SEEN_SCHEMA = vol.Schema(
    {vol.Optional("config_entry_id"): cv.string}
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialise une entrée de configuration Lirflix."""
    tracked_slugs: list[str] = entry.data.get(CONF_SHOWS, [])
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL_MINUTES,
        entry.data.get(CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES),
    )

    coordinator = LirflixCoordinator(hass, entry.entry_id, tracked_slugs, scan_interval)
    await coordinator.async_load_stored_state()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _async_register_services(hass)
    return True


def _async_register_services(hass: HomeAssistant) -> None:
    """Enregistre les services Lirflix (une seule fois, au premier setup)."""
    if hass.services.has_service(DOMAIN, SERVICE_MARK_ALL_SEEN):
        return

    async def _async_mark_all_seen(call: ServiceCall) -> None:
        entry_id = call.data.get("config_entry_id")
        coordinators: dict[str, LirflixCoordinator] = hass.data.get(DOMAIN, {})
        targets = (
            [coordinators[entry_id]] if entry_id and entry_id in coordinators
            else list(coordinators.values())
        )
        for coordinator in targets:
            await coordinator.async_mark_all_seen()

    hass.services.async_register(
        DOMAIN, SERVICE_MARK_ALL_SEEN, _async_mark_all_seen, schema=_MARK_ALL_SEEN_SCHEMA
    )


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recharge l'entrée quand ses options changent (ex: intervalle de scan)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharge une entrée de configuration Lirflix."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
