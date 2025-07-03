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

        try:
            api = PSPrices(url)
            product_id = await api.obtain_skuid()
        except APIError as e:
            embed_error = discord.Embed(
                title="❌ Invalid URL", 
                description=f"🚫 {e}", 
                color=0xe74c3c
            )
            embed_error.set_footer(text="💡 Make sure you're using a valid PSPrices URL!")
            await ctx.edit(embed=embed_error)
            return

        embed_success = discord.Embed(
            title="✅ Product ID Found!",
            description=f"🆔 **Product ID:** `{product_id}`",
            color=0x27ae60
        )
        embed_success.set_footer(text="📋 Copy this ID to use with PSN commands!")
        await ctx.edit(embed=embed_success)
       

def setup(bot: commands.Bot) -> None:
    bot.add_cog(PSPricesCog(bot))