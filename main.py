import discord
from discord.ext import commands
import asyncio
import os
import sys
import threading
import random
import time
import json
from flask import Flask

OWNER_ID = 1281497404931051541
dm_history = {}
active_dm_sessions = {}
LOG_CHANNEL_ID = 1344933909778792500
warnings_data = {}

# Leveling and Economy Data
leveling_data = {} # user_id -> {"xp": 0, "level": 1, "last_daily": 0}

def load_leveling():
    global leveling_data
    if os.path.exists("leveling.json"):
        try:
            with open("leveling.json", "r") as f:
                leveling_data = json.load(f)
        except:
            leveling_data = {}

def save_leveling():
    try:
        with open("leveling.json", "w") as f:
            json.dump(leveling_data, f)
    except:
        pass

# Authorized users for -autotrain all
autotrain_authorized = set()

def load_autotrain_auth():
    global autotrain_authorized
    if os.path.exists("autotrain_auth.json"):
        try:
            with open("autotrain_auth.json", "r") as f:
                autotrain_authorized = set(json.load(f))
        except:
            autotrain_authorized = set()

def save_autotrain_auth():
    try:
        with open("autotrain_auth.json", "w") as f:
            json.dump(list(autotrain_authorized), f)
    except:
        pass

load_autotrain_auth()

load_leveling()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="-", intents=intents, help_command=None)

welcome_settings = {}
goodbye_settings = {}
system_status = {}

def load_settings():
    try:
        if os.path.exists("welcome_settings.txt"):
            with open("welcome_settings.txt", "r") as f:
                for line in f:
                    parts = line.strip().split("|")
                    if len(parts) == 3:
                        guild_id, channel_id, image_url = parts
                        welcome_settings[int(guild_id)] = {"channel": int(channel_id), "image": image_url}
        if os.path.exists("goodbye_settings.txt"):
            with open("goodbye_settings.txt", "r") as f:
                for line in f:
                    parts = line.strip().split("|")
                    if len(parts) == 3:
                        guild_id, channel_id, image_url = parts
                        goodbye_settings[int(guild_id)] = {"channel": int(channel_id), "image": image_url}
        if os.path.exists("system_status.txt"):
            with open("system_status.txt", "r") as f:
                for line in f:
                    parts = line.strip().split("|")
                    if len(parts) == 2:
                        guild_id, status = parts
                        system_status[int(guild_id)] = status == "True"
        print("Welcome/Goodbye settings loaded.")
    except Exception as e:
        print(f"Error loading settings: {e}")

def save_settings():
    try:
        with open("welcome_settings.txt", "w") as f:
            for gid, data in welcome_settings.items():
                f.write(f"{gid}|{data['channel']}|{data['image']}\n")
        with open("goodbye_settings.txt", "w") as f:
            for gid, data in goodbye_settings.items():
                f.write(f"{gid}|{data['channel']}|{data['image']}\n")
        with open("system_status.txt", "w") as f:
            for gid, status in system_status.items():
                f.write(f"{gid}|{status}\n")
    except Exception as e:
        print(f"Error saving settings: {e}")

def load_warnings():
    if os.path.exists("warnings.txt"):
        try:
            with open("warnings.txt", "r") as f:
                for line in f:
                    parts = line.strip().split("|")
                    if len(parts) >= 2:
                        user_id = int(parts[0])
                        reasons = parts[1:]
                        warnings_data[user_id] = reasons
        except:
            pass

def save_warnings():
    try:
        with open("warnings.txt", "w") as f:
            for uid, reasons in warnings_data.items():
                f.write(f"{uid}|{'|'.join(reasons)}\n")
    except:
        pass

load_settings()
load_warnings()

restart_channel = None
restart_user = None

@bot.event
async def on_ready():
    global restart_channel, restart_user
    print(f"Bot logged in as {bot.user}")
    if restart_channel and restart_user:
        channel = bot.get_channel(restart_channel)
        if channel:
            await channel.send(f"✅ <@{restart_user}> The bot has fully restarted and is back online.")
        restart_channel = None
        restart_user = None

@bot.event
async def on_member_join(member):
    if system_status.get(member.guild.id) and member.guild.id in welcome_settings:
        data = welcome_settings[member.guild.id]
        channel = member.guild.get_channel(data['channel'])
        if channel:
            embed = discord.Embed(title=f"Welcome to {member.guild.name}!", description=f"Glad to have you here, {member.mention}!", color=0x00FF00)
            embed.set_image(url=data['image'])
            await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    if system_status.get(member.guild.id) and member.guild.id in goodbye_settings:
        data = goodbye_settings[member.guild.id]
        channel = member.guild.get_channel(data['channel'])
        if channel:
            embed = discord.Embed(title="Goodbye!", description=f"{member.name} has left. We'll miss you!", color=0xFF0000)
            embed.set_image(url=data['image'])
            await channel.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def togglewelcome(ctx, status: str = None):
    if status is None:
        current = system_status.get(ctx.guild.id, False)
        await ctx.send(f"The welcome system is currently **{'ENABLED' if current else 'DISABLED'}**.")
        return
    if status.lower() == "on":
        system_status[ctx.guild.id] = True
        save_settings()
        await ctx.send("✅ Welcome and Goodbye messages have been **ENABLED**.")
    elif status.lower() == "off":
        system_status[ctx.guild.id] = False
        save_settings()
        await ctx.send("❌ Welcome and Goodbye messages have been **DISABLED**.")

@bot.command(name="welcome")
@commands.has_permissions(manage_guild=True)
async def welcome_command(ctx, channel: discord.TextChannel = None):
    if not channel or not ctx.message.attachments:
        await ctx.send("Usage: `-welcome #channel` (attach image)")
        return
    image_url = ctx.message.attachments[0].url
    welcome_settings[ctx.guild.id] = {"channel": channel.id, "image": image_url}
    save_settings()
    await ctx.send("✅ Welcome settings saved!")

@bot.command(name="bye")
@commands.has_permissions(manage_guild=True)
async def bye_command(ctx, channel: discord.TextChannel = None):
    if not channel or not ctx.message.attachments:
        await ctx.send("Usage: `-bye #channel` (attach image)")
        return
    image_url = ctx.message.attachments[0].url
    goodbye_settings[ctx.guild.id] = {"channel": channel.id, "image": image_url}
    save_settings()
    await ctx.send("✅ Goodbye settings saved!")

@bot.command()
async def viewdms(ctx, user: discord.User = None):
    if ctx.author.id != OWNER_ID: return
    if not user: return await ctx.send("Usage: `-viewdms <user>`")
    history = dm_history.get(user.id, [])
    if not history: return await ctx.send("No history.")
    history_text = "\n".join(history[-15:])
    embed = discord.Embed(title="Recent DMs with", description=f"**{user.name}#{user.discriminator}**\nUser ID: {user.id}\n\n**Last Messages:**\n{history_text}", color=0x2ecc71)
    await ctx.send(embed=embed)

@bot.command()
async def dmc(ctx, user: discord.User = None):
    if ctx.author.id != OWNER_ID: return
    if not user: return await ctx.send("Usage: `-dmc <user>`")
    
    history = dm_history.get(user.id, [])
    history_text = "\n".join(history[-15:]) if history else "No previous messages found."
    embed = discord.Embed(title="Recent DMs with", description=f"**{user.name}#{user.discriminator}**\nUser ID: {user.id}\n\n**Last Messages:**\n{history_text}", color=0x2ecc71)
    await ctx.send(embed=embed)
    
    await ctx.send(f"Control established with **{user.name}**. Type to send. Type `exit` to stop.")
    active_dm_sessions[ctx.author.id] = user

    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    while True:
        try:
            msg = await bot.wait_for('message', check=check, timeout=600.0)
            if msg.content.lower() == 'exit':
                active_dm_sessions.pop(ctx.author.id, None)
                await ctx.send("Exited.")
                break
            try:
                await user.send(msg.content)
                await msg.add_reaction("✅")
                dm_history.setdefault(user.id, []).append(f"{bot.user.name}: {msg.content}")
            except:
                active_dm_sessions.pop(ctx.author.id, None)
                await ctx.send("Failed to send.")
                break
        except asyncio.TimeoutError:
            active_dm_sessions.pop(ctx.author.id, None)
            await ctx.send("Timed out.")
            break

@bot.command()
async def dm(ctx, user: discord.User = None, *, message: str = None):
    if ctx.author.id != OWNER_ID: return
    if not user or not message: return
    try:
        await user.send(message)
        await ctx.message.add_reaction("✅")
        dm_history.setdefault(user.id, []).append(f"{bot.user.name}: {message}")
    except: 
        await ctx.send("Failed.")

@bot.command()
async def changepfp(ctx):
    if ctx.author.id != OWNER_ID: return
    if not ctx.message.attachments:
        await ctx.send("Please attach an image to change the profile picture.")
        return
    try:
        image_bytes = await ctx.message.attachments[0].read()
        await bot.user.edit(avatar=image_bytes)
        await ctx.send("✅ Profile picture updated successfully!")
    except Exception as e:
        await ctx.send(f"❌ Failed to update profile picture: {e}")

@bot.command()
async def changename(ctx, *, name: str = None):
    if ctx.author.id != OWNER_ID: return
    if not name:
        await ctx.send("Usage: `-changename <new name>`")
        return
    try:
        await bot.user.edit(username=name)
        await ctx.send(f"✅ Bot name updated to: **{name}**")
    except Exception as e:
        await ctx.send(f"❌ Failed to update bot name: {e}")

