import discord, os, random, json, requests
from discord.ext.commands import Bot, Context, max_concurrency, BucketType, cooldown
from discord.ext.commands.errors import CommandOnCooldown
from dotenv import load_dotenv
from time import sleep, time
from roastedbyai import Conversation, MessageLimitExceeded, CharacterLimitExceeded, Style

load_dotenv()

# Using the bot's ID as prefix
intents = discord.Intents.default()
intents.message_content = True
bot = Bot(command_prefix="r!", intents=intents, help_command=None)
bot.__version__ = "1.2.1"

# Load roasts from JSON file
with open("database/roast.json", "r", encoding="UTF-8") as f:
    roasts = json.load(f)

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

# 🔥 Roast Battle Command
@bot.command(name="roast", description="Start an AI roast session.")
@max_concurrency(1, BucketType.user)
@max_concurrency(4, BucketType.channel)
@max_concurrency(12, BucketType.guild)
@cooldown(1, 30, BucketType.user)
async def _roast(ctx: Context, target: str = None, *, style: str = "default"):
    if target != "me":
        await _roast_someone(ctx, target)
        return

    style = style.lower().replace(" ", "_")
    if style not in Style.all:
        await ctx.reply(f"❌ Invalid style. Use `{bot.command_prefix}help roast` for options.")
        return

    pb = PromptButtons()
    msg = await ctx.reply("🔥 Ready to get roasted? Click **Confirm** to continue!", view=pb)
    pb.msg, pb.ctx, pb.style = msg, ctx, style

# 📌 Buttons for roast confirmation
class PromptButtons(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
        self.msg, self.ctx, self.style = None, None, None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Not your battle!", ephemeral=True)
            return

        await self.msg.edit(content="🔥 Let’s get roasting! Send your best roast.", view=None)
        stop_view = RoastBattleCancel()
        msg = await self.ctx.send(f"{self.ctx.author.mention} Start roasting! Type **stop** to end.", view=stop_view)
        await start_roast_battle(self.ctx, msg, stop_view)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Not your battle!", ephemeral=True)
            return
        await self.msg.edit(content="🚫 Roast battle canceled.", view=None)

# 🔴 Stop Button
class RoastBattleCancel(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
        self.ctx, self.convo = None, None

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.grey)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Not your battle!", ephemeral=True)
            return
        self.convo.kill()
        self.convo.killed = True
        await interaction.message.edit(content="🔥 Roast battle ended!", view=None)
        await interaction.response.send_message("Boo! You quit early!")

# 🧠 AI Roast Battle (Chatbot-like)
async def start_roast_battle(ctx: Context, prev_msg: discord.Message, view: RoastBattleCancel):
    convo = Conversation(view.ctx.style)
    view.ctx, view.convo = ctx, convo

    def check(m: discord.Message):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

    while convo.alive:
        try:
            msg: discord.Message = await bot.wait_for("message", check=check, timeout=300)
            raw_response = requests.post(convo._Conversation__url, json={"input": msg.content}, headers=convo._Conversation__headers)
            print(f"🔍 API Response: {raw_response.text}")  # Debugging

            response = raw_response.json().get("content", None)
            if msg.content.lower() in ["stop", "quit"]:
                await ctx.send("🔥 Roast battle ended! You ran away like a chicken. 🐔")
                convo.kill()
                return

            if not response:
                await ctx.reply("⚠️ AI didn't respond! Try again.")
                continue

            prev_msg = await msg.reply(response, view=view)

        except (requests.exceptions.JSONDecodeError, MessageLimitExceeded, CharacterLimitExceeded) as e:
            await ctx.reply("⚠️ Too much roasting! Try again.")
            print(f"API Error: {e}")
            return
        except TimeoutError:
            await ctx.send("⏳ You took too long. Roast battle ended.")
            convo.kill()
            return

# 🎯 Roast Someone
async def _roast_someone(ctx: Context, target: str = None):
    if not target:
        await ctx.reply(random.choice([
            "🔥 Forgot to mention someone! Who do you want to roast?",
            "🚨 Name someone to roast!"
        ]))
        return

    roast = random.choice(roasts)
    roast_msg = f"{target} {roast}" if type(roast) is str else roast[0]
    await ctx.send(roast_msg)

# 📢 Help Command
@bot.command(name="help", description="Shows available commands.")
async def help(ctx: Context, *, command: str = None):
    if command:
        cmd = bot.get_command(command)
        helpmsg = f"**`{command}`**\n{cmd.help if cmd else '❌ Command not found.'}"
    else:
        helpmsg = "**🔹 Available Commands:**\n"
        for cmd in bot.walk_commands():
            helpmsg += f"🔹 `{cmd.qualified_name}` - {cmd.description or 'No description.'}\n"
    await ctx.reply(helpmsg)

# 📶 Ping Command
@bot.command(name="ping", description="Check bot latency.")
async def ping(ctx: Context):
    await ctx.reply(f"🏓 Pong! Latency: **{round(bot.latency * 1000)}ms**")

# 🔄 Version Command
@bot.command(name="version", description="Show bot version.")
async def version(ctx: Context):
    await ctx.reply(f"**🤖 Bot Version:** `{bot.__version__}`")

# 🌐 Network Test Command
@bot.command(name="network", description="Check API connectivity.")
async def network(ctx: Context):
    try:
        response = requests.get("https://www.google.com", timeout=5)
        if response.status_code == 200:
            await ctx.reply("✅ Network connection: **OK**")
        else:
            await ctx.reply("⚠️ Network issue detected!")
    except requests.exceptions.RequestException:
        await ctx.reply("❌ No network connection!")

# 🚀 Handle Cooldowns
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandOnCooldown):
        await ctx.reply(f"⏳ Cooldown! Try again in **{round(error.retry_after, 1)}s**.")

# 🎭 Run Bot
if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"), reconnect=True)
