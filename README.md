# SPD Party Bot

[Português do Brasil](README.pt-BR.md)

**SPD Party Bot** is a free and open source Discord bot for organizing gaming parties, squads and quick community events.

It provides a Party Hub where members can create party invites, join with buttons, manage slots and queues, receive reminders, and optionally get temporary private voice channels for each party.

> [!TIP]
> Staff/setup commands require **Manage Server** permission or the configured Staff role.

> [!IMPORTANT]
> SPD Party does **not** require Administrator permission.

![Discord Bots](https://top.gg/api/widget/1502116547009970347.svg)

[TOP.GG](https://top.gg//bot/1502116547009970347)

## ✨ Features

- Party Hub with interactive buttons
- Party creation through Discord modals/forms
- Party title, slots, time, description and image URL
- Quick responses: **Going**, **Maybe** and **Not going**
- Click the same response again to remove yourself from that list
- Queue system when the party is full
- Automatic promotion from queue when a confirmed member leaves
- Private management panel for hosts and staff
- Edit and close parties
- Automatic reminders before the scheduled time
- Automatic party closing after the party ends
- Discord timestamp support for parsed times
- Per-server configuration
- Per-server language: `pt-BR` and `en-US`
- Per-server timezone
- Dynamic bot status
- Embed themes and custom colors
- Default party image per server
- Saved banner presets per server
- Optional `@everyone` ping when creating parties
- Optional Host role
- Optional Staff role
- Optional command channel restriction for `/party hub`
- Temporary private voice channels for parties
- Temporary party role for voice access
- Automatic voice channel and role cleanup

## 🎮 How it works

Staff creates a Party Hub with:

```txt
/party hub
```

Members use the **Create Party** button. The bot opens a form with:

- Party title
- Number of slots
- Time
- Description
- Image link

After submitting, the party invite is posted in the configured invite channel.

Members can click:

```txt
✅ Going
❔ Maybe
❌ Not going
```

Clicking the same button again removes the member from that list. If a confirmed member leaves **Going**, the next member in the queue is promoted automatically.

## 🔊 Temporary party calls

SPD Party can create a temporary private voice channel for each party.

When the party starts, or when the host/staff uses **Manage → Create call**, the bot can:

- Create a temporary role for that party
- Create a private voice channel
- Give access only to the host and members marked as **Going**
- Use the voice channel format: `Jogando┇🎮 Party Name`
- Create the channel inside the configured/default voice category
- Remove voice access when someone leaves **Going**
- Give voice access to promoted queue members
- Delete the voice channel and role when the party ends
- Wait until everyone leaves the call before deleting it

Required permissions for this optional feature:

- Manage Channels
- Manage Roles

> [!IMPORTANT]
> The bot role must be above the temporary roles it creates, otherwise Discord will block role assignment/removal.

## 🎨 Visual customization

Server staff can customize the bot in `/party config`.

Available visual options:

- Embed color
- Quick embed themes
- Server language
- Server timezone
- Default party image
- Saved banners
- Choose saved banner
- Clear saved banners

Quick themes include:

- SPD Neon
- Lime Green
- Ocean Blue
- Crimson Red
- Golden
- Cyber Pink
- Dark Steel
- Ice Cyan

## 🌎 Languages

SPD Party currently supports:

- `pt-BR` — Português do Brasil
- `en-US` — English

The language can be changed per server in `/party config`.

## 🧩 Commands

### `/party hub`

Creates the Party Hub in the current channel.

Can be used by staff, users with **Manage Server**, or the configured Host role in the allowed command channel.

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
- Embed theme
- Default party image
- Saved banners
- `@everyone` ping
- Whether everyone can create parties
- Automatic reminders
- Automatic party closing

### `/party lista`

Lists open parties in the current server.

### `/party limpar`

Removes closed parties from the local database for the current server.

> [!TIP]
> `/party config`, `/party hub` and `/party limpar` are staff/setup commands.

## ⚙️ Initial setup

After adding the bot to your server, use:

```txt
/party config
```

Configure:

1. Invite channel
2. Log channel
3. Command channel, optional
4. Host role, optional
5. Staff role, optional
6. Language
7. Timezone
8. Visual settings, optional

Then go to the channel where you want the Hub and use:

```txt
/party hub
```

## 🔐 Recommended permissions

SPD Party does not require Administrator permission.

Recommended permissions:

- View Channels
- Send Messages
- Read Message History
- Embed Links
- Use Application Commands
- Mention Everyone, optional and configurable
- Manage Channels, only needed for temporary party calls
- Manage Roles, only needed for temporary party voice roles

> [!NOTE]
> `Mention Everyone` is only used if enabled in the server configuration.

## 🕒 Supported time formats

Examples:

```txt
today 18:30
tomorrow 19:00
08/05/2026 18:30
08/05/2026 18:30 - 20:30
08/05/2026 18:30 - 09/05/2026 01:00
```

When the time is recognized, the bot displays Discord timestamps such as:

- Starts in X hours
- Started X minutes ago
- Ends in X hours
- Ended X minutes ago
- Duration

## 🚀 Railway hosting

Set the required variable:

```txt
DISCORD_TOKEN=YOUR_BOT_TOKEN
```

Optional but recommended for persistence:

```txt
DATA_DIR=/data
```

If using `DATA_DIR=/data`, create a Railway Volume mounted at:

```txt
/data
```

This keeps server configuration and party data persistent across deploys.

## 💻 Running locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Run with environment variables.

### Windows CMD

```bat
set DISCORD_TOKEN=YOUR_BOT_TOKEN
set DATA_DIR=%cd%\data
python bot.py
```

### PowerShell

```powershell
$env:DISCORD_TOKEN="YOUR_BOT_TOKEN"
$env:DATA_DIR="$PWD\data"
python bot.py
```

The bot stores local data in:

```txt
data/config.json
data/parties.json
```

Do not commit local data files.

## 📁 Suggested `.gitignore`

```gitignore
config.json
parties.json
.env
data/
__pycache__/
*.pyc
```

## 🧪 Notes for reviewers

SPD Party is free and open source.

The bot does not require Administrator permission. Core features are available without payment. Setup/staff commands require **Manage Server** permission or the configured Staff role.

Optional temporary voice features require **Manage Channels** and **Manage Roles**. If those permissions are not granted, the main party features still work.

Recommended entry point:

```txt
/party hub
```

## 💜 Support the project

SPD Party is free and open source.

Support is completely optional and helps keep the bot online, maintained and improving over time.

Supporters may receive community perks such as:

- Name listed in the README
- Priority consideration for suggestions
- Early preview of planned features when available
- Supporter badge/role in the support server, if available

Core bot features are not locked behind payment.

### Project Boosters

<!-- Add $30 supporters here -->

### Community Supporters

<!-- Add $15 supporters here -->

### Supporters

<!-- Add $5 supporters here -->

## 🛣️ Future ideas

- PostgreSQL database
- Web dashboard
- Game templates and presets
- Recurring parties
- Party history
- Participation ranking
- More visual presets
- Advanced party automation

## 📄 License

This project is licensed under the MIT License.