@bot.command()
async def role(ctx, action: str = None, user: discord.Member = None, role: discord.Role = None):
    if ctx.author.id != OWNER_ID: return
    if not action or not user or not role:
        await ctx.send("Usage: `-role add <@user/ID> <@role/ID>` or `-role remove <@user/ID> <@role/ID>`")
        return
    
    if action.lower() == "add":
        try:
            await user.add_roles(role)
            await ctx.send(f"✅ Added role **{role.name}** to **{user.display_name}**")
        except Exception as e:
            await ctx.send(f"❌ Failed to add role: {e}")
    elif action.lower() == "remove":
        try:
            await user.remove_roles(role)
            await ctx.send(f"✅ Removed role **{role.name}** from **{user.display_name}**")
        except Exception as e:
            await ctx.send(f"❌ Failed to remove role: {e}")
    else:
        await ctx.send("Invalid action! Use `add` or `remove`.")

@bot.command()
async def warn(ctx, user: discord.Member = None, *, reason: str = "No reason provided"):
    if ctx.author.id != OWNER_ID: return
    if not user: return await ctx.send("Usage: `-warn @user [reason]`")
    warnings_data.setdefault(user.id, []).append(reason)
    save_warnings()
    await ctx.send(f"⚠️ **{user.display_name}** has been warned. Reason: {reason}")
    try: 
        await user.send(f"You have been warned in **{ctx.guild.name}** for: {reason}")
    except: 
        pass

@bot.command()
async def warnings(ctx, user: discord.Member = None):
    if ctx.author.id != OWNER_ID: return
    if not user: return await ctx.send("Usage: `-warnings @user`")
    user_warnings = warnings_data.get(user.id, [])
    if not user_warnings:
        return await ctx.send(f"**{user.display_name}** has no warnings.")
    warn_list = "\n".join([f"{i+1}. {r}" for i, r in enumerate(user_warnings)])
    await ctx.send(f"**Warnings for {user.display_name}:**\n{warn_list}")

@bot.command()
async def clearwarnings(ctx, user: discord.Member = None):
    if ctx.author.id != OWNER_ID: return
    if not user: return await ctx.send("Usage: `-clearwarnings @user`")
    if user.id in warnings_data:
        del warnings_data[user.id]
        save_warnings()
        await ctx.send(f"✅ Cleared all warnings for **{user.display_name}**.")
    else:
        await ctx.send(f"**{user.display_name}** had no warnings to clear.")

@bot.command(name="poll")
async def poll_command(ctx, *, content: str = None):
    if ctx.author.id != OWNER_ID: return
    if not content: return await ctx.send("Usage: `-poll Question | Option1 | Option2...`")
    try: 
        await ctx.message.delete()
    except: 
        pass
    parts = [p.strip() for p in content.split("|")]
    if len(parts) < 2: return
    question = parts[0]
    options = parts[1:]
    if len(options) > 10:
        return await ctx.send("Max 10 options.")
    reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    description = ""
    for i, option in enumerate(options):
        description += f"{reactions[i]} {option}\n"
    embed = discord.Embed(title=f"📊 {question}", description=description, color=0x3498db)
    poll_msg = await ctx.send(embed=embed)
    for i in range(len(options)):
        await poll_msg.add_reaction(reactions[i])

@bot.command(name="lock")
async def lock_channel(ctx, channel: discord.TextChannel = None):
    if ctx.author.id != OWNER_ID: return
    channel = channel or ctx.channel
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    try:
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"🔒 **{channel.name}** has been locked.")
    except Exception as e:
        await ctx.send(f"❌ Failed to lock channel: {e}")

@bot.command(name="unlock")
async def unlock_channel(ctx, channel: discord.TextChannel = None):
    if ctx.author.id != OWNER_ID: return
    channel = channel or ctx.channel
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = True
    try:
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"🔓 **{channel.name}** has been unlocked.")
    except Exception as e:
        await ctx.send(f"❌ Failed to unlock channel: {e}")

@bot.command()
async def link(ctx):
    if ctx.author.id != OWNER_ID: return
    invite_url = "https://discord.com/oauth2/authorize?client_id=1342781411135983647&permissions=8&integration_type=0&scope=bot"
    try:
        await ctx.author.send(invite_url)
        await ctx.send("✅ Invite link sent to your DMs.")
    except:
        await ctx.send(f"❌ Couldn't send DM. Here it is: {invite_url}")

