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

SERVICE_MARK_ALL_SEEN = "mark_all_seen"

STORAGE_VERSION = 1
STORAGE_KEY_TEMPLATE = "lirflix_{entry_id}_acknowledged"

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
ATTR_PENDING_SHOWS = "pending_shows"
ATTR_LATEST_SHOW_TITLE = "latest_show_title"

# Jours de diffusion tels qu'on les trouve dans data/shows.json : soit des
# noms de jours en français (simples ou en liste séparée par des virgules),
# soit le mot-clé anglais "weekdays". Index de semaine : lundi=0 ... dimanche=6.
WEEKDAY_ALIASES: dict[str, int] = {
    "lundi": 0,
    "mardi": 1,
    "mercredi": 2,
    "jeudi": 3,
    "vendredi": 4,
    "samedi": 5,
    "dimanche": 6,
}
WEEKDAYS_KEYWORD = "weekdays"
