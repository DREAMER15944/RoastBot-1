import discord
import os
import random
import json
import requests
from time import sleep, time
from dotenv import load_dotenv
from discord.ext.commands import Bot, Context, cooldown, BucketType, MemberConverter, CommandOnCooldown
from roastedbyai import Conversation, MessageLimitExceeded, CharacterLimitExceeded, Style

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = Bot(command_prefix="r!", intents=intents, help_command=None)
bot.__version__ = "1.2.1"
mc = MemberConverter()

# Load roasts database
with open("database/roast.json", "r", encoding="UTF-8") as f:
    roasts = json.load(f)


@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")


### --- 🔥 ROAST COMMAND --- ###
@bot.command(name="roast", description="Start an AI roast battle. Take turns roasting each other.")
@cooldown(1, 30, BucketType.user)
async def roast(ctx: Context, target: str = None, *, style: str = "default"):
    """AI Roast Battle Command"""
    if target and target.lower() != "me":
        try:
            target = await mc.convert(ctx, target)
        except:
            target = None
        await roast_someone(ctx, target)
        return

    style = style.lower().replace(" ", "_")
    if style not in Style.all:
        await ctx.reply(f"❌ Invalid style. Use `{bot.command_prefix}help roast` for a list of styles.")
        return

    view = RoastPrompt(ctx, style)
    msg = await ctx.reply(
        "🔥 We'll take turns roasting each other. Are you sure you can handle it?",
        view=view
    )
    view.msg = msg


### --- 🎭 ROAST BUTTON PROMPT --- ###
class RoastPrompt(discord.ui.View):
    def __init__(self, ctx, style, *, timeout=180):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.style = style

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("⚠️ This is not your roast battle.", ephemeral=True)
            return

        stop_view = RoastStop(self.ctx)
        await self.msg.edit(content="🔥 You accepted the roast battle. Bring it on!", view=None)
        await self.ctx.send(f"{self.ctx.author.mention}, give me your best roast!", view=stop_view)
        await start_roast_battle(self.ctx, self.style, stop_view)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("⚠️ This is not your roast battle.", ephemeral=True)
            return

        await self.msg.edit(content="❌ You chickened out of the roast battle.", view=None)


### --- 🚫 ROAST STOP BUTTON --- ###
class RoastStop(discord.ui.View):
    def __init__(self, ctx, *, timeout=180):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.convo = None

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.grey)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("⚠️ This is not your roast battle.", ephemeral=True)
            return

        self.convo.kill()
        await interaction.message.edit(content="🚫 Roast battle stopped.", view=None)
        await interaction.response.send_message("Boo, you're no fun!")


### --- 🔄 ROAST BATTLE FUNCTION --- ###
async def start_roast_battle(ctx: Context, style: str, view: RoastStop):
    convo = Conversation(style)
    view.convo = convo

    def check(m: discord.Message):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

    while convo.alive:
        try:
            msg: discord.Message = await bot.wait_for("message", check=check, timeout=300)
            if msg.content.lower() in ["stop", "quit"]:
                await ctx.send("🚫 Roast battle ended. You couldn't handle the heat!")
                convo.kill()
                return

            await ctx.typing()
            response = convo.send(msg.content)
            if not response:
                await ctx.reply("⚠️ AI didn't respond! Try again.")
                continue

            await msg.reply(response, view=view)

        except Exception as e:
            await ctx.reply("⚠️ AI Error. Try again later.")
            print(f"❌ API Error: {e}")
            return


### --- 🎯 ROAST SOMEONE COMMAND --- ###
async def roast_someone(ctx: Context, target: discord.Member = None):
    """Roast someone directly"""
    if target is None:
        await ctx.reply("You forgot to mention someone to roast! 😆")
        return
    if target.id == ctx.author.id:
        await ctx.reply("😂 You want to roast yourself? That's some next-level self-burn.")
        return
    if target.id == bot.user.id:
        await ctx.reply("I’m flawless. I don’t roast myself. 😎")
        return

    roast = random.choice(roasts).replace("{mention}", target.mention)
    await ctx.channel.send(roast)


### --- 📌 GENERAL COMMANDS --- ###
@bot.command(name="ping", description="Check bot latency.")
async def ping(ctx: Context):
    """Returns the bot's ping"""
    latency = round(bot.latency * 1000, 2)
    await ctx.reply(f"🏓 Pong! Latency: `{latency}ms`")


@bot.command(name="version", description="Show bot version info.")
async def version(ctx: Context):
    """Returns the bot version"""
    await ctx.reply(f"🤖 Bot Version: `{bot.__version__}`")


@bot.command(name="network", description="Test network connectivity.")
async def network(ctx: Context):
    """Checks if the bot can access the internet"""
    try:
        requests.get("https://www.google.com", timeout=5)
        await ctx.reply("✅ Network is working fine!")
    except requests.ConnectionError:
        await ctx.reply("❌ No internet connection detected!")


@bot.command(name="help", description="Shows the help menu.")
async def help(ctx: Context, command: str = None):
    """Shows the help menu."""
    if command is None:
        help_msg = f"📜 **{bot.user.display_name} Help Menu**\n\n"
        for cmd in bot.walk_commands():
            help_msg += f"🔹 `{cmd.qualified_name}` - {cmd.description or 'No description provided.'}\n"
    else:
        cmd = bot.get_command(command)
        help_msg = f"📌 **`{command}`**\n" + (cmd.help if cmd else "❌ Command not found.")
    await ctx.reply(help_msg)


### --- 🎯 ERROR HANDLING --- ###
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandOnCooldown):
        await ctx.reply(f"⏳ You're on cooldown! Try again in **`{round(error.retry_after, 1)}s`**.")
    else:
        print(f"❌ Error: {error}")


### --- 🚀 BOT STARTUP --- ###
if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"), reconnect=True)

