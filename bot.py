import discord
import os
import random
import json
import requests
from discord.ext.commands import Bot, Context, cooldown, BucketType, MemberConverter, CommandOnCooldown
from dotenv import load_dotenv
from time import sleep, time

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = Bot(command_prefix="r!", intents=intents, help_command=None)
bot.__version__ = "1.2.3"
mc = MemberConverter()

# Logging function
def log_message(msg):
    print(f"[BOT LOG] {msg}")

# 🔹 Network test function
def test_network():
    log_message("Testing network connectivity...")
    try:
        response = requests.get("https://discord.com", timeout=5)
        if response.status_code == 200:
            log_message("✅ Internet connection working!")
            return True
        else:
            log_message("⚠️ Warning: Internet may be unstable!")
            return False
    except requests.RequestException:
        log_message("❌ No internet connection detected!")
        return False

# Load roast data
try:
    with open("database/roast.json", "r", encoding="UTF-8") as f:
        roasts = json.load(f)
    log_message("✅ Roast data loaded successfully!")
except FileNotFoundError:
    log_message("❌ Error: 'roast.json' file not found! Please check the path.")
    exit(1)

# Bot ready event
@bot.event
async def on_ready():
    log_message(f"✅ Bot is online as {bot.user}")

# 🔹 Ping command
@bot.command(name="ping", help="Check bot latency.")
async def ping(ctx: Context):
    latency = round(bot.latency * 1000)  # Convert to ms
    await ctx.send(f"🏓 Pong! Latency: `{latency}ms`")

# 🔹 Network test command
@bot.command(name="network", help="Check internet connection.")
async def network(ctx: Context):
    if test_network():
        await ctx.send("✅ Network is working fine!")
    else:
        await ctx.send("❌ No internet connection detected!")

# 🔹 Roast command (single roast)
@bot.command(name="roast", description="Roast yourself or someone else!")
@cooldown(1, 30, BucketType.user)
async def roast(ctx: Context, target: str = None):
    if target and target.lower() == "me":
        await start_roast_battle(ctx)
        return

    if target:
        try:
            target = await mc.convert(ctx, target)
        except:
            target = None
    roast_target = target or ctx.author
    roast_message = random.choice(roasts).replace("{mention}", f"**{roast_target.display_name}**")
    await ctx.send(f"{roast_target.mention} {roast_message}")

# 🔹 Interactive Roast Battle
async def start_roast_battle(ctx: Context):
    await ctx.send(
        f"🔥 {ctx.author.mention}, you think you can handle this? Alright, let's take turns roasting each other!\n"
        f"Type your best roast, or say **stop** to quit!"
    )

    def check(m):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

    while True:
        try:
            msg = await bot.wait_for("message", check=check, timeout=120)
            if msg.content.lower() in ["stop", "quit"]:
                await ctx.send("😆 You chickened out! Better luck next time.")
                return

            roast_response = random.choice(roasts).replace("{mention}", f"**{ctx.author.display_name}**")
            await ctx.send(roast_response)

        except TimeoutError:
            await ctx.send("⏳ You took too long! Roast battle over.")
            return

# 🔹 Help command
@bot.command(name="help", description="Show available commands.")
async def help(ctx: Context):
    help_msg = "**📜 Available Commands:**\n"
    for command in bot.commands:
        help_msg += f"**`{bot.command_prefix}{command.name}`** - {command.help}\n"
    await ctx.send(help_msg)

# 🔹 Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandOnCooldown):
        await ctx.reply(f"⏳ Cooldown active! Try again in **{round(error.retry_after, 1)}s**")
    else:
        log_message(f"⚠️ Error: {error}")

# Start bot
if __name__ == "__main__":
    if not test_network():
        exit(1)  # Stop bot if no network
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        log_message("❌ ERROR: Discord Bot Token not found in environment variables!")
        exit(1)
    bot.run(TOKEN, reconnect=True)
