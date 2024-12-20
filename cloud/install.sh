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
sudo apt install python3.12 -y
sudo apt install python3.12-venv -y
sudo apt install ffmpeg -y

git clone https://github.com/SenZmaKi/YTMusicBot.git
cd YTMusicBot
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
if [ "$TEST" = true ]; then
    pip install -r dev-requirements.txt
    pytest -s -v
else
    python3.12 -m ytmusicbot.youtube --configure-random-songs
fi

deactivate
if [ -f "../.env" ]; then
  mv ../.env .env
fi