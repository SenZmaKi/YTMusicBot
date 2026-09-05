<h1 align="center">
<img align="center" height="80px" width="80px" src="https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/.github/images/icon.png" alt="icon"> YTMusicBot</h1>
<p align="center">
A feature rich and blazingly fast Discord bot for playing music from YouTube.
</p>

<p align="center">
  <a href="#installation">Installation</a> •
  <a href="#features">Features</a> •
  <a href="#support">Support</a> •
  <a href="#contribution">Contribution</a> •
  <a href="#cloud-deployment-ubuntu">Cloud Deployment</a> •
  <a href="#testing">Testing</a> •
  <a href="#commands">Commands</a> •
  <a href="#environment-variables">Environment Variables</a>
</p>

<video src="https://github.com/user-attachments/assets/06fae060-0bc9-43b0-8153-04f4cf430e22" 
       width="100%" 
       height="auto" 
       controls 
       autoplay 
       loop 
       muted 
       poster="https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/.github/images/demo.png" 
       preload="auto" 
       playsinline>
</video>

## Features

- **Search Songs**: Search for songs on YouTube.
- **Play Songs**: Play songs or playlists directly by title or URL.
- **Queue Management**: Add, remove, or view songs in the queue.
- **Volume Control**: Adjust the playback volume.
- **Playback Control**: Pause, resume, skip, loop and shuffle songs.
- **Favourites**: Mark songs as favourites and view or play them later.
- **Bot Management**: For bot owners to manage the bot's life cycle, performance and data.

## Installation

1. Ensure you have [uv](https://docs.astral.sh/uv/getting-started/installation/) and [Git](https://github.com/git-guides/install-git) installed. uv will install the required Python version when needed.

2. Clone the repository:

   ```bash
   git clone https://github.com/SenZmaKi/YTMusicBot.git
   cd YTMusicBot
   ```

3. Install the locked dependencies:

   ```bash
   uv sync
   ```

4. Install [FFmpeg](https://www.ffmpeg.org/)

   - Windows
     ```bash
     winget install Gyan.FFmpeg
     ```
   - Mac
     ```bash
     brew install ffmpeg
     ```
   - Linux

     Use your distro's package manager

5. [Setup the bot](https://github.com/SenZmaKi/YTMusicBot/tree/master/docs/setup-bot.md)

6. Configure random songs:

   ```bash
   uv run python -m ytmusicbot.youtube --configure-random-songs
   ```

   - Optionally you can use custom random songs.

     - Create a `custom_random_songs_config.json` file in the project root directory with the following format:

     ```json
     [
       {
         "artist": "Sauti Sol",
         "playlist_url": "https://www.youtube.com/watch?v=Or2sMfOcTtw&list=RDEMGKSEWOD6zbF-FHc_dLYrPg&start_radio=1"
       },
       {
         "artist": "Cigarettes After Sex",
         "playlist_url": "https://www.youtube.com/watch?v=Or2sMfOcTtw&list=RDEMGKSEWOD6zbF-FHc_dLYrPg&start_radio=1"
       }
     ]
     ```

     - Then run

       ```bash
       uv run python -m ytmusicbot.youtube --configure-random-songs
       ```

7. Run the bot:

   ```bash
   uv run python -m ytmusicbot.discord
   ```

## Contribution

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Submit a pull request with a detailed description of the changes.

## Support

- You can support the development of YTMusicBot through donations on [GitHub Sponsors](https://github.com/sponsors/SenZmaKi).
- You can also leave a star on the github for more discord degens to know about it.
- YTMusicBot is open to pull requests, so if you have ideas for improvements, feel free to [contribute](#contribution)!

## Cloud Deployment (Ubuntu)

The cloud deployment scripts are located in the `YTMusicBot/cloud` directory.

### Installation Script

The `install.sh` script installs the bot and its dependencies.

- Create a `.env` file with your configuration in the current working directory then run

  ```bash
  curl https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/cloud/install.sh | bash
  ```

### Kill Script

The `kill.sh` script terminates the background bot process.

### Run Script

The `run.sh` script starts the bot.

### NoHup Script

The `nohup.sh` script runs the bot in the background.

## Dokploy Deployment

Pushes to `main` run linting, formatting checks, and tests, then publish the
container image to GitHub Container Registry and trigger a Dokploy deployment.

Add these GitHub Actions repository secrets before pushing:

- `DOKPLOY_URL`: the base URL of your Dokploy instance
- `DOKPLOY_API_KEY`: a Dokploy API key
- `DOKPLOY_APP_ID`: the ID of the Dokploy application to deploy

In Dokploy, configure the application to use
`ghcr.io/<github-owner>/<repository>:latest`. If the package is private, add
GitHub Container Registry credentials. Configure the bot variables listed
below in Dokploy, and persist `/app/cache` and `/app/random_songs` if downloads
and generated random-song data should survive deployments. This bot is a
long-running worker and does not expose an HTTP port.

If YouTube requires authentication, follow the
[YouTube cookie deployment guide](docs/youtube-cookies.md) to securely export,
test, and mount a Netscape cookie file. The guide includes Dokploy-specific
mount settings and explains permissions, JavaScript runtimes, and server-IP
limitations.

## Testing

1. Install development dependencies and the Git hooks:

   ```bash
   uv sync --dev
   uv run pre-commit install
   ```

2. Run tests:

   ```bash
   uv run python -m pytest
   ```

## [Commands](https://github.com/SenZmaKi/YTMusicBot/blob/master/docs/commands.md)

## [Environment Variables](https://github.com/SenZmaKi/YTMusicBot/blob/master/docs/env.md)
