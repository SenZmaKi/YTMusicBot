# Environment variables

These can be autoloaded if you create a `.env` file in the project root directory.

```env
DISCORD_TOKEN=<token-goes-here>  # required
SERVER_IDS=<server-1,server-2>   # required
MAX_SEARCH_RESULTS=1000          # optional, max cached search results
DISCORD_MSG_LIMIT=2000           # optional, the current discord message limit
MAX_DOWNLOADS_SIZE_MBS=1000      # optional, the max size of cached downloads in megabytes
SONG_URLS_CACHE_LIFETIME=86400   # optional, the cache lifetime for song URLs in seconds
```
