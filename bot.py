import discord, os, random, json
from discord.ext.commands import Bot, Context, max_concurrency, BucketType, cooldown, MemberConverter
from discord.ext.commands.errors import CommandOnCooldown
from dotenv import load_dotenv
from time import sleep, time
from roastedbyai import Conversation, MessageLimitExceeded, CharacterLimitExceeded, Style

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = Bot(command_prefix="r!", intents=intents, help_command=None)
bot.__version__ = "1.2.0"
mc = MemberConverter()

# Load roast messages
with open("database/roast.json", "r", encoding="UTF-8") as f:
    roasts = json.load(f)

@bot.event
async def on_ready():
    print("Bot logged in as {}".format(bot.user))

@bot.command(name="roast", description="Start an AI roast session.")
@max_concurrency(1, BucketType.user)
@cooldown(1, 30, BucketType.user)
async def _roast(ctx: Context, target: str = None, *, style: str = "default"):
    if target != "me":
        try:
            target = await mc.convert(ctx, target)
        except:
            target = None
        await _roast_someone(ctx, target)
        return

    style = style.lower().replace(" ", "_")
    if style not in Style.all:
        await ctx.reply(f"Invalid style! Use `{bot.command_prefix}help roast` for valid styles.")
        return

    pb = PromptButtons(ctx, style=style)
    msg = await ctx.reply(
        "We'll be taking turns roasting each other. Are you sure you can handle this?",
        view=pb
    )
    pb.msg = msg

class PromptButtons(discord.ui.View):
    def __init__(self, ctx, style, *, timeout=180):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.style = style

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This is not your roast battle.", ephemeral=True)
            return

        await interaction.response.defer()
        await _roast_battle(self.ctx, prev_msg=self.msg, style=self.style)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This is not your roast battle.", ephemeral=True)
            return
        await self.msg.edit(content="You chickened out of the roast battle.", view=None)

class RoastBattleCancel(discord.ui.View):
    def __init__(self, ctx, convo, *, timeout=180):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.convo = convo

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.grey)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This is not your roast battle.", ephemeral=True)
            return
        self.convo.kill()
        await interaction.message.edit(content="Roast battle ended.", view=None)

async def _roast_battle(ctx: Context, prev_msg: discord.Message, *, style: str = Style.default):
    convo = Conversation(style)

    def check(m: discord.Message):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

    prev_msg = None
    while convo.alive:
        try:
            msg = await bot.wait_for("message", check=check, timeout=300)

            response = convo.send(msg.content)
            print(f"API Response: {response}")  # Debugging log

            if not response or response.strip() == "":
                await ctx.reply("Oops! I couldn't generate a roast this time. Try again.")
                return

            if msg.content.lower() in ["stop", "quit"]:
                await ctx.channel.send(f"{ctx.author.mention} quit the battle. Weak!")
                convo.kill()
                return

            rbc = RoastBattleCancel(ctx, convo)
            prev_msg = await msg.reply(response, view=rbc)

        except TimeoutError:
            convo.kill()
            await ctx.send(f"{ctx.author.mention} roast session timed out.")
            return

async def _roast_someone(ctx: Context, target: discord.Member = None):
    if target is None:
        await ctx.reply("Mention someone to roast!")
        return
    elif target.id == ctx.author.id:
        await ctx.reply("Why roast yourself? Go find an enemy!")
        return
    elif target.id == bot.user.id:
        await ctx.reply("You can't roast me, I'm invincible!")
        return

    roast = random.choice(roasts).replace("{mention}", target.mention)
    await ctx.channel.send(roast)

@bot.event
async def on_command_error(ctx, ex):
    if isinstance(ex, CommandOnCooldown):
        await ctx.reply(f"You're on cooldown. Try again in **{round(ex.retry_after, 1)}s**.")

@bot.command(name="help", description="Shows the help menu.")
async def help(ctx: Context, *, command: str = None):
    if command is None:
        helpmsg = f"# {bot.user.display_name} Help Menu\n"
        for cmd in bot.walk_commands():
            helpmsg += f"## - `{cmd.qualified_name}`\n> {cmd.description or 'No description provided.'}\n"
    else:
        cmd = bot.get_command(command)
        helpmsg = f"# `{command}`\n" + (cmd.help if cmd else "This command does not exist.")
    await ctx.reply(helpmsg)

if __name__ == "__main__":
    PORT = os.getenv("PORT", 5000)  # Ensure port is set for Render
    bot.run(os.environ.get("TOKEN"), reconnect=True)
