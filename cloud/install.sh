# curl https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/cloud/install.sh | bash

# curl https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/cloud/install.sh | bash -s -- --dev

set -e

INSTALL_DEV=false
for arg in "$@"; do
    if [[ "$arg" == "--dev" || "$arg" == "-d" ]]; then
        INSTALL_DEV=true
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
if [ "$INSTALL_DEV" = true ]; then
    pip install -r dev-requirements.txt
fi

python3.12 -m ytmusicbot.youtube --configure-random-songs
deactivate
[ -f "../.env" ] && mv ../.env .env