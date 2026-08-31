"""Config flow pour Lirflix."""
from __future__ import annotations

import logging
from typing import Any

import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SHOWS,
    DATA_URL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def _fetch_show_options(hass) -> list[SelectOptionDict]:
    session = async_get_clientsession(hass)
    async with async_timeout.timeout(20):
        resp = await session.get(DATA_URL)
        resp.raise_for_status()
        raw = await resp.json(content_type=None)
    options = [
        SelectOptionDict(value=slug, label=show.get("title", slug))
        for slug, show in sorted(raw.items(), key=lambda kv: kv[1].get("title", kv[0]))
    ]
    return options


class LirflixConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gère la configuration initiale de l'intégration Lirflix."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        try:
            options = await _fetch_show_options(self.hass)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Impossible de récupérer la liste des émissions : %s", err)
            return self.async_abort(reason="cannot_connect")

        if user_input is not None:
            if not user_input.get(CONF_SHOWS):
                errors["base"] = "no_shows_selected"
            else:
                await self.async_set_unique_id(
                    "lirflix_" + "_".join(sorted(user_input[CONF_SHOWS]))
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Lirflix",
                    data={
                        CONF_SHOWS: user_input[CONF_SHOWS],
                        CONF_SCAN_INTERVAL_MINUTES: user_input.get(
                            CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
                        ),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_SHOWS): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL_MINUTES, default=DEFAULT_SCAN_INTERVAL_MINUTES
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=180)),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "LirflixOptionsFlow":
        return LirflixOptionsFlow(config_entry)


class LirflixOptionsFlow(config_entries.OptionsFlow):
    """Permet de modifier les émissions suivies et l'intervalle de scan."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        try:
            options = await _fetch_show_options(self.hass)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Impossible de récupérer la liste des émissions : %s", err)
            return self.async_abort(reason="cannot_connect")

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_shows = self._config_entry.options.get(
            CONF_SHOWS, self._config_entry.data.get(CONF_SHOWS, [])
        )
        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL_MINUTES,
            self._config_entry.data.get(
                CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
            ),
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_SHOWS, default=current_shows): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL_MINUTES, default=current_interval
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=180)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
