# Smart Home Controller (Telegram)

A small [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) service that controls devices on your LAN from Telegram: **Yeelight** bulbs, **Wake-on-LAN** for PCs, and **ICMP reachability** checks for configured hosts.

## Features

- **Access control**: admins listed in config; new users ask for access via `/start` until an admin runs `/verify`.
- **Commands for authorized users** (from `local_data.txt`): `bulbs`, `pcs`, `ping` — inline keyboards for toggle / WoL / ping status.
- **Admin**: `/verify <username> <chat_id>`, `/reload` to re-read data files without restarting (token changes still require a container restart).

## Requirements

- Python **3.12+** (matches the Docker image).
- Dependencies (see `Dockerfile`): `python-telegram-bot` 22.x with SOCKS extras, `yeelight`, `wakeonlan`, `httpx`.
- On the host/container: `ping` (ICMP) for the `ping` command — the Docker image installs `iputils-ping`.

## Configuration

State lives under **`DATA_DIR`** (default: `./data` next to the scripts).

| File | Purpose |
|------|---------|
| `secure_data.txt` | Bot token (first line `API_KEY_CTR <token>`) and admin usernames with Telegram chat IDs. Can be bootstrapped from env; see below. |
| `session_data.txt` | Verified users (`<username> <chat_id>` per line); updated when admins verify users. |
| `local_data.txt` | Device map: sections prefixed with `!section` followed by `name value` lines (value is IP, MAC, or hostname depending on section). |

### `local_data.txt` format

```text
!bulbs
living_room 192.168.1.10
!pcs
desktop AA:BB:CC:DD:EE:FF
!ping
router 192.168.1.1
```

Sections used by the bot: **`bulbs`**, **`pcs`**, **`ping`**. (A `servers` block exists in the support module but is not wired into the active command map.)

### Environment variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather). Used if `secure_data.txt` is missing or has an empty token line. Alias: `API_KEY_CTR`. |
| `BOT_ADMINS_JSON` | JSON map of admin Telegram **usernames** to chat id, e.g. `{"myuser":{"id":"123456"}}` or `{"myuser":"123456"}`. Used when `secure_data.txt` has no admin lines yet. |
| `DATA_DIR` | Directory for `secure_data.txt`, `session_data.txt`, `local_data.txt`. |
| `TELEGRAM_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` | Optional proxy URL for Telegram Bot API (e.g. if the network blocks `api.telegram.org`). |

## Run with Docker

The compose file uses **`network_mode: host`** so the bot can reach Yeelight and send WoL on the same LAN as the machine.

1. Create a `.env` (not committed) with at least `TELEGRAM_BOT_TOKEN` and `BOT_ADMINS_JSON`, or populate `./data/secure_data.txt` before first run.
2. Mount `./data` so tokens and verified users persist.

```bash
docker compose up -d --build
```

Adjust or remove `TELEGRAM_PROXY` in `docker-compose.yml` if you do not use a proxy.

## Run locally (venv)

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install "python-telegram-bot>=22,<23" "python-telegram-bot[socks]" yeelight wakeonlan httpx
export TELEGRAM_BOT_TOKEN="..."   # or use data/secure_data.txt
export DATA_DIR="$(pwd)/data"
python smart_home_controller_tg.py
```

## Optional: SOCKS5 sidecar

The `socks5-nl/` directory contains a **Dante**-based SOCKS5 setup documented in [`socks5-nl/SOCKS5-NL-SETUP.md`](socks5-nl/SOCKS5-NL-SETUP.md) for routing Telegram traffic through another exit.

## Project layout

| Path | Role |
|------|------|
| `smart_home_controller_tg.py` | Bot entrypoint, handlers, polling bootstrap. |
| `smart_home_controller_support.py` | Data loading, decorators, Yeelight / WoL / ping logic. |
| `Dockerfile`, `docker-compose.yml` | Container build and run. |
