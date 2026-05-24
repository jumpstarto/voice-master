import discord
import keep_alive
from discord.ext import commands, tasks
import aiosqlite
from datetime import datetime
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="-", intents=intents)

CREATE_NAME = "➕ Join To Create"
CATEGORY_NAME = "VoiceMaster"

vc_owners = {}
join_times = {}

# ---------------- DATABASE ----------------

async def setup_db():
    async with aiosqlite.connect("database.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS voice_time (
            user_id INTEGER,
            time INTEGER
        )
        """)
        await db.commit()

# ---------------- AUTO MESSAGE WHEN ADDED ----------------

@bot.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send("Run `-setup` to setup VoiceMaster")
            break

# ---------------- VOICE TRACKING ----------------

@bot.event
async def on_voice_state_update(member, before, after):

    # TRACK ALL USERS (NOT JUST BOT VCs)
    if after.channel:
        join_times[member.id] = datetime.now()

    if before.channel and member.id in join_times:
        seconds = int((datetime.now() - join_times[member.id]).total_seconds())
        del join_times[member.id]

        async with aiosqlite.connect("database.db") as db:
            await db.execute(
                "INSERT INTO voice_time VALUES (?, ?)",
                (member.id, seconds)
            )
            await db.commit()

    # CREATE PRIVATE VC
    if after.channel and after.channel.name == CREATE_NAME:
        category = discord.utils.get(member.guild.categories, name=CATEGORY_NAME)
        vc = await member.guild.create_voice_channel(
            name=f"{member.name}'s VC",
            category=category
        )

        vc_owners[vc.id] = member.id
        await member.move_to(vc)

        # CREATE CONTROL TEXT CHANNEL
        txt = await member.guild.create_text_channel(
            name=f"{member.name}-vc",
            category=category
        )

        await txt.set_permissions(member, read_messages=True, send_messages=True)
        await txt.set_permissions(member.guild.default_role, read_messages=False)

        embed = discord.Embed(
            title="🎟️ Lottery Interface",
            description=(
                "🔒 Lock VC\n🔓 Unlock VC\n❌ Kick\n👑 Claim\n"
                "👥 Limit\n✏️ Rename\n🔇 Mute\n🎤 Unmute"
            ),
            color=0x2b2d31
        )

        await txt.send(embed=embed, view=Panel())

    # DELETE VC + TEXT
    if before.channel and before.channel.id in vc_owners:
        if len(before.channel.members) == 0:
            category = before.channel.category

            # delete text channel
            for ch in category.text_channels:
                if before.channel.name.split("'")[0] in ch.name:
                    await ch.delete()

            await before.channel.delete()
            del vc_owners[before.channel.id]

# ---------------- PANEL ----------------

class Panel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def owner(self, interaction):
        vc = interaction.user.voice.channel
        return vc_owners.get(vc.id) == interaction.user.id

    async def fail(self, interaction):
        await interaction.response.send_message("Not VC owner", ephemeral=True)

    @discord.ui.button(emoji="🔒", style=discord.ButtonStyle.secondary)
    async def lock(self, interaction, _):
        if not self.owner(interaction): return await self.fail(interaction)
        vc = interaction.user.voice.channel
        await vc.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message("Locked", ephemeral=True)

    @discord.ui.button(emoji="🔓", style=discord.ButtonStyle.secondary)
    async def unlock(self, interaction, _):
        if not self.owner(interaction): return await self.fail(interaction)
        vc = interaction.user.voice.channel
        await vc.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.response.send_message("Unlocked", ephemeral=True)

    @discord.ui.button(emoji="❌", style=discord.ButtonStyle.danger)
    async def kick(self, interaction, _):
        if not self.owner(interaction): return await self.fail(interaction)
        for m in interaction.user.voice.channel.members:
            if m != interaction.user:
                await m.move_to(None)
        await interaction.response.send_message("Kicked all", ephemeral=True)

    @discord.ui.button(emoji="👑", style=discord.ButtonStyle.primary)
    async def claim(self, interaction, _):
        vc = interaction.user.voice.channel
        vc_owners[vc.id] = interaction.user.id
        await interaction.response.send_message("Claimed", ephemeral=True)

    @discord.ui.button(emoji="👥", style=discord.ButtonStyle.secondary)
    async def limit(self, interaction, _):
        if not self.owner(interaction): return await self.fail(interaction)
        await interaction.response.send_modal(LimitModal())

    @discord.ui.button(emoji="✏️", style=discord.ButtonStyle.secondary)
    async def rename(self, interaction, _):
        if not self.owner(interaction): return await self.fail(interaction)
        await interaction.response.send_modal(RenameModal())

    @discord.ui.button(emoji="🔇", style=discord.ButtonStyle.secondary)
    async def mute(self, interaction, _):
        if not self.owner(interaction): return await self.fail(interaction)
        for m in interaction.user.voice.channel.members:
            if m != interaction.user:
                await m.edit(mute=True)
        await interaction.response.send_message("Muted", ephemeral=True)

    @discord.ui.button(emoji="🎤", style=discord.ButtonStyle.success)
    async def unmute(self, interaction, _):
        if not self.owner(interaction): return await self.fail(interaction)
        for m in interaction.user.voice.channel.members:
            if m != interaction.user:
                await m.edit(mute=False)
        await interaction.response.send_message("Unmuted", ephemeral=True)

# ---------------- MODALS ----------------

class RenameModal(discord.ui.Modal, title="Rename VC"):
    name = discord.ui.TextInput(label="New Name")

    async def on_submit(self, interaction):
        await interaction.user.voice.channel.edit(name=self.name.value)
        await interaction.response.send_message("Renamed", ephemeral=True)

class LimitModal(discord.ui.Modal, title="Set Limit"):
    limit = discord.ui.TextInput(label="User Limit")

    async def on_submit(self, interaction):
        await interaction.user.voice.channel.edit(user_limit=int(self.limit.value))
        await interaction.response.send_message("Limit set", ephemeral=True)

# ---------------- SETUP COMMAND ----------------

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    category = discord.utils.get(ctx.guild.categories, name=CATEGORY_NAME)
    if not category:
        category = await ctx.guild.create_category(CATEGORY_NAME)

    await ctx.guild.create_voice_channel(CREATE_NAME, category=category)

    await ctx.send("✅ VoiceMaster setup complete")

# ---------------- LEADERBOARD ----------------

@bot.command()
async def leaderboard(ctx):
    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute("""
        SELECT user_id, SUM(time) as total
        FROM voice_time
        GROUP BY user_id
        ORDER BY total DESC
        LIMIT 10
        """)
        rows = await cursor.fetchall()

    text = ""
    for i, (uid, total) in enumerate(rows, 1):
        user = await bot.fetch_user(uid)
        text += f"{i}. {user.name} - {total//3600}h\n"

    embed = discord.Embed(title="🏆 Voice Leaderboard", description=text)
    await ctx.send(embed=embed)

# ---------------- RUN ----------------

# The bot token must be set via the DISCORD_TOKEN environment variable.
# In Railway: add DISCORD_TOKEN to your service's environment variables.
token = os.getenv("MTUwODE2MDMwNzk4MDI3MTY5Ng.GUVilp.TuTI0NV0fNCs8H75KFrxb28RbdHZhacqO20pz8")
if not token:
    raise RuntimeError(
        "MTUwODE2MDMwNzk4MDI3MTY5Ng.GUVilp.TuTI0NV0fNCs8H75KFrxb28RbdHZhacqO20pz8"
        "Add it to your Railway service environment variables."
    )

bot.run(token)
