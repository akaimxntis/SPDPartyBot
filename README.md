# SPD Party Bot

SPD Party Bot is an open source Discord bot for organizing gaming parties, squads and quick community events.

Authorized members can create party invites through an interactive form, set slots, time, description and image, and let players respond with buttons such as **Going**, **Maybe** and **Not going**. When a party is full, the bot automatically adds new participants to a queue.

## ✨ Features

- Party Hub with interactive buttons.
- Party creation through Discord modals/forms.
- Quick response buttons:
  - ✅ Going
  - ❔ Maybe
  - ❌ Not going
- Slot/capacity system.
- Automatic queue when a party is full.
- Private management panel for hosts and staff.
- Edit and close parties.
- Per-server invite channel.
- Per-server log channel.
- Configurable Host role.
- Configurable Staff role.
- Option to allow everyone to create parties.
- Optional `@everyone` mention when creating a party.
- Image support through links.
- Discord timestamp support.
- Shows when a party starts, started, ends, ended and its duration.
- Per-server timezone configuration.
- Multi-server support.
- Languages:
  - English
  - Portuguese (Brazil)
- JSON persistence.
- `DATA_DIR` support for persistent volumes on hosting platforms such as Railway.

## 🎮 How it works

Staff creates a Hub with:

```txt
/party hub
```

Members can then click **Create Party**.

The bot opens a form with:

- Party title
- Number of slots
- Time
- Description
- Image link

After submitting, the invite is posted in the configured invite channel.

Example party invite:

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

You can configure:

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

After adding the bot to a server, run:

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

Then go to the channel where you want the Hub and run:

```txt
/party hub
```

## 🔐 Recommended permissions

The bot needs:

- View Channels
- Send Messages
- Read Message History
- Embed Links
- Use Application Commands
- Mention `@everyone`, optional

For private channels, add the bot role to the channel permissions.

## 🌎 Languages

The bot supports:

- `en-US` — English
- `pt-BR` — Portuguese (Brazil)

The language can be changed per server in the configuration panel.

## 🕒 Supported time formats

The time field accepts examples such as:

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
LICENSE
```

## 📦 requirements.txt

```txt
discord.py>=2.4.0
```

## 🔧 config.example.json

Recommended example:

```json
{
  "token": "",
  "guilds": {}
}
```

Do not publish your real token. Use an environment variable instead.

## 🚀 Hosting on Railway

On Railway, configure this variable:

```txt
DISCORD_TOKEN=YOUR_BOT_TOKEN
```

Optional, but recommended for persistence:

```txt
DATA_DIR=/data
```

If you use `DATA_DIR=/data`, create a Railway Volume mounted at:

```txt
/data
```

This allows the bot to keep server configuration and party data after redeploys.

## ▶️ Start command

```bash
python bot.py
```

## 🔒 Security

Never publish your bot token on GitHub.

Use the environment variable:

```txt
DISCORD_TOKEN
```

If your token leaks, reset it immediately in the Discord Developer Portal.

## 📝 Logs

When configured, the log channel records actions such as:

- Party created
- User marked Going
- User marked Maybe
- User marked Not going
- User joined the queue
- Party edited
- Party closed
- Configuration changed

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

In active development.

## 💡 Future ideas

- PostgreSQL database.
- Automatic party expiration.
- Temporary voice channel creation.
- Game templates/presets.
- Web dashboard.
- Party history.
- Participation ranking.
- Automatic reminders before the scheduled time.

## 📄 License

This project is licensed under the MIT License.
