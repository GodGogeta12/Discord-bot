import discord
from discord.ext import commands
import asyncio
import os
import threading
from flask import Flask

OWNER_ID = 1281497404931051541
dm_history = {}
active_dm_sessions = {}
LOG_CHANNEL_ID = 1344933909778792500
warnings_data = {}

intents = discord.Intents.default()
intents.message_content = True
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

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")

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

@bot.event
async def on_message(message):
    if message.author.bot and message.author != bot.user: 
        return
    
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


owner_lock = False

@bot.command()
async def ownerlock(ctx):
    global owner_lock
    if ctx.author.id != 1281497404931051541:
        return

    owner_lock = not owner_lock

    if owner_lock:
        await ctx.reply("🔒 Owner lock enabled. Only the bot owner can use commands.")
    else:
        await ctx.reply("🔓 Owner lock disabled. Everyone can use commands again.")


@bot.check
async def global_command_check(ctx):
    if owner_lock and ctx.author.id != 1281497404931051541:
        return False
    return True


# Flask Keep Alive
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
