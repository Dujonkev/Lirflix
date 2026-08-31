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

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_SCAN_INTERVAL_MINUTES, CONF_SHOWS, DEFAULT_SCAN_INTERVAL_MINUTES, DOMAIN
from .coordinator import LirflixCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialise une entrée de configuration Lirflix."""
    tracked_slugs: list[str] = entry.data.get(CONF_SHOWS, [])
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL_MINUTES,
        entry.data.get(CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES),
    )

    coordinator = LirflixCoordinator(hass, tracked_slugs, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recharge l'entrée quand ses options changent (ex: intervalle de scan)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharge une entrée de configuration Lirflix."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
