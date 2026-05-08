import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import discord
from discord import app_commands
from discord.ext import commands


DATA_DIR = Path(os.getenv("DATA_DIR") or Path(__file__).parent)
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = DATA_DIR / "config.json"
PARTIES_PATH = DATA_DIR / "parties.json"

DEFAULT_GUILD_CONFIG = {
    "party_channel_id": 0,
    "log_channel_id": 0,
    "host_role_id": 0,
    "staff_role_id": 0,
    "embed_color": 16766720,
    "everyone_can_create": False,
    "ping_everyone": True,
}

DEFAULT_CONFIG = {
    "token": "",
    "guilds": {},
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
        return default.copy() if isinstance(default, dict) else default

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        save_json(path, default)
        return default.copy() if isinstance(default, dict) else default

    if isinstance(default, dict) and isinstance(data, dict):
        changed = False
        for key, value in default.items():
            if key not in data:
                data[key] = value
                changed = True

        # Migração automática da versão antiga, que usava um servidor só.
        old_guild_id = int(data.get("guild_id", 0) or 0) if "guild_id" in data else 0
        if old_guild_id:
            guild_key = str(old_guild_id)
            data.setdefault("guilds", {})
            if guild_key not in data["guilds"]:
                data["guilds"][guild_key] = DEFAULT_GUILD_CONFIG.copy()

            guild_conf = data["guilds"][guild_key]
            for old_key in DEFAULT_GUILD_CONFIG:
                if old_key in data:
                    guild_conf[old_key] = data[old_key]

            for old_key in (
                "guild_id",
                "party_channel_id",
                "log_channel_id",
                "host_role_id",
                "staff_role_id",
                "embed_color",
                "hub_channel_id",
            ):
                data.pop(old_key, None)
            changed = True

        if changed:
            save_json(path, data)

    return data


config: Dict[str, Any] = load_json(CONFIG_PATH, DEFAULT_CONFIG)
parties: Dict[str, Any] = load_json(PARTIES_PATH, {})


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

        data.setdefault("status", "open")
        data.setdefault("capacity", 4)
        data.setdefault("title", "Party")
        data.setdefault("description", "")
        data.setdefault("time", "")
        data.setdefault("image_url", "")

    if changed:
        save_json(PARTIES_PATH, parties)


normalize_parties()

TOKEN = os.getenv("DISCORD_TOKEN") or config.get("token")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
_commands_synced = False


def save_config():
    save_json(CONFIG_PATH, config)


def save_parties():
    save_json(PARTIES_PATH, parties)


def get_guild_config(guild_id: Optional[int]) -> Dict[str, Any]:
    if not guild_id:
        return DEFAULT_GUILD_CONFIG.copy()

    guild_key = str(guild_id)
    guilds = config.setdefault("guilds", {})

    if guild_key not in guilds:
        guilds[guild_key] = DEFAULT_GUILD_CONFIG.copy()
        save_config()

    guild_conf = guilds[guild_key]
    changed = False
    for key, value in DEFAULT_GUILD_CONFIG.items():
        if key not in guild_conf:
            guild_conf[key] = value
            changed = True

    if changed:
        save_config()

    return guild_conf


def set_guild_config_value(guild_id: int, key: str, value: Any):
    guild_conf = get_guild_config(guild_id)
    guild_conf[key] = value
    save_config()


def guild_color(guild_id: Optional[int]) -> int:
    return int(get_guild_config(guild_id).get("embed_color", 16766720))


def guild_id_from_interaction(interaction: discord.Interaction) -> Optional[int]:
    return int(interaction.guild_id) if interaction.guild_id else None


def member_has_role(member: discord.Member, role_id: int) -> bool:
    if not role_id:
        return False
    return any(role.id == role_id for role in member.roles)


def is_staff(member: discord.Member) -> bool:
    guild_conf = get_guild_config(member.guild.id)
    staff_role_id = int(guild_conf.get("staff_role_id", 0) or 0)
    return member.guild_permissions.manage_guild or member_has_role(member, staff_role_id)


def interaction_member_is_staff(interaction: discord.Interaction) -> bool:
    return isinstance(interaction.user, discord.Member) and is_staff(interaction.user)


async def reject_if_not_staff(interaction: discord.Interaction) -> bool:
    if not interaction.guild or not interaction_member_is_staff(interaction):
        await interaction.response.send_message(
            "Você precisa ser staff ou ter **Gerenciar servidor** para usar essa configuração.",
            ephemeral=True,
        )
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


async def fetch_text_channel(channel_id: int) -> Optional[discord.TextChannel]:
    if not channel_id:
        return None

    channel = bot.get_channel(channel_id)
    if isinstance(channel, discord.TextChannel):
        return channel

    try:
        fetched = await bot.fetch_channel(channel_id)
    except discord.HTTPException:
        return None

    if isinstance(fetched, discord.TextChannel):
        return fetched

    return None


async def log_action(guild: Optional[discord.Guild], text: str):
    if not guild:
        return

    guild_conf = get_guild_config(guild.id)
    log_channel_id = int(guild_conf.get("log_channel_id", 0) or 0)
    if not log_channel_id:
        return

    channel = await fetch_text_channel(log_channel_id)
    if not channel:
        return

    try:
        await channel.send(text)
    except discord.HTTPException:
        pass


def config_status_text(guild_id: int) -> str:
    guild_conf = get_guild_config(guild_id)

    def channel_text(channel_id: int):
        return f"<#{channel_id}>" if channel_id else "`não definido`"

    def role_text(role_id: int):
        return f"<@&{role_id}>" if role_id else "`não definido`"

    everyone_text = "`sim`" if guild_conf.get("everyone_can_create") else "`não`"
    ping_text = "`sim`" if guild_conf.get("ping_everyone") else "`não`"

    return (
        f"**Canal de convites:** {channel_text(int(guild_conf.get('party_channel_id', 0) or 0))}\n"
        f"**Canal de logs:** {channel_text(int(guild_conf.get('log_channel_id', 0) or 0))}\n"
        f"**Cargo Host:** {role_text(int(guild_conf.get('host_role_id', 0) or 0))}\n"
        f"**Cargo Staff:** {role_text(int(guild_conf.get('staff_role_id', 0) or 0))}\n"
        f"**Todos podem criar party:** {everyone_text}\n"
        f"**Marcar @everyone ao criar:** {ping_text}\n"
        f"**Cor do embed:** `{int(guild_conf.get('embed_color', 16766720))}`"
    )


def make_hub_embed(guild_id: Optional[int]) -> discord.Embed:
    guild_conf = get_guild_config(guild_id)
    party_channel_id = int(guild_conf.get("party_channel_id", 0) or 0)

    embed = discord.Embed(
        title="🎮 Hub de Parties — SPD",
        description=(
            "Crie e acompanhe convites de party pelo painel abaixo.\n\n"
            "**🎮 Criar Party** — abre um formulário para criar convite.\n"
            "**📋 Ver Parties** — mostra as parties abertas.\n"
            "**👤 Minhas Parties** — mostra onde você está participando.\n"
            "**❓ Ajuda** — explica o sistema."
        ),
        color=guild_color(guild_id),
    )

    if party_channel_id:
        embed.add_field(
            name="📢 Canal dos convites",
            value=f"As parties criadas aqui serão enviadas em <#{party_channel_id}>.",
            inline=False,
        )
    else:
        embed.add_field(
            name="⚠️ Configuração pendente",
            value="A staff ainda precisa configurar o canal dos convites.",
            inline=False,
        )

    embed.set_footer(text="Use /party-config-panel para configurar o bot")
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
    time_text = data.get("time", "")
    host_id = data.get("host_id")

    status_text = "🟢 Aberta" if status == "open" else "🔴 Encerrada"

    embed = discord.Embed(
        title=title,
        description=data.get("description") or None,
        color=guild_color(guild_id) if status == "open" else 0x555555,
    )

    if time_text:
        embed.add_field(name="Time", value=time_text, inline=False)

    embed.add_field(
        name=f"✅ Vou ({len(accepted)}/{capacity})",
        value=short_mentions(accepted),
        inline=True,
    )
    embed.add_field(
        name=f"❔ Talvez ({len(tentative)}/{capacity})",
        value=short_mentions(tentative),
        inline=True,
    )
    embed.add_field(
        name=f"❌ Não vou ({len(declined)}/99)",
        value=short_mentions(declined),
        inline=True,
    )

    if queue:
        embed.add_field(name=f"📋 Fila ({len(queue)})", value=mention_list(queue), inline=False)

    embed.add_field(name="Status", value=status_text, inline=True)
    embed.add_field(name="Host", value=f"<@{host_id}>", inline=True)

    if image_url:
        embed.set_image(url=image_url)

    embed.set_footer(text=f"Created by {data.get('host_name', 'unknown')} • Party ID: {party_id}")
    return embed


async def update_party_message(party_id: str):
    data = parties.get(party_id)
    if not data:
        return

    channel = await fetch_text_channel(int(data.get("channel_id", 0) or 0))
    if not channel:
        return

    try:
        message = await channel.fetch_message(int(data["message_id"]))
        disabled = data.get("status") != "open"
        await message.edit(embed=make_party_embed(party_id), view=PartyView(disabled=disabled))
    except discord.HTTPException:
        pass


class HubView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Criar Party", emoji="🎮", style=discord.ButtonStyle.success, custom_id="hub:create_party")
    async def create_party(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        if not interaction.guild or not isinstance(member, discord.Member):
            await interaction.response.send_message("Use isso dentro de um servidor.", ephemeral=True)
            return

        if not can_create_party(member):
            guild_conf = get_guild_config(interaction.guild.id)
            host_role_id = int(guild_conf.get("host_role_id", 0) or 0)
            required = f"<@&{host_role_id}>" if host_role_id else "cargo Host configurado pela staff"
            await interaction.response.send_message(
                f"Você não tem permissão para criar parties.\nCargo necessário: {required}.",
                ephemeral=True,
            )
            return

        guild_conf = get_guild_config(interaction.guild.id)
        if not int(guild_conf.get("party_channel_id", 0) or 0):
            await interaction.response.send_message(
                "O canal de convites ainda não foi configurado.\nA staff precisa usar `/party-config-panel`.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(CreatePartyModal())

    @discord.ui.button(label="Ver Parties", emoji="📋", style=discord.ButtonStyle.primary, custom_id="hub:list_parties")
    async def list_parties(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = guild_id_from_interaction(interaction)
        open_parties = [
            (party_id, data)
            for party_id, data in parties.items()
            if data.get("status") == "open" and int(data.get("guild_id", 0) or 0) == guild_id
        ]

        if not open_parties:
            await interaction.response.send_message("Não tem nenhuma party aberta no momento.", ephemeral=True)
            return

        lines = []
        for party_id, data in open_parties[:20]:
            accepted = len(data.get("accepted", []))
            capacity = data.get("capacity", 0)
            channel_id = data.get("channel_id")
            message_id = data.get("message_id")
            lines.append(
                f"🎮 **{data.get('title', 'Party')}** — `{accepted}/{capacity}` — "
                f"Host: <@{data.get('host_id')}> — "
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
                role = "Host"
            elif user_id in data.get("accepted", []):
                role = "Vou"
            elif user_id in data.get("tentative", []):
                role = "Talvez"
            elif user_id in data.get("declined", []):
                role = "Não vou"
            elif user_id in data.get("queue", []):
                role = "Fila"

            if role:
                found.append((party_id, data, role))

        if not found:
            await interaction.response.send_message("Você não está em nenhuma party aberta.", ephemeral=True)
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
        guild_conf = get_guild_config(guild_id_from_interaction(interaction))
        host_role_id = int(guild_conf.get("host_role_id", 0) or 0)
        host_text = "todos os membros" if guild_conf.get("everyone_can_create") else (f"<@&{host_role_id}>" if host_role_id else "cargo Host configurado pela staff")
        text = (
            "**Como funciona:**\n\n"
            "1. Clique em **🎮 Criar Party**.\n"
            "2. Preencha título, vagas, horário, descrição e imagem.\n"
            "3. O convite aparece no canal configurado pela staff.\n"
            "4. O pessoal clica em ✅, ❔ ou ❌.\n"
            "5. Se **Vou** lotar, quem clicar em ✅ vai para a fila.\n"
            "6. O host ou a staff usa **⚙️ Gerenciar** para editar ou encerrar.\n\n"
            f"Quem pode criar party: {host_text}."
        )
        await interaction.response.send_message(text, ephemeral=True)


class CreatePartyModal(discord.ui.Modal, title="Criar Party"):
    title_input = discord.ui.TextInput(label="Título da party", placeholder="Ex: Lego Party - 4 Jogadores", max_length=100, required=True)
    capacity = discord.ui.TextInput(label="Vagas", placeholder="Ex: 4", max_length=2, required=True)
    time = discord.ui.TextInput(label="Horário", placeholder="Ex: Hoje 18:30 - 20:30", max_length=120, required=False)
    description = discord.ui.TextInput(label="Descrição", placeholder="Ex: Bora jogar LEGO Party!", style=discord.TextStyle.paragraph, max_length=500, required=False)
    image_url = discord.ui.TextInput(label="Imagem por link", placeholder="Ex: https://site.com/imagem.png", max_length=300, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user

        if not interaction.guild or not isinstance(member, discord.Member):
            await interaction.followup.send("Esse formulário só funciona dentro de servidor.", ephemeral=True)
            return

        if not can_create_party(member):
            await interaction.followup.send("Você não tem permissão para criar parties.", ephemeral=True)
            return

        try:
            capacity_value = int(str(self.capacity.value).strip())
        except ValueError:
            await interaction.followup.send("O campo **Vagas** precisa ser um número.", ephemeral=True)
            return

        if capacity_value < 1 or capacity_value > 25:
            await interaction.followup.send("As vagas precisam ficar entre **1** e **25**.", ephemeral=True)
            return

        image = str(self.image_url.value).strip()
        if image and not image.lower().startswith(("http://", "https://")):
            await interaction.followup.send("O link da imagem precisa começar com `http://` ou `https://`.", ephemeral=True)
            return

        guild_conf = get_guild_config(interaction.guild.id)
        channel = await fetch_text_channel(int(guild_conf.get("party_channel_id", 0) or 0))
        if not channel:
            await interaction.followup.send(
                "Canal de convites não encontrado.\nA staff precisa usar `/party-config-panel` para configurar.",
                ephemeral=True,
            )
            return

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
            "time": str(self.time.value).strip(),
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
            message = await channel.send(content=content, embed=make_party_embed(party_id), view=PartyView(), allowed_mentions=allowed_mentions)
        except discord.Forbidden:
            parties.pop(party_id, None)
            save_parties()
            await interaction.followup.send("Achei o canal de convites, mas não tenho permissão para enviar mensagem nele.", ephemeral=True)
            return
        except discord.HTTPException as error:
            parties.pop(party_id, None)
            save_parties()
            await interaction.followup.send(f"Erro ao criar a party: `{error}`", ephemeral=True)
            return

        parties[party_id]["message_id"] = message.id
        save_parties()

        await interaction.followup.send(f"Party criada com sucesso em {channel.mention}: {message.jump_url}", ephemeral=True)
        await log_action(interaction.guild, f"🎮 <@{member.id}> criou a party **{parties[party_id]['title']}** `{party_id}` em {channel.mention}.")


class EditPartyModal(discord.ui.Modal, title="Editar Party"):
    def __init__(self, party_id: str):
        super().__init__()
        self.party_id = party_id
        data = parties[party_id]

        self.title_input = discord.ui.TextInput(label="Título da party", default=data.get("title", ""), max_length=100, required=True)
        self.capacity = discord.ui.TextInput(label="Vagas", default=str(data.get("capacity", 4)), max_length=2, required=True)
        self.time = discord.ui.TextInput(label="Horário", default=data.get("time", ""), max_length=120, required=False)
        self.description = discord.ui.TextInput(label="Descrição", default=data.get("description", ""), style=discord.TextStyle.paragraph, max_length=500, required=False)
        self.image_url = discord.ui.TextInput(label="Imagem por link", default=data.get("image_url", ""), max_length=300, required=False)

        self.add_item(self.title_input)
        self.add_item(self.capacity)
        self.add_item(self.time)
        self.add_item(self.description)
        self.add_item(self.image_url)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = parties.get(self.party_id)
        if not data:
            await interaction.followup.send("Essa party não existe mais.", ephemeral=True)
            return

        member = interaction.user
        if not isinstance(member, discord.Member) or not can_manage_party(member, data):
            await interaction.followup.send("Só o host ou a staff pode editar essa party.", ephemeral=True)
            return

        try:
            capacity_value = int(str(self.capacity.value).strip())
        except ValueError:
            await interaction.followup.send("O campo **Vagas** precisa ser um número.", ephemeral=True)
            return

        if capacity_value < 1 or capacity_value > 25:
            await interaction.followup.send("As vagas precisam ficar entre **1** e **25**.", ephemeral=True)
            return

        image = str(self.image_url.value).strip()
        if image and not image.lower().startswith(("http://", "https://")):
            await interaction.followup.send("O link da imagem precisa começar com `http://` ou `https://`.", ephemeral=True)
            return

        data["title"] = str(self.title_input.value).strip()
        data["capacity"] = capacity_value
        data["time"] = str(self.time.value).strip()
        data["description"] = str(self.description.value).strip()
        data["image_url"] = image

        while len(data.get("accepted", [])) > capacity_value:
            moved = data["accepted"].pop()
            data["queue"].insert(0, moved)

        save_parties()
        await update_party_message(self.party_id)
        await interaction.followup.send("Party editada com sucesso.", ephemeral=True)
        await log_action(interaction.guild, f"✏️ <@{member.id}> editou a party **{data['title']}** `{self.party_id}`.")


class ManagePartyView(discord.ui.View):
    def __init__(self, party_id: str):
        super().__init__(timeout=180)
        self.party_id = party_id

    @discord.ui.button(label="Editar Party", emoji="✏️", style=discord.ButtonStyle.primary)
    async def edit_party(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = parties.get(self.party_id)
        if not data:
            await interaction.response.send_message("Essa party não existe mais.", ephemeral=True)
            return

        member = interaction.user
        if not isinstance(member, discord.Member) or not can_manage_party(member, data):
            await interaction.response.send_message("Só o host ou a staff pode editar essa party.", ephemeral=True)
            return

        await interaction.response.send_modal(EditPartyModal(self.party_id))

    @discord.ui.button(label="Encerrar Party", emoji="🔒", style=discord.ButtonStyle.danger)
    async def close_party(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = parties.get(self.party_id)
        if not data:
            await interaction.response.send_message("Essa party não existe mais.", ephemeral=True)
            return

        member = interaction.user
        if not isinstance(member, discord.Member) or not can_manage_party(member, data):
            await interaction.response.send_message("Só o host ou a staff pode encerrar essa party.", ephemeral=True)
            return

        if data.get("status") == "closed":
            await interaction.response.send_message("Essa party já está encerrada.", ephemeral=True)
            return

        data["status"] = "closed"
        save_parties()
        await update_party_message(self.party_id)
        await interaction.response.send_message("Party encerrada.", ephemeral=True)
        await log_action(interaction.guild, f"🔒 <@{member.id}> encerrou a party **{data['title']}** `{self.party_id}`.")


class PartyView(discord.ui.View):
    def __init__(self, disabled: bool = False):
        super().__init__(timeout=None)
        if disabled:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True

    async def get_party(self, interaction: discord.Interaction) -> Optional[str]:
        if not interaction.message:
            await interaction.response.send_message("Não consegui identificar essa party.", ephemeral=True)
            return None

        party_id = find_party_by_message(interaction.message.id)
        if not party_id or party_id not in parties:
            await interaction.response.send_message("Essa party não existe mais no banco de dados.", ephemeral=True)
            return None
        return party_id

    @discord.ui.button(emoji="✅", label="Vou", style=discord.ButtonStyle.success, custom_id="party:accepted")
    async def accepted_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        party_id = await self.get_party(interaction)
        if not party_id:
            return

        data = parties[party_id]
        if data.get("status") != "open":
            await interaction.response.send_message("Essa party já foi encerrada.", ephemeral=True)
            return

        user_id = interaction.user.id
        capacity = int(data.get("capacity", 4))
        if user_id in data.get("accepted", []):
            await interaction.response.send_message("Você já marcou **Vou**.", ephemeral=True)
            return

        clean_user_from_party(data, user_id)
        if len(data["accepted"]) < capacity:
            data["accepted"].append(user_id)
            msg = "Você marcou **Vou**."
            log_msg = f"✅ <@{user_id}> marcou Vou na party **{data['title']}** `{party_id}`."
        else:
            data["queue"].append(user_id)
            msg = "A party está cheia. Você entrou na **fila**."
            log_msg = f"📋 <@{user_id}> entrou na fila da party **{data['title']}** `{party_id}`."

        save_parties()
        await interaction.response.send_message(msg, ephemeral=True)
        await log_action(interaction.guild, log_msg)
        await update_party_message(party_id)

    @discord.ui.button(emoji="❔", label="Talvez", style=discord.ButtonStyle.primary, custom_id="party:tentative")
    async def tentative_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        party_id = await self.get_party(interaction)
        if not party_id:
            return

        data = parties[party_id]
        if data.get("status") != "open":
            await interaction.response.send_message("Essa party já foi encerrada.", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in data.get("tentative", []):
            await interaction.response.send_message("Você já marcou **Talvez**.", ephemeral=True)
            return

        was_accepted = user_id in data.get("accepted", [])
        clean_user_from_party(data, user_id)
        data["tentative"].append(user_id)
        promoted = promote_from_queue(data) if was_accepted else None
        save_parties()

        msg = "Você marcou **Talvez**."
        if promoted:
            msg += f"\n<@{promoted}> foi puxado da fila."

        await interaction.response.send_message(msg, ephemeral=True)
        await log_action(interaction.guild, f"❔ <@{user_id}> marcou Talvez na party **{data['title']}** `{party_id}`.")
        await update_party_message(party_id)

    @discord.ui.button(emoji="❌", label="Não vou", style=discord.ButtonStyle.danger, custom_id="party:declined")
    async def declined_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        party_id = await self.get_party(interaction)
        if not party_id:
            return

        data = parties[party_id]
        if data.get("status") != "open":
            await interaction.response.send_message("Essa party já foi encerrada.", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in data.get("declined", []):
            await interaction.response.send_message("Você já marcou **Não vou**.", ephemeral=True)
            return

        was_accepted = user_id in data.get("accepted", [])
        clean_user_from_party(data, user_id)
        data["declined"].append(user_id)
        promoted = promote_from_queue(data) if was_accepted else None
        save_parties()

        msg = "Você marcou **Não vou**."
        if promoted:
            msg += f"\n<@{promoted}> foi puxado da fila."

        await interaction.response.send_message(msg, ephemeral=True)
        await log_action(interaction.guild, f"❌ <@{user_id}> marcou Não vou na party **{data['title']}** `{party_id}`.")
        await update_party_message(party_id)

    @discord.ui.button(emoji="⚙️", label="Gerenciar", style=discord.ButtonStyle.secondary, custom_id="party:manage")
    async def manage_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        party_id = await self.get_party(interaction)
        if not party_id:
            return

        data = parties[party_id]
        member = interaction.user
        if not isinstance(member, discord.Member) or not can_manage_party(member, data):
            await interaction.response.send_message("Só o host ou a staff pode gerenciar essa party.", ephemeral=True)
            return

        embed = discord.Embed(
            title="⚙️ Gerenciar Party",
            description=f"Party: **{data.get('title', 'Party')}**\nID: `{party_id}`\n\nEscolha uma ação abaixo.",
            color=guild_color(guild_id_from_interaction(interaction)),
        )
        await interaction.response.send_message(embed=embed, view=ManagePartyView(party_id), ephemeral=True)


class PartyChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Escolha o canal onde os convites das parties vão aparecer",
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        if not interaction.guild_id:
            await interaction.response.send_message("Use isso dentro de um servidor.", ephemeral=True)
            return
        channel = self.values[0]
        set_guild_config_value(interaction.guild_id, "party_channel_id", channel.id)
        await interaction.response.edit_message(content=None, embed=make_config_embed(interaction.guild_id), view=ConfigPanelView())
        await log_action(interaction.guild, f"⚙️ <@{interaction.user.id}> definiu o canal de convites como {channel.mention}.")


class LogChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Escolha o canal de logs",
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        if not interaction.guild_id:
            await interaction.response.send_message("Use isso dentro de um servidor.", ephemeral=True)
            return
        channel = self.values[0]
        set_guild_config_value(interaction.guild_id, "log_channel_id", channel.id)
        await interaction.response.edit_message(content=None, embed=make_config_embed(interaction.guild_id), view=ConfigPanelView())
        await log_action(interaction.guild, f"⚙️ <@{interaction.user.id}> definiu o canal de logs como {channel.mention}.")


class HostRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Escolha o cargo que pode criar parties", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        if not interaction.guild_id:
            await interaction.response.send_message("Use isso dentro de um servidor.", ephemeral=True)
            return
        role = self.values[0]
        set_guild_config_value(interaction.guild_id, "host_role_id", role.id)
        set_guild_config_value(interaction.guild_id, "everyone_can_create", False)
        await interaction.response.edit_message(content=None, embed=make_config_embed(interaction.guild_id), view=ConfigPanelView())
        await log_action(interaction.guild, f"⚙️ <@{interaction.user.id}> definiu o cargo Host como {role.mention}.")


class StaffRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Escolha o cargo da staff", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        if not interaction.guild_id:
            await interaction.response.send_message("Use isso dentro de um servidor.", ephemeral=True)
            return
        role = self.values[0]
        set_guild_config_value(interaction.guild_id, "staff_role_id", role.id)
        await interaction.response.edit_message(content=None, embed=make_config_embed(interaction.guild_id), view=ConfigPanelView())
        await log_action(interaction.guild, f"⚙️ <@{interaction.user.id}> definiu o cargo Staff como {role.mention}.")


class ManualChannelModal(discord.ui.Modal, title="Definir canal por ID"):
    def __init__(self, target_key: str, title_text: str):
        super().__init__(title=title_text)
        self.target_key = target_key
        self.channel_id_input = discord.ui.TextInput(label="ID do canal", placeholder="Ex: 123456789012345678", max_length=25, required=True)
        self.add_item(self.channel_id_input)

    async def on_submit(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        if not interaction.guild_id:
            await interaction.response.send_message("Use isso dentro de um servidor.", ephemeral=True)
            return

        try:
            channel_id = int(str(self.channel_id_input.value).strip())
        except ValueError:
            await interaction.response.send_message("O ID do canal precisa ser numérico.", ephemeral=True)
            return

        channel = await fetch_text_channel(channel_id)
        if not channel:
            await interaction.response.send_message(
                "Não achei esse canal. Confira o ID e se o bot tem permissão para ver o canal.",
                ephemeral=True,
            )
            return

        if channel.guild.id != interaction.guild_id:
            await interaction.response.send_message("Esse canal não pertence a este servidor.", ephemeral=True)
            return

        set_guild_config_value(interaction.guild_id, self.target_key, channel_id)
        await interaction.response.send_message(f"Canal definido: {channel.mention}", ephemeral=True)
        await log_action(interaction.guild, f"⚙️ <@{interaction.user.id}> definiu `{self.target_key}` como {channel.mention} via ID.")


class ManualRoleModal(discord.ui.Modal, title="Definir cargo por ID"):
    def __init__(self, target_key: str, title_text: str):
        super().__init__(title=title_text)
        self.target_key = target_key
        self.role_id_input = discord.ui.TextInput(label="ID do cargo", placeholder="Ex: 123456789012345678", max_length=25, required=True)
        self.add_item(self.role_id_input)

    async def on_submit(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        if not interaction.guild:
            await interaction.response.send_message("Use isso dentro de um servidor.", ephemeral=True)
            return

        try:
            role_id = int(str(self.role_id_input.value).strip())
        except ValueError:
            await interaction.response.send_message("O ID do cargo precisa ser numérico.", ephemeral=True)
            return

        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("Não achei esse cargo neste servidor. Confira o ID.", ephemeral=True)
            return

        set_guild_config_value(interaction.guild.id, self.target_key, role_id)
        if self.target_key == "host_role_id":
            set_guild_config_value(interaction.guild.id, "everyone_can_create", False)
        await interaction.response.send_message(f"Cargo definido: {role.mention}", ephemeral=True)
        await log_action(interaction.guild, f"⚙️ <@{interaction.user.id}> definiu `{self.target_key}` como {role.mention} via ID.")


class ConfigColorModal(discord.ui.Modal, title="Alterar cor do embed"):
    color_value = discord.ui.TextInput(label="Cor decimal", placeholder="Ex: 16766720", max_length=8, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if await reject_if_not_staff(interaction):
            return
        if not interaction.guild_id:
            await interaction.response.send_message("Use isso dentro de um servidor.", ephemeral=True)
            return
        try:
            value = int(str(self.color_value.value).strip())
        except ValueError:
            await interaction.response.send_message("A cor precisa ser um número decimal.", ephemeral=True)
            return

        if value < 0 or value > 16777215:
            await interaction.response.send_message("A cor precisa estar entre `0` e `16777215`.", ephemeral=True)
            return

        set_guild_config_value(interaction.guild_id, "embed_color", value)
        await interaction.response.send_message(f"Cor alterada para `{value}`.", ephemeral=True)
        await log_action(interaction.guild, f"⚙️ <@{interaction.user.id}> alterou a cor do embed para `{value}`.")


class SelectOnlyView(discord.ui.View):
    def __init__(self, select: discord.ui.Select):
        super().__init__(timeout=180)
        self.add_item(select)


def make_config_embed(guild_id: int) -> discord.Embed:
    embed = discord.Embed(
        title="⚙️ Configuração do Party Bot",
        description=config_status_text(guild_id) + "\n\nUse os botões abaixo para alterar a configuração.",
        color=guild_color(guild_id),
    )
    embed.set_footer(text="Esse painel aparece só para quem usou o comando")
    return embed


class ConfigPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Canal de Convites", emoji="📢", style=discord.ButtonStyle.primary, row=0)
    async def set_party_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(
            content="Escolha o canal onde os convites das parties serão enviados:",
            embed=None,
            view=SelectOnlyView(PartyChannelSelect()),
        )

    @discord.ui.button(label="Canal de Logs", emoji="📜", style=discord.ButtonStyle.primary, row=0)
    async def set_log_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content="Escolha o canal de logs:", embed=None, view=SelectOnlyView(LogChannelSelect()))

    @discord.ui.button(label="Cargo Host", emoji="🎮", style=discord.ButtonStyle.secondary, row=1)
    async def set_host_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content="Escolha o cargo que pode criar parties:", embed=None, view=SelectOnlyView(HostRoleSelect()))

    @discord.ui.button(label="Cargo Staff", emoji="🛡️", style=discord.ButtonStyle.secondary, row=1)
    async def set_staff_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.edit_message(content="Escolha o cargo da staff:", embed=None, view=SelectOnlyView(StaffRoleSelect()))

    @discord.ui.button(label="ID Canal Convites", emoji="🔢", style=discord.ButtonStyle.secondary, row=2)
    async def set_party_channel_by_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.send_modal(ManualChannelModal("party_channel_id", "Canal de convites por ID"))

    @discord.ui.button(label="ID Canal Logs", emoji="🔢", style=discord.ButtonStyle.secondary, row=2)
    async def set_log_channel_by_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.send_modal(ManualChannelModal("log_channel_id", "Canal de logs por ID"))

    @discord.ui.button(label="ID Cargo Host", emoji="🔢", style=discord.ButtonStyle.secondary, row=3)
    async def set_host_role_by_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.send_modal(ManualRoleModal("host_role_id", "Cargo Host por ID"))

    @discord.ui.button(label="ID Cargo Staff", emoji="🔢", style=discord.ButtonStyle.secondary, row=3)
    async def set_staff_role_by_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.send_modal(ManualRoleModal("staff_role_id", "Cargo Staff por ID"))

    @discord.ui.button(label="Todos podem criar", emoji="👥", style=discord.ButtonStyle.secondary, row=4)
    async def toggle_everyone_can_create(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        if not interaction.guild_id:
            await interaction.response.send_message("Use isso dentro de um servidor.", ephemeral=True)
            return
        guild_conf = get_guild_config(interaction.guild_id)
        new_value = not bool(guild_conf.get("everyone_can_create", False))
        set_guild_config_value(interaction.guild_id, "everyone_can_create", new_value)
        await interaction.response.edit_message(content=None, embed=make_config_embed(interaction.guild_id), view=ConfigPanelView())

    @discord.ui.button(label="Ping @everyone", emoji="📣", style=discord.ButtonStyle.secondary, row=4)
    async def toggle_ping_everyone(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        if not interaction.guild_id:
            await interaction.response.send_message("Use isso dentro de um servidor.", ephemeral=True)
            return
        guild_conf = get_guild_config(interaction.guild_id)
        new_value = not bool(guild_conf.get("ping_everyone", True))
        set_guild_config_value(interaction.guild_id, "ping_everyone", new_value)
        await interaction.response.edit_message(content=None, embed=make_config_embed(interaction.guild_id), view=ConfigPanelView())

    @discord.ui.button(label="Cor", emoji="🎨", style=discord.ButtonStyle.secondary, row=4)
    async def set_embed_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        await interaction.response.send_modal(ConfigColorModal())

    @discord.ui.button(label="Atualizar", emoji="🔄", style=discord.ButtonStyle.success, row=4)
    async def refresh_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await reject_if_not_staff(interaction):
            return
        if not interaction.guild_id:
            await interaction.response.send_message("Use isso dentro de um servidor.", ephemeral=True)
            return
        await interaction.response.edit_message(content=None, embed=make_config_embed(interaction.guild_id), view=ConfigPanelView())


@bot.event
async def on_ready():
    global _commands_synced

    print(f"Logado como {bot.user}. Servidores: {len(bot.guilds)}")
    bot.add_view(HubView())
    bot.add_view(PartyView())

    if _commands_synced:
        return

    try:
        synced = await bot.tree.sync()
        _commands_synced = True
        print(f"Comandos globais sincronizados: {len(synced)}")
    except Exception as error:
        print(f"Erro ao sincronizar comandos: {error}")


@bot.tree.command(name="setup-party-hub", description="Cria o Hub de Parties no canal onde o comando foi usado.")
async def setup_party_hub(interaction: discord.Interaction):
    member = interaction.user
    if not interaction.guild or not isinstance(member, discord.Member):
        await interaction.response.send_message("Use esse comando dentro de um servidor.", ephemeral=True)
        return

    if not is_staff(member):
        await interaction.response.send_message("Você precisa ser staff ou ter **Gerenciar servidor** para criar o Hub.", ephemeral=True)
        return

    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use esse comando em um canal de texto normal.", ephemeral=True)
        return

    try:
        message = await interaction.channel.send(embed=make_hub_embed(interaction.guild.id), view=HubView())
    except discord.Forbidden:
        await interaction.response.send_message("Não tenho permissão para enviar mensagem nesse canal.", ephemeral=True)
        return
    except discord.HTTPException as error:
        await interaction.response.send_message(f"Erro ao criar o Hub: `{error}`", ephemeral=True)
        return

    await interaction.response.send_message(f"Hub criado nesse canal: {message.jump_url}", ephemeral=True)
    await log_action(interaction.guild, f"🧩 <@{member.id}> criou o Hub de Parties em {interaction.channel.mention}.")


@bot.tree.command(name="party-config-panel", description="Abre o painel de configuração do Party Bot neste servidor.")
async def party_config_panel(interaction: discord.Interaction):
    member = interaction.user
    if not interaction.guild or not isinstance(member, discord.Member):
        await interaction.response.send_message("Use esse comando dentro de um servidor.", ephemeral=True)
        return

    if not is_staff(member):
        await interaction.response.send_message("Você precisa ser staff ou ter **Gerenciar servidor** para configurar o bot.", ephemeral=True)
        return

    await interaction.response.send_message(embed=make_config_embed(interaction.guild.id), view=ConfigPanelView(), ephemeral=True)


@bot.tree.command(name="party-list", description="Lista parties abertas deste servidor.")
async def party_list(interaction: discord.Interaction):
    guild_id = guild_id_from_interaction(interaction)
    open_parties = [
        (party_id, data)
        for party_id, data in parties.items()
        if data.get("status") == "open" and int(data.get("guild_id", 0) or 0) == guild_id
    ]

    if not open_parties:
        await interaction.response.send_message("Não tem nenhuma party aberta.", ephemeral=True)
        return

    lines = []
    for party_id, data in open_parties[:20]:
        channel_id = data.get("channel_id")
        message_id = data.get("message_id")
        accepted = len(data.get("accepted", []))
        capacity = data.get("capacity", 0)
        lines.append(
            f"🎮 **{data.get('title', 'Party')}** — `{accepted}/{capacity}` — "
            f"Host: <@{data.get('host_id')}> — "
            f"[abrir](https://discord.com/channels/{interaction.guild_id}/{channel_id}/{message_id})"
        )

    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@bot.tree.command(name="party-clean-closed", description="Remove do banco as parties encerradas deste servidor.")
async def party_clean_closed(interaction: discord.Interaction):
    member = interaction.user
    if not interaction.guild or not isinstance(member, discord.Member) or not is_staff(member):
        await interaction.response.send_message("Só a staff pode limpar parties encerradas.", ephemeral=True)
        return

    guild_id = interaction.guild.id
    before = len(parties)
    closed_ids = [
        party_id
        for party_id, data in parties.items()
        if data.get("status") == "closed" and int(data.get("guild_id", 0) or 0) == guild_id
    ]

    for party_id in closed_ids:
        parties.pop(party_id, None)

    save_parties()
    await interaction.response.send_message(f"Limpeza concluída. Removidas: **{before - len(parties)}** parties encerradas.", ephemeral=True)


if not TOKEN or TOKEN in ("COLE_SEU_TOKEN_AQUI", "SEU_TOKEN", "COLOQUE_SEU_TOKEN_AQUI"):
    raise RuntimeError("Coloque o token do bot em DISCORD_TOKEN no Railway ou no config.json.")

bot.run(TOKEN)