@bot.command()
async def servers(ctx):
    if ctx.author.id != OWNER_ID: return
    guilds = bot.guilds
    if not guilds:
        await ctx.send("The bot is not in any servers.")
        return
    server_list = "\n".join([f"{i+1}. {g.name} ({g.id})" for i, g in enumerate(guilds)])
    await ctx.send(f"**Servers I'm in:**\n{server_list}\n\nType the number of the server.")
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        try:
            index = int(msg.content) - 1
            selected_guild = guilds[index]
        except (ValueError, IndexError):
            await ctx.send("Invalid selection.")
            return
    except asyncio.TimeoutError:
        await ctx.send("Timed out.")
        return
    
    await ctx.send(f"Would you like me to leave **{selected_guild.name}** or invite you? (Type: leave or invite)")
    
    try:
        action_msg = await bot.wait_for('message', check=check, timeout=60.0)
        action = action_msg.content.lower()
        
        if action == "leave":
            await selected_guild.leave()
            await ctx.send(f"✅ Left **{selected_guild.name}**.")
        elif action == "invite":
            invite = await selected_guild.text_channels[0].create_invite(max_uses=1, max_age=3600)
            await ctx.send(f"✅ Invite link: {invite}")
        else:
            await ctx.send("Invalid action. Say 'leave' or 'invite'.")
    except asyncio.TimeoutError:
        await ctx.send("Timed out.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
async def ping(ctx):
    """Check the bot's latency."""
    await ctx.send(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    """Get information about a user."""
    member = member or ctx.author
    roles = [role.name for role in member.roles if role.name != "@everyone"]
    embed = discord.Embed(title=f"👤 User Info - {member.name}", color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name=f"Roles ({len(roles)})", value=", ".join(roles) if roles else "None", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    """Get information about the server."""
    guild = ctx.guild
    embed = discord.Embed(title=f"🏰 Server Info - {guild.name}", color=0x7289DA)
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Owner", value=guild.owner, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Created At", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Channels", value=f"Text: {len(guild.text_channels)} | Voice: {len(guild.voice_channels)}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def coinflip(ctx):
    """Flip a coin!"""
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 It's **{result}**!")

@bot.command()
async def dice(ctx, sides: int = 6):
    """Roll a dice! Usage: -dice [sides]"""
    if sides < 2: return await ctx.send("Dice must have at least 2 sides!")
    result = random.randint(1, sides)
    await ctx.send(f"🎲 You rolled a **{result}**!")

@bot.command()
async def purge(ctx, amount: int):
    """Delete a number of messages. Usage: -purge <amount>"""
    if not ctx.author.guild_permissions.manage_messages:
        return await ctx.send("❌ You need 'Manage Messages' permission.")
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Deleted {amount} messages.", delete_after=3)

@bot.command()
async def restart(ctx):
    global restart_channel, restart_user
    if ctx.author.id != OWNER_ID:
        return
    restart_channel = ctx.channel.id
    restart_user = ctx.author.id
    await ctx.reply("🔄 Restarting bot...")
    os.execv(sys.executable, ['python'] + sys.argv)

owner_lock = False
autotrain_tasks = {}   # user_id -> asyncio.Task (train only)
autoall_tasks   = {}   # user_id -> asyncio.Task (all cooldowns)

@bot.command()
async def ownerlock(ctx):
    global owner_lock
    if ctx.author.id != OWNER_ID:
        return
    owner_lock = not owner_lock
    if owner_lock:
        await ctx.reply("🔒 Owner lock enabled. Only the bot owner can use commands.")
    else:
        await ctx.reply("🔓 Owner lock disabled. Everyone can use commands again.")

@bot.check
async def global_command_check(ctx):
    # Block non-owners from using any commands in DMs
    if isinstance(ctx.channel, discord.DMChannel) and ctx.author.id != OWNER_ID:
        return False
    if owner_lock and ctx.author.id != OWNER_ID:
        return False
    return True

# --- DBZ Economy & Leveling Commands ---

def get_user_data(user_id: str):
    """Get or create user data entry."""
    if user_id not in leveling_data:
        leveling_data[user_id] = {
            "xp": 0, "level": 1, "zeni": 0,
            "last_daily": 0, "last_train": 0, "last_raid": 0, "last_fight": 0,
            "no_cooldown": False,
            "transformations": ["base"],
            "active_transformation": None,
            "inventory": {},
            "dragon_balls": [],
            "awaiting_wish": False,
        }
    d = leveling_data[user_id]
    d.setdefault("zeni", 0)
    d.setdefault("last_train", 0)
    d.setdefault("last_raid", 0)
    d.setdefault("last_fight", 0)
    d.setdefault("no_cooldown", False)
    d.setdefault("transformations", ["base"])
    d.setdefault("active_transformation", None)
    d.setdefault("inventory", {})
    d.setdefault("dragon_balls", [])
    d.setdefault("awaiting_wish", False)
    d.setdefault("train_upgrade", 1)
    d.setdefault("daily_upgrade", 1)
    return d

def check_level_up(user_id: str):
    """Check and apply level ups. Returns new level if leveled up, else None."""
    data = leveling_data[user_id]
    xp_needed = data["level"] * 500
    if data["xp"] >= xp_needed:
        data["level"] += 1
        data["xp"] -= xp_needed
        return data["level"]
    return None

def get_effective_power_level(user_id: str) -> int:
    """Returns power level multiplied by active transformation."""
    data = get_user_data(user_id)
    base = data["level"]
    key = data.get("active_transformation")
    if key and key in TRANSFORMATIONS:
        return base * TRANSFORMATIONS[key]["multiplier"]
    return base

# Capsule Shop Items
CAPSULE_SHOP = {
    "1": {"name": "🥗 Senzu Bean", "desc": "+200 XP boost", "price": 500, "xp_bonus": 200},
    "2": {"name": "💊 Hyperbolic Time Capsule", "desc": "+500 XP boost", "price": 1200, "xp_bonus": 500},
    "3": {"name": "🔥 Super Saiyan Capsule", "desc": "+1000 XP boost", "price": 2500, "xp_bonus": 1000},
}

# Upgrade System
MAX_UPGRADE = 10
UPGRADE_COSTS = [1000, 3000, 8000, 20000, 50000, 120000, 300000, 700000, 2000000]
# Index 0 = cost to go from level 1 → 2, index 8 = 9 → 10 (MAX)

# (min_zeni, max_zeni, min_xp, max_xp, dragon_ball_chance)
TRAIN_REWARDS = {
    1:  (100,   350,   30,   100,  0.00),
    2:  (200,   600,   60,   180,  0.00),
    3:  (400,   1000,  100,  280,  0.00),
    4:  (700,   1600,  160,  400,  0.00),
    5:  (1200,  2500,  240,  600,  0.00),
    6:  (2000,  4000,  350,  900,  0.00),
    7:  (3200,  6500,  500,  1300, 0.01),
    8:  (5000,  10000, 750,  2000, 0.03),
    9:  (8000,  16000, 1200, 3500, 0.05),
    10: (12000, 30000, 2000, 6000, 0.10),
}

DAILY_REWARDS = {
    1:  (200,   600,   50,   150,  0.00),
    2:  (400,   1100,  100,  280,  0.00),
    3:  (800,   2000,  180,  450,  0.00),
    4:  (1400,  3500,  280,  700,  0.00),
    5:  (2500,  6000,  450,  1100, 0.00),
    6:  (4000,  9000,  650,  1600, 0.00),
    7:  (6500,  15000, 1000, 2500, 0.02),
    8:  (10000, 24000, 1600, 4000, 0.04),
    9:  (16000, 40000, 2500, 7000, 0.07),
    10: (25000, 75000, 4000, 12000,0.15),
}

UPGRADE_TIER_NAMES = {1:"Beginner",2:"Novice",3:"Apprentice",4:"Fighter",5:"Warrior",
                      6:"Elite",7:"Champion",8:"Legend",9:"Ascended",10:"⭐ MAX"}

def roll_train_reward(user_id: str):
    """Roll train rewards scaled to the user's train upgrade level. Returns (zeni, xp, got_db)."""
    data = get_user_data(user_id)
    lvl = data.get("train_upgrade", 1)
    r = TRAIN_REWARDS[lvl]
    zeni = random.randint(r[0], r[1])
    xp   = random.randint(r[2], r[3])
    got_db = None
    if r[4] > 0:
        missing = [i for i in range(1, 8) if i not in data["dragon_balls"]]
        if missing and random.random() < r[4]:
            ball = random.choice(missing)
            data["dragon_balls"].append(ball)
            data["dragon_balls"].sort()
            got_db = ball
    return zeni, xp, got_db

def roll_daily_reward(user_id: str):
    """Roll daily rewards scaled to the user's daily upgrade level. Returns (zeni, xp, got_db)."""
    data = get_user_data(user_id)
    lvl = data.get("daily_upgrade", 1)
    r = DAILY_REWARDS[lvl]
    zeni = random.randint(r[0], r[1])
    xp   = random.randint(r[2], r[3])
    got_db = None
    if r[4] > 0:
        missing = [i for i in range(1, 8) if i not in data["dragon_balls"]]
        if missing and random.random() < r[4]:
            ball = random.choice(missing)
            data["dragon_balls"].append(ball)
            data["dragon_balls"].sort()
            got_db = ball
    return zeni, xp, got_db

# Transformations
TRANSFORMATIONS = {
    "base":          {"name": "Base",              "price": 0,       "multiplier": 1,    "color": 0xAAAAAA, "emoji": "👤"},
    "great_ape":     {"name": "Great Ape",          "price": 1000,    "multiplier": 2,    "color": 0x8B4513, "emoji": "🦍"},
    "super_saiyan":  {"name": "Super Saiyan",       "price": 5000,    "multiplier": 5,    "color": 0xFFFF00, "emoji": "⚡"},
    "ssj2":          {"name": "Super Saiyan 2",     "price": 12000,   "multiplier": 10,   "color": 0xFFFF44, "emoji": "⚡⚡"},
    "ssj3":          {"name": "Super Saiyan 3",     "price": 25000,   "multiplier": 20,   "color": 0xFFD700, "emoji": "💛"},
    "ssjg":          {"name": "Super Saiyan God",   "price": 60000,   "multiplier": 50,   "color": 0xFF0000, "emoji": "🔴"},
    "ssjb":          {"name": "Super Saiyan Blue",  "price": 150000,  "multiplier": 100,  "color": 0x0099FF, "emoji": "🔵"},
    "ultra_instinct":{"name": "Ultra Instinct",     "price": 500000,  "multiplier": 500,  "color": 0xE0E0E0, "emoji": "🌀"},
}

# Loot Items
ITEMS = {
    "zeni_shard":    {"name": "Zeni Shard",    "emoji": "💎", "desc": "A fragment of Zeni",           "sell": 50},
    "ki_stone":      {"name": "Ki Stone",      "emoji": "🔮", "desc": "Compressed Ki energy",         "sell": 100},
    "senzu_bean":    {"name": "Senzu Bean",    "emoji": "🫘", "desc": "Restores your energy (+150 XP)","sell": 200, "use_xp": 150},
    "power_capsule": {"name": "Power Capsule", "emoji": "💊", "desc": "+300 XP when used",             "sell": 300, "use_xp": 300},
    "dragon_radar":  {"name": "Dragon Radar",  "emoji": "📡", "desc": "Boosts Dragon Ball find rate",  "sell": 800},
}

RECIPES = {
    "power_capsule": {"ki_stone": 3, "zeni_shard": 2},
    "dragon_radar":  {"ki_stone": 5, "zeni_shard": 10},
}

# Enemies (fight)
ENEMIES = [
    {"name": "Saibaman",          "power": 1,    "zeni": (50,  200),   "xp": (20,  60),   "drop": 0.40},
    {"name": "Raditz",            "power": 5,    "zeni": (200, 500),   "xp": (80,  160),  "drop": 0.50},
    {"name": "Nappa",             "power": 10,   "zeni": (400, 900),   "xp": (150, 300),  "drop": 0.55},
    {"name": "Vegeta (Scouter)",  "power": 18,   "zeni": (600, 1300),  "xp": (250, 450),  "drop": 0.60},
    {"name": "Dodoria",           "power": 20,   "zeni": (700, 1400),  "xp": (280, 480),  "drop": 0.60},
    {"name": "Zarbon",            "power": 25,   "zeni": (800, 1600),  "xp": (320, 550),  "drop": 0.65},
    {"name": "Ginyu Force",       "power": 50,   "zeni": (1500,3000),  "xp": (600,1000),  "drop": 0.65},
    {"name": "Frieza (Final)",    "power": 100,  "zeni": (3000,6000),  "xp": (1000,2000), "drop": 0.70},
    {"name": "Cell (Perfect)",    "power": 200,  "zeni": (5000,10000), "xp": (2000,4000), "drop": 0.75},
    {"name": "Kid Buu",           "power": 500,  "zeni": (10000,20000),"xp": (4000,8000), "drop": 0.80},
    {"name": "Jiren",             "power": 1000, "zeni": (20000,40000),"xp": (8000,15000),"drop": 0.85},
    {"name": "Moro",              "power": 2000, "zeni": (40000,80000),"xp": (15000,30000),"drop":0.90},
]

# Dragon Ball Wishes
WISHES = {
    "zeni":      {"desc": "50,000 Zeni",                    "emoji": "💴"},
    "level":     {"desc": "Gain 5 Power Levels instantly",   "emoji": "⚡"},
    "transform": {"desc": "Unlock a random transformation",  "emoji": "🌟"},
    "reset":     {"desc": "Reset all your cooldowns",        "emoji": "🔄"},
    "immortal":  {"desc": "No cooldowns for 24 hours",       "emoji": "♾️"},
}

@bot.command(aliases=['sc'])
async def scouter(ctx, member: discord.Member = None):
    """Check your Zeni balance."""
    member = member or ctx.author
    user_id = str(member.id)
    data = get_user_data(user_id)
    save_leveling()
    eff = get_effective_power_level(user_id)
    active_key = data.get("active_transformation")
    active_t = TRANSFORMATIONS.get(active_key) if active_key else None
    color = active_t["color"] if active_t else 0xFFA500
    embed = discord.Embed(title=f"🔭 Scouter Reading — {member.display_name}", color=color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="💴 Zeni", value=f"{data['zeni']:,}", inline=True)
    embed.add_field(name="⚡ Effective Power Level", value=f"{eff:,}", inline=True)
    embed.add_field(name="✨ XP", value=f"{data['xp']} / {data['level'] * 500}", inline=True)
    if active_t:
        embed.add_field(name="🌟 Transformation", value=f"{active_t['emoji']} {active_t['name']} (×{active_t['multiplier']})", inline=True)
    embed.add_field(name="📊 Base Level", value=data["level"], inline=True)
    dbs = data.get("dragon_balls", [])
    if dbs:
        embed.add_field(name=f"🔮 Dragon Balls [{len(dbs)}/7]", value=" ".join(f"⭐{n}" for n in dbs), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def balance(ctx, member: discord.Member = None):
    """Alias for -scouter."""
    await ctx.invoke(bot.get_command("scouter"), member=member)

@bot.command(aliases=['dc'])
async def dailycapsule(ctx):
    """Claim your daily Zeni capsule!"""
    user_id = str(ctx.author.id)
    data = get_user_data(user_id)
    current_time = time.time()

    if not data["no_cooldown"] and current_time - data["last_daily"] < 86400:
        remaining = 86400 - (current_time - data["last_daily"])
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        return await ctx.send(f"⏳ Daily capsule already claimed! Come back in **{hours}h {minutes}m**.")

    zeni_gain, xp_gain, got_db = roll_daily_reward(user_id)
    data["zeni"] += zeni_gain
    data["xp"] += xp_gain
    data["last_daily"] = current_time

    new_level = check_level_up(user_id)
    save_leveling()

    dlvl = data.get("daily_upgrade", 1)
    embed = discord.Embed(title=f"💊 Daily Capsule Claimed! (Tier {dlvl} — {UPGRADE_TIER_NAMES[dlvl]})", color=0x00BFFF)
    embed.add_field(name="💴 Zeni Earned", value=f"+{zeni_gain:,}", inline=True)
    embed.add_field(name="✨ XP Earned", value=f"+{xp_gain}", inline=True)
    if got_db:
        embed.add_field(name="🌟 Dragon Ball!", value=f"⭐ {got_db}-Star Ball dropped!", inline=True)
        if len(data["dragon_balls"]) == 7:
            embed.add_field(name="🐉 ALL 7!", value="Use `-summon`!", inline=False)
    if new_level:
        embed.add_field(name="⚡ LEVEL UP!", value=f"You are now Power Level **{new_level}**!", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    """Alias for -dailycapsule."""
    await ctx.invoke(bot.get_command("dailycapsule"))

@bot.command()
async def train(ctx):
    """Train to earn Zeni and XP! (1 hour cooldown)"""
    user_id = str(ctx.author.id)
    data = get_user_data(user_id)
    current_time = time.time()

    if not data["no_cooldown"] and current_time - data["last_train"] < 3600:
        remaining = 3600 - (current_time - data["last_train"])
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        return await ctx.send(f"💪 You're still recovering from training! Rest for **{minutes}m {seconds}s**.")

    zeni_gain, xp_gain, got_db = roll_train_reward(user_id)
    data["zeni"] += zeni_gain
    data["xp"] += xp_gain
    data["last_train"] = current_time

    new_level = check_level_up(user_id)
    save_leveling()

    training_msgs = [
        "You trained in the Hyperbolic Time Chamber!",
        "You sparred with Vegeta and survived!",
        "You completed 10,000 push-ups under King Kai!",
        "You trained under 100x gravity!",
        "You meditated and focused your Ki!",
    ]
    tlvl = data.get("train_upgrade", 1)
    embed = discord.Embed(title=f"💪 Training Complete! (Tier {tlvl} — {UPGRADE_TIER_NAMES[tlvl]})", description=random.choice(training_msgs), color=0xFF4500)
    embed.add_field(name="💴 Zeni Earned", value=f"+{zeni_gain:,}", inline=True)
    embed.add_field(name="✨ XP Earned", value=f"+{xp_gain}", inline=True)
    if got_db:
        embed.add_field(name="🌟 Dragon Ball!", value=f"⭐ {got_db}-Star Ball dropped!", inline=True)
        if len(data["dragon_balls"]) == 7:
            embed.add_field(name="🐉 ALL 7!", value="Use `-summon`!", inline=False)
    if new_level:
        embed.add_field(name="⚡ LEVEL UP!", value=f"You are now Power Level **{new_level}**!", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def work(ctx):
    """Alias for -train."""
    await ctx.invoke(bot.get_command("train"))

async def auto_train_loop(user_id: str, channel):
    """Background loop that trains a user automatically."""
    training_msgs = [
        "You trained in the Hyperbolic Time Chamber!",
        "You sparred with Vegeta and survived!",
        "You completed 10,000 push-ups under King Kai!",
        "You trained under 100x gravity!",
        "You meditated and focused your Ki!",
    ]
    first_run = True
    while True:
        try:
            data = get_user_data(user_id)
            current_time = time.time()

            # If there's a cooldown remaining and no_cooldown is off, wait it out
            if not data["no_cooldown"] and not first_run:
                elapsed = current_time - data["last_train"]
                wait_secs = max(0, 3600 - elapsed)
                if wait_secs > 0:
                    await asyncio.sleep(wait_secs)

            first_run = False
            data = get_user_data(user_id)
            current_time = time.time()

            # Still on cooldown and no bypass? wait a bit more and retry
            if not data["no_cooldown"] and (current_time - data["last_train"] < 3600):
                await asyncio.sleep(10)
                continue

            zeni_gain, xp_gain, got_db = roll_train_reward(user_id)
            data["zeni"] += zeni_gain
            data["xp"] += xp_gain
            data["last_train"] = current_time

            new_level = check_level_up(user_id)
            save_leveling()

            tlvl = data.get("train_upgrade", 1)
            embed = discord.Embed(title=f"🤖 Auto-Train Complete! (Tier {tlvl})", description=random.choice(training_msgs), color=0xFF4500)
            embed.add_field(name="💴 Zeni", value=f"+{zeni_gain:,}", inline=True)
            embed.add_field(name="✨ XP", value=f"+{xp_gain}", inline=True)
            if got_db:
                embed.add_field(name="🌟 Dragon Ball!", value=f"⭐ {got_db}-Star Ball!", inline=True)
            if new_level:
                embed.add_field(name="⚡ LEVEL UP!", value=f"Power Level **{new_level}**!", inline=False)
            next_train = "immediately (no cooldown)" if data["no_cooldown"] else "in 1 hour"
            embed.set_footer(text=f"Training again {next_train} | Use -autotrain stop to stop")
            await channel.send(embed=embed)

            # If no cooldown bypass, wait the full hour before looping again
            if not data["no_cooldown"]:
                await asyncio.sleep(3600)
            else:
                await asyncio.sleep(2)  # tiny delay to avoid hammering

        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(60)

async def auto_all_loop(user_id: str, channel):
    """Background loop that runs every cooldown action automatically."""
    training_msgs = [
        "You trained in the Hyperbolic Time Chamber!",
        "You sparred with Vegeta and survived!",
        "You completed 10,000 push-ups under King Kai!",
        "You trained under 100x gravity!",
        "You meditated and focused your Ki!",
    ]
    while True:
        try:
            data = get_user_data(user_id)
            now = time.time()
            no_cd = data["no_cooldown"]
            ran = []
            earned_zeni = 0
            earned_xp = 0
            leveled_up = None

            # --- Daily ---
            if no_cd or (now - data["last_daily"] >= 86400):
                zg, xg, db = roll_daily_reward(user_id)
                data["zeni"] += zg
                data["xp"] += xg
                data["last_daily"] = now
                earned_zeni += zg
                earned_xp += xg
                dlvl = data.get("daily_upgrade", 1)
                db_note = f" 🌟{db}-Star Ball!" if db else ""
                ran.append(f"💊 Daily Capsule T{dlvl} (+{zg:,} 💴, +{xg} XP{db_note})")

            # --- Train ---
            if no_cd or (now - data["last_train"] >= 3600):
                zg, xg, db = roll_train_reward(user_id)
                data["zeni"] += zg
                data["xp"] += xg
                data["last_train"] = now
                earned_zeni += zg
                earned_xp += xg
                tlvl = data.get("train_upgrade", 1)
                db_note = f" 🌟{db}-Star Ball!" if db else ""
                ran.append(f"💪 Train T{tlvl} — {random.choice(training_msgs)} (+{zg:,} 💴, +{xg} XP{db_note})")

            # --- Fight (PvE) ---
            if no_cd or (now - data["last_fight"] >= 1800):
                eff_pl = get_effective_power_level(user_id)
                eligible = [e for e in ENEMIES if e["power"] <= eff_pl * 2]
                enemy = random.choice(eligible if eligible else ENEMIES[:3])
                ratio = eff_pl / max(enemy["power"], 1)
                win_chance = min(0.90, max(0.20, ratio / (ratio + 1)))
                if random.random() < win_chance:
                    zg = random.randint(*enemy["zeni"])
                    xg = random.randint(*enemy["xp"])
                    data["zeni"] += zg
                    data["xp"] += xg
                    data["last_fight"] = now
                    earned_zeni += zg
                    earned_xp += xg
                    # Chance for item or Dragon Ball
                    has_radar = data["inventory"].get("dragon_radar", 0) > 0
                    if random.random() < enemy["drop"]:
                        item_key = random.choice(list(ITEMS.keys()))
                        data["inventory"][item_key] = data["inventory"].get(item_key, 0) + 1
                    missing_dbs = [i for i in range(1, 8) if i not in data["dragon_balls"]]
                    db_chance = 0.08 if has_radar else 0.04
                    if missing_dbs and random.random() < db_chance:
                        ball = random.choice(missing_dbs)
                        data["dragon_balls"].append(ball)
                        data["dragon_balls"].sort()
                    ran.append(f"⚔️ Beat **{enemy['name']}** (+{zg:,} 💴, +{xg} XP)")
                else:
                    penalty = random.randint(50, 200)
                    data["zeni"] = max(0, data["zeni"] - penalty)
                    data["last_fight"] = now
                    ran.append(f"⚔️ Lost to **{enemy['name']}** (−{penalty:,} 💴)")

            if ran:
                nl = check_level_up(user_id)
                if nl:
                    leveled_up = nl
                save_leveling()
                embed = discord.Embed(title="🤖 Auto-All Cycle Complete!", color=0x9B59B6)
                embed.add_field(name="Actions Ran", value="\n".join(ran), inline=False)
                embed.add_field(name="💴 Total Zeni", value=f"+{earned_zeni:,}", inline=True)
                embed.add_field(name="✨ Total XP", value=f"+{earned_xp}", inline=True)
                if leveled_up:
                    embed.add_field(name="⚡ LEVEL UP!", value=f"Power Level **{leveled_up}**!", inline=False)
                if len(data["dragon_balls"]) == 7:
                    embed.add_field(name="🐉 ALL 7 DRAGON BALLS!", value="Use `-summon`!", inline=False)
                # Next cycle timing
                if no_cd:
                    embed.set_footer(text="No cooldown — running again in 2s | -autotrain stop to stop")
                    await channel.send(embed=embed)
                    await asyncio.sleep(2)
                else:
                    soonest = min(
                        86400 - (now - data["last_daily"]),
                        3600  - (now - data["last_train"]),
                        1800  - (now - data["last_fight"]),
                    )
                    wait = max(10, soonest)
                    mins = int(wait // 60)
                    secs = int(wait % 60)
                    embed.set_footer(text=f"Next action in {mins}m {secs}s | -autotrain stop to stop")
                    await channel.send(embed=embed)
                    await asyncio.sleep(wait)
            else:
                # Nothing to run yet — sleep until the soonest cooldown expires
                soonest = min(
                    86400 - (now - data["last_daily"]),
                    3600  - (now - data["last_train"]),
                    1800  - (now - data["last_fight"]),
                )
                await asyncio.sleep(max(10, soonest))

        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(60)

@bot.command(aliases=['at'])
async def autotrain(ctx, action: str = None):
    """Start/stop auto-train or auto-all. Usage: -autotrain start/stop/all"""
    user_id = str(ctx.author.id)
    is_owner = ctx.author.id == OWNER_ID
    is_authorized = user_id in autotrain_authorized

    if not action:
        train_status = "🟢 Running" if user_id in autotrain_tasks else "🔴 Stopped"
        all_status   = "🟢 Running" if user_id in autoall_tasks   else "🔴 Stopped"
        return await ctx.send(
            f"**Auto-Train:** {train_status}\n**Auto-All:** {all_status}\n"
            f"Usage: `-autotrain start` | `-autotrain stop` | `-autotrain all` (authorized only)"
        )

    action = action.lower()

    if action == "all":
        if not (is_owner or is_authorized):
            return await ctx.send("❌ You are not authorized to use auto-all. Ask the owner to run `-atauth @you`.")
        if user_id in autoall_tasks:
            return await ctx.send("⚠️ Auto-all is already running! Use `-autotrain stop` to stop it.")
        task = asyncio.create_task(auto_all_loop(user_id, ctx.channel))
        autoall_tasks[user_id] = task
        await ctx.send("✅ **Auto-All** started! Daily, training, and fights will run automatically as their cooldowns expire.")
        return

    if action == "start":
        if user_id in autotrain_tasks:
            return await ctx.send("⚠️ Auto-train is already running! Use `-autotrain stop` to stop it.")
        task = asyncio.create_task(auto_train_loop(user_id, ctx.channel))
        autotrain_tasks[user_id] = task
        data = get_user_data(user_id)
        note = "No cooldown — training constantly!" if data["no_cooldown"] else "Training every hour automatically."
        return await ctx.send(f"✅ Auto-train started! {note}")

    if action == "stop":
        stopped = []
        if user_id in autotrain_tasks:
            autotrain_tasks[user_id].cancel()
            del autotrain_tasks[user_id]
            stopped.append("auto-train")
        if user_id in autoall_tasks:
            autoall_tasks[user_id].cancel()
            del autoall_tasks[user_id]
            stopped.append("auto-all")
        if stopped:
            return await ctx.send(f"🛑 Stopped: {', '.join(stopped)}.")
        return await ctx.send("❌ Nothing is running.")

@bot.command()
async def atauth(ctx, member: discord.Member = None):
    """Owner only: Authorize or deauthorize a user for -autotrain all."""
    if ctx.author.id != OWNER_ID:
        return
    if not member:
        names = []
        for uid in autotrain_authorized:
            u = bot.get_user(int(uid))
            names.append(u.display_name if u else f"User {uid}")
        authorized_list = ", ".join(names) if names else "None"
        return await ctx.send(f"**Authorized for Auto-All:** {authorized_list}\nUsage: `-atauth @user` to toggle.")
    uid = str(member.id)
    if uid in autotrain_authorized:
        autotrain_authorized.discard(uid)
        save_autotrain_auth()
        await ctx.send(f"❌ **{member.display_name}** removed from auto-all authorization.")
    else:
        autotrain_authorized.add(uid)
        save_autotrain_auth()
        await ctx.send(f"✅ **{member.display_name}** authorized to use `-autotrain all`.")

def build_capsule_embed(user_id: str):
    data = get_user_data(user_id)
    embed = discord.Embed(title="🏪 Capsule Corp Shop", description="Click a button to instantly purchase!", color=0x1ABC9C)
    for num, item in CAPSULE_SHOP.items():
        embed.add_field(name=item["name"], value=f"{item['desc']}\n💴 **{item['price']:,} Zeni**", inline=True)
    embed.set_footer(text=f"Your balance: {data['zeni']:,} Zeni")
    return embed

class CapsuleBuyButton(discord.ui.Button):
    def __init__(self, num, item, user_id):
        super().__init__(label=f"{item['name']} — {item['price']:,} 💴", style=discord.ButtonStyle.primary, row=0)
        self.num = num
        self.item = item
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
        data = get_user_data(self.user_id)
        if data["zeni"] < self.item["price"]:
            return await interaction.response.send_message(
                f"❌ Need **{self.item['price']:,} Zeni** but you have **{data['zeni']:,}**.", ephemeral=True)
        data["zeni"] -= self.item["price"]
        data["xp"] += self.item["xp_bonus"]
        new_level = check_level_up(self.user_id)
        save_leveling()
        msg = f"✅ Bought **{self.item['name']}**! +{self.item['xp_bonus']} XP"
        if new_level:
            msg += f"\n⚡ **LEVEL UP!** Power Level **{new_level}**!"
        await interaction.response.send_message(msg, ephemeral=True)
        await interaction.message.edit(embed=build_capsule_embed(self.user_id))

class CapsuleShopView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=60)
        for num, item in CAPSULE_SHOP.items():
            self.add_item(CapsuleBuyButton(num, item, user_id))

@bot.command(aliases=['cs', 'cshop', 'shop'])
async def capsuleshop(ctx):
    """Browse and buy from the Capsule Shop!"""
    user_id = str(ctx.author.id)
    get_user_data(user_id)

    # Example item (change to your system if needed)
    item_key = "capsule"
    price = CAPSULE_ITEMS[item_key]["price"]

    data = get_user_data(user_id)
    max_afford = data["zeni"] // price

    await ctx.send(
        f"💰 **Price:** {price:,} Zeni\n"
        f"🛒 You can afford **{max_afford:,}**\n\n"
        f"What would you like to buy?",
        view=BuyAmountView(user_id, item_key)
    )


class BuyAmountView(discord.ui.View):
    def __init__(self, user_id, item_key):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.item_key = item_key

        data = get_user_data(user_id)
        price = CAPSULE_ITEMS[item_key]["price"]

        self.max_afford = data["zeni"] // price

        # Disable buttons if user can't afford them
        if self.max_afford < 1:
            self.buy1.disabled = True
            self.buymax.disabled = True
        if self.max_afford < 100:
            self.buy100.disabled = True
        if self.max_afford < 10000:
            self.buy10000.disabled = True

    async def buy(self, interaction, amount):
        data = get_user_data(self.user_id)
        price = CAPSULE_ITEMS[self.item_key]["price"]

        if amount == "max":
            amount = self.max_afford

        if amount <= 0:
            await interaction.response.send_message(
                "❌ You can't afford any.",
                ephemeral=True
            )
            return

        total = price * amount

        if data["zeni"] < total:
            await interaction.response.send_message(
                "❌ Not enough Zeni.",
                ephemeral=True
            )
            return

        data["zeni"] -= total
        data["inventory"][self.item_key] = data["inventory"].get(self.item_key, 0) + amount

        await interaction.response.send_message(
            f"✅ You bought **{amount:,}x {CAPSULE_ITEMS[self.item_key]['name']}** for **{total:,} Zeni**",
            ephemeral=True
        )

    @discord.ui.button(label="Buy 1", style=discord.ButtonStyle.secondary)
    async def buy1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy(interaction, 1)

    @discord.ui.button(label="Buy 100", style=discord.ButtonStyle.secondary)
    async def buy100(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy(interaction, 100)

    @discord.ui.button(label="Buy 10000", style=discord.ButtonStyle.secondary)
    async def buy10000(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy(interaction, 10000)

    @discord.ui.button(label="Buy Max", style=discord.ButtonStyle.success)
    async def buymax(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy(interaction, "max")
        
@bot.command(aliases=['pl'])
async def powerlevels(ctx):
    """View the interactive leaderboard."""
    if not leveling_data:
        return await ctx.send("No warriors have trained yet!")
    view = LeaderboardView(guild=ctx.guild, scope="global")
    embed = view.build_embed(bot)
    await ctx.send(embed=embed, view=view)

@bot.command()
async def leaderboard(ctx):
    """Alias for -powerlevels."""
    await ctx.invoke(bot.get_command("powerlevels"))

@bot.command()
async def raid(ctx, member: discord.Member = None):
    """Raid another warrior to steal their Zeni! (30 min cooldown)"""
    user_id = str(ctx.author.id)
    if not member or member == ctx.author:
        return await ctx.send("Usage: `-raid @user`")

    data = get_user_data(user_id)
    target_data = get_user_data(str(member.id))
    current_time = time.time()

    if not data["no_cooldown"] and current_time - data["last_raid"] < 1800:
        remaining = 1800 - (current_time - data["last_raid"])
        minutes = int(remaining // 60)
        return await ctx.send(f"⚔️ You need to recover from your last raid! Wait **{minutes}m**.")

    if target_data["zeni"] < 100:
        return await ctx.send(f"❌ **{member.display_name}** doesn't have enough Zeni to raid (min 100).")

    data["last_raid"] = current_time
    success = random.random() < 0.55  # 55% success rate

    if success:
        stolen = random.randint(50, min(500, int(target_data["zeni"] * 0.3)))
        data["zeni"] += stolen
        target_data["zeni"] -= stolen
        save_leveling()
        embed = discord.Embed(title="⚔️ Raid Successful!", description=f"You raided **{member.display_name}** and stole **{stolen:,} Zeni**!", color=0x2ECC71)
    else:
        penalty = random.randint(50, 200)
        data["zeni"] = max(0, data["zeni"] - penalty)
        save_leveling()
        embed = discord.Embed(title="💀 Raid Failed!", description=f"**{member.display_name}** fought back! You lost **{penalty:,} Zeni**.", color=0xE74C3C)

    await ctx.send(embed=embed)

@bot.command()
async def rob(ctx, member: discord.Member = None):
    """Alias for -raid."""
    await ctx.invoke(bot.get_command("raid"), member=member)

@bot.command()
async def transfer(ctx, member: discord.Member = None, amount: int = None):
    """Send Zeni to another user. Usage: -transfer @user <amount>"""
    user_id = str(ctx.author.id)
    if not member or not amount:
        return await ctx.send("Usage: `-transfer @user <amount>`")
    if member == ctx.author:
        return await ctx.send("❌ You can't transfer Zeni to yourself.")
    if amount <= 0:
        return await ctx.send("❌ Amount must be positive.")

    data = get_user_data(user_id)
    target_data = get_user_data(str(member.id))

    if data["zeni"] < amount:
        return await ctx.send(f"❌ You only have **{data['zeni']:,} Zeni**.")

    data["zeni"] -= amount
    target_data["zeni"] += amount
    save_leveling()

    embed = discord.Embed(title="💴 Zeni Transferred!", color=0x3498DB)
    embed.add_field(name="Sent To", value=member.display_name, inline=True)
    embed.add_field(name="Amount", value=f"{amount:,} Zeni", inline=True)
    embed.add_field(name="Your Balance", value=f"{data['zeni']:,} Zeni", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def pay(ctx, member: discord.Member = None, amount: int = None):
    """Alias for -transfer."""
    await ctx.invoke(bot.get_command("transfer"), member=member, amount=amount)

@bot.command()
async def cd(ctx, member: discord.Member = None, *, time_str: str = None):
    """Owner only: Set or reset cooldowns for a user. Usage: -cd @user <time or reset>"""
    if ctx.author.id != OWNER_ID:
        return
    if not member or not time_str:
        return await ctx.send("Usage: `-cd @user <option>`\nOptions: `off` (no cooldown), `on` (re-enable), `reset` (skip current wait), `30m`, `1h`, `3600`")

    user_id = str(member.id)
    data = get_user_data(user_id)
    current_time = time.time()

    if time_str.lower() == "off":
        data["no_cooldown"] = True
        save_leveling()
        return await ctx.send(f"✅ Cooldowns **disabled** for **{member.display_name}**. They can use daily/train/raid with no limits.")

    if time_str.lower() == "on":
        data["no_cooldown"] = False
        save_leveling()
        return await ctx.send(f"✅ Cooldowns **re-enabled** for **{member.display_name}**.")

    if time_str.lower() in ("reset", "0"):
        data["last_daily"] = 0
        data["last_train"] = 0
        data["last_raid"] = 0
        save_leveling()
        return await ctx.send(f"✅ All cooldowns reset for **{member.display_name}**. They can use all commands immediately.")

    # Parse time string like 30m, 1h, 3600
    import re
    seconds = 0
    matches = re.findall(r'(\d+)([hms]?)', time_str.lower())
    for value, unit in matches:
        value = int(value)
        if unit == 'h':
            seconds += value * 3600
        elif unit == 'm':
            seconds += value * 60
        elif unit == 's' or unit == '':
            seconds += value

    if seconds <= 0:
        return await ctx.send("❌ Invalid time. Use formats like `30m`, `1h`, `3600`, or `reset`.")

    # Set all cooldowns so they expire after the given duration
    applied_at = current_time - (86400 - seconds) if seconds < 86400 else current_time
    data["last_daily"] = current_time - (86400 - min(seconds, 86400))
    data["last_train"] = current_time - (3600 - min(seconds, 3600))
    data["last_raid"] = current_time - (1800 - min(seconds, 1800))
    save_leveling()

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    time_display = f"{hours}h {minutes}m {secs}s".strip()
    await ctx.send(f"✅ Cooldowns set for **{member.display_name}** — they must wait **{time_display}** before using daily/train/raid again.")

@bot.command()
async def level(ctx, member: discord.Member = None):
    """Check your Power Level."""
    member = member or ctx.author
    user_id = str(member.id)
    data = get_user_data(user_id)
    save_leveling()
    xp_needed = data["level"] * 500
    eff = get_effective_power_level(user_id)
    active_key = data.get("active_transformation")
    active_t = TRANSFORMATIONS.get(active_key) if active_key else None
    color = active_t["color"] if active_t else 0x00FF00
    embed = discord.Embed(title=f"⚡ {member.display_name}'s Power Level", color=color)
    embed.add_field(name="⚡ Effective PL", value=f"{eff:,}", inline=True)
    embed.add_field(name="📊 Base Level", value=data["level"], inline=True)
    embed.add_field(name="✨ XP", value=f"{data['xp']} / {xp_needed}", inline=True)
    embed.add_field(name="💴 Zeni", value=f"{data['zeni']:,}", inline=True)
    if active_t:
        embed.add_field(name="🌟 Form", value=f"{active_t['emoji']} {active_t['name']} ×{active_t['multiplier']}", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def xp(ctx, member: discord.Member = None):
    """Check your XP."""
    member = member or ctx.author
    user_id = str(member.id)
    data = get_user_data(user_id)
    save_leveling()
    await ctx.send(f"✨ **{member.display_name}** has **{data['xp']} XP** and is Power Level **{data['level']}**.")

# ── TRANSFORMATION COMMANDS ──────────────────────────────────────────────────

def build_transform_embed(user_id: str):
    data = get_user_data(user_id)
    owned = data["transformations"]
    active = data.get("active_transformation")
    active_name = TRANSFORMATIONS[active]["name"] if active and active in TRANSFORMATIONS else "Base"
    embed = discord.Embed(title="🌟 Transformation Shop", description="Click a button to buy or equip a transformation!", color=0xFFD700)
    for key, t in TRANSFORMATIONS.items():
        if key == "base":
            continue
        if key in owned:
            status = f"✅ **Active** ×{t['multiplier']}" if active == key else f"Owned ×{t['multiplier']}"
        else:
            status = f"💴 {t['price']:,} Zeni  ×{t['multiplier']}"
        embed.add_field(name=f"{t['emoji']} {t['name']}", value=status, inline=True)
    embed.set_footer(text=f"Balance: {data['zeni']:,} Zeni | Active form: {active_name}")
    return embed

class TransformButton(discord.ui.Button):
    def __init__(self, key, t, owned, active_key, user_id, row):
        if key in owned:
            if active_key == key:
                label, style = f"✅ {t['name']}", discord.ButtonStyle.success
            else:
                label, style = f"Equip {t['emoji']} {t['name']}", discord.ButtonStyle.secondary
        else:
            price_str = f"{t['price']:,}" if t["price"] > 0 else "Free"
            label, style = f"Buy {t['emoji']} {t['name']} | {price_str} 💴", discord.ButtonStyle.primary
        super().__init__(label=label, style=style, row=row)
        self.key = key
        self.t = t
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
        data = get_user_data(self.user_id)
        if self.key not in data["transformations"]:
            if data["zeni"] < self.t["price"]:
                return await interaction.response.send_message(
                    f"❌ Need **{self.t['price']:,} Zeni** but you have **{data['zeni']:,}**.", ephemeral=True)
            data["zeni"] -= self.t["price"]
            data["transformations"].append(self.key)
            save_leveling()
            msg = f"✅ Unlocked **{self.t['emoji']} {self.t['name']}**! (×{self.t['multiplier']} Power Level)"
        elif data.get("active_transformation") == self.key:
            data["active_transformation"] = None
            save_leveling()
            msg = f"👤 Returned to Base form."
        else:
            data["active_transformation"] = self.key
            save_leveling()
            eff = get_effective_power_level(self.user_id)
            msg = f"⚡ Transformed into **{self.t['emoji']} {self.t['name']}**! Effective PL: **{eff:,}**"
        await interaction.response.send_message(msg, ephemeral=True)
        new_view = make_transform_view(self.user_id)
        await interaction.message.edit(embed=build_transform_embed(self.user_id), view=new_view)

def make_transform_view(user_id: str):
    data = get_user_data(user_id)
    owned = data["transformations"]
    active = data.get("active_transformation")
    view = discord.ui.View(timeout=120)
    keys = [k for k in TRANSFORMATIONS if k != "base"]
    for i, key in enumerate(keys):
        t = TRANSFORMATIONS[key]
        view.add_item(TransformButton(key, t, owned, active, user_id, row=i // 4))
    return view

@bot.command(aliases=['ts', 'tshop'])
async def transformshop(ctx):
    """Browse and buy/equip transformations."""
    user_id = str(ctx.author.id)
    get_user_data(user_id)
    await ctx.send(embed=build_transform_embed(user_id), view=make_transform_view(user_id))

@bot.command(aliases=['tf'])
async def transform(ctx, action: str = None, *, key: str = None):
    """Buy or activate a transformation. -transform buy <key> | -transform <key>"""
    user_id = str(ctx.author.id)
    data = get_user_data(user_id)

    if not action:
        owned = [f"{TRANSFORMATIONS[k]['emoji']} **{TRANSFORMATIONS[k]['name']}**" for k in data["transformations"] if k in TRANSFORMATIONS]
        active = data["active_transformation"]
        active_name = TRANSFORMATIONS[active]["name"] if active and active in TRANSFORMATIONS else "None"
        return await ctx.send(f"⚡ Active: **{active_name}**\nOwned: {', '.join(owned)}\nUse `-transformshop` to browse, `-transform buy <key>` to buy, `-transform <key>` to equip, `-detransform` to revert.")

    if action.lower() == "buy":
        if not key:
            return await ctx.send("Usage: `-transform buy <key>` — see keys with `-transformshop`")
        key = key.lower().replace(" ", "_")
        if key not in TRANSFORMATIONS:
            return await ctx.send(f"❌ Unknown transformation. See `-transformshop` for valid keys.")
        if key in data["transformations"]:
            return await ctx.send(f"✅ You already own **{TRANSFORMATIONS[key]['name']}**.")
        t = TRANSFORMATIONS[key]
        if t["price"] == 0:
            data["transformations"].append(key)
            save_leveling()
            return await ctx.send(f"✅ Unlocked **{t['name']}**!")
        if data["zeni"] < t["price"]:
            return await ctx.send(f"❌ You need **{t['price']:,} Zeni** but only have **{data['zeni']:,}**.")
        data["zeni"] -= t["price"]
        data["transformations"].append(key)
        save_leveling()
        embed = discord.Embed(title=f"✅ Transformation Unlocked: {t['emoji']} {t['name']}", color=t["color"])
        embed.add_field(name="Power Multiplier", value=f"×{t['multiplier']}", inline=True)
        embed.add_field(name="Zeni Spent", value=f"{t['price']:,}", inline=True)
        embed.set_footer(text=f"Use `-transform {key}` to equip it!")
        return await ctx.send(embed=embed)

    # Equip transformation
    key = action.lower().replace(" ", "_")
    if key not in TRANSFORMATIONS:
        return await ctx.send(f"❌ Unknown transformation key. See `-transformshop`.")
    if key not in data["transformations"]:
        return await ctx.send(f"❌ You haven't unlocked **{TRANSFORMATIONS[key]['name']}** yet. Buy it with `-transform buy {key}`.")
    data["active_transformation"] = key if key != "base" else None
    save_leveling()
    t = TRANSFORMATIONS[key]
    eff = get_effective_power_level(user_id)
    embed = discord.Embed(title=f"{t['emoji']} Transformation: {t['name']}!", color=t["color"])
    embed.add_field(name="Power Multiplier", value=f"×{t['multiplier']}", inline=True)
    embed.add_field(name="Effective Power Level", value=f"{eff:,}", inline=True)
    await ctx.send(embed=embed)

@bot.command(aliases=['dtf'])
async def detransform(ctx):
    """Revert to base form."""
    user_id = str(ctx.author.id)
    data = get_user_data(user_id)
    data["active_transformation"] = None
    save_leveling()
    await ctx.send(f"👤 **{ctx.author.display_name}** returned to Base form. Power Level: **{data['level']:,}**")

# ── FIGHT SYSTEM ─────────────────────────────────────────────────────────────

@bot.command(aliases=['f'])
async def fight(ctx, member: discord.Member = None):
    """Fight an enemy or another user! Drops Zeni, XP, and items."""
    user_id = str(ctx.author.id)
    data = get_user_data(user_id)
    current_time = time.time()

    if not data["no_cooldown"] and current_time - data["last_fight"] < 1800:
        remaining = 1800 - (current_time - data["last_fight"])
        minutes = int(remaining // 60)
        return await ctx.send(f"⚔️ You need to recover! Fight again in **{minutes}m**.")

    data["last_fight"] = current_time
    eff_pl = get_effective_power_level(user_id)

    # PvP fight
    if member and member != ctx.author:
        target_id = str(member.id)
        target_data = get_user_data(target_id)
        target_eff = get_effective_power_level(target_id)

        ratio = eff_pl / max(target_eff, 1)
        win_chance = min(0.85, max(0.15, ratio / (ratio + 1)))
        won = random.random() < win_chance

        if won:
            stolen = random.randint(100, max(100, int(target_data["zeni"] * 0.15)))
            xp_gain = random.randint(100, 300)
            data["zeni"] += stolen
            target_data["zeni"] = max(0, target_data["zeni"] - stolen)
            data["xp"] += xp_gain
            check_level_up(user_id)
            save_leveling()
            embed = discord.Embed(title=f"⚔️ {ctx.author.display_name} vs {member.display_name}", color=0x2ECC71)
            embed.add_field(name="Result", value=f"🏆 **{ctx.author.display_name}** wins!", inline=False)
            embed.add_field(name="💴 Stolen", value=f"{stolen:,} Zeni", inline=True)
            embed.add_field(name="✨ XP", value=f"+{xp_gain}", inline=True)
        else:
            penalty = random.randint(50, 300)
            data["zeni"] = max(0, data["zeni"] - penalty)
            save_leveling()
            embed = discord.Embed(title=f"⚔️ {ctx.author.display_name} vs {member.display_name}", color=0xE74C3C)
            embed.add_field(name="Result", value=f"💀 **{ctx.author.display_name}** was defeated!", inline=False)
            embed.add_field(name="💴 Lost", value=f"{penalty:,} Zeni", inline=True)
        return await ctx.send(embed=embed)

    # PvE fight — pick enemy based on power level
    eligible = [e for e in ENEMIES if e["power"] <= eff_pl * 2]
    enemy = random.choice(eligible if eligible else ENEMIES[:3])

    enemy_power = enemy["power"]
    ratio = eff_pl / max(enemy_power, 1)
    win_chance = min(0.90, max(0.20, ratio / (ratio + 1)))
    won = random.random() < win_chance

    if won:
        zeni_gain = random.randint(*enemy["zeni"])
        xp_gain = random.randint(*enemy["xp"])
        data["zeni"] += zeni_gain
        data["xp"] += xp_gain
        new_level = check_level_up(user_id)

        # Item drop
        dropped_item = None
        has_radar = data["inventory"].get("dragon_radar", 0) > 0
        db_chance = 0.08 if has_radar else 0.04
        if random.random() < enemy["drop"]:
            item_key = random.choice(list(ITEMS.keys()))
            item = ITEMS[item_key]
            data["inventory"][item_key] = data["inventory"].get(item_key, 0) + 1
            dropped_item = item

        # Dragon Ball drop
        dropped_db = None
        missing_dbs = [i for i in range(1, 8) if i not in data["dragon_balls"]]
        if missing_dbs and random.random() < db_chance:
            ball = random.choice(missing_dbs)
            data["dragon_balls"].append(ball)
            data["dragon_balls"].sort()
            dropped_db = ball

        save_leveling()
        embed = discord.Embed(title=f"⚔️ Fight vs {enemy['name']}!", color=0x2ECC71)
        embed.add_field(name="Result", value="🏆 Victory!", inline=False)
        embed.add_field(name="💴 Zeni", value=f"+{zeni_gain:,}", inline=True)
        embed.add_field(name="✨ XP", value=f"+{xp_gain}", inline=True)
        if dropped_item:
            embed.add_field(name="🎁 Item Drop", value=f"{dropped_item['emoji']} {dropped_item['name']}", inline=True)
        if dropped_db:
            embed.add_field(name="🌟 Dragon Ball!", value=f"⭐ {dropped_db}-Star Ball found!", inline=True)
        if new_level:
            embed.add_field(name="⚡ LEVEL UP!", value=f"Power Level **{new_level}**!", inline=False)
        if len(data["dragon_balls"]) == 7:
            embed.add_field(name="🐉 ALL 7 DRAGON BALLS!", value="Use `-summon` to call Shenron!", inline=False)
    else:
        penalty = random.randint(50, 250)
        data["zeni"] = max(0, data["zeni"] - penalty)
        save_leveling()
        embed = discord.Embed(title=f"⚔️ Fight vs {enemy['name']}!", color=0xE74C3C)
        embed.add_field(name="Result", value="💀 Defeated! Train harder.", inline=False)
        embed.add_field(name="💴 Lost", value=f"{penalty:,} Zeni", inline=True)
        embed.set_footer(text="Tip: Transform to boost your power level before fighting!")

    await ctx.send(embed=embed)

# ── INVENTORY / ITEMS ─────────────────────────────────────────────────────────

@bot.command(aliases=['inv'])
async def inventory(ctx, member: discord.Member = None):
    """View your item inventory."""
    member = member or ctx.author
    user_id = str(member.id)
    data = get_user_data(user_id)
    inv = data["inventory"]
    if not inv:
        return await ctx.send(f"**{member.display_name}**'s inventory is empty. Fight enemies to find items!")
    embed = discord.Embed(title=f"🎒 {member.display_name}'s Inventory", color=0x9B59B6)
    for key, count in inv.items():
        if count > 0 and key in ITEMS:
            item = ITEMS[key]
            embed.add_field(name=f"{item['emoji']} {item['name']} ×{count}", value=item["desc"], inline=False)
    dbs = data["dragon_balls"]
    if dbs:
        db_str = " ".join([f"⭐{n}" for n in dbs])
        embed.add_field(name=f"🔮 Dragon Balls [{len(dbs)}/7]", value=db_str, inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def use(ctx, *, item_key: str = None):
    """Use an item from your inventory. -use <item_key>"""
    if not item_key:
        return await ctx.send("Usage: `-use <item_key>` (e.g. `-use senzu_bean`)")
    user_id = str(ctx.author.id)
    data = get_user_data(user_id)
    key = item_key.lower().replace(" ", "_")
    if key not in ITEMS:
        return await ctx.send("❌ Unknown item. Check `-inventory` for your items.")
    if data["inventory"].get(key, 0) <= 0:
        return await ctx.send(f"❌ You don't have any **{ITEMS[key]['name']}**.")
    item = ITEMS[key]
    if "use_xp" not in item:
        return await ctx.send(f"❌ **{item['name']}** can't be used directly.")
    data["inventory"][key] -= 1
    data["xp"] += item["use_xp"]
    new_level = check_level_up(user_id)
    save_leveling()
    embed = discord.Embed(title=f"✅ Used {item['emoji']} {item['name']}!", color=0x2ECC71)
    embed.add_field(name="✨ XP Gained", value=f"+{item['use_xp']}", inline=True)
    if new_level:
        embed.add_field(name="⚡ LEVEL UP!", value=f"Power Level **{new_level}**!", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def craft(ctx, *, item_key: str = None):
    """Craft an item from materials. -craft <item_key>"""
    if not item_key:
        available = ", ".join(f"`{k}`" for k in RECIPES)
        return await ctx.send(f"Craftable items: {available}\nUsage: `-craft <item_key>`")
    user_id = str(ctx.author.id)
    data = get_user_data(user_id)
    key = item_key.lower().replace(" ", "_")
    if key not in RECIPES:
        return await ctx.send(f"❌ No recipe for that. Craftable: {', '.join(f'`{k}`' for k in RECIPES)}")
    recipe = RECIPES[key]
    for mat, qty in recipe.items():
        if data["inventory"].get(mat, 0) < qty:
            item_name = ITEMS[mat]["name"] if mat in ITEMS else mat
            return await ctx.send(f"❌ You need **{qty}× {item_name}** but only have {data['inventory'].get(mat, 0)}.")
    for mat, qty in recipe.items():
        data["inventory"][mat] -= qty
    data["inventory"][key] = data["inventory"].get(key, 0) + 1
    save_leveling()
    item = ITEMS[key]
    embed = discord.Embed(title=f"🔨 Crafted {item['emoji']} {item['name']}!", color=0x1ABC9C)
    mats_used = "\n".join([f"−{qty}× {ITEMS[m]['name']}" for m, qty in recipe.items()])
    embed.add_field(name="Materials Used", value=mats_used, inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def sell(ctx, item_key: str = None, amount: int = 1):
    """Sell items for Zeni. -sell <item_key> [amount]"""
    if not item_key:
        prices = "\n".join([f"{ITEMS[k]['emoji']} **{ITEMS[k]['name']}** — {ITEMS[k]['sell']:,} Zeni each" for k in ITEMS])
        return await ctx.send(f"**Sell Prices:**\n{prices}\nUsage: `-sell <item_key> [amount]`")
    user_id = str(ctx.author.id)
    data = get_user_data(user_id)
    key = item_key.lower().replace(" ", "_")
    if key not in ITEMS:
        return await ctx.send("❌ Unknown item.")
    if amount <= 0:
        return await ctx.send("❌ Amount must be positive.")
    owned = data["inventory"].get(key, 0)
    if owned < amount:
        return await ctx.send(f"❌ You only have **{owned}** of that item.")
    item = ITEMS[key]
    total = item["sell"] * amount
    data["inventory"][key] -= amount
    data["zeni"] += total
    save_leveling()
    await ctx.send(f"✅ Sold **{amount}× {item['emoji']} {item['name']}** for **{total:,} Zeni**!")

# ── DRAGON BALL SYSTEM ────────────────────────────────────────────────────────

@bot.command(aliases=['db'])
async def dragonballs(ctx, member: discord.Member = None):
    """Check your Dragon Ball collection."""
    member = member or ctx.author
    user_id = str(member.id)
    data = get_user_data(user_id)
    dbs = data["dragon_balls"]
    found = set(dbs)
    all_balls = ""
    for i in range(1, 8):
        if i in found:
            all_balls += f"⭐**{i}**  "
        else:
            all_balls += f"○{i}  "
    embed = discord.Embed(title=f"🔮 {member.display_name}'s Dragon Balls [{len(dbs)}/7]", color=0xFFD700)
    embed.add_field(name="Collection", value=all_balls, inline=False)
    if len(dbs) == 7:
        embed.add_field(name="🐉 Ready!", value="Use `-summon` to call Shenron!", inline=False)
    else:
        embed.set_footer(text="Dragon Balls drop from fights. A Dragon Radar boosts your find rate!")
    await ctx.send(embed=embed)

@bot.command()
async def summon(ctx):
    """Summon Shenron with all 7 Dragon Balls!"""
    user_id = str(ctx.author.id)
    data = get_user_data(user_id)

    if len(data["dragon_balls"]) < 7:
        missing = [i for i in range(1, 8) if i not in data["dragon_balls"]]
        return await ctx.send(f"🔮 You need all 7 Dragon Balls! Missing: {', '.join(str(m) for m in missing)}")

    data["awaiting_wish"] = True
    save_leveling()

    wish_list = "\n".join([f"`{k}` — {v['emoji']} {v['desc']}" for k, v in WISHES.items()])
    embed = discord.Embed(
        title="🐉 SHENRON HAS BEEN SUMMONED!",
        description="*The eternal dragon rises from the Dragon Balls, the sky turns dark...*\n\n**\"I will grant you any one wish. Speak your wish now!\"**",
        color=0x00FF44
    )
    embed.add_field(name="Available Wishes", value=wish_list, inline=False)
    embed.set_footer(text="Use -wish <wish> to make your wish!")
    await ctx.send(embed=embed)

@bot.command()
async def wish(ctx, *, wish_key: str = None):
    """Make a wish from Shenron after summoning. -wish <wish>"""
    user_id = str(ctx.author.id)
    data = get_user_data(user_id)

    if not data.get("awaiting_wish"):
        return await ctx.send("🐉 Shenron hasn't been summoned! Collect all 7 Dragon Balls and use `-summon` first.")
    if not wish_key:
        wish_list = "\n".join([f"`{k}` — {v['emoji']} {v['desc']}" for k, v in WISHES.items()])
        return await ctx.send(f"Make your wish! Options:\n{wish_list}")

    key = wish_key.lower().strip()
    if key not in WISHES:
        return await ctx.send(f"❌ Invalid wish. Options: {', '.join(f'`{k}`' for k in WISHES)}")

    # Grant the wish
    data["dragon_balls"] = []
    data["awaiting_wish"] = False
    w = WISHES[key]
    result_text = ""

    if key == "zeni":
        data["zeni"] += 50000
        result_text = "**+50,000 Zeni** added to your balance!"

    elif key == "level":
        for _ in range(5):
            data["level"] += 1
        result_text = f"**+5 Power Levels!** You are now Level **{data['level']}**!"

    elif key == "transform":
        locked = [k for k in TRANSFORMATIONS if k not in data["transformations"] and k != "base"]
        if locked:
            chosen = random.choice(locked)
            data["transformations"].append(chosen)
            t = TRANSFORMATIONS[chosen]
            result_text = f"Unlocked **{t['emoji']} {t['name']}** (×{t['multiplier']} multiplier)!"
        else:
            data["zeni"] += 25000
            result_text = "All transformations already unlocked! Received **25,000 Zeni** instead."

    elif key == "reset":
        data["last_daily"] = 0
        data["last_train"] = 0
        data["last_raid"] = 0
        data["last_fight"] = 0
        result_text = "All cooldowns have been **reset**. You can use everything immediately!"

    elif key == "immortal":
        data["no_cooldown"] = True
        result_text = "You have been granted **no cooldowns for 24 hours**! Train and fight freely!"
        asyncio.create_task(_remove_immortal(user_id, 86400))

    save_leveling()
    embed = discord.Embed(
        title=f"🐉 Wish Granted! {w['emoji']}",
        description=f"*\"Your wish has been granted. Farewell!\"*\n\n{result_text}",
        color=0x00FF44
    )
    embed.set_footer(text="The Dragon Balls have scattered across the world...")
    await ctx.send(embed=embed)

async def _remove_immortal(user_id: str, delay: int):
    await asyncio.sleep(delay)
    if user_id in leveling_data:
        leveling_data[user_id]["no_cooldown"] = False
        save_leveling()

@bot.event
async def on_message(message):
    if message.author.bot and message.author != bot.user: 
        return
    
    # Passive XP Gain
    if not isinstance(message.channel, discord.DMChannel) and message.author != bot.user:
        user_id = str(message.author.id)
        if user_id not in leveling_data:
            leveling_data[user_id] = {"xp": 0, "level": 1, "last_daily": 0}
        
        leveling_data[user_id]["xp"] += random.randint(5, 15)
        xp_needed = leveling_data[user_id]["level"] * 500
        if leveling_data[user_id]["xp"] >= xp_needed:
            leveling_data[user_id]["level"] += 1
            leveling_data[user_id]["xp"] -= xp_needed
            try:
                await message.channel.send(f"🎉 **{message.author.name}**, you leveled up to **Level {leveling_data[user_id]['level']}**!", delete_after=10)
            except: pass
        save_leveling()

    if isinstance(message.channel, discord.DMChannel):
        user_id = message.author.id
        content = message.content or "[No Content]"
        entry = f"{message.author.name}: {content}"
        dm_history.setdefault(user_id, []).append(entry)
        
        chan = bot.get_channel(LOG_CHANNEL_ID)
        if chan and message.author != bot.user:
            try:
                await chan.send(f"**{message.author.name}**: {content}")
            except:
                pass
            
        for owner_id, target in active_dm_sessions.items():
            if message.author.id == target.id:
                owner = bot.get_user(owner_id)
                if owner: 
                    try:
                        await owner.send(f"**[{message.author.name}]:** {content}")
                    except:
                        pass

    await bot.process_commands(message)

app = Flask('')

@app.route('/')
def home():
    return "Alive"

def run_flask():
    app.run(host='0.0.0.0', port=5000)

threading.Thread(target=run_flask, daemon=True).start()

token = os.environ.get("TOKEN")
if token:
    bot.run(token)
else:
    print("No TOKEN found. Set the TOKEN environment variable.")
