import discord
from discord.ext import commands

tutorialstring = (
    "🎮 **1**. First go to playstation.com\n"
    "🌍 **2**. When you have loaded check the link and you will see your region\n"
    "🔐 **3**. Now login to your account\n"
    "🔍 **4**. Go to inspect element and click '>>' at the top\n"
    "📱 **5**. Click on the 'Application' option\n"
    "🍪 **6**. Navigate to cookies for playstation.com and look for the 'pdccws_p' cookie. That cookie is your token\n"
    "🆔 **7**. You will find the avatar id by using /psprices product_id with the url to the avatar page on psprices\n"
)

credits_string = (
    "💻 **Original Creator:** [groriz11](https://github.com/groriz11)\n"
    "🛠️ **Maintained by:** [OpenAI](https://openai.com/codex/)\n"
    "🤖 **Bot Development:** PSNToolBot Team\n"
    "⚡ **Powered by:** Discord.py & PSNAWP\n"
    "🎨 **Enhanced with:** Custom embeds and emojis"
)

tutorialemb = discord.Embed(
    title="📚 **HOW TO USE THE BOT**", 
    description=tutorialstring, 
    color=0x3498db
)
tutorialemb.set_footer(text="💡 Need help? Check out our commands!")

creditsemb = discord.Embed(
    title="👥 **CREDITS & INFORMATION**",
    description=credits_string,
    color=0x9b59b6
)
creditsemb.set_footer(text="🙏 Thank you for using PSNToolBot!")

class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @discord.slash_command(description="🏓 Pings the bot to check latency.")
    async def ping(self, ctx: discord.ApplicationContext) -> None:
        latency = self.bot.latency * 1000
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"⚡ **Latency:** {latency:.2f}ms",
            color=0x2ecc71
        )
        embed.set_footer(text="🤖 Bot is running smoothly!")
        await ctx.respond(embed=embed)

    @discord.slash_command(description="📚 Shows how to use the bot.")
    async def tutorial(self, ctx: discord.ApplicationContext) -> None:
        await ctx.respond(embed=tutorialemb, ephemeral=True)

    @discord.slash_command(description="👥 Shows credits and bot information.")
    async def credits(self, ctx: discord.ApplicationContext) -> None:
        await ctx.respond(embed=creditsemb, ephemeral=True)

def setup(bot: commands.Bot) -> None:
    bot.add_cog(Misc(bot))
