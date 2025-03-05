import discord, os, json, random
from discord.ext import commands
from dotenv import load_dotenv
from roastedbyai import Conversation, Style

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="r!", intents=intents, help_command=None)

# Load roast lines
with open("database/roast.json", "r", encoding="UTF-8") as f:
    roasts = json.load(f)

@bot.event
async def on_ready():
    print(f"🔥 {bot.user} is online and ready to roast!")

@bot.command(name="roast", description="Start an interactive AI roast battle.")
async def roast(ctx, target: str = None, *, style: str = "default"):
    """Initiates a roast battle with AI responding interactively."""
    if target and target.lower() != "me":
        await roast_someone(ctx, target)
        return

    style = style.lower().replace(" ", "_")
    if style not in Style.all:
        await ctx.reply(f"Invalid style. Use `{bot.command_prefix}help roast` for options.")
        return

    view = PromptButtons()
    msg = await ctx.reply("🔥 Ready for a roast battle? Confirm to start!", view=view)
    view.msg, view.ctx, view.style = msg, ctx, style

class PromptButtons(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
        self.msg = None
        self.ctx = None
        self.style = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your roast battle!", ephemeral=True)
            return

        await self.msg.edit(content="🔥 Let’s roast! You start first!", view=None)
        msg = await self.ctx.send(f"{self.ctx.author.mention}, hit me with your best roast!")
        await roast_battle(self.ctx, prev_msg=msg, style=self.style)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your roast battle!", ephemeral=True)
            return
        await self.msg.edit(content="😶 You backed out. Maybe next time!", view=None)

class RoastBattleCancel(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
        self.ctx = None
        self.convo = None

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.grey)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your roast battle!", ephemeral=True)
            return
        self.convo.kill()
        await interaction.message.edit(content="🔥 Roast battle ended!", view=None)

async def roast_battle(ctx, prev_msg, *, style="default"):
    """Handles the back-and-forth AI roast battle."""
    convo = Conversation(style)

    def check(m):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

    while convo.alive:
        try:
            msg = await bot.wait_for("message", check=check, timeout=300)
            if msg.content.lower() in ["stop", "quit"]:
                await ctx.send(f"😆 {ctx.author.mention} chickened out! Roast battle over.")
                convo.kill()
                return

            await ctx.typing()
            response = convo.send(msg.content)
            rbc = RoastBattleCancel()
            prev_msg = await msg.reply(response, view=rbc)
            rbc.ctx, rbc.convo = ctx, convo

        except Exception:
            convo.kill()
            return

async def roast_someone(ctx, target):
    """Roasts a specific user."""
    try:
        target_member = await commands.MemberConverter().convert(ctx, target)
    except:
        await ctx.reply("❌ User not found!")
        return

    roast_line = random.choice(roasts).replace("{mention}", f"**{target_member.display_name}**")
    await ctx.send(f"{target_member.mention} {roast_line}")

bot.run(os.getenv("TOKEN"))
