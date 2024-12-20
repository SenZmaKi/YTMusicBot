# Commands

- **`/search`**: Search for a song on YouTube.

  - Parameters: `query` (required), `max_results` (optional, default: 3)

- **`/play`**: Play a song or playlist by title or URL.

  - Parameters: `title_or_url` (required)

- **`/queue`**: Add a song to the queue by title or URL.

  - Parameters: `title_or_url` (required)

- **`/show_queue`**: Show the current song queue.

- **`/clear_queue`**: Clear the song queue.

- **`/set_volume`**: Set the playback volume.

  - Parameters: `volume` (required)

- **`/increase_volume`**: Increase the volume by 10%.

- **`/decrease_volume`**: Decrease the volume by 10%.

- **`/pause`**: Pause the current song.

- **`/resume`**: Resume the current song or last session.

- **`/now_playing`**: Show the currently playing song.

- **`/loop`**: Enable looping of the current song.

- **`/unloop`**: Disable looping.

- **`/shuffle`**: Shuffle the song queue.

- **`/favourite`**: Mark a song as a favourite.

- **`/unfavourite`**: Remove a song from favourites.

- **`/show_favourites`**: Show the list of favourite songs.
- **`/play_favourites`**: Plays favourite songs.

- **`/dequeue`**: Remove a song from the queue by number.

  - Parameters: `song_number` (required)

- **`/dequeue_next`**: Remove the next song from the queue.

- **`/dequeue_previous`**: Remove the previous song from the queue.

- **`/dequeue_current`**: Remove the current song from the queue.

- **`/stop`**: Stop the current song.

- **`/random`**: Play a random song.

- **`/skip_to`**: Skip to a specific song in the queue.

  - Parameters: `song_number` (required)

- **`/repo`**: Show the link to the bot's source code.

- **`/creator`**: Show the link to the bot's creator.

- **Owner Commands**:

  The owner is whoever added the bot to the server.

  - **`/owner reset_cache`**: Reset all the bot's cache.
  - **`/owner metrics`**: Show the bot's metrics.
  - **`/owner stop_bot`**: Stop the bot.
  - **`/owner restart_bot`**: Restart the bot.
