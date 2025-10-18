import discord
import os
from discord.ext import commands
from discord import Option
from api.common import APIError
from api.psn import PSN, PSNRequest
from psnawp_api.core.psnawp_exceptions import PSNAWPNotFoundError as PSNAWPNotFound

valid_regions = [
    "ar-AE", "ar-BH", "ar-KW", "ar-LB", "ar-OM", "ar-QA", "ar-SA", "ch-HK",
    "ch-TW", "cs-CZ", "da-DK", "de-AT", "de-CH", "de-DE", "de-LU", "el-GR",
    "en-AE", "en-AR", "en-AU", "en-BG", "en-BH", "en-BR", "en-CA", "en-CL",
    "en-CO", "en-CR", "en-CY", "en-CZ", "en-DK", "en-EC", "en-ES", "en-FI",
    "en-GB", "en-GR", "en-HK", "en-HR", "en-HU", "en-ID", "en-IL", "en-IN",
    "en-IS", "en-KW", "en-LB", "en-MT", "en-MX", "en-MY", "en-NO", "en-NZ",
    "en-OM", "en-PA", "en-PE", "en-PL", "en-QA", "en-RO", "en-SA", "en-SE",
    "en-SG", "en-SI", "en-SK", "en-TH", "en-TR", "en-TW", "en-US", "en-ZA",
    "es-AR", "es-BR", "es-CL", "es-CO", "es-CR", "es-EC", "es-ES", "es-GT",
    "es-HN", "es-MX", "es-PA", "es-PE", "es-PY", "es-SV", "fi-FI", "fr-BE",
    "fr-CA", "fr-CH", "fr-FR", "fr-LU", "hu-HU", "id-ID", "it-CH", "it-IT",
    "ja-JP", "ko-KR", "nl-BE", "nl-NL", "no-NO", "pl-PL", "pt-BR", "pt-PT",
    "ro-RO", "ru-RU", "ru-UA", "sv-SE", "th-TH", "tr-TR", "vi-VN", "zh-CN",
    "zh-HK", "zh-TW"
]
valid_regionsShow = [
    valid_regions[i:i + 5] for i in range(0, len(valid_regions), 10)
]
valid_regionsShow = "\n".join(
    [", ".join(sublist) for sublist in valid_regionsShow])
invalid_region = discord.Embed(
    title="❌ Invalid Region",
    description=
    "🌍 Please use a valid region code (e.g., 'en-US', 'en-GB', 'fr-FR')",
    color=0xe74c3c)

npsso_desc = "NPSSO token (leave blank to use default)"
token_desc = "PDC cookie (leave blank to use default)"
id_desc = "ID from psprices product_id command"
region_desc = "For example 'en-US', check 'playstation.com'"


