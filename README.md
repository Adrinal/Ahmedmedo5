# Adrinal CLI

A colorful terminal AI chat powered by OpenRouter — works on Termux, Linux, and Windows.

## Setup

### Termux (Android)
```bash
pkg install python git
pip install requests
git clone https://github.com/Adrinal/AdrinalCLI
cd AdrinalCLI
cp config.example.json config.json
nano config.json
python chat.py
