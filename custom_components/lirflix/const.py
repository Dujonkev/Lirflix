"""Constantes pour l'intégration Lirflix."""
from datetime import timedelta

DOMAIN = "lirflix"

DATA_URL = "https://lirflix.net/data/shows.json"
SHOW_PAGE_URL = "https://lirflix.net/emission/{slug}"

CONF_SHOWS = "shows"
CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"

DEFAULT_SCAN_INTERVAL_MINUTES = 20
DEFAULT_SCAN_INTERVAL = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES)

EVENT_NEW_EPISODE = "lirflix_new_episode"

ATTR_SLUG = "slug"
ATTR_SHOW_TITLE = "show_title"
ATTR_EPISODE_NUMBER = "episode_number"
ATTR_EPISODE_TITLE = "episode_title"
ATTR_AIR_DAY = "air_day"
ATTR_AIR_TIME = "air_time"
ATTR_URL = "url"
ATTR_IMAGE = "image"
ATTR_TOTAL_EPISODES = "total_episodes"
ATTR_LAST_UPDATED = "last_updated"
