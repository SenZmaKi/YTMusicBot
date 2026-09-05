# curl https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/cloud/install.sh | bash

# curl https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/cloud/install.sh | bash -s -- --test

set -e

TEST=false
for arg in "$@"; do
    if [[ "$arg" == "--test" || "$arg" == "-t" ]]; then
        TEST=true
        break
    fi
done


sudo apt update -y
sudo apt install git -y
sudo apt install ffmpeg -y
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

git clone https://github.com/SenZmaKi/YTMusicBot.git
cd YTMusicBot
uv sync
if [ "$TEST" = true ]; then
    uv run python -m pytest -s -v
else
    uv run python -m ytmusicbot.youtube --configure-random-songs
fi

if [ -f "../.env" ]; then
  mv ../.env .env
fi
