import discord, os, random, json, requests
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

# Load roast messages from JSON
with open("database/roast.json", "r", encoding="UTF-8") as f:
    roasts = json.load(f)

@bot.event
async def on_ready():
    print("Bot logged in as {}".format(bot.user))

@bot.command(name="roast", description="Start an AI roast session.")
@max_concurrency(1, BucketType.user)
@cooldown(1, 30, BucketType.user)
async def _roast(ctx: Context, target: str = None, *, style: str = "default"):
    """Start an AI roast battle."""
    if target != "me":
        try:
            target = await mc.convert(ctx, target)
        except:
            target = None
        await _roast_someone(ctx, target)
        return

    style = style.lower().replace(" ", "_")
    if style not in Style.all:
        await ctx.reply(f"Invalid style. Run `{bot.command_prefix}help roast` for available styles.")
        return

    pb = PromptButtons()
    msg = await ctx.reply(
        "We'll take turns roasting each other. Are you sure you can handle it?",
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
            await interaction.response.send_message("This isn't your battle.", ephemeral=True)
            return

        await self.msg.edit(content="You accepted the roast battle!", view=None)
        msg = await self.ctx.send(f"{self.ctx.author.mention} Start roasting! Type 'stop' to end.")
        await _roast_battle(self.ctx, prev_msg=msg, style=self.style)

@bot.command(name="test_network", description="Check if the bot has internet access.")
async def test_network(ctx: Context):
    """Check if the bot can access the internet."""
    try:
        response = requests.get("https://google.com")
        await ctx.send(f"✅ Network Test Passed! Status Code: {response.status_code}")
    except Exception as e:
        await ctx.send(f"❌ Network Test Failed! Error: {str(e)}")

async def _roast_battle(ctx: Context, prev_msg: discord.Message, *, style: str = Style.default):
    """Handles the roast battle logic."""
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
                        await ctx.channel.send(f"{ctx.author.mention} chickened out. Battle over!")
                        convo.kill()
                        return

                    response = convo.send(msg.content)
                    
                    # Debugging log
                    print(f"API Response: {response}")

                    # Handle invalid responses
                    if not response or not isinstance(response, str):
                        await ctx.send("The AI failed to respond. Try again later!")
                        convo.kill()
                        return

                except TimeoutError:
                    sleep(1)
                    await ctx.send(f"{ctx.author.mention} I'm too tired to continue. Bye!")
                    convo.kill()
                    return
                except MessageLimitExceeded:
                    await ctx.reply("Enough roasting! Someone is burning...")
                    return
                except CharacterLimitExceeded:
                    await ctx.reply("Too long! Keep it under 250 characters.")
                    break
                except json.decoder.JSONDecodeError:
                    print("⚠️ JSON Decode Error: API returned invalid JSON.")
                    await ctx.send("Error processing response. Try again later.")
                    return

                if prev_msg:
                    await prev_msg.edit(content=prev_msg.content, view=None)

                prev_msg = await msg.reply(response)

        except TimeoutError:
            convo.kill()

async def _roast_someone(ctx: Context, target: discord.Member = None):
    """Roast a specific person."""
    if target is None:
        await ctx.reply("You forgot to mention someone to roast!")
        return
    elif target.id == ctx.author.id:
        await ctx.reply("Why roast yourself? Are you okay?")
        return
    elif target.id == bot.user.id:
        await ctx.reply("Nice try! I won't roast myself.")
        return

    roast = random.choice(roasts)
    if type(roast) is list:
        roast_text = roast[0].replace("{mention}", f"**{target.display_name}**").replace("{author}", f"**{ctx.author.display_name}**")
        roast_explanation = roast[1]
    else:
        roast_text = roast

    await ctx.channel.send(f"{target.mention} {roast_text}")

@bot.event
async def on_command_error(ctx, ex):
    if isinstance(ex, CommandOnCooldown):
        await ctx.reply(f"You're on cooldown. Try again in **{round(ex.retry_after, 1)}s**")

@bot.command(name="help", description="Shows the help menu.")
async def help(ctx: Context, *, command: str = None):
    """Shows the help menu."""
    if command is None:
        helpmsg = f"# {bot.user.display_name} Help Menu\n"
        for cmd in bot.walk_commands():
            helpmsg += f"## - `{cmd.qualified_name}`\n> {cmd.description or 'No description provided.'}\n"
    else:
        cmd = bot.get_command(command)
        helpmsg = f"# `{command}`\n" + (cmd.help if cmd else "This command does not exist.")
    await ctx.reply(helpmsg)

if __name__ == "__main__":
    bot.run(os.environ.get("TOKEN"), reconnect=True)
