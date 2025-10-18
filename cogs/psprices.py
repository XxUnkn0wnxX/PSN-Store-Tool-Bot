import discord
from discord import Option
from discord.ext import commands
from api.common import APIError
from api.psprices import PSPrices

class PSPricesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    ps_prices_group = discord.SlashCommandGroup("psprices", description="🏷️ PSPrices utilities")

    @ps_prices_group.command(description="🔗 Grabs the product ID from a PSPrices URL.")
    async def product_id(
              self,
              ctx: discord.ApplicationContext, 
              url: Option(str, description="🔗 Link to psprices avatar page") # type: ignore
            ) -> None:
        
        embed_processing = discord.Embed(
            title="🔗 Processing URL...",
            description="⏳ Extracting product ID from PSPrices link...",
            color=0xf39c12
        )
        await ctx.respond(embed=embed_processing)

        embed_disabled = discord.Embed(
            title="⚠️ Command Unavailable",
            description=(
                "PSPrices now blocks automated access, so this lookup is disabled. "
                "Open the PSPrices link in your browser, copy the PlayStation Store "
                "product ID manually, and use that with the PSN commands."
            ),
            color=0xe67e22
        )
        embed_disabled.set_footer(text="📝 Example product ID: EP4015-NPEB00982_00-AVAGARESTG000009")
        await ctx.edit(embed=embed_disabled)
        return
       

def setup(bot: commands.Bot) -> None:
    bot.add_cog(PSPricesCog(bot))
