import discord, os, random, json, requests
from discord.ext.commands import Bot, Context, max_concurrency, BucketType, cooldown, MemberConverter
from discord.ext.commands.errors import CommandOnCooldown
from dotenv import load_dotenv
from time import sleep, time

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = Bot(command_prefix="r!", intents=intents, help_command=None)
mc = MemberConverter()

# Load roasts from JSON
with open("database/roast.json", "r", encoding="UTF-8") as f:
    roasts = json.load(f)

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

# ✅ Network Check Command
@bot.command(name="network", description="Check if the bot has internet access.")
async def network(ctx: Context):
    try:
        response = requests.get("https://www.google.com", timeout=5)
        if response.status_code == 200:
            await ctx.reply("✅ Bot has an active internet connection!")
        else:
            await ctx.reply("⚠️ Bot is online but unable to reach external networks.")
    except requests.ConnectionError:
        await ctx.reply("❌ No internet connection detected!")

# ✅ Roast Battle Interactive Command
@bot.command(name="roast", description="Start a roast battle with the AI.")
@max_concurrency(1, BucketType.user)
@cooldown(1, 30, BucketType.user)
async def roast(ctx: Context, target: str = None):
    if target == "me":
        await start_roast_battle(ctx)
    else:
        try:
            target = await mc.convert(ctx, target)
        except:
            target = None
        await roast_someone(ctx, target)

async def start_roast_battle(ctx: Context):
    pb = PromptButtons()
    msg = await ctx.reply(
        "🔥 Ready for a roast battle? I'll roast you, and you can try to roast me back! Click **Confirm** to start.",
        view=pb
    )
    pb.msg = msg
    pb.ctx = ctx

async def roast_someone(ctx: Context, target: discord.Member = None):
    if target is None:
        await ctx.reply("Who do you want to roast? Mention them like `r!roast @user`")
        return
    roast = random.choice(roasts).replace("{mention}", f"**{target.display_name}**")
    await ctx.channel.send(f"{target.mention} {roast}")

class PromptButtons(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
        self.msg: discord.Message = None
        self.ctx: Context = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This is not your roast battle!", ephemeral=True)
            return
        await self.msg.edit(content="🔥 Roast battle started! Send your best roast.", view=None)
        await self.ctx.send(f"{self.ctx.author.mention} You go first! Send me your best roast.")
        await roast_battle(self.ctx)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This is not your roast battle!", ephemeral=True)
            return
        await self.msg.edit(content="❌ Roast battle canceled.", view=None)

async def roast_battle(ctx: Context):
    while True:
        try:
            msg = await bot.wait_for("message", check=lambda m: m.author == ctx.author, timeout=300)
            if msg.content.lower() in ["stop", "quit"]:
                await ctx.send(f"{ctx.author.mention} chickened out of the roast battle! 🐔🔥")
                break
            else:
                roast = random.choice(roasts)
                await ctx.send(roast)
        except Exception as e:
            print(f"Error in roast battle: {e}")
            break

# ✅ Error Handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandOnCooldown):
        await ctx.reply(f"⏳ You're on cooldown! Try again in **{round(error.retry_after, 1)}s**.")
    elif isinstance(error, discord.ext.commands.CommandNotFound):
        await ctx.reply("❌ Invalid command! Use `r!help` for the list of commands.")
    else:
        print(f"⚠️ Error: {error}")

# ✅ Help Command
@bot.command(name="help", description="Shows the help menu.")
async def help(ctx: Context):
    help_msg = "**📜 Commands:**\n"
    help_msg += "`r!roast @user` - Roast someone 🔥\n"
    help_msg += "`r!roast me` - Start an interactive roast battle\n"
    help_msg += "`r!network` - Check bot's internet connection 🌐\n"
    help_msg += "`r!help` - Show this help menu 📜\n"
    await ctx.reply(help_msg)

if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))
