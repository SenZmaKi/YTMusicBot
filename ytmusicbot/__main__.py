from ytmusicbot.discord.main import main
from ytmusicbot.youtube.main import configure_random_songs
import sys

if "--configure-random-songs" in sys.argv or "-crs" in sys.argv:
    configure_random_songs()
else:
    main()
