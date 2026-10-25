#!/data/data/com.termux/files/usr/bin/bash
set -e
pkg update -y
pkg install -y python termux-api
python -m pip install --upgrade pip
if [ ! -f .env ]; then cp .env.example .env; fi
echo
echo 'Setup complete. Edit .env, then run: python main.py'
echo 'Voice features also require the Termux:API Android app and microphone/speech permissions.'
