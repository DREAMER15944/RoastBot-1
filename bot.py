import discord, os, random, json, socket
from discord.ext import commands
from dotenv import load_dotenv
from roastedbyai import Conversation, MessageLimitExceeded, CharacterLimitExceeded, Style

load_dotenv()

# Setup bot
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="r!", intents=intents, help_command=None)
bot.__version__ = "1.3.0"

# Load roasts
with open("database/roast.json", "r", encoding="UTF-8") as f:
    roasts = json.load(f)

# Network connectivity check
def check_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online and ready!")
    if not check_internet():
        print("⚠ Warning: No internet connection detected!")

# Commands
@bot.command(name="ping", description="Check bot's latency.")
async def ping(ctx):
    await ctx.reply(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")

@bot.command(name="version", description="Shows bot version.")
async def version(ctx):
    await ctx.reply(f"🤖 Roast Bot Version: `{bot.__version__}`")

@bot.command(name="help", description="Shows the help menu.")
async def help(ctx, *, command: str = None):
    if command is None:
        helpmsg = f"📜 **{bot.user.display_name} Help Menu**\n"
        for cmd in bot.commands:
            helpmsg += f"**`{cmd.name}`** - {cmd.description}\n"
    else:
        cmd = bot.get_command(command)
        helpmsg = f"**`{command}`**\n{cmd.help if cmd else 'This command does not exist.'}"
    await ctx.reply(helpmsg)

# AI Roast Battle
@bot.command(name="roast", description="Start an AI roast battle!")
async def roast(ctx, *, style: str = "default"):
    style = style.lower().replace(" ", "_")
    if style not in Style.all:
        await ctx.reply(f"❌ Invalid style! Use `{bot.command_prefix}help roast` for valid styles.")
        return
    
    view = RoastConfirmButtons()
    msg = await ctx.reply("🔥 Ready to roast? Click **Confirm** to start!", view=view)
    view.ctx, view.msg, view.style = ctx, msg, style

class RoastConfirmButtons(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
        self.ctx = None
        self.msg = None
        self.style = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("🚫 Not your battle!", ephemeral=True)
            return
        
        await self.msg.edit(content="🔥 Roast battle started! Give me your best shot!", view=None)
        stop_view = RoastStopButton()
        stop_view.ctx = self.ctx
        await start_roast_battle(self.ctx, stop_view)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("🚫 Not your battle!", ephemeral=True)
            return
        await self.msg.edit(content="🐔 You chickened out!", view=None)

class RoastStopButton(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
        self.ctx = None
        self.convo = None

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.grey)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("🚫 Not your battle!", ephemeral=True)
            return
        self.convo.kill()
        await interaction.message.edit(content="💀 Roast battle ended!", view=None)
        await interaction.response.send_message("Boringggg...")

async def start_roast_battle(ctx, stop_view):
    convo = Conversation("default")
    stop_view.convo = convo
    await ctx.send(f"{ctx.author.mention} Alright, hit me with your best roast!", view=stop_view)

    def check(m):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

    prev_msg = None
    while convo.alive:
        try:
            msg = await bot.wait_for("message", check=check, timeout=300)
            response = None
            while response is None:
                try:
                    if msg.content.lower() in ["stop", "quit"]:
                        await ctx.send("🐔 You chickened out! Byeee!")
                        convo.kill()
                        return
                    await ctx.typing()
                    response = convo.send(msg.content)
                except (MessageLimitExceeded, CharacterLimitExceeded):
                    await ctx.reply("💀 Too much! Keep it under 250 characters!")
                    break
                else:
                    if prev_msg:
                        await prev_msg.edit(content=prev_msg.content, view=None)
                    prev_msg = await msg.reply(response, view=stop_view)
        except TimeoutError:
            convo.kill()

# Error Handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"🕒 Cooldown! Try again in `{round(error.retry_after, 1)}s`")
    else:
        await ctx.reply(f"⚠ Error: `{str(error)}`")

# Run bot
if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"), reconnect=True)
