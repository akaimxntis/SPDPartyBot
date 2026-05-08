# SPD Party Bot

[Português do Brasil](README.pt-BR.md)

SPD Party Bot is a Discord bot for organizing gaming parties, squads and quick events in community servers.

Authorized members can create party invites through an interactive form, define slots, time, description and image URL. Players can respond with interactive buttons such as **Going**, **Maybe** and **Not going**. When a party is full, the bot automatically places new participants in a queue.

> [!TIP]
> Setup commands like `/party config`, `/party hub` and `/party limpar` require the **Manage Server** permission or the configured Staff role. Regular users can still create parties from the Hub button if allowed by the server settings.
>
> The configured Host role can also use `/party hub`, but only in the configured Command channel. The Hub is always created in the channel where `/party hub` is used.

## ✨ Features

- Party Hub with interactive buttons.
- Party creation through Discord modals/forms.
- Quick responses: ✅ Going, ❔ Maybe, ❌ Not going.
- Slot/capacity system.
- Automatic queue when the party is full.
- Private management panel for hosts and staff.
- Edit and close parties.
- Automatic party expiration.
- Automatic reminders before the scheduled time.
- Configurable invite channel per server.
- Configurable log channel per server.
- Configurable command channel for Host role usage.
- Configurable Host and Staff roles.
- Option to allow everyone to create parties.
- Optional `@everyone` mention when creating a party.
- Image URL support.
- Time support with Discord timestamps.
- Per-server timezone configuration.
- Multi-server support.
- Languages: Portuguese Brazil and English.
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

After that, the invite is posted in the configured invite channel.

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

Staff members or users with **Manage Server** permission can use it in any text channel.

Users with the configured **Host role** can use it only in the configured **Command channel**.

The Hub is always posted in the same channel where the command is used.

### `/party config`

Opens the server configuration panel.

It allows configuring:

- Invite channel
- Log channel
- Command channel
- Host role
- Staff role
- Language
- Timezone
- Embed color
- `@everyone` ping
- Whether everyone can create parties
- Automatic party expiration
- Automatic reminders

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
3. Command channel, optional but recommended if the Host role will use `/party hub`
4. Host role
5. Staff role
6. Language
7. Timezone

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

## ⏰ Automatic reminders and expiration

When enabled in the configuration panel:

- The bot can remind participants before a scheduled party starts.
- The bot can automatically close parties after the scheduled end time.
- If no end time is provided, the bot can close the party after a configured amount of active time.

These settings are configured per server.

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
- Party automatically closed
- Settings changed

## 👥 Multi-server support

The bot stores separate settings for each server.

Each server can have its own invite channel, log channel, command channel, Host role, Staff role, language, timezone, embed color, expiration settings and reminder settings.

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
- Temporary voice channel creation.
- Game templates/presets.
- Web dashboard.
- Party history.
- Participation ranking.

## 📄 License

This project is licensed under the MIT License.
