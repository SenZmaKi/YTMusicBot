#!/usr/bin/env bash

# curl https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/cloud/install.sh | bash

set -e

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
python3.12 -m ytmusicbot.youtube --configure-random-songs
deactivate
chmod +x google-cloud/*.sh
mv ../.env .env
