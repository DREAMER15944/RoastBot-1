
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
bot.__version__ = "1.2.1"
mc = MemberConverter()

# Load roasts
with open("database/roast.json", "r", encoding="UTF-8") as f:
    roasts = json.load(f)

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")

@bot.command(name="roast", description="Start an AI roast session. Take turns roasting with the AI.")
@max_concurrency(1, BucketType.user)
@cooldown(1, 30, BucketType.user)
async def _roast(ctx: Context, target: str = None, *, style: str = "default"):
    """Start an AI roast battle. If 'me' is given, roast the user interactively."""
    if target != "me":
        try:
            target = await mc.convert(ctx, target)
        except:
            target = None
        await _roast_someone(ctx, target)
        return

    style = style.lower().replace(" ", "_")
    if style not in Style.all:
        await ctx.reply(f"Invalid style. Use `{bot.command_prefix}help roast` for valid styles.")
        return

    pb = PromptButtons()
    msg = await ctx.reply(
        "We'll take turns roasting each other. Are you sure you can handle this?",
        view=pb
    )
    pb.msg = msg
    pb.ctx = ctx
    pb.style = style

class PromptButtons(discord.ui.View):
    def __init__(self, *, timeout=180):
        self.msg: discord.Message = None
        self.ctx: Context = None
        self.style: str = None
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your roast battle.", ephemeral=True)
            return
        await self.msg.edit(content="Roast battle started! Give me your best roast.", view=None)
        msg = await self.ctx.send(f"{self.ctx.author.mention} Alright, hit me with your best roast!")
        await _roast_battle(self.ctx, prev_msg=msg, style=self.style)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your roast battle.", ephemeral=True)
            return
        await self.msg.edit(content="You chickened out of the roast battle.", view=None)

class RoastBattleCancel(discord.ui.View):
    def __init__(self, *, timeout=180):
        self.ctx: Context = None
        self.convo: Conversation = None
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.grey)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your roast battle.", ephemeral=True)
            return
        self.convo.kill()
        self.convo.killed = True
        await interaction.message.edit(content=interaction.message.content, view=None)
        await interaction.response.send_message("You bailed out. Weak move.")

async def _roast_battle(ctx: Context, prev_msg: discord.Message, *, style: str = Style.default):
    """Handles interactive AI roast battles."""
    convo = Conversation(style)

    def check(m: discord.Message):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

    prev_msg = None
    while convo.alive:
        try:
            msg: discord.Message = await bot.wait_for("message", check=check, timeout=300)
            response = None
            while response is None:
                try:
                    if hasattr(convo, "killed"):
                        return
                    await ctx.typing()
                    if msg.content.lower() in ["stop", "quit"]:
                        if prev_msg:
                            await prev_msg.edit(content=prev_msg.content, view=None)
                        await ctx.channel.send(f"{ctx.author.mention} ran away. Weak move.")
                        convo.kill()
                        return
                    else:
                        response = convo.send(msg.content)
                except TimeoutError:
                    sleep(1)
                    await ctx.send(f"{ctx.author.mention}, I'm too tired for this. Later.")
                    convo.kill()
                    return
                except MessageLimitExceeded:
                    await ctx.reply("Enough roasting, you're already on fire!")
                    return
                except CharacterLimitExceeded:
                    await ctx.reply("Too long! Keep it under 250 characters.")
                    break
                else:
                    if prev_msg:
                        await prev_msg.edit(content=prev_msg.content, view=None)
                    rbc = RoastBattleCancel()
                    prev_msg = await msg.reply(response, view=rbc)
                    rbc.ctx = ctx
                    rbc.convo = convo
        except TimeoutError:
            convo.kill()
    if convo.alive:
        convo.kill()

async def _roast_someone(ctx: Context, target: discord.Member = None):
    """Roasts a specific user."""
    if target is None:
        await ctx.reply(random.choice([
            "You forgot to mention someone, dumbass.",
            "Cooking up a roast... Ready in <t:{}:f>".format(int(time() + random.randint(50_000, 500_000_000))),
        ]))
        return
    elif target.id == ctx.author.id:
        await ctx.reply(random.choice([
            "Roasting yourself? That's next-level loneliness.",
            "Look in the mirror for your roast."
        ]))
        return
    elif target.id == bot.user.id:
        await ctx.reply("I'm perfect. No roasts for me.")
        return

    roast = random.choice(roasts).replace("{mention}", f"**{target.display_name}**").replace("{author}", f"**{ctx.author.display_name}**")
    await ctx.reply(f"{target.mention} {_roast}")

@bot.event
async def on_command_error(ctx, ex):
    if isinstance(ex, CommandOnCooldown):
        await ctx.reply(f"Cooldown! Try again in **`{round(ex.retry_after, 1)}s`**")

@bot.command(name="help", description="Shows help menu.")
async def help(ctx: Context, *, command: str = None):
    """Displays help information."""
    if command is None:
        helpmsg = f"# {bot.user.display_name} Help Menu\n"
        for cmd in bot.walk_commands():
            helpmsg += f"## - `{cmd.qualified_name}`\n> {cmd.description or 'No description provided.'}\n"
    else:
        cmd = bot.get_command(command)
        helpmsg = f"# `{command}`\n" + (cmd.help if cmd else "Command not found.")
    await ctx.reply(helpmsg)

if __name__ == "__main__":
    bot.run(os.environ.get("TOKEN"), reconnect=True)