class PSNCog(commands.Cog):

    def __init__(self, secret: str, bot: commands.Bot, default_pdc: str | None = None) -> None:
        self.bot = bot
        self.api = PSN(secret, default_pdc)

    psn_group = discord.SlashCommandGroup("psn")

    @psn_group.command(description="🔍 Checks an avatar for you.")
    async def check_avatar(
        self,
        ctx: discord.ApplicationContext,
        pdc: Option(str, description=token_desc, required=False),  # type: ignore
        npsso: Option(str, description=npsso_desc, required=False),  # type: ignore
        product_id: Option(str, description=id_desc),  # type: ignore
        region: Option(str, description=region_desc)  # type: ignore
    ) -> None:

        embed_checking = discord.Embed(
            title="🔍 Checking Avatar...",
            description="⏳ Please wait while we fetch your avatar!",
            color=0xffa726)
        await ctx.respond(embed=embed_checking, ephemeral=True)

        if region not in valid_regions:
            await ctx.respond(embed=invalid_region, ephemeral=True)
            return

        cookie_arg = pdc or None
        npsso_arg = npsso or None

        request = PSNRequest(region=region,
                             product_id=product_id,
                             pdccws_p=cookie_arg,
                             npsso=npsso_arg)

        try:
            avatar_url = await self.api.check_avatar(request)
        except APIError as e:
            embed_error = discord.Embed(title="❌ Error Occurred",
                                        description=f"🚫 {e}",
                                        color=0xe74c3c)
            embed_error.set_footer(text="💡 Check your inputs and try again!")
            await ctx.respond(embed=embed_error, ephemeral=True)
            return

        embed_success = discord.Embed(
            title="✅ Avatar Found!",
            description="🖼️ Here's your PlayStation avatar preview:",
            color=0x27ae60)
        embed_success.set_image(url=avatar_url)
        embed_success.set_footer(text="🎮 Ready to add to cart!")
        await ctx.respond(embed=embed_success, ephemeral=True)

    @psn_group.command(
        description="🛒 Adds the avatar you input into your cart.")
    async def add_avatar(
        self,
        ctx: discord.ApplicationContext,
        pdc: Option(str, description=token_desc, required=False),  # type: ignore
        npsso: Option(str, description=npsso_desc, required=False),  # type: ignore
        product_id: Option(str, description=id_desc),  # type: ignore
        region: Option(str, description=region_desc)  # type: ignore
    ) -> None:

        embed_adding = discord.Embed(
            title="🛒 Adding to Cart...",
            description="⏳ Please wait while we add your avatar to cart!",
            color=0xf39c12)
        await ctx.respond(embed=embed_adding, ephemeral=True)

        if region not in valid_regions:
            await ctx.respond(embed=invalid_region, ephemeral=True)
            return

        cookie_arg = pdc or None
        npsso_arg = npsso or None

        request = PSNRequest(region=region,
                             product_id=product_id,
                             pdccws_p=cookie_arg,
                             npsso=npsso_arg)

        try:
            await self.api.add_to_cart(request)
        except APIError as e:
            embed_error = discord.Embed(title="❌ Failed to Add",
                                        description=f"🚫 {e}",
                                        color=0xe74c3c)
            embed_error.set_footer(
                text="💡 Make sure your token and product ID are correct!")
            await ctx.respond(embed=embed_error, ephemeral=True)
            return

        embed_success = discord.Embed(
            title="✅ Added Successfully!",
            description=f"🛒 **{product_id}** has been added to your cart!",
            color=0x27ae60)
        embed_success.set_footer(text="🎮 Check your PlayStation Store cart!")
        await ctx.respond(embed=embed_success, ephemeral=True)

    @psn_group.command(
        description="🗑️ Removes the avatar you input from your cart.")
    async def remove_avatar(
        self,
        ctx: discord.ApplicationContext,
        pdc: Option(str, description=token_desc, required=False),  # type: ignore
        npsso: Option(str, description=npsso_desc, required=False),  # type: ignore
        product_id: Option(str, description=id_desc),  # type: ignore
        region: Option(str, description=region_desc)  # type: ignore
    ) -> None:

        embed_removing = discord.Embed(
            title="🗑️ Removing from Cart...",
            description="⏳ Please wait while we remove your avatar from cart!",
            color=0xf39c12)
        await ctx.respond(embed=embed_removing, ephemeral=True)

        if region not in valid_regions:
            await ctx.respond(embed=invalid_region, ephemeral=True)
            return

        cookie_arg = pdc or None
        npsso_arg = npsso or None

        request = PSNRequest(region=region,
                             product_id=product_id,
                             pdccws_p=cookie_arg,
                             npsso=npsso_arg)

        try:
            await self.api.remove_from_cart(request)
        except APIError as e:
            embed_error = discord.Embed(title="❌ Failed to Remove",
                                        description=f"🚫 {e}",
                                        color=0xe74c3c)
            embed_error.set_footer(
                text="💡 Make sure the item is in your cart!")
            await ctx.respond(embed=embed_error, ephemeral=True)
            return

        embed_success = discord.Embed(
            title="✅ Removed Successfully!",
            description=f"🗑️ **{product_id}** has been removed from your cart!",
            color=0x27ae60)
        embed_success.set_footer(
            text="🎮 Item removed from PlayStation Store cart!")
        await ctx.respond(embed=embed_success, ephemeral=True)

    @psn_group.command(
        description="🆔 Gets the account ID from a PSN username.")
    async def account_id(self, ctx: discord.ApplicationContext,
                         username: str) -> None:
        embed_searching = discord.Embed(
            title="🔍 Searching User...",
            description=
            f"⏳ Looking up **{username}** on PlayStation Network...",
            color=0xf39c12)
        await ctx.respond(embed=embed_searching)

        try:
            accid = await self.api.obtain_account_id(username)
        except APIError as e:
            embed_error = discord.Embed(title="❌ User Not Found",
                                        description=f"🚫 {e}",
                                        color=0xe74c3c)
            embed_error.set_footer(text="💡 Check the username and try again!")
            await ctx.edit(embed=embed_error)
            return

        embed_success = discord.Embed(
            title=f"🎮 {username}",
            description=f"🆔 **Account ID:** `{accid}`",
            color=0x27ae60)
        embed_success.set_footer(text="✅ Account ID retrieved successfully!")
        await ctx.edit(embed=embed_success)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(PSNCog(os.getenv("NPSSO"), bot, os.getenv("PDC")))
