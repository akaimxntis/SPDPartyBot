import json
import os
import re
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands, tasks


# ============================================================
# Arquivos / dados
# ============================================================

DATA_DIR = Path(os.getenv("DATA_DIR") or Path(__file__).parent)
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = DATA_DIR / "config.json"
PARTIES_PATH = DATA_DIR / "parties.json"

DEFAULT_GUILD_CONFIG = {
    "party_channel_id": 0,
    "log_channel_id": 0,
    "command_channel_id": 0,
    "host_role_id": 0,
    "staff_role_id": 0,
    "embed_color": 16766720,
    "everyone_can_create": False,
    "ping_everyone": True,
    "language": "pt-BR",
    "timezone_offset_minutes": -180,  # UTC-3 por padrão
    "auto_close_enabled": True,
    "auto_close_after_hours": 6,
    "reminder_enabled": True,
    "reminder_minutes": 15,
}

DEFAULT_CONFIG = {
    "token": "",
    "guilds": {},
}

SUPPORTED_LANGUAGES = {
    "pt-BR": "Português do Brasil",
    "en-US": "English",
}


def save_json(path: Path, data):
    """Salva JSON de forma atômica para reduzir risco de corromper o arquivo."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")

    with tmp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")

    tmp_path.replace(path)


def load_json(path: Path, default):
    if not path.exists():
        save_json(path, default)
        return deepcopy(default)

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        save_json(path, default)
        return deepcopy(default)

    if isinstance(default, dict) and isinstance(data, dict):
        changed = False
        for key, value in default.items():
            if key not in data:
                data[key] = deepcopy(value)
                changed = True

        # Migração automática da versão antiga, que usava um servidor só.
        old_guild_id = int(data.get("guild_id", 0) or 0) if "guild_id" in data else 0
        if old_guild_id:
            guild_key = str(old_guild_id)
            data.setdefault("guilds", {})
            if guild_key not in data["guilds"]:
                data["guilds"][guild_key] = deepcopy(DEFAULT_GUILD_CONFIG)

            guild_conf = data["guilds"][guild_key]
            for old_key in DEFAULT_GUILD_CONFIG:
                if old_key in data:
                    guild_conf[old_key] = data[old_key]

            for old_key in (
                "guild_id",
                "party_channel_id",
                "log_channel_id",
                "command_channel_id",
                "host_role_id",
                "staff_role_id",
                "embed_color",
                "everyone_can_create",
                "ping_everyone",
            ):
                data.pop(old_key, None)
            changed = True

        if changed:
            save_json(path, data)

    return data


config: Dict[str, Any] = load_json(CONFIG_PATH, DEFAULT_CONFIG)
parties: Dict[str, Any] = load_json(PARTIES_PATH, {})


# ============================================================
# I18N
# ============================================================

I18N = {
    "pt-BR": {
        "hub_title": "🎮 Hub de Parties — SPD",
        "hub_desc": (
            "Crie e acompanhe convites de party pelo painel abaixo.\n\n"
            "**🎮 Criar Party** — abre um formulário para criar convite.\n"
            "**📋 Ver Parties** — mostra as parties abertas.\n"
            "**👤 Minhas Parties** — mostra onde você está participando.\n"
            "**❓ Ajuda** — explica o sistema."
        ),
        "party_channel": "📢 Canal dos convites",
        "party_channel_ok": "As parties criadas aqui serão enviadas em {channel}.",
        "config_pending": "⚠️ Configuração pendente",
        "config_pending_desc": "A staff ainda precisa configurar o canal dos convites.",
        "hub_footer": "Use /party config para configurar o bot",
        "create_party": "Criar Party",
        "list_parties": "Ver Parties",
        "my_parties": "Minhas Parties",
        "help": "Ajuda",
        "use_inside_server": "Use isso dentro de um servidor.",
        "no_perm_create": "Você não tem permissão para criar parties.\nCargo necessário: {required}.",
        "no_party_channel": "O canal de convites ainda não foi configurado.\nA staff precisa usar `/party config`.",
        "no_open_parties": "Não tem nenhuma party aberta no momento.",
        "not_in_party": "Você não está em nenhuma party aberta.",
        "help_text": (
            "**Como funciona:**\n\n"
            "1. Clique em **🎮 Criar Party**.\n"
            "2. Preencha título, vagas, horário, descrição e imagem.\n"
            "3. O convite aparece no canal configurado pela staff.\n"
            "4. O pessoal clica em ✅, ❔ ou ❌.\n"
            "5. Se **Vou** lotar, quem clicar em ✅ vai para a fila.\n"
            "6. O host ou a staff usa **⚙️ Gerenciar** para editar ou encerrar.\n\n"
            "Quem pode criar party: {host_text}."
        ),
        "everyone": "todos os membros",
        "host_role_required": "cargo Host configurado pela staff",
        "modal_create_title": "Criar Party",
        "modal_edit_title": "Editar Party",
        "party_title_label": "Título da party",
        "party_title_placeholder": "Ex: Lego Party - 4 Jogadores",
        "capacity_label": "Vagas",
        "capacity_placeholder": "Ex: 4",
        "time_label": "Horário",
        "time_placeholder": "Ex: hoje 18:30 - 20:30 ou 08/05/2026 18:30",
        "desc_label": "Descrição",
        "desc_placeholder": "Ex: Bora jogar LEGO Party!",
        "image_label": "Imagem por link",
        "image_placeholder": "Ex: https://site.com/imagem.png",
        "capacity_number": "O campo **Vagas** precisa ser um número.",
        "capacity_range": "As vagas precisam ficar entre **1** e **25**.",
        "image_invalid": "O link da imagem precisa começar com `http://` ou `https://`.",
        "party_channel_not_found": "Canal de convites não encontrado.\nA staff precisa usar `/party config` para configurar.",
        "party_channel_no_perm": "Achei o canal de convites, mas não tenho permissão para enviar mensagem nele.",
        "party_create_error": "Erro ao criar a party: `{error}`",
        "party_created": "Party criada com sucesso em {channel}: {url}",
        "log_party_created": "🎮 {user} criou a party **{title}** `{party_id}` em {channel}.",
        "time_parse_warning": "\n⚠️ Não consegui interpretar o horário automaticamente. Ele foi salvo como texto.",
        "party_missing": "Essa party não existe mais.",
        "only_host_staff_edit": "Só o host ou a staff pode editar essa party.",
        "only_host_staff_manage": "Só o host ou a staff pode gerenciar essa party.",
        "only_host_staff_close": "Só o host ou a staff pode encerrar essa party.",
        "party_edited": "Party editada com sucesso.",
        "party_closed": "Party encerrada.",
        "party_already_closed": "Essa party já está encerrada.",
        "manage_party": "⚙️ Gerenciar Party",
        "manage_desc": "Party: **{title}**\nID: `{party_id}`\n\nEscolha uma ação abaixo.",
        "edit_party": "Editar Party",
        "close_party": "Encerrar Party",
        "party_identify_fail": "Não consegui identificar essa party.",
        "party_db_missing": "Essa party não existe mais no banco de dados.",
        "party_closed_click": "Essa party já foi encerrada.",
        "already_going": "Você já marcou **Vou**.",
        "already_maybe": "Você já marcou **Talvez**.",
        "already_no": "Você já marcou **Não vou**.",
        "marked_going": "Você marcou **Vou**.",
        "marked_maybe": "Você marcou **Talvez**.",
        "marked_no": "Você marcou **Não vou**.",
        "queue_joined": "A party está cheia. Você entrou na **fila**.",
        "promoted": "\n{user} foi puxado da fila.",
        "btn_going": "Vou",
        "btn_maybe": "Talvez",
        "btn_no": "Não vou",
        "btn_manage": "Gerenciar",
        "field_time": "Horário",
        "field_status": "Status",
        "field_host": "Organizador",
        "field_queue": "📋 Fila ({count})",
        "going_field": "✅ Vou ({current}/{capacity})",
        "maybe_field": "❔ Talvez ({current}/{capacity})",
        "no_field": "❌ Não vou ({current})",
        "status_open": "🟢 Aberta",
        "status_closed": "🔴 Encerrada",
        "created_by": "Criado por {name} • Party ID: {party_id}",
        "starts": "Começa {relative}",
        "started": "Começou {relative}",
        "ends": "Termina {relative}",
        "ended": "Terminou {relative}",
        "duration": "Duração: {duration}",
        "active_since": "Ativa desde {relative}",
        "created_relative": "Criada {relative}",
        "config_title": "⚙️ Configuração do Party Bot",
        "config_desc": "Veja a configuração atual abaixo. Use os botões para alterar por categoria.",
        "config_footer": "Esse painel aparece só para quem usou o comando",
        "section_channels": "📢 Canais",
        "section_roles": "🎭 Cargos",
        "section_behavior": "⚙️ Comportamento",
        "section_appearance": "🎨 Aparência e idioma",
        "section_status": "🩺 Diagnóstico",
        "not_defined": "não definido",
        "ok": "✅ OK",
        "warn": "⚠️ Atenção",
        "bad": "❌ Problema",
        "channel_invites": "Canal de convites",
        "channel_logs": "Canal de logs",
        "channel_commands": "Canal de comandos",
        "role_host": "Cargo Host",
        "role_staff": "Cargo Staff",
        "everyone_create": "Todos podem criar party",
        "ping_everyone": "Marcar @everyone ao criar",
        "auto_close": "Encerrar parties automaticamente",
        "auto_close_after": "Encerrar após",
        "reminders": "Lembretes automáticos",
        "reminder_before": "Lembrar antes",
        "embed_color": "Cor do embed",
        "language": "Idioma",
        "timezone": "Fuso horário",
        "yes": "sim",
        "no": "não",
        "config_select_channel_party": "Escolha o canal onde os convites das parties serão enviados:",
        "config_select_channel_logs": "Escolha o canal de logs:",
        "config_select_channel_commands": "Escolha o canal onde o cargo Host pode usar /party hub:",
        "config_select_host_role": "Escolha o cargo que pode criar parties:",
        "config_select_staff_role": "Escolha o cargo da staff:",
        "back": "Voltar",
        "refresh": "Atualizar",
        "test_invites": "Testar convites",
        "test_logs": "Testar logs",
        "manual_id": "Usar ID manual",
        "channel_set": "Canal definido: {channel}",
        "role_set": "Cargo definido: {role}",
        "id_channel_numeric": "O ID do canal precisa ser numérico.",
        "id_role_numeric": "O ID do cargo precisa ser numérico.",
        "channel_not_found": "Não achei esse canal. Confira o ID e se o bot tem permissão para ver o canal.",
        "role_not_found": "Não achei esse cargo neste servidor. Confira o ID.",
        "channel_wrong_guild": "Esse canal não pertence a este servidor.",
        "color_changed": "Cor alterada para `{value}`.",
        "color_number": "A cor precisa ser um número decimal.",
        "color_range": "A cor precisa estar entre `0` e `16777215`.",
        "timezone_changed": "Fuso horário alterado para UTC{offset}.",
        "timezone_invalid": "Use um formato como `-3`, `+0`, `+2`, `-03:30` ou `+05:30`.",
        "language_changed": "Idioma alterado para **{language}**.",
        "test_invites_msg": "✅ Teste do canal de convites: se você está vendo isso, eu consigo enviar mensagens aqui.",
        "test_logs_msg": "✅ Teste de logs: canal configurado corretamente.",
        "test_sent": "Teste enviado em {channel}.",
        "test_no_channel": "Esse canal ainda não foi configurado.",
        "test_forbidden": "Achei o canal, mas não tenho permissão para enviar mensagens nele.",
        "staff_needed": "Você precisa ser staff ou ter **Gerenciar servidor** para usar essa configuração.",
        "hub_staff_needed": "Você precisa ser staff, ter **Gerenciar servidor** ou usar o cargo Host no canal permitido para criar o Hub.",
        "hub_command_channel_needed": "A staff precisa configurar o **Canal de comandos** antes do cargo Host poder usar `/party hub`.",
        "hub_wrong_channel": "Você só pode usar `/party hub` em {channel}.",
        "clean_staff_needed": "Só a staff pode limpar parties encerradas.",
        "hub_created": "Hub criado nesse canal: {url}",
        "hub_no_perm": "Não tenho permissão para enviar mensagem nesse canal.",
        "normal_text_channel_only": "Use esse comando em um canal de texto normal.",
        "config_command_desc": "Abre o painel de configuração do Party Bot neste servidor.",
        "clean_done": "Limpeza concluída. Removidas: **{count}** parties encerradas.",
        "party_reminder": "⏰ A party **{title}** começa {relative}!\n{mentions}\n{url}",
        "party_auto_closed_end": "🔒 A party **{title}** foi encerrada automaticamente porque o horário terminou.",
        "party_auto_closed_timeout": "🔒 A party **{title}** foi encerrada automaticamente por tempo ativo excedido.",
        "log_party_auto_closed": "🔒 Party **{title}** `{party_id}` encerrada automaticamente.",
    },
    "en-US": {
        "hub_title": "🎮 Party Hub — SPD",
        "hub_desc": (
            "Create and track party invites using the panel below.\n\n"
            "**🎮 Create Party** — opens the invite form.\n"
            "**📋 View Parties** — shows open parties.\n"
            "**👤 My Parties** — shows where you are participating.\n"
            "**❓ Help** — explains the system."
        ),
        "party_channel": "📢 Invite channel",
        "party_channel_ok": "Parties created here will be sent to {channel}.",
        "config_pending": "⚠️ Setup pending",
        "config_pending_desc": "Staff still needs to configure the invite channel.",
        "hub_footer": "Use /party config to configure the bot",
        "create_party": "Create Party",
        "list_parties": "View Parties",
        "my_parties": "My Parties",
        "help": "Help",
        "use_inside_server": "Use this inside a server.",
        "no_perm_create": "You do not have permission to create parties.\nRequired role: {required}.",
        "no_party_channel": "The invite channel has not been configured yet.\nStaff needs to use `/party config`.",
        "no_open_parties": "There are no open parties right now.",
        "not_in_party": "You are not in any open party.",
        "help_text": (
            "**How it works:**\n\n"
            "1. Click **🎮 Create Party**.\n"
            "2. Fill title, slots, time, description and image.\n"
            "3. The invite appears in the configured channel.\n"
            "4. Members click ✅, ❔ or ❌.\n"
            "5. If **Going** is full, the next ✅ clicks join the queue.\n"
            "6. Host or staff uses **⚙️ Manage** to edit or close.\n\n"
            "Who can create parties: {host_text}."
        ),
        "everyone": "everyone",
        "host_role_required": "Host role configured by staff",
        "modal_create_title": "Create Party",
        "modal_edit_title": "Edit Party",
        "party_title_label": "Party title",
        "party_title_placeholder": "Ex: Lego Party - 4 Players",
        "capacity_label": "Slots",
        "capacity_placeholder": "Ex: 4",
        "time_label": "Time",
        "time_placeholder": "Ex: today 18:30 - 20:30 or 05/08/2026 18:30",
        "desc_label": "Description",
        "desc_placeholder": "Ex: Let's play LEGO Party!",
        "image_label": "Image link",
        "image_placeholder": "Ex: https://site.com/image.png",
        "capacity_number": "The **Slots** field must be a number.",
        "capacity_range": "Slots must be between **1** and **25**.",
        "image_invalid": "The image link must start with `http://` or `https://`.",
        "party_channel_not_found": "Invite channel not found.\nStaff needs to use `/party config`.",
        "party_channel_no_perm": "I found the invite channel, but I do not have permission to send messages there.",
        "party_create_error": "Error creating party: `{error}`",
        "party_created": "Party created in {channel}: {url}",
        "log_party_created": "🎮 {user} created party **{title}** `{party_id}` in {channel}.",
        "time_parse_warning": "\n⚠️ I could not parse the time automatically. It was saved as text.",
        "party_missing": "This party no longer exists.",
        "only_host_staff_edit": "Only the host or staff can edit this party.",
        "only_host_staff_manage": "Only the host or staff can manage this party.",
        "only_host_staff_close": "Only the host or staff can close this party.",
        "party_edited": "Party edited successfully.",
        "party_closed": "Party closed.",
        "party_already_closed": "This party is already closed.",
        "manage_party": "⚙️ Manage Party",
        "manage_desc": "Party: **{title}**\nID: `{party_id}`\n\nChoose an action below.",
        "edit_party": "Edit Party",
        "close_party": "Close Party",
        "party_identify_fail": "I could not identify this party.",
        "party_db_missing": "This party no longer exists in the database.",
        "party_closed_click": "This party has already been closed.",
        "already_going": "You already marked **Going**.",
        "already_maybe": "You already marked **Maybe**.",
        "already_no": "You already marked **Not going**.",
        "marked_going": "You marked **Going**.",
        "marked_maybe": "You marked **Maybe**.",
        "marked_no": "You marked **Not going**.",
        "queue_joined": "The party is full. You joined the **queue**.",
        "promoted": "\n{user} was promoted from the queue.",
        "btn_going": "Going",
        "btn_maybe": "Maybe",
        "btn_no": "Not going",
        "btn_manage": "Manage",
        "field_time": "Time",
        "field_status": "Status",
        "field_host": "Host",
        "field_queue": "📋 Queue ({count})",
        "going_field": "✅ Going ({current}/{capacity})",
        "maybe_field": "❔ Maybe ({current}/{capacity})",
        "no_field": "❌ Not going ({current})",
        "status_open": "🟢 Open",
        "status_closed": "🔴 Closed",
        "created_by": "Created by {name} • Party ID: {party_id}",
        "starts": "Starts {relative}",
        "started": "Started {relative}",
        "ends": "Ends {relative}",
        "ended": "Ended {relative}",
        "duration": "Duration: {duration}",
        "active_since": "Active since {relative}",
        "created_relative": "Created {relative}",
        "config_title": "⚙️ Party Bot Configuration",
        "config_desc": "Check the current setup below. Use the buttons to change settings by category.",
        "config_footer": "This panel is only visible to you",
        "section_channels": "📢 Channels",
        "section_roles": "🎭 Roles",
        "section_behavior": "⚙️ Behavior",
        "section_appearance": "🎨 Appearance and language",
        "section_status": "🩺 Diagnostics",
        "not_defined": "not defined",
        "ok": "✅ OK",
        "warn": "⚠️ Warning",
        "bad": "❌ Problem",
        "channel_invites": "Invite channel",
        "channel_logs": "Log channel",
        "channel_commands": "Command channel",
        "role_host": "Host role",
        "role_staff": "Staff role",
        "everyone_create": "Everyone can create parties",
        "ping_everyone": "Mention @everyone on creation",
        "auto_close": "Automatically close parties",
        "auto_close_after": "Close after",
        "reminders": "Automatic reminders",
        "reminder_before": "Remind before",
        "embed_color": "Embed color",
        "language": "Language",
        "timezone": "Timezone",
        "yes": "yes",
        "no": "no",
        "config_select_channel_party": "Choose where party invites will be sent:",
        "config_select_channel_logs": "Choose the log channel:",
        "config_select_channel_commands": "Choose the channel where the Host role can use /party hub:",
        "config_select_host_role": "Choose the role that can create parties:",
        "config_select_staff_role": "Choose the staff role:",
        "back": "Back",
        "refresh": "Refresh",
        "test_invites": "Test invites",
        "test_logs": "Test logs",
        "manual_id": "Use manual ID",
        "channel_set": "Channel set: {channel}",
        "role_set": "Role set: {role}",
        "id_channel_numeric": "The channel ID must be numeric.",
        "id_role_numeric": "The role ID must be numeric.",
        "channel_not_found": "I could not find this channel. Check the ID and my permissions.",
        "role_not_found": "I could not find this role in this server. Check the ID.",
        "channel_wrong_guild": "This channel does not belong to this server.",
        "color_changed": "Color changed to `{value}`.",
        "color_number": "The color must be a decimal number.",
        "color_range": "The color must be between `0` and `16777215`.",
        "timezone_changed": "Timezone changed to UTC{offset}.",
        "timezone_invalid": "Use a format like `-3`, `+0`, `+2`, `-03:30` or `+05:30`.",
        "language_changed": "Language changed to **{language}**.",
        "test_invites_msg": "✅ Invite channel test: if you see this, I can send messages here.",
        "test_logs_msg": "✅ Log test: channel configured correctly.",
        "test_sent": "Test sent in {channel}.",
        "test_no_channel": "This channel is not configured yet.",
        "test_forbidden": "I found the channel, but I cannot send messages there.",
        "staff_needed": "You need to be staff or have **Manage Server** to use this setting.",
        "hub_staff_needed": "You need to be staff, have **Manage Server**, or use the Host role in the allowed channel to create the Hub.",
        "hub_command_channel_needed": "Staff needs to configure the **Command channel** before the Host role can use `/party hub`.",
        "hub_wrong_channel": "You can only use `/party hub` in {channel}.",
        "clean_staff_needed": "Only staff can clean closed parties.",
        "hub_created": "Hub created in this channel: {url}",
        "hub_no_perm": "I do not have permission to send messages in this channel.",
        "normal_text_channel_only": "Use this command in a normal text channel.",
        "config_command_desc": "Open this server's Party Bot configuration panel.",
        "clean_done": "Cleanup complete. Removed **{count}** closed parties.",
        "party_reminder": "⏰ Party **{title}** starts {relative}!\n{mentions}\n{url}",
        "party_auto_closed_end": "🔒 Party **{title}** was automatically closed because its scheduled time ended.",
        "party_auto_closed_timeout": "🔒 Party **{title}** was automatically closed because it has been active for too long.",
        "log_party_auto_closed": "🔒 Party **{title}** `{party_id}` was automatically closed.",
    },
}


def lang_for_guild(guild_id: Optional[int]) -> str:
    if not guild_id:
        return "pt-BR"
    value = get_guild_config(guild_id).get("language", "pt-BR")
    return value if value in I18N else "pt-BR"


def tr(guild_id: Optional[int], key: str, **kwargs) -> str:
    lang = lang_for_guild(guild_id)
    text = I18N.get(lang, I18N["pt-BR"]).get(key, I18N["pt-BR"].get(key, key))
    try:
        return text.format(**kwargs)
    except Exception:
        return text


# ============================================================
# Config / persistência
# ============================================================


def normalize_parties():
    """Migra parties antigas para o formato interno atual sem quebrar o bot."""
    changed = False

    for party_id, data in list(parties.items()):
        if not isinstance(data, dict):
            parties.pop(party_id, None)
            changed = True
            continue

        aliases = {
            "accepted": ["Aceitou", "Vou"],
            "tentative": ["Talvez"],
            "declined": ["Recusou", "Negou", "Não vou", "Nao vou"],
            "capacity": ["Capacidade", "Vagas"],
        }

        for canonical, old_names in aliases.items():
            if canonical in data:
                continue
            for old_name in old_names:
                if old_name in data:
                    data[canonical] = data.pop(old_name)
                    changed = True
                    break

        for list_key in ("accepted", "tentative", "declined", "queue"):
            if list_key not in data or not isinstance(data.get(list_key), list):
                data[list_key] = []
                changed = True

        for int_key in ("start_ts", "end_ts", "created_ts"):
            if int_key in data and data[int_key] in ("", None):
                data[int_key] = 0
                changed = True

        if not data.get("created_ts"):
            data["created_ts"] = int(datetime.now(timezone.utc).timestamp())
            changed = True

        data.setdefault("status", "open")
        data.setdefault("capacity", 4)
        data.setdefault("title", "Party")
        data.setdefault("description", "")
        data.setdefault("time", "")
        data.setdefault("image_url", "")
        if "reminder_sent" not in data:
            data["reminder_sent"] = False
            changed = True

    if changed:
        save_json(PARTIES_PATH, parties)


normalize_parties()

TOKEN = os.getenv("DISCORD_TOKEN") or config.get("token")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
_commands_synced = False
FORCE_COMMAND_RESET = os.getenv("FORCE_COMMAND_RESET", "0").strip().lower() in {"1", "true", "yes", "sim"}


def save_config():
    save_json(CONFIG_PATH, config)


def save_parties():
    save_json(PARTIES_PATH, parties)


def get_guild_config(guild_id: Optional[int]) -> Dict[str, Any]:
    if not guild_id:
        return deepcopy(DEFAULT_GUILD_CONFIG)

    guild_key = str(guild_id)
    guilds = config.setdefault("guilds", {})

    if guild_key not in guilds:
        guilds[guild_key] = deepcopy(DEFAULT_GUILD_CONFIG)
        save_config()

    guild_conf = guilds[guild_key]
    changed = False
    for key, value in DEFAULT_GUILD_CONFIG.items():
        if key not in guild_conf:
            guild_conf[key] = deepcopy(value)
            changed = True

    if changed:
        save_config()

    return guild_conf


def set_guild_config_value(guild_id: int, key: str, value: Any):
    guild_conf = get_guild_config(guild_id)
    guild_conf[key] = value
    save_config()


def guild_color(guild_id: Optional[int]) -> int:
    try:
        return int(get_guild_config(guild_id).get("embed_color", 16766720))
    except (ValueError, TypeError):
        return 16766720


def guild_tz(guild_id: Optional[int]) -> timezone:
    minutes = int(get_guild_config(guild_id).get("timezone_offset_minutes", -180) or 0)
    return timezone(timedelta(minutes=minutes))


def guild_id_from_interaction(interaction: discord.Interaction) -> Optional[int]:
    return int(interaction.guild_id) if interaction.guild_id else None


# ============================================================
# Permissões / utilitários
# ============================================================


def member_has_role(member: discord.Member, role_id: int) -> bool:
    if not role_id:
        return False
    return any(role.id == role_id for role in member.roles)


def is_staff(member: discord.Member) -> bool:
    guild_conf = get_guild_config(member.guild.id)
    staff_role_id = int(guild_conf.get("staff_role_id", 0) or 0)
    return member.guild_permissions.manage_guild or member_has_role(member, staff_role_id)


def is_host(member: discord.Member) -> bool:
    guild_conf = get_guild_config(member.guild.id)
    host_role_id = int(guild_conf.get("host_role_id", 0) or 0)
    return member_has_role(member, host_role_id)


def interaction_member_is_staff(interaction: discord.Interaction) -> bool:
    return isinstance(interaction.user, discord.Member) and is_staff(interaction.user)


async def reject_if_not_staff(interaction: discord.Interaction) -> bool:
    if not interaction.guild or not interaction_member_is_staff(interaction):
        if not interaction.response.is_done():
            await interaction.response.send_message(tr(guild_id_from_interaction(interaction), "staff_needed"), ephemeral=True)
        return True
    return False


def can_create_party(member: discord.Member) -> bool:
    guild_conf = get_guild_config(member.guild.id)
    host_role_id = int(guild_conf.get("host_role_id", 0) or 0)
    staff_role_id = int(guild_conf.get("staff_role_id", 0) or 0)
    everyone_can_create = bool(guild_conf.get("everyone_can_create", False))

    return (
        everyone_can_create
        or member.guild_permissions.manage_guild
        or member_has_role(member, host_role_id)
        or member_has_role(member, staff_role_id)
    )


def can_manage_party(member: discord.Member, party_data: Dict[str, Any]) -> bool:
    return member.id == int(party_data.get("host_id", 0)) or is_staff(member)


def find_party_by_message(message_id: int) -> Optional[str]:
    for party_id, data in parties.items():
        if int(data.get("message_id", 0)) == int(message_id):
            return party_id
    return None


def clean_user_from_party(data: Dict[str, Any], user_id: int):
    for key in ("accepted", "tentative", "declined", "queue"):
        if user_id in data.get(key, []):
            data[key].remove(user_id)


def short_mentions(user_ids, empty="—"):
    if not user_ids:
        return empty

    mentions = [f"<@{user_id}>" for user_id in user_ids[:8]]
    extra = len(user_ids) - 8
    if extra > 0:
        mentions.append(f"+{extra}")

    return "\n".join(mentions)


def mention_list(user_ids):
    if not user_ids:
        return "—"

    lines = []
    for index, user_id in enumerate(user_ids[:15], start=1):
        lines.append(f"{index}. <@{user_id}>")

    extra = len(user_ids) - 15
    if extra > 0:
        lines.append(f"... e mais {extra}")

    return "\n".join(lines)


def promote_from_queue(data: Dict[str, Any]) -> Optional[int]:
    capacity = int(data.get("capacity", 4))

    if len(data.get("accepted", [])) >= capacity:
        return None

    queue = data.get("queue", [])
    if not queue:
        return None

    promoted_user = queue.pop(0)
    data["accepted"].append(promoted_user)
    return promoted_user


async def fetch_messageable_channel(channel_id: int):
    if not channel_id:
        return None

    channel = bot.get_channel(channel_id)
    if channel and hasattr(channel, "send"):
        return channel

    try:
        fetched = await bot.fetch_channel(channel_id)
    except discord.HTTPException:
        return None

    if fetched and hasattr(fetched, "send"):
        return fetched

    return None


async def log_action(guild: Optional[discord.Guild], text: str):
    if not guild:
        return

    guild_conf = get_guild_config(guild.id)
    log_channel_id = int(guild_conf.get("log_channel_id", 0) or 0)
    if not log_channel_id:
        return

    channel = await fetch_messageable_channel(log_channel_id)
    if not channel:
        return

    try:
        await channel.send(text)
    except discord.HTTPException:
        pass


def discord_relative(ts: int) -> str:
    return f"<t:{int(ts)}:R>"


def discord_full(ts: int) -> str:
    return f"<t:{int(ts)}:F>"


def format_duration(seconds: int, guild_id: Optional[int]) -> str:
    lang = lang_for_guild(guild_id)
    seconds = max(0, int(seconds))
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24
    hours = hours % 24
    minutes = minutes % 60

    if lang == "en-US":
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes or not parts:
            parts.append(f"{minutes}m")
        return " ".join(parts)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}min")
    return " ".join(parts)


def parse_timezone_offset(text: str) -> Optional[int]:
    cleaned = text.strip().upper().replace("UTC", "")
    match = re.fullmatch(r"([+-]?)(\d{1,2})(?::?(\d{2}))?", cleaned)
    if not match:
        return None

    sign_raw, hour_raw, minute_raw = match.groups()
    hours = int(hour_raw)
    minutes = int(minute_raw or 0)
    if hours > 14 or minutes > 59:
        return None
    sign = -1 if sign_raw == "-" else 1
    return sign * (hours * 60 + minutes)


def format_timezone_offset(minutes: int) -> str:
    sign = "+" if minutes >= 0 else "-"
    total = abs(int(minutes))
    h = total // 60
    m = total % 60
    if m:
        return f"{sign}{h:02d}:{m:02d}"
    return f"{sign}{h}"


def parse_party_time(raw: str, guild_id: Optional[int]) -> Tuple[str, int, int, bool]:
    """
    Interpreta formatos simples:
    - hoje 18:30
    - amanhã 19:00 - 21:00
    - 08/05/2026 18:30
    - 08/05/2026 18:30 - 20:30
    - 08/05/2026 18:30 - 09/05/2026 01:00

    Retorna: (texto_original, start_ts, end_ts, parsed)
    """
    text = (raw or "").strip()
    if not text:
        return "", 0, 0, False

    tz = guild_tz(guild_id)
    now_local = datetime.now(tz)
    lowered = text.lower().strip()

    # Separador de intervalo. Evita quebrar datas por hífen porque usamos dd/mm/yyyy.
    start_part = text
    end_part = ""
    if " - " in text:
        start_part, end_part = text.split(" - ", 1)
    elif " às " in lowered:
        parts = re.split(r"\s+às\s+", text, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            start_part, end_part = parts

    start_part = start_part.strip()
    end_part = end_part.strip()

    def parse_start(part: str) -> Optional[datetime]:
        p = part.strip().lower()
        date_base = None

        if p.startswith(("hoje ", "today ")):
            date_base = now_local.date()
            p = re.sub(r"^(hoje|today)\s+", "", p, flags=re.IGNORECASE)
        elif p.startswith(("amanhã ", "amanha ", "tomorrow ")):
            date_base = (now_local + timedelta(days=1)).date()
            p = re.sub(r"^(amanhã|amanha|tomorrow)\s+", "", p, flags=re.IGNORECASE)

        # dd/mm/yyyy hh:mm ou dd/mm hh:mm
        match = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\s+(\d{1,2}):(\d{2})", p)
        if match:
            day, month, year, hour, minute = match.groups()
            year_int = int(year) if year else now_local.year
            if year_int < 100:
                year_int += 2000
            try:
                return datetime(year_int, int(month), int(day), int(hour), int(minute), tzinfo=tz)
            except ValueError:
                return None

        # yyyy-mm-dd hh:mm
        match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})", p)
        if match:
            year, month, day, hour, minute = match.groups()
            try:
                return datetime(int(year), int(month), int(day), int(hour), int(minute), tzinfo=tz)
            except ValueError:
                return None

        # somente hh:mm: assume hoje, ou data_base se veio hoje/amanhã
        match = re.search(r"(\d{1,2}):(\d{2})", p)
        if match:
            hour, minute = match.groups()
            base = date_base or now_local.date()
            try:
                dt = datetime(base.year, base.month, base.day, int(hour), int(minute), tzinfo=tz)
                # Se o usuário digitou só hora e já passou muito, assume amanhã.
                if date_base is None and dt < now_local - timedelta(hours=2):
                    dt += timedelta(days=1)
                return dt
            except ValueError:
                return None

        return None

    def parse_end(part: str, start_dt: datetime) -> Optional[datetime]:
        if not part:
            return None
        parsed = parse_start(part)
        if parsed:
            # Se o fim tem só hora, parse_start pode assumir hoje. Ajusta para dia do início.
            if not re.search(r"\d{1,2}/\d{1,2}|\d{4}-\d{1,2}-\d{1,2}|amanh|tomorrow|today|hoje", part, re.I):
                parsed = parsed.replace(year=start_dt.year, month=start_dt.month, day=start_dt.day)
            if parsed <= start_dt:
                parsed += timedelta(days=1)
            return parsed
        return None

    start_dt = parse_start(start_part)
    if not start_dt:
        return text, 0, 0, False

    end_dt = parse_end(end_part, start_dt) if end_part else None
    return text, int(start_dt.timestamp()), int(end_dt.timestamp()) if end_dt else 0, True


def time_status_lines(data: Dict[str, Any], guild_id: Optional[int]) -> str:
    raw = data.get("time") or ""
    start_ts = int(data.get("start_ts", 0) or 0)
    end_ts = int(data.get("end_ts", 0) or 0)
    created_ts = int(data.get("created_ts", 0) or 0)
    now_ts = int(datetime.now(timezone.utc).timestamp())

    lines = []
    if raw:
        lines.append(raw)
    if start_ts:
        lines.append(discord_full(start_ts))
        if now_ts < start_ts:
            lines.append(tr(guild_id, "starts", relative=discord_relative(start_ts)))
        else:
            lines.append(tr(guild_id, "started", relative=discord_relative(start_ts)))
    if end_ts:
        if now_ts < end_ts:
            lines.append(tr(guild_id, "ends", relative=discord_relative(end_ts)))
        else:
            lines.append(tr(guild_id, "ended", relative=discord_relative(end_ts)))
        if start_ts and end_ts > start_ts:
            lines.append(tr(guild_id, "duration", duration=format_duration(end_ts - start_ts, guild_id)))
    elif start_ts and now_ts >= start_ts:
        lines.append(tr(guild_id, "active_since", relative=discord_relative(start_ts)))
    elif created_ts and not start_ts:
        lines.append(tr(guild_id, "created_relative", relative=discord_relative(created_ts)))

    return "\n".join(lines) if lines else "—"


# ============================================================
# Embeds
# ============================================================


def make_hub_embed(guild_id: Optional[int]) -> discord.Embed:
    guild_conf = get_guild_config(guild_id)
    party_channel_id = int(guild_conf.get("party_channel_id", 0) or 0)

    embed = discord.Embed(
        title=tr(guild_id, "hub_title"),
        description=tr(guild_id, "hub_desc"),
        color=guild_color(guild_id),
    )

    if party_channel_id:
        embed.add_field(
            name=tr(guild_id, "party_channel"),
            value=tr(guild_id, "party_channel_ok", channel=f"<#{party_channel_id}>"),
            inline=False,
        )
    else:
        embed.add_field(
            name=tr(guild_id, "config_pending"),
            value=tr(guild_id, "config_pending_desc"),
            inline=False,
        )

    embed.set_footer(text=tr(guild_id, "hub_footer"))
    return embed


def make_party_embed(party_id: str) -> discord.Embed:
    data = parties[party_id]
    guild_id = int(data.get("guild_id", 0) or 0)

    title = data.get("title") or "Party"
    capacity = int(data.get("capacity", 4))
    accepted = data.get("accepted", [])
    tentative = data.get("tentative", [])
    declined = data.get("declined", [])
    queue = data.get("queue", [])
    status = data.get("status", "open")
    image_url = data.get("image_url", "")
    host_id = data.get("host_id")

    status_text = tr(guild_id, "status_open") if status == "open" else tr(guild_id, "status_closed")

    embed = discord.Embed(
        title=title,
        description=data.get("description") or None,
        color=guild_color(guild_id) if status == "open" else 0x555555,
    )

    if data.get("time") or data.get("start_ts") or data.get("created_ts"):
        embed.add_field(name=tr(guild_id, "field_time"), value=time_status_lines(data, guild_id), inline=False)

    embed.add_field(name=tr(guild_id, "going_field", current=len(accepted), capacity=capacity), value=short_mentions(accepted), inline=True)
    embed.add_field(name=tr(guild_id, "maybe_field", current=len(tentative), capacity=capacity), value=short_mentions(tentative), inline=True)
    embed.add_field(name=tr(guild_id, "no_field", current=len(declined)), value=short_mentions(declined), inline=True)

    if queue:
        embed.add_field(name=tr(guild_id, "field_queue", count=len(queue)), value=mention_list(queue), inline=False)

    embed.add_field(name=tr(guild_id, "field_status"), value=status_text, inline=True)
    embed.add_field(name=tr(guild_id, "field_host"), value=f"<@{host_id}>", inline=True)

    if image_url:
        embed.set_image(url=image_url)

    embed.set_footer(text=tr(guild_id, "created_by", name=data.get("host_name", "unknown"), party_id=party_id))
    return embed


async def update_party_message(party_id: str):
    data = parties.get(party_id)
    if not data:
        return

    channel = await fetch_messageable_channel(int(data.get("channel_id", 0) or 0))
    if not channel:
        return

    try:
        message = await channel.fetch_message(int(data["message_id"]))
        disabled = data.get("status") != "open"
        guild_id = int(data.get("guild_id", 0) or 0)
        await message.edit(embed=make_party_embed(party_id), view=PartyView(disabled=disabled, guild_id=guild_id))
    except discord.HTTPException:
        pass


# ============================================================
# Views do Hub e Party
# ============================================================


class HubView(discord.ui.View):
    def __init__(self, guild_id: Optional[int] = None):
        super().__init__(timeout=None)

        # Ajusta os labels do Hub conforme o idioma do servidor quando o Hub é criado/editado.
        # A instância registrada no on_ready continua sem guild_id apenas para manter os custom_id persistentes.
        self.create_party.label = tr(guild_id, "create_party")
        self.list_parties.label = tr(guild_id, "list_parties")
        self.my_parties.label = tr(guild_id, "my_parties")
        self.help_button.label = tr(guild_id, "help")

    @discord.ui.button(label="Criar Party", emoji="🎮", style=discord.ButtonStyle.success, custom_id="hub:create_party")
    async def create_party(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = guild_id_from_interaction(interaction)
        member = interaction.user
        if not interaction.guild or not isinstance(member, discord.Member):
            await interaction.response.send_message(tr(guild_id, "use_inside_server"), ephemeral=True)
            return

        if not can_create_party(member):
            guild_conf = get_guild_config(interaction.guild.id)
            host_role_id = int(guild_conf.get("host_role_id", 0) or 0)
            required = f"<@&{host_role_id}>" if host_role_id else tr(guild_id, "host_role_required")
            await interaction.response.send_message(tr(guild_id, "no_perm_create", required=required), ephemeral=True)
            return

        guild_conf = get_guild_config(interaction.guild.id)
        if not int(guild_conf.get("party_channel_id", 0) or 0):
            await interaction.response.send_message(tr(guild_id, "no_party_channel"), ephemeral=True)
            return

        await interaction.response.send_modal(CreatePartyModal(guild_id))

    @discord.ui.button(label="Ver Parties", emoji="📋", style=discord.ButtonStyle.primary, custom_id="hub:list_parties")
    async def list_parties(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = guild_id_from_interaction(interaction)
        open_parties = [
            (party_id, data)
            for party_id, data in parties.items()
            if data.get("status") == "open" and int(data.get("guild_id", 0) or 0) == guild_id
        ]

        if not open_parties:
            await interaction.response.send_message(tr(guild_id, "no_open_parties"), ephemeral=True)
            return

        lines = []
        for party_id, data in open_parties[:20]:
            accepted = len(data.get("accepted", []))
            capacity = data.get("capacity", 0)
            channel_id = data.get("channel_id")
            message_id = data.get("message_id")
            lines.append(
                f"🎮 **{data.get('title', 'Party')}** — `{accepted}/{capacity}` — "
                f"{tr(guild_id, 'field_host')}: <@{data.get('host_id')}> — "
                f"[abrir](https://discord.com/channels/{interaction.guild_id}/{channel_id}/{message_id})"
            )

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @discord.ui.button(label="Minhas Parties", emoji="👤", style=discord.ButtonStyle.secondary, custom_id="hub:my_parties")
    async def my_parties(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = guild_id_from_interaction(interaction)
        user_id = interaction.user.id
        found = []

        for party_id, data in parties.items():
            if data.get("status") != "open" or int(data.get("guild_id", 0) or 0) != guild_id:
                continue

            role = None
            if data.get("host_id") == user_id:
                role = tr(guild_id, "field_host")
            elif user_id in data.get("accepted", []):
                role = tr(guild_id, "btn_going")
            elif user_id in data.get("tentative", []):
                role = tr(guild_id, "btn_maybe")
            elif user_id in data.get("declined", []):
                role = tr(guild_id, "btn_no")
            elif user_id in data.get("queue", []):
                role = "Fila" if lang_for_guild(guild_id) == "pt-BR" else "Queue"

            if role:
                found.append((party_id, data, role))

        if not found:
            await interaction.response.send_message(tr(guild_id, "not_in_party"), ephemeral=True)
            return

        lines = []
        for party_id, data, role in found:
            channel_id = data.get("channel_id")
            message_id = data.get("message_id")
            lines.append(
                f"🎮 **{data.get('title', 'Party')}** — {role} — "
                f"[abrir](https://discord.com/channels/{interaction.guild_id}/{channel_id}/{message_id})"
            )

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @discord.ui.button(label="Ajuda", emoji="❓", style=discord.ButtonStyle.secondary, custom_id="hub:help")
    async def help_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = guild_id_from_interaction(interaction)
        guild_conf = get_guild_config(guild_id)
        host_role_id = int(guild_conf.get("host_role_id", 0) or 0)
        host_text = tr(guild_id, "everyone") if guild_conf.get("everyone_can_create") else (f"<@&{host_role_id}>" if host_role_id else tr(guild_id, "host_role_required"))
        await interaction.response.send_message(tr(guild_id, "help_text", host_text=host_text), ephemeral=True)


class CreatePartyModal(discord.ui.Modal):
    def __init__(self, guild_id: Optional[int]):
        super().__init__(title=tr(guild_id, "modal_create_title"))
        self.guild_id = guild_id
        self.title_input = discord.ui.TextInput(label=tr(guild_id, "party_title_label"), placeholder=tr(guild_id, "party_title_placeholder"), max_length=100, required=True)
        self.capacity = discord.ui.TextInput(label=tr(guild_id, "capacity_label"), placeholder=tr(guild_id, "capacity_placeholder"), max_length=2, required=True)
        self.time = discord.ui.TextInput(label=tr(guild_id, "time_label"), placeholder=tr(guild_id, "time_placeholder"), max_length=120, required=False)
        self.description = discord.ui.TextInput(label=tr(guild_id, "desc_label"), placeholder=tr(guild_id, "desc_placeholder"), style=discord.TextStyle.paragraph, max_length=500, required=False)
        self.image_url = discord.ui.TextInput(label=tr(guild_id, "image_label"), placeholder=tr(guild_id, "image_placeholder"), max_length=300, required=False)
        self.add_item(self.title_input)
        self.add_item(self.capacity)
        self.add_item(self.time)
        self.add_item(self.description)
        self.add_item(self.image_url)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = guild_id_from_interaction(interaction)
        member = interaction.user

        if not interaction.guild or not isinstance(member, discord.Member):
            await interaction.followup.send(tr(guild_id, "use_inside_server"), ephemeral=True)
            return

        if not can_create_party(member):
            await interaction.followup.send(tr(guild_id, "no_perm_create", required=tr(guild_id, "host_role_required")), ephemeral=True)
            return

        try:
            capacity_value = int(str(self.capacity.value).strip())
        except ValueError:
            await interaction.followup.send(tr(guild_id, "capacity_number"), ephemeral=True)
            return

        if capacity_value < 1 or capacity_value > 25:
            await interaction.followup.send(tr(guild_id, "capacity_range"), ephemeral=True)
            return

        image = str(self.image_url.value).strip()
        if image and not image.lower().startswith(("http://", "https://")):
            await interaction.followup.send(tr(guild_id, "image_invalid"), ephemeral=True)
            return

        guild_conf = get_guild_config(interaction.guild.id)
        channel = await fetch_messageable_channel(int(guild_conf.get("party_channel_id", 0) or 0))
        if not channel:
            await interaction.followup.send(tr(guild_id, "party_channel_not_found"), ephemeral=True)
            return

        time_text, start_ts, end_ts, parsed_time = parse_party_time(str(self.time.value), guild_id)

        party_id = uuid.uuid4().hex[:8]
        parties[party_id] = {
            "id": party_id,
            "guild_id": interaction.guild_id,
            "channel_id": channel.id,
            "message_id": 0,
            "host_id": member.id,
            "host_name": member.display_name,
            "title": str(self.title_input.value).strip(),
            "capacity": capacity_value,
            "time": time_text,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "created_ts": int(datetime.now(timezone.utc).timestamp()),
            "reminder_sent": False,
            "description": str(self.description.value).strip(),
            "image_url": image,
            "accepted": [member.id],
            "tentative": [],
            "declined": [],
            "queue": [],
            "status": "open",
        }

        ping_everyone = bool(guild_conf.get("ping_everyone", True))
        content = "@everyone" if ping_everyone else None
        allowed_mentions = discord.AllowedMentions(everyone=ping_everyone)

        try:
            message = await channel.send(content=content, embed=make_party_embed(party_id), view=PartyView(guild_id=interaction.guild.id), allowed_mentions=allowed_mentions)
        except discord.Forbidden:
            parties.pop(party_id, None)
            save_parties()
            await interaction.followup.send(tr(guild_id, "party_channel_no_perm"), ephemeral=True)
            return
        except discord.HTTPException as error:
            parties.pop(party_id, None)
            save_parties()
            await interaction.followup.send(tr(guild_id, "party_create_error", error=error), ephemeral=True)
            return

        parties[party_id]["message_id"] = message.id
        save_parties()

        extra = "" if parsed_time or not time_text else tr(guild_id, "time_parse_warning")
        await interaction.followup.send(tr(guild_id, "party_created", channel=channel.mention, url=message.jump_url) + extra, ephemeral=True)
        await log_action(interaction.guild, tr(guild_id, "log_party_created", user=f"<@{member.id}>", title=parties[party_id]["title"], party_id=party_id, channel=channel.mention))


class EditPartyModal(discord.ui.Modal):
    def __init__(self, party_id: str):
        data = parties[party_id]
        self.party_id = party_id
        self.guild_id = int(data.get("guild_id", 0) or 0)
        super().__init__(title=tr(self.guild_id, "modal_edit_title"))

        self.title_input = discord.ui.TextInput(label=tr(self.guild_id, "party_title_label"), default=data.get("title", ""), max_length=100, required=True)
        self.capacity = discord.ui.TextInput(label=tr(self.guild_id, "capacity_label"), default=str(data.get("capacity", 4)), max_length=2, required=True)
        self.time = discord.ui.TextInput(label=tr(self.guild_id, "time_label"), default=data.get("time", ""), max_length=120, required=False)
        self.description = discord.ui.TextInput(label=tr(self.guild_id, "desc_label"), default=data.get("description", ""), style=discord.TextStyle.paragraph, max_length=500, required=False)
        self.image_url = discord.ui.TextInput(label=tr(self.guild_id, "image_label"), default=data.get("image_url", ""), max_length=300, required=False)

        self.add_item(self.title_input)
        self.add_item(self.capacity)
        self.add_item(self.time)
        self.add_item(self.description)
        self.add_item(self.image_url)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = guild_id_from_interaction(interaction)
        data = parties.get(self.party_id)
        if not data:
            await interaction.followup.send(tr(guild_id, "party_missing"), ephemeral=True)
            return

        member = interaction.user
        if not isinstance(member, discord.Member) or not can_manage_party(member, data):
            await interaction.followup.send(tr(guild_id, "only_host_staff_edit"), ephemeral=True)
            return

        try:
            capacity_value = int(str(self.capacity.value).strip())
        except ValueError:
            await interaction.followup.send(tr(guild_id, "capacity_number"), ephemeral=True)
            return

        if capacity_value < 1 or capacity_value > 25:
            await interaction.followup.send(tr(guild_id, "capacity_range"), ephemeral=True)
            return

        image = str(self.image_url.value).strip()
        if image and not image.lower().startswith(("http://", "https://")):
            await interaction.followup.send(tr(guild_id, "image_invalid"), ephemeral=True)
            return

        time_text, start_ts, end_ts, parsed_time = parse_party_time(str(self.time.value), guild_id)

        data["title"] = str(self.title_input.value).strip()
        data["capacity"] = capacity_value
        data["time"] = time_text
        data["start_ts"] = start_ts
        data["end_ts"] = end_ts
        data["reminder_sent"] = False if start_ts else data.get("reminder_sent", False)
        data["description"] = str(self.description.value).strip()
        data["image_url"] = image

        while len(data.get("accepted", [])) > capacity_value:
            moved = data["accepted"].pop()
            data["queue"].insert(0, moved)

        save_parties()
        await update_party_message(self.party_id)
        extra = "" if parsed_time or not time_text else tr(guild_id, "time_parse_warning")
        await interaction.followup.send(tr(guild_id, "party_edited") + extra, ephemeral=True)
        await log_action(interaction.guild, f"✏️ <@{member.id}> editou a party **{data['title']}** `{self.party_id}`.")


class ManagePartyView(discord.ui.View):
    def __init__(self, party_id: str):
        super().__init__(timeout=180)
        self.party_id = party_id
        guild_id = int(parties.get(party_id, {}).get("guild_id", 0) or 0)
        self.edit_party.label = tr(guild_id, "edit_party")
        self.close_party.label = tr(guild_id, "close_party")

    @discord.ui.button(label="Editar Party", emoji="✏️", style=discord.ButtonStyle.primary)
    async def edit_party(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = guild_id_from_interaction(interaction)
        data = parties.get(self.party_id)
        if not data:
            await interaction.response.send_message(tr(guild_id, "party_missing"), ephemeral=True)
            return

        member = interaction.user
        if not isinstance(member, discord.Member) or not can_manage_party(member, data):
            await interaction.response.send_message(tr(guild_id, "only_host_staff_edit"), ephemeral=True)
            return

        await interaction.response.send_modal(EditPartyModal(self.party_id))

    @discord.ui.button(label="Encerrar Party", emoji="🔒", style=discord.ButtonStyle.danger)
    async def close_party(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = guild_id_from_interaction(interaction)
        data = parties.get(self.party_id)
        if not data:
            await interaction.response.send_message(tr(guild_id, "party_missing"), ephemeral=True)
            return

        member = interaction.user
        if not isinstance(member, discord.Member) or not can_manage_party(member, data):
            await interaction.response.send_message(tr(guild_id, "only_host_staff_close"), ephemeral=True)
            return

        if data.get("status") == "closed":
            await interaction.response.send_message(tr(guild_id, "party_already_closed"), ephemeral=True)
            return

        data["status"] = "closed"
        save_parties()
        await update_party_message(self.party_id)
        await interaction.response.send_message(tr(guild_id, "party_closed"), ephemeral=True)
        await log_action(interaction.guild, f"🔒 <@{member.id}> encerrou a party **{data['title']}** `{self.party_id}`.")


class PartyView(discord.ui.View):
    def __init__(self, disabled: bool = False, guild_id: Optional[int] = None):
        super().__init__(timeout=None)

        # Ajusta os labels dos botões conforme o idioma do servidor quando a mensagem é criada/editada.
        # A instância registrada no on_ready continua sem guild_id apenas para manter os custom_id persistentes.
        self.accepted_button.label = tr(guild_id, "btn_going")
        self.tentative_button.label = tr(guild_id, "btn_maybe")
        self.declined_button.label = tr(guild_id, "btn_no")
        self.manage_button.label = tr(guild_id, "btn_manage")

        if disabled:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True

    async def get_party(self, interaction: discord.Interaction) -> Optional[str]:
        guild_id = guild_id_from_interaction(interaction)
        if not interaction.message:
            await interaction.response.send_message(tr(guild_id, "party_identify_fail"), ephemeral=True)
            return None

        party_id = find_party_by_message(interaction.message.id)
        if not party_id or party_id not in parties:
            await interaction.response.send_message(tr(guild_id, "party_db_missing"), ephemeral=True)
            return None
        return party_id

    @discord.ui.button(emoji="✅", label="Vou", style=discord.ButtonStyle.success, custom_id="party:accepted")
    async def accepted_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = guild_id_from_interaction(interaction)
        party_id = await self.get_party(interaction)
        if not party_id:
            return

        data = parties[party_id]
        if data.get("status") != "open":
            await interaction.response.send_message(tr(guild_id, "party_closed_click"), ephemeral=True)
            return

        user_id = interaction.user.id
        capacity = int(data.get("capacity", 4))
        if user_id in data.get("accepted", []):
            await interaction.response.send_message(tr(guild_id, "already_going"), ephemeral=True)
            return

        clean_user_from_party(data, user_id)
        if len(data["accepted"]) < capacity:
            data["accepted"].append(user_id)
            msg = tr(guild_id, "marked_going")
            log_msg = f"✅ <@{user_id}> marcou Vou na party **{data['title']}** `{party_id}`."
        else:
            data["queue"].append(user_id)
            msg = tr(guild_id, "queue_joined")
            log_msg = f"📋 <@{user_id}> entrou na fila da party **{data['title']}** `{party_id}`."

        save_parties()
        await interaction.response.send_message(msg, ephemeral=True)
        await log_action(interaction.guild, log_msg)
        await update_party_message(party_id)

    @discord.ui.button(emoji="❔", label="Talvez", style=discord.ButtonStyle.primary, custom_id="party:tentative")
    async def tentative_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = guild_id_from_interaction(interaction)
        party_id = await self.get_party(interaction)
        if not party_id:
            return

        data = parties[party_id]
        if data.get("status") != "open":
            await interaction.response.send_message(tr(guild_id, "party_closed_click"), ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in data.get("tentative", []):
            await interaction.response.send_message(tr(guild_id, "already_maybe"), ephemeral=True)
            return

        was_accepted = user_id in data.get("accepted", [])
        clean_user_from_party(data, user_id)
        data["tentative"].append(user_id)
        promoted = promote_from_queue(data) if was_accepted else None
        save_parties()

        msg = tr(guild_id, "marked_maybe")
        if promoted:
            msg += tr(guild_id, "promoted", user=f"<@{promoted}>")

        await interaction.response.send_message(msg, ephemeral=True)
        await log_action(interaction.guild, f"❔ <@{user_id}> marcou Talvez na party **{data['title']}** `{party_id}`.")
        await update_party_message(party_id)

    @discord.ui.button(emoji="❌", label="Não vou", style=discord.ButtonStyle.danger, custom_id="party:declined")
    async def declined_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = guild_id_from_interaction(interaction)
        party_id = await self.get_party(interaction)
        if not party_id:
            return

        data = parties[party_id]
        if data.get("status") != "open":
            await interaction.response.send_message(tr(guild_id, "party_closed_click"), ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in data.get("declined", []):
            await interaction.response.send_message(tr(guild_id, "already_no"), ephemeral=True)
            return

        was_accepted = user_id in data.get("accepted", [])
        clean_user_from_party(data, user_id)
        data["declined"].append(user_id)
        promoted = promote_from_queue(data) if was_accepted else None
        save_parties()

        msg = tr(guild_id, "marked_no")
        if promoted:
            msg += tr(guild_id, "promoted", user=f"<@{promoted}>")

        await interaction.response.send_message(msg, ephemeral=True)
        await log_action(interaction.guild, f"❌ <@{user_id}> marcou Não vou na party **{data['title']}** `{party_id}`.")
        await update_party_message(party_id)

    @discord.ui.button(emoji="⚙️", label="Gerenciar", style=discord.ButtonStyle.secondary, custom_id="party:manage")
    async def manage_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = guild_id_from_interaction(interaction)
        party_id = await self.get_party(interaction)
        if not party_id:
            return

        data = parties[party_id]
        member = interaction.user
        if not isinstance(member, discord.Member) or not can_manage_party(member, data):
            await interaction.response.send_message(tr(guild_id, "only_host_staff_manage"), ephemeral=True)
            return

        embed = discord.Embed(
            title=tr(guild_id, "manage_party"),
            description=tr(guild_id, "manage_desc", title=data.get("title", "Party"), party_id=party_id),
            color=guild_color(guild_id),
        )
        await interaction.response.send_message(embed=embed, view=ManagePartyView(party_id), ephemeral=True)


# ============================================================
# Config panel
# ============================================================


async def channel_preview(guild: discord.Guild, channel_id: int, label: str, required_perms: Tuple[str, ...]) -> str:
    guild_id = guild.id
    if not channel_id:
        return f"**{label}:** `{tr(guild_id, 'not_defined')}` — {tr(guild_id, 'warn')}"

    channel = await fetch_messageable_channel(channel_id)
    if not channel:
        return f"**{label}:** <#{channel_id}> — {tr(guild_id, 'bad')}"

    me = guild.me or guild.get_member(bot.user.id)
    status = tr(guild_id, "ok")
    if me and hasattr(channel, "permissions_for"):
        perms = channel.permissions_for(me)
        missing = [perm for perm in required_perms if not getattr(perms, perm, False)]
        if missing:
            translated = ", ".join(missing)
            status = f"{tr(guild_id, 'warn')} (`{translated}`)"

    return f"**{label}:** {channel.mention} — {status}"


def role_preview(guild: discord.Guild, role_id: int, label: str) -> str:
    guild_id = guild.id
    if not role_id:
        return f"**{label}:** `{tr(guild_id, 'not_defined')}` — {tr(guild_id, 'warn')}"
    role = guild.get_role(role_id)
    if not role:
        return f"**{label}:** `<@&{role_id}>` — {tr(guild_id, 'bad')}"
    return f"**{label}:** {role.mention} — {tr(guild_id, 'ok')}"


async def make_config_embed(guild: discord.Guild) -> discord.Embed:
    guild_id = guild.id
    guild_conf = get_guild_config(guild_id)

    embed = discord.Embed(
        title=tr(guild_id, "config_title"),
        description=tr(guild_id, "config_desc"),
        color=guild_color(guild_id),
    )

    channels = [
        await channel_preview(guild, int(guild_conf.get("party_channel_id", 0) or 0), tr(guild_id, "channel_invites"), ("view_channel", "send_messages", "embed_links", "read_message_history")),
        await channel_preview(guild, int(guild_conf.get("log_channel_id", 0) or 0), tr(guild_id, "channel_logs"), ("view_channel", "send_messages", "read_message_history")),
        await channel_preview(guild, int(guild_conf.get("command_channel_id", 0) or 0), tr(guild_id, "channel_commands"), ("view_channel", "send_messages", "read_message_history")),
    ]
    embed.add_field(name=tr(guild_id, "section_channels"), value="\n".join(channels), inline=False)

    roles = [
        role_preview(guild, int(guild_conf.get("host_role_id", 0) or 0), tr(guild_id, "role_host")),
        role_preview(guild, int(guild_conf.get("staff_role_id", 0) or 0), tr(guild_id, "role_staff")),
    ]
    embed.add_field(name=tr(guild_id, "section_roles"), value="\n".join(roles), inline=False)

    yes = tr(guild_id, "yes")
    no = tr(guild_id, "no")
    auto_close_hours = int(guild_conf.get("auto_close_after_hours", 6) or 6)
    reminder_minutes = int(guild_conf.get("reminder_minutes", 15) or 15)
    behavior = (
        f"**{tr(guild_id, 'everyone_create')}:** `{'sim' if guild_conf.get('everyone_can_create') else 'não'}`\n"
        f"**{tr(guild_id, 'ping_everyone')}:** `{'sim' if guild_conf.get('ping_everyone') else 'não'}`\n"
        f"**{tr(guild_id, 'auto_close')}:** `{'sim' if guild_conf.get('auto_close_enabled', True) else 'não'}`\n"
        f"**{tr(guild_id, 'auto_close_after')}:** `{auto_close_hours}h`\n"
        f"**{tr(guild_id, 'reminders')}:** `{'sim' if guild_conf.get('reminder_enabled', True) else 'não'}`\n"
        f"**{tr(guild_id, 'reminder_before')}:** `{reminder_minutes}min`"
    )
    if lang_for_guild(guild_id) == "en-US":
        behavior = behavior.replace("`sim`", f"`{yes}`").replace("`não`", f"`{no}`")
    embed.add_field(name=tr(guild_id, "section_behavior"), value=behavior, inline=False)

    tz_minutes = int(guild_conf.get("timezone_offset_minutes", -180) or 0)
    appearance = (
        f"**{tr(guild_id, 'language')}:** `{SUPPORTED_LANGUAGES.get(lang_for_guild(guild_id), lang_for_guild(guild_id))}`\n"
        f"**{tr(guild_id, 'timezone')}:** `UTC{format_timezone_offset(tz_minutes)}`\n"
        f"**{tr(guild_id, 'embed_color')}:** `{int(guild_conf.get('embed_color', 16766720))}`"
    )
    embed.add_field(name=tr(guild_id, "section_appearance"), value=appearance, inline=False)

    embed.set_footer(text=tr(guild_id, "config_footer"))
    return embed


class PartyChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, guild_id: Optional[int]):
        super().__init__(
            placeholder=tr(guild_id, "config_select_channel_party"),
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        channel = self.values[0]
        set_guild_config_value(interaction.guild_id, "party_channel_id", channel.id)
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=ConfigPanelView(interaction.guild.id))
        await log_action(interaction.guild, f"⚙️ <@{interaction.user.id}> definiu o canal de convites como {channel.mention}.")


class LogChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, guild_id: Optional[int]):
        super().__init__(
            placeholder=tr(guild_id, "config_select_channel_logs"),
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        channel = self.values[0]
        set_guild_config_value(interaction.guild_id, "log_channel_id", channel.id)
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=ConfigPanelView(interaction.guild.id))
        await log_action(interaction.guild, f"⚙️ <@{interaction.user.id}> definiu o canal de logs como {channel.mention}.")


class CommandChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, guild_id: Optional[int]):
        super().__init__(
            placeholder=tr(guild_id, "config_select_channel_commands"),
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        channel = self.values[0]
        set_guild_config_value(interaction.guild_id, "command_channel_id", channel.id)
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=ConfigPanelView(interaction.guild.id))
        await log_action(interaction.guild, f"⚙️ <@{interaction.user.id}> definiu o canal de comandos como {channel.mention}.")


class HostRoleSelect(discord.ui.RoleSelect):
    def __init__(self, guild_id: Optional[int]):
        super().__init__(placeholder=tr(guild_id, "config_select_host_role"), min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        role = self.values[0]
        set_guild_config_value(interaction.guild_id, "host_role_id", role.id)
        set_guild_config_value(interaction.guild_id, "everyone_can_create", False)
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=ConfigPanelView(interaction.guild.id))
        await log_action(interaction.guild, f"⚙️ <@{interaction.user.id}> definiu o cargo Host como {role.mention}.")


class StaffRoleSelect(discord.ui.RoleSelect):
    def __init__(self, guild_id: Optional[int]):
        super().__init__(placeholder=tr(guild_id, "config_select_staff_role"), min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        role = self.values[0]
        set_guild_config_value(interaction.guild_id, "staff_role_id", role.id)
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=ConfigPanelView(interaction.guild.id))
        await log_action(interaction.guild, f"⚙️ <@{interaction.user.id}> definiu o cargo Staff como {role.mention}.")


class ManualChannelModal(discord.ui.Modal):
    def __init__(self, guild_id: Optional[int], target_key: str, title_text: str):
        super().__init__(title=title_text)
        self.guild_id = guild_id
        self.target_key = target_key
        self.channel_id_input = discord.ui.TextInput(label="ID do canal" if lang_for_guild(guild_id) == "pt-BR" else "Channel ID", placeholder="Ex: 123456789012345678", max_length=25, required=True)
        self.add_item(self.channel_id_input)

    async def on_submit(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        guild_id = guild_id_from_interaction(interaction)
        try:
            channel_id = int(str(self.channel_id_input.value).strip())
        except ValueError:
            await interaction.response.send_message(tr(guild_id, "id_channel_numeric"), ephemeral=True)
            return

        channel = await fetch_messageable_channel(channel_id)
        if not channel:
            await interaction.response.send_message(tr(guild_id, "channel_not_found"), ephemeral=True)
            return

        if getattr(channel, "guild", None) and channel.guild.id != interaction.guild_id:
            await interaction.response.send_message(tr(guild_id, "channel_wrong_guild"), ephemeral=True)
            return

        set_guild_config_value(interaction.guild_id, self.target_key, channel_id)
        await interaction.response.send_message(tr(guild_id, "channel_set", channel=channel.mention), ephemeral=True)
        await log_action(interaction.guild, f"⚙️ <@{interaction.user.id}> definiu `{self.target_key}` como {channel.mention} via ID.")


class ManualRoleModal(discord.ui.Modal):
    def __init__(self, guild_id: Optional[int], target_key: str, title_text: str):
        super().__init__(title=title_text)
        self.guild_id = guild_id
        self.target_key = target_key
        self.role_id_input = discord.ui.TextInput(label="ID do cargo" if lang_for_guild(guild_id) == "pt-BR" else "Role ID", placeholder="Ex: 123456789012345678", max_length=25, required=True)
        self.add_item(self.role_id_input)

    async def on_submit(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        guild_id = guild_id_from_interaction(interaction)
        try:
            role_id = int(str(self.role_id_input.value).strip())
        except ValueError:
            await interaction.response.send_message(tr(guild_id, "id_role_numeric"), ephemeral=True)
            return

        role = interaction.guild.get_role(role_id) if interaction.guild else None
        if not role:
            await interaction.response.send_message(tr(guild_id, "role_not_found"), ephemeral=True)
            return

        set_guild_config_value(interaction.guild.id, self.target_key, role_id)
        if self.target_key == "host_role_id":
            set_guild_config_value(interaction.guild.id, "everyone_can_create", False)
        await interaction.response.send_message(tr(guild_id, "role_set", role=role.mention), ephemeral=True)
        await log_action(interaction.guild, f"⚙️ <@{interaction.user.id}> definiu `{self.target_key}` como {role.mention} via ID.")


class ConfigColorModal(discord.ui.Modal):
    def __init__(self, guild_id: Optional[int]):
        super().__init__(title="Alterar cor do embed" if lang_for_guild(guild_id) == "pt-BR" else "Change embed color")
        self.guild_id = guild_id
        self.color_value = discord.ui.TextInput(label=tr(guild_id, "embed_color"), placeholder="Ex: 16766720", max_length=8, required=True)
        self.add_item(self.color_value)

    async def on_submit(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        guild_id = guild_id_from_interaction(interaction)
        try:
            value = int(str(self.color_value.value).strip())
        except ValueError:
            await interaction.response.send_message(tr(guild_id, "color_number"), ephemeral=True)
            return

        if value < 0 or value > 16777215:
            await interaction.response.send_message(tr(guild_id, "color_range"), ephemeral=True)
            return

        set_guild_config_value(interaction.guild_id, "embed_color", value)
        await interaction.response.send_message(tr(guild_id, "color_changed", value=value), ephemeral=True)
        await log_action(interaction.guild, f"⚙️ <@{interaction.user.id}> alterou a cor do embed para `{value}`.")


class TimezoneModal(discord.ui.Modal):
    def __init__(self, guild_id: Optional[int]):
        super().__init__(title="Alterar fuso horário" if lang_for_guild(guild_id) == "pt-BR" else "Change timezone")
        self.guild_id = guild_id
        self.offset = discord.ui.TextInput(label="UTC offset", placeholder="Ex: -3, +0, +2, -03:30", max_length=8, required=True)
        self.add_item(self.offset)

    async def on_submit(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        guild_id = guild_id_from_interaction(interaction)
        minutes = parse_timezone_offset(str(self.offset.value))
        if minutes is None:
            await interaction.response.send_message(tr(guild_id, "timezone_invalid"), ephemeral=True)
            return
        set_guild_config_value(interaction.guild_id, "timezone_offset_minutes", minutes)
        await interaction.response.send_message(tr(guild_id, "timezone_changed", offset=format_timezone_offset(minutes)), ephemeral=True)


class LanguageSelect(discord.ui.Select):
    def __init__(self, guild_id: Optional[int]):
        options = [
            discord.SelectOption(label="Português do Brasil", value="pt-BR", emoji="🇧🇷"),
            discord.SelectOption(label="English", value="en-US", emoji="🇺🇸"),
        ]
        super().__init__(placeholder=tr(guild_id, "language"), min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        guild_id = guild_id_from_interaction(interaction)
        selected = self.values[0]
        set_guild_config_value(interaction.guild_id, "language", selected)
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=ConfigPanelView(interaction.guild.id))
        await interaction.followup.send(tr(guild_id, "language_changed", language=SUPPORTED_LANGUAGES[selected]), ephemeral=True)


class SelectOnlyView(discord.ui.View):
    def __init__(self, guild_id: Optional[int], select: discord.ui.Select):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.add_item(select)

    @discord.ui.button(label="Voltar", emoji="↩️", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=ConfigPanelView(interaction.guild.id))


class ConfigPanelView(discord.ui.View):
    def __init__(self, guild_id: Optional[int]):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        # Labels traduzidas no painel.
        self.channels_button.label = "Canais" if lang_for_guild(guild_id) == "pt-BR" else "Channels"
        self.roles_button.label = "Cargos" if lang_for_guild(guild_id) == "pt-BR" else "Roles"
        self.behavior_button.label = "Comportamento" if lang_for_guild(guild_id) == "pt-BR" else "Behavior"
        self.appearance_button.label = "Aparência/Idioma" if lang_for_guild(guild_id) == "pt-BR" else "Appearance/Language"
        self.refresh_panel.label = tr(guild_id, "refresh")

    @discord.ui.button(label="Canais", emoji="📢", style=discord.ButtonStyle.primary, row=0)
    async def channels_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=ChannelsConfigView(interaction.guild.id))

    @discord.ui.button(label="Cargos", emoji="🎭", style=discord.ButtonStyle.primary, row=0)
    async def roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=RolesConfigView(interaction.guild.id))

    @discord.ui.button(label="Comportamento", emoji="⚙️", style=discord.ButtonStyle.secondary, row=0)
    async def behavior_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=BehaviorConfigView(interaction.guild.id))

    @discord.ui.button(label="Aparência/Idioma", emoji="🎨", style=discord.ButtonStyle.secondary, row=0)
    async def appearance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=AppearanceConfigView(interaction.guild.id))

    @discord.ui.button(label="Atualizar", emoji="🔄", style=discord.ButtonStyle.success, row=1)
    async def refresh_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=ConfigPanelView(interaction.guild.id))


class ChannelsConfigView(discord.ui.View):
    def __init__(self, guild_id: Optional[int]):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.set_party_channel.label = tr(guild_id, "channel_invites")
        self.set_log_channel.label = tr(guild_id, "channel_logs")
        self.set_command_channel.label = tr(guild_id, "channel_commands")
        self.set_party_channel_by_id.label = f"ID {tr(guild_id, 'channel_invites')}"
        self.set_log_channel_by_id.label = f"ID {tr(guild_id, 'channel_logs')}"
        self.set_command_channel_by_id.label = f"ID {tr(guild_id, 'channel_commands')}"
        self.test_party_channel.label = tr(guild_id, "test_invites")
        self.test_log_channel.label = tr(guild_id, "test_logs")
        self.back.label = tr(guild_id, "back")

    @discord.ui.button(label="Canal de Convites", emoji="📢", style=discord.ButtonStyle.primary, row=0)
    async def set_party_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=tr(self.guild_id, "config_select_channel_party"), embed=None, view=SelectOnlyView(self.guild_id, PartyChannelSelect(self.guild_id)))

    @discord.ui.button(label="Canal de Logs", emoji="📜", style=discord.ButtonStyle.primary, row=0)
    async def set_log_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=tr(self.guild_id, "config_select_channel_logs"), embed=None, view=SelectOnlyView(self.guild_id, LogChannelSelect(self.guild_id)))

    @discord.ui.button(label="Canal de Comandos", emoji="⌨️", style=discord.ButtonStyle.primary, row=0)
    async def set_command_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=tr(self.guild_id, "config_select_channel_commands"), embed=None, view=SelectOnlyView(self.guild_id, CommandChannelSelect(self.guild_id)))


    @discord.ui.button(label="ID Canal Convites", emoji="🔢", style=discord.ButtonStyle.secondary, row=1)
    async def set_party_channel_by_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.send_modal(ManualChannelModal(self.guild_id, "party_channel_id", "Canal de convites por ID"))

    @discord.ui.button(label="ID Canal Logs", emoji="🔢", style=discord.ButtonStyle.secondary, row=1)
    async def set_log_channel_by_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.send_modal(ManualChannelModal(self.guild_id, "log_channel_id", "Canal de logs por ID"))

    @discord.ui.button(label="ID Canal Comandos", emoji="🔢", style=discord.ButtonStyle.secondary, row=1)
    async def set_command_channel_by_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.send_modal(ManualChannelModal(self.guild_id, "command_channel_id", "Canal de comandos por ID"))


    @discord.ui.button(label="Testar convites", emoji="🧪", style=discord.ButtonStyle.success, row=2)
    async def test_party_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await send_channel_test(interaction, "party_channel_id", "test_invites_msg")

    @discord.ui.button(label="Testar logs", emoji="🧪", style=discord.ButtonStyle.success, row=2)
    async def test_log_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await send_channel_test(interaction, "log_channel_id", "test_logs_msg")


    @discord.ui.button(label="Voltar", emoji="↩️", style=discord.ButtonStyle.secondary, row=3)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=ConfigPanelView(interaction.guild.id))


async def send_channel_test(interaction: discord.Interaction, key: str, message_key: str):
    guild_id = guild_id_from_interaction(interaction)
    guild_conf = get_guild_config(guild_id)
    channel_id = int(guild_conf.get(key, 0) or 0)
    if not channel_id:
        await interaction.response.send_message(tr(guild_id, "test_no_channel"), ephemeral=True)
        return
    channel = await fetch_messageable_channel(channel_id)
    if not channel:
        await interaction.response.send_message(tr(guild_id, "channel_not_found"), ephemeral=True)
        return
    try:
        await channel.send(tr(guild_id, message_key))
    except discord.Forbidden:
        await interaction.response.send_message(tr(guild_id, "test_forbidden"), ephemeral=True)
        return
    await interaction.response.send_message(tr(guild_id, "test_sent", channel=channel.mention), ephemeral=True)


class RolesConfigView(discord.ui.View):
    def __init__(self, guild_id: Optional[int]):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.set_host_role.label = tr(guild_id, "role_host")
        self.set_staff_role.label = tr(guild_id, "role_staff")
        self.set_host_role_by_id.label = f"ID {tr(guild_id, 'role_host')}"
        self.set_staff_role_by_id.label = f"ID {tr(guild_id, 'role_staff')}"
        self.back.label = tr(guild_id, "back")

    @discord.ui.button(label="Cargo Host", emoji="🎮", style=discord.ButtonStyle.primary, row=0)
    async def set_host_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=tr(self.guild_id, "config_select_host_role"), embed=None, view=SelectOnlyView(self.guild_id, HostRoleSelect(self.guild_id)))

    @discord.ui.button(label="Cargo Staff", emoji="🛡️", style=discord.ButtonStyle.primary, row=0)
    async def set_staff_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=tr(self.guild_id, "config_select_staff_role"), embed=None, view=SelectOnlyView(self.guild_id, StaffRoleSelect(self.guild_id)))

    @discord.ui.button(label="ID Cargo Host", emoji="🔢", style=discord.ButtonStyle.secondary, row=1)
    async def set_host_role_by_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.send_modal(ManualRoleModal(self.guild_id, "host_role_id", "Cargo Host por ID"))

    @discord.ui.button(label="ID Cargo Staff", emoji="🔢", style=discord.ButtonStyle.secondary, row=1)
    async def set_staff_role_by_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.send_modal(ManualRoleModal(self.guild_id, "staff_role_id", "Cargo Staff por ID"))

    @discord.ui.button(label="Voltar", emoji="↩️", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=ConfigPanelView(interaction.guild.id))


class BehaviorConfigView(discord.ui.View):
    def __init__(self, guild_id: Optional[int]):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.toggle_everyone_can_create.label = tr(guild_id, "everyone_create")
        self.toggle_ping_everyone.label = tr(guild_id, "ping_everyone")
        self.toggle_auto_close.label = tr(guild_id, "auto_close")
        self.toggle_reminders.label = tr(guild_id, "reminders")
        self.back.label = tr(guild_id, "back")

    @discord.ui.button(label="Todos podem criar", emoji="👥", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_everyone_can_create(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        guild_conf = get_guild_config(interaction.guild_id)
        new_value = not bool(guild_conf.get("everyone_can_create", False))
        set_guild_config_value(interaction.guild_id, "everyone_can_create", new_value)
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=BehaviorConfigView(interaction.guild.id))

    @discord.ui.button(label="Ping @everyone", emoji="📣", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_ping_everyone(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        guild_conf = get_guild_config(interaction.guild_id)
        new_value = not bool(guild_conf.get("ping_everyone", True))
        set_guild_config_value(interaction.guild_id, "ping_everyone", new_value)
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=BehaviorConfigView(interaction.guild.id))

    @discord.ui.button(label="Encerrar automaticamente", emoji="🔒", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_auto_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        guild_conf = get_guild_config(interaction.guild_id)
        new_value = not bool(guild_conf.get("auto_close_enabled", True))
        set_guild_config_value(interaction.guild_id, "auto_close_enabled", new_value)
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=BehaviorConfigView(interaction.guild.id))

    @discord.ui.button(label="Lembretes automáticos", emoji="⏰", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_reminders(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        guild_conf = get_guild_config(interaction.guild_id)
        new_value = not bool(guild_conf.get("reminder_enabled", True))
        set_guild_config_value(interaction.guild_id, "reminder_enabled", new_value)
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=BehaviorConfigView(interaction.guild.id))

    @discord.ui.button(label="Voltar", emoji="↩️", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=ConfigPanelView(interaction.guild.id))


class AppearanceConfigView(discord.ui.View):
    def __init__(self, guild_id: Optional[int]):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.set_language.label = tr(guild_id, "language")
        self.set_embed_color.label = tr(guild_id, "embed_color")
        self.set_timezone.label = tr(guild_id, "timezone")
        self.back.label = tr(guild_id, "back")

    @discord.ui.button(label="Idioma", emoji="🌐", style=discord.ButtonStyle.primary, row=0)
    async def set_language(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=None, embed=None, view=SelectOnlyView(self.guild_id, LanguageSelect(self.guild_id)))

    @discord.ui.button(label="Cor", emoji="🎨", style=discord.ButtonStyle.secondary, row=0)
    async def set_embed_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.send_modal(ConfigColorModal(self.guild_id))

    @discord.ui.button(label="Fuso horário", emoji="🕒", style=discord.ButtonStyle.secondary, row=0)
    async def set_timezone(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.send_modal(TimezoneModal(self.guild_id))

    @discord.ui.button(label="Voltar", emoji="↩️", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content=None, embed=await make_config_embed(interaction.guild), view=ConfigPanelView(interaction.guild.id))



# ============================================================
# Automatic reminders / expiration
# ============================================================


def party_jump_url(data: Dict[str, Any]) -> str:
    guild_id = int(data.get("guild_id", 0) or 0)
    channel_id = int(data.get("channel_id", 0) or 0)
    message_id = int(data.get("message_id", 0) or 0)
    if guild_id and channel_id and message_id:
        return f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
    return ""


def party_participant_mentions(data: Dict[str, Any]) -> str:
    user_ids = []
    for key in ("accepted", "tentative"):
        for user_id in data.get(key, []):
            if user_id not in user_ids:
                user_ids.append(user_id)
    if not user_ids:
        return ""
    return " ".join(f"<@{user_id}>" for user_id in user_ids[:40])


async def send_party_channel_message(data: Dict[str, Any], content: str, mention_users: bool = False):
    channel = await fetch_messageable_channel(int(data.get("channel_id", 0) or 0))
    if not channel:
        return
    try:
        await channel.send(content, allowed_mentions=discord.AllowedMentions(users=mention_users, everyone=False, roles=False))
    except discord.HTTPException:
        pass


async def auto_close_party(party_id: str, data: Dict[str, Any], reason_key: str):
    if data.get("status") != "open":
        return
    guild_id = int(data.get("guild_id", 0) or 0)
    data["status"] = "closed"
    data["auto_closed"] = True
    save_parties()
    await update_party_message(party_id)
    await send_party_channel_message(data, tr(guild_id, reason_key, title=data.get("title", "Party")))
    guild = bot.get_guild(guild_id)
    await log_action(guild, tr(guild_id, "log_party_auto_closed", title=data.get("title", "Party"), party_id=party_id))


@tasks.loop(seconds=60)
async def party_maintenance_loop():
    now_ts = int(datetime.now(timezone.utc).timestamp())
    changed = False

    for party_id, data in list(parties.items()):
        if not isinstance(data, dict) or data.get("status") != "open":
            continue

        guild_id = int(data.get("guild_id", 0) or 0)
        guild_conf = get_guild_config(guild_id)
        start_ts = int(data.get("start_ts", 0) or 0)
        end_ts = int(data.get("end_ts", 0) or 0)

        if guild_conf.get("reminder_enabled", True) and start_ts and not data.get("reminder_sent", False):
            reminder_minutes = int(guild_conf.get("reminder_minutes", 15) or 15)
            reminder_ts = start_ts - max(1, reminder_minutes) * 60
            if reminder_ts <= now_ts < start_ts:
                mentions = party_participant_mentions(data)
                url = party_jump_url(data)
                content = tr(
                    guild_id,
                    "party_reminder",
                    title=data.get("title", "Party"),
                    relative=discord_relative(start_ts),
                    mentions=mentions,
                    url=url,
                )
                await send_party_channel_message(data, content, mention_users=True)
                data["reminder_sent"] = True
                changed = True

        if guild_conf.get("auto_close_enabled", True):
            if end_ts and now_ts >= end_ts:
                await auto_close_party(party_id, data, "party_auto_closed_end")
                continue
            if start_ts and not end_ts:
                auto_close_hours = int(guild_conf.get("auto_close_after_hours", 6) or 6)
                if now_ts >= start_ts + max(1, auto_close_hours) * 3600:
                    await auto_close_party(party_id, data, "party_auto_closed_timeout")
                    continue

    if changed:
        save_parties()


@party_maintenance_loop.before_loop
async def before_party_maintenance_loop():
    await bot.wait_until_ready()

# ============================================================
# Eventos / slash commands
# ============================================================


@bot.event
async def on_ready():
    global _commands_synced

    print(f"Logado como {bot.user}. Servidores: {len(bot.guilds)}")
    bot.add_view(HubView())
    bot.add_view(PartyView())

    if not party_maintenance_loop.is_running():
        party_maintenance_loop.start()
        print("Loop de manutenção de parties iniciado.")

    if _commands_synced:
        return

    try:
        # Sempre limpa comandos antigos específicos de servidor.
        # Eles foram criados nas versões antigas com guild=discord.Object(...).
        for guild in bot.guilds:
            bot.tree.clear_commands(guild=discord.Object(id=guild.id))
            await bot.tree.sync(guild=discord.Object(id=guild.id))
            print(f"Comandos antigos de servidor limpos em: {guild.name}")

        if FORCE_COMMAND_RESET:
            # Reset forte dos comandos globais.
            # Use apenas uma vez no Railway com FORCE_COMMAND_RESET=1.
            # Depois remova a variável ou mude para 0.
            print("FORCE_COMMAND_RESET ativo: apagando comandos globais antigos...")
            bot.tree.clear_commands(guild=None)
            await bot.tree.sync()
            bot.tree.add_command(party_group)

        synced = await bot.tree.sync()
        _commands_synced = True
        print(f"Comandos globais sincronizados: {len(synced)}")
        print("Comandos globais ativos:", ", ".join(command.name for command in synced))
    except Exception as error:
        print(f"Erro ao sincronizar comandos: {error}")


party_group = app_commands.Group(
    name="party",
    description="Comandos do sistema de parties.",
)


@party_group.command(name="hub", description="Cria o Hub de Parties no canal atual.")
async def party_hub(interaction: discord.Interaction):
    member = interaction.user
    guild_id = guild_id_from_interaction(interaction)

    if not interaction.guild or not isinstance(member, discord.Member):
        await interaction.response.send_message(tr(guild_id, "use_inside_server"), ephemeral=True)
        return

    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message(tr(guild_id, "normal_text_channel_only"), ephemeral=True)
        return

    guild_conf = get_guild_config(interaction.guild.id)
    staff_allowed = is_staff(member)
    host_allowed = is_host(member)

    if not staff_allowed:
        if not host_allowed:
            await interaction.response.send_message(tr(guild_id, "hub_staff_needed"), ephemeral=True)
            return

        command_channel_id = int(guild_conf.get("command_channel_id", 0) or 0)
        if not command_channel_id:
            await interaction.response.send_message(tr(guild_id, "hub_command_channel_needed"), ephemeral=True)
            return

        if interaction.channel_id != command_channel_id:
            await interaction.response.send_message(
                tr(guild_id, "hub_wrong_channel", channel=f"<#{command_channel_id}>"),
                ephemeral=True,
            )
            return

    try:
        message = await interaction.channel.send(embed=make_hub_embed(interaction.guild.id), view=HubView(interaction.guild.id))
    except discord.Forbidden:
        await interaction.response.send_message(tr(guild_id, "hub_no_perm"), ephemeral=True)
        return
    except discord.HTTPException as error:
        await interaction.response.send_message(f"Erro ao criar o Hub: `{error}`", ephemeral=True)
        return

    await interaction.response.send_message(tr(guild_id, "hub_created", url=message.jump_url), ephemeral=True)
    await log_action(interaction.guild, f"🧩 <@{member.id}> criou o Hub de Parties em {interaction.channel.mention}.")


@party_group.command(name="config", description="Abre o painel de configuração do Party Bot neste servidor.")
async def party_config(interaction: discord.Interaction):
    member = interaction.user
    guild_id = guild_id_from_interaction(interaction)

    if not interaction.guild or not isinstance(member, discord.Member):
        await interaction.response.send_message(tr(guild_id, "use_inside_server"), ephemeral=True)
        return

    if not is_staff(member):
        await interaction.response.send_message(tr(guild_id, "staff_needed"), ephemeral=True)
        return

    await interaction.response.send_message(
        embed=await make_config_embed(interaction.guild),
        view=ConfigPanelView(interaction.guild.id),
        ephemeral=True,
    )


@party_group.command(name="lista", description="Lista parties abertas deste servidor.")
async def party_lista(interaction: discord.Interaction):
    guild_id = guild_id_from_interaction(interaction)
    open_parties = [
        (party_id, data)
        for party_id, data in parties.items()
        if data.get("status") == "open" and int(data.get("guild_id", 0) or 0) == guild_id
    ]

    if not open_parties:
        await interaction.response.send_message(tr(guild_id, "no_open_parties"), ephemeral=True)
        return

    lines = []
    for party_id, data in open_parties[:20]:
        channel_id = data.get("channel_id")
        message_id = data.get("message_id")
        accepted = len(data.get("accepted", []))
        capacity = data.get("capacity", 0)
        lines.append(
            f"🎮 **{data.get('title', 'Party')}** — `{accepted}/{capacity}` — "
            f"{tr(guild_id, 'field_host')}: <@{data.get('host_id')}> — "
            f"[abrir](https://discord.com/channels/{interaction.guild_id}/{channel_id}/{message_id})"
        )

    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@party_group.command(name="limpar", description="Remove do banco as parties encerradas deste servidor.")
async def party_limpar(interaction: discord.Interaction):
    member = interaction.user
    guild_id = guild_id_from_interaction(interaction)

    if not interaction.guild or not isinstance(member, discord.Member) or not is_staff(member):
        await interaction.response.send_message(tr(guild_id, "clean_staff_needed"), ephemeral=True)
        return

    before = len(parties)
    closed_ids = [
        party_id
        for party_id, data in parties.items()
        if data.get("status") == "closed" and int(data.get("guild_id", 0) or 0) == interaction.guild.id
    ]

    for party_id in closed_ids:
        parties.pop(party_id, None)

    save_parties()
    removed = before - len(parties)
    await interaction.response.send_message(tr(guild_id, "clean_done", count=removed), ephemeral=True)


bot.tree.add_command(party_group)


if not TOKEN or TOKEN in ("COLE_SEU_TOKEN_AQUI", "SEU_TOKEN", "COLOQUE_SEU_TOKEN_AQUI"):
    raise RuntimeError("Coloque o token do bot em DISCORD_TOKEN no Railway ou no config.json.")

bot.run(TOKEN)
