# SPD Party Bot

[Português do Brasil](README.pt-BR.md)

SPD Party Bot is a Discord bot for organizing gaming parties, squads and quick events in community servers.

Authorized members can create party invites through an interactive form, define slots, time, description and image URL. Players can respond with interactive buttons such as **Going**, **Maybe** and **Not going**. When a party is full, the bot automatically places new participants in a queue.

## ✨ Features

- Party Hub with interactive buttons.
- Party creation through Discord modals/forms.
- Quick responses:
  - ✅ Going
  - ❔ Maybe
  - ❌ Not going
- Slot/capacity system.
- Automatic queue when the party is full.
- Private management panel for hosts and staff.
- Edit and close parties.
- Configurable invite channel per server.
- Configurable log channel per server.
- Configurable Host role.
- Configurable Staff role.
- Option to allow everyone to create parties.
- Optional `@everyone` mention when creating a party.
- Image URL support.
- Time support with Discord timestamps.
- Shows when the party starts, started, ends, ended and its duration.
- Per-server timezone configuration.
- Multi-server support.
- Languages:
  - Portuguese Brazil
  - English
- JSON-based storage.
- `DATA_DIR` support for persistent volumes on hosts like Railway.

## 🎮 How it works

Staff creates a Party Hub with:

```txt
/party hub
```

Members then use the **Create Party** button.

The bot opens a form with:

- Party title
- Number of slots
- Time
- Description
- Image link

After that, the invite is posted in the configured channel.

Example invite:

```txt
🎮 Lego Party - 4 Players

Time
Today 18:30 - 20:30
Starts in 2 hours
Duration: 2h

✅ Going (1/4)
❔ Maybe (0/4)
❌ Not going (0)

Status: Open
Host: @user
```

## 🧩 Commands

### `/party hub`

Creates the Party Hub in the current channel.

Only staff members or users with **Manage Server** permission can use it.

### `/party config`

Opens the server configuration panel.

It allows configuring:

- Invite channel
- Log channel
- Host role
- Staff role
- Language
- Timezone
- Embed color
- `@everyone` ping
- Whether everyone can create parties

### `/party lista`

Lists open parties in the current server.

### `/party limpar`

Removes closed parties from the local database for the current server.

## ⚙️ Initial setup

After adding the bot to your server, use:

```txt
/party config
```

Configure:

1. Invite channel
2. Log channel
3. Host role
4. Staff role
5. Language
6. Timezone

Then go to the channel where you want the Hub and use:

```txt
/party hub
```

## 🔐 Recommended permissions

The bot needs the following permissions:

- View Channels
- Send Messages
- Read Message History
- Embed Links
- Use Application Commands
- Mention `@everyone`, optional

For private channels, manually add the bot role to the channel permissions.

## 🌎 Languages

The bot supports:

- `pt-BR` — Português do Brasil
- `en-US` — English

The language can be changed per server in the configuration panel.

## 🕒 Supported time formats

The time field accepts examples like:

```txt
today 18:30
tomorrow 19:00
08/05/2026 18:30
08/05/2026 18:30 - 20:30
08/05/2026 18:30 - 09/05/2026 01:00
```

When the time is recognized, the bot displays automatic Discord timestamps, such as:

- Starts in X hours
- Started X minutes ago
- Ends in X hours
- Ended X minutes ago
- Party duration

## 🗂️ Main files

```txt
bot.py
config.example.json
parties.example.json
requirements.txt
README.md
README.pt-BR.md
LICENSE
```

## 📦 requirements.txt

```txt
discord.py>=2.4.0
```

## 🔧 config.example.json

Recommended model:

```json
{
  "token": "",
  "guilds": {}
}
```

Copy it to `config.json` only for local development.

Do not publish `config.json` with real server data or tokens.

## 🚀 Railway hosting

On Railway, configure the following variable:

```txt
DISCORD_TOKEN=YOUR_BOT_TOKEN
```

Optional, but recommended for persistence:

```txt
DATA_DIR=/data
```

If using `DATA_DIR=/data`, create a Railway Volume mounted at:

```txt
/data
```

This allows the bot to save configuration and party data in persistent storage.

## ▶️ Start Command

```bash
python bot.py
```

## 🔒 Security

Never publish your bot token on GitHub.

Use the environment variable:

```txt
DISCORD_TOKEN
```

If your token is leaked, reset it immediately in the Discord Developer Portal.

The public repository should not include:

```txt
config.json
parties.json
.env
data/
```

Use the example files instead:

```txt
config.example.json
parties.example.json
```

## 📝 Logs

When configured, the log channel records actions such as:

- Party created
- User marked Going
- User marked Maybe
- User marked Not going
- User joined the queue
- Party edited
- Party closed
- Settings changed

## 👥 Multi-server support

The bot stores separate settings for each server.

Each server can have its own:

- Invite channel
- Log channel
- Host role
- Staff role
- Language
- Timezone
- Embed color

## 💜 Supporters

Thanks to everyone supporting this project!

### Project Boosters



<!-- Add $30 supporters here -->

### Community Supporters



<!-- Add $15 supporters here -->

### Supporters



<!-- Add $5 supporters here -->

## 📌 Project status

Active development.

## 💡 Future ideas

- PostgreSQL database.
- Automatic party expiration.
- Temporary voice channel creation.
- Game templates/presets.
- Web dashboard.
- Party history.
- Participation ranking.
- Automatic notifications before the scheduled time.

## 📄 License

This project is licensed under the MIT License.
