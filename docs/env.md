# Environment variables

These can be autoloaded if you create a `.env` file in the project root directory.

```env
DISCORD_TOKEN=<token-goes-here>  # required
SERVER_IDS=<server-1,server-2>   # required
MAX_SEARCH_RESULTS=1000          # optional, max cached search results
DISCORD_MSG_LIMIT=2000           # optional, the current discord message limit
MAX_DOWNLOADS_SIZE_MBS=1000      # optional, the max size of cached downloads in megabytes
SONG_URLS_CACHE_LIFETIME=86400   # optional, button URL cache lifetime in seconds
YTDLP_COOKIE_FILE=C:\\path\\to\\cookies.txt # optional, Netscape-format YouTube cookies
YTDLP_COOKIES_FROM_BROWSER=chrome # optional local alternative: chrome, edge, or firefox
```

Set only one cookie option. `YTDLP_COOKIE_FILE` takes precedence and is
recommended for a long-running bot. Keep the cookie file outside this repository
because it contains account credentials.

For production deployment, see the
[Dokploy cookie setup guide](dokploy-cookies.md).
