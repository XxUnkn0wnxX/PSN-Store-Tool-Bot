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
region_desc = "Region code (e.g. 'en-US' or 'US')"

COUNTRY_OVERRIDES = {
    "UK": "en-GB",
    "GB": "en-GB",
    "US": "en-US",
    "CA": "en-CA",
    "AU": "en-AU",
    "NZ": "en-NZ",
    "MX": "es-MX",
    "BR": "pt-BR",
    "PT": "pt-PT",
    "DE": "de-DE",
    "FR": "fr-FR",
    "ES": "es-ES",
    "IT": "it-IT",
    "JP": "ja-JP",
    "KR": "ko-KR",
    "CN": "zh-CN",
    "HK": "zh-HK",
    "TW": "zh-TW",
    "RU": "ru-RU",
    "ZA": "en-ZA",
    "SG": "en-SG",
}


def mask_value(value: str, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible * 2:
        return value[:visible] + "…" if len(value) > visible else "***"
    return f"{value[:visible]}…{value[-visible:]}"

def normalize_region_input(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise APIError("Region is required")

    # direct match (case-insensitive)
    for region in valid_regions:
        if region.lower() == candidate.lower():
            return region

    upper = candidate.upper()

    # explicit overrides first
    if upper in COUNTRY_OVERRIDES:
        return COUNTRY_OVERRIDES[upper]

    # default to en-<country>
    if len(upper) == 2:
        preferred = f"en-{upper}"
        if preferred in valid_regions:
            return preferred
        # fall back to first region ending with country code
        for region in valid_regions:
            if region.upper().endswith(f"-{upper}"):
                return region

    raise APIError("Invalid region code or alias")


class PSNCog(commands.Cog):

    def __init__(self, secret: str, bot: commands.Bot, default_pdc: str | None = None, allowed_guild_id: str | None = None) -> None:
        self.bot = bot
        self.api = PSN(secret, default_pdc)
        self.allowed_guild_id = allowed_guild_id

    @staticmethod
    def _auth_error_embed(
        base_message: str | None,
        cookie_override: bool,
        npsso_override: bool,
        need_cookie: bool = True,
        need_npsso: bool = True,
    ) -> discord.Embed:
        headline = base_message or "PlayStation rejected the provided credentials."
        description_lines = [
            f"🚫 {headline}",
            "",
            "Please refresh the affected PlayStation credentials:",
        ]

        need_cookie = bool(need_cookie)
        need_npsso = bool(need_npsso)
        if not (need_cookie or need_npsso):
            need_cookie = True
            need_npsso = True

        if need_cookie and need_npsso:
            description_lines.insert(1, "Detected issue with both pdccws_p cookie and NPSSO token.")
        elif need_cookie:
            description_lines.insert(1, "Detected issue with the pdccws_p cookie.")
        elif need_npsso:
            description_lines.insert(1, "Detected issue with the NPSSO token.")

        if need_cookie:
            if cookie_override:
                description_lines.append("• Refresh the `pdccws_p` cookie you supplied with this command.")
            else:
                description_lines.append("• Refresh the `PDC` value stored in your `.env` file.")

        if need_npsso:
            if npsso_override:
                description_lines.append("• Refresh the NPSSO token you supplied with this command.")
            else:
                description_lines.append("• Refresh the `NPSSO` value stored in your `.env` file.")

        description_lines.append("After updating, restart the bot or re-run the command with the new values.")

        embed = discord.Embed(
            title="🔐 Authentication Required",
            description="\n".join(description_lines),
            color=0xe67e22,
        )
        embed.set_footer(text="Need help? Run /tutorial for step-by-step token instructions.")
        return embed

    psn_group = discord.SlashCommandGroup("psn")

    @psn_group.command(description="🔍 Checks an avatar for you.")
    async def check_avatar(
        self,
        ctx: discord.ApplicationContext,
        product_id: Option(str, description=id_desc),  # type: ignore
        region: Option(str, description=region_desc),  # type: ignore
        pdc: Option(str, description=token_desc, required=False),  # type: ignore
        npsso: Option(str, description=npsso_desc, required=False)  # type: ignore
    ) -> None:

        if not await self._ensure_allowed_guild(ctx):
            return

        embed_checking = discord.Embed(
            title="🔍 Checking Avatar...",
            description="⏳ Please wait while we fetch your avatar!",
            color=0xffa726)
        await ctx.respond(embed=embed_checking)

        try:
            region = normalize_region_input(region)
        except APIError as e:
            await ctx.respond(embed=discord.Embed(title="❌ Invalid Region", description=f"🚫 {e}", color=0xe74c3c))
            return

        cookie_arg = pdc or None
        npsso_arg = npsso or None

        request = PSNRequest(region=region,
                             product_id=product_id,
                             pdccws_p=cookie_arg,
                             npsso=npsso_arg)

        if cookie_arg:
            print(f"[psn] Using custom PDC from command for {ctx.author}: {mask_value(cookie_arg)}")
        if npsso_arg:
            masked = npsso_arg[:4] + "…" + npsso_arg[-4:] if len(npsso_arg) > 8 else "***"
            print(f"[psn] Using custom NPSSO from command for {ctx.author}: {masked}")

        try:
            avatar_url = await self.api.check_avatar(request)
        except APIError as e:
            message = e.message if getattr(e, "message", None) else str(e)
            if getattr(e, "code", None) == "auth":
                hints = getattr(e, "hints", {}) or {}
                need_cookie = hints.get("cookie", True)
                need_npsso = hints.get("npsso", True)
                if not (need_cookie or need_npsso):
                    need_cookie = need_npsso = True
                embed_error = self._auth_error_embed(
                    message,
                    cookie_arg is not None,
                    npsso_arg is not None,
                    need_cookie,
                    need_npsso,
                )
            else:
                embed_error = discord.Embed(
                    title="❌ Error Occurred",
                    description=f"🚫 {message}",
                    color=0xe74c3c,
                )
                embed_error.set_footer(text="💡 Check your inputs and try again!")
            await ctx.respond(embed=embed_error)
            return

        embed_success = discord.Embed(
            title="✅ Avatar Found!",
            description="🖼️ Here's your PlayStation avatar preview:",
            color=0x27ae60)
        embed_success.set_image(url=avatar_url)
        embed_success.set_footer(text="🎮 Ready to add to cart!")
        await ctx.respond(embed=embed_success)

    @commands.command(name="check_avatar")
    async def check_avatar_prefix(self, ctx: commands.Context, product_id: str, region: str) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return

        try:
            region = normalize_region_input(region)
        except APIError as e:
            await ctx.send(embed=discord.Embed(title="❌ Invalid Region", description=f"🚫 {e}", color=0xe74c3c))
            return

        request = PSNRequest(region=region, product_id=product_id)

        try:
            avatar_url = await self.api.check_avatar(request)
        except APIError as e:
            message = e.message if getattr(e, "message", None) else str(e)
            if getattr(e, "code", None) == "auth":
                hints = getattr(e, "hints", {}) or {}
                need_cookie = hints.get("cookie", True)
                need_npsso = hints.get("npsso", True)
                if not (need_cookie or need_npsso):
                    need_cookie = need_npsso = True
                embed_error = self._auth_error_embed(
                    message,
                    False,
                    False,
                    need_cookie,
                    need_npsso,
                )
            else:
                embed_error = discord.Embed(
                    title="❌ Error Occurred",
                    description=f"🚫 {message}",
                    color=0xe74c3c,
                )
                embed_error.set_footer(text="💡 Check your inputs and try again!")
            await ctx.send(embed=embed_error)
            return

        embed_success = discord.Embed(
            title="✅ Avatar Found!",
            description="🖼️ Here's your PlayStation avatar preview:",
            color=0x27ae60,
        )
        embed_success.set_image(url=avatar_url)
        embed_success.set_footer(text="🎮 Ready to add to cart!")
        await ctx.send(embed=embed_success)

    @psn_group.command(
        description="🛒 Adds the avatar you input into your cart.")
    async def add_avatar(
        self,
        ctx: discord.ApplicationContext,
        product_id: Option(str, description=id_desc),  # type: ignore
        region: Option(str, description=region_desc),  # type: ignore
        pdc: Option(str, description=token_desc, required=False),  # type: ignore
        npsso: Option(str, description=npsso_desc, required=False)  # type: ignore
    ) -> None:

        if not await self._ensure_allowed_guild(ctx):
            return

        embed_adding = discord.Embed(
            title="🛒 Adding to Cart...",
            description="⏳ Please wait while we add your avatar to cart!",
            color=0xf39c12)
        await ctx.respond(embed=embed_adding)

        try:
            region = normalize_region_input(region)
        except APIError as e:
            await ctx.respond(embed=discord.Embed(title="❌ Invalid Region", description=f"🚫 {e}", color=0xe74c3c))
            return

        cookie_arg = pdc or None
        npsso_arg = npsso or None

        request = PSNRequest(region=region,
                             product_id=product_id,
                             pdccws_p=cookie_arg,
                             npsso=npsso_arg)

        if cookie_arg:
            print(f"[psn] Using custom PDC from command for {ctx.author}: {mask_value(cookie_arg)}")
        if npsso_arg:
            masked = npsso_arg[:4] + "…" + npsso_arg[-4:] if len(npsso_arg) > 8 else "***"
            print(f"[psn] Using custom NPSSO from command for {ctx.author}: {masked}")

        try:
            await self.api.add_to_cart(request)
        except APIError as e:
            message = e.message if getattr(e, "message", None) else str(e)
            if getattr(e, "code", None) == "auth":
                hints = getattr(e, "hints", {}) or {}
                need_cookie = hints.get("cookie", True)
                need_npsso = hints.get("npsso", True)
                if not (need_cookie or need_npsso):
                    need_cookie = need_npsso = True
                embed_error = self._auth_error_embed(
                    message,
                    cookie_arg is not None,
                    npsso_arg is not None,
                    need_cookie,
                    need_npsso,
                )
            else:
                embed_error = discord.Embed(
                    title="❌ Failed to Add",
                    description=f"🚫 {message}",
                    color=0xe74c3c,
                )
                embed_error.set_footer(
                    text="💡 Make sure your token and product ID are correct!"
                )
            await ctx.respond(embed=embed_error)
            return

        embed_success = discord.Embed(
            title="✅ Added Successfully!",
            description=f"🛒 **{product_id}** has been added to your cart!",
            color=0x27ae60)
        embed_success.set_footer(text="🎮 Check your PlayStation Store cart!")
        await ctx.respond(embed=embed_success)

    @commands.command(name="add_avatar")
    async def add_avatar_prefix(self, ctx: commands.Context, product_id: str, region: str) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return

        try:
            region = normalize_region_input(region)
        except APIError as e:
            await ctx.send(embed=discord.Embed(title="❌ Invalid Region", description=f"🚫 {e}", color=0xe74c3c))
            return

        request = PSNRequest(region=region, product_id=product_id)

        try:
            await self.api.add_to_cart(request)
        except APIError as e:
            message = e.message if getattr(e, "message", None) else str(e)
            if getattr(e, "code", None) == "auth":
                hints = getattr(e, "hints", {}) or {}
                need_cookie = hints.get("cookie", True)
                need_npsso = hints.get("npsso", True)
                if not (need_cookie or need_npsso):
                    need_cookie = need_npsso = True
                embed_error = self._auth_error_embed(
                    message,
                    False,
                    False,
                    need_cookie,
                    need_npsso,
                )
            else:
                embed_error = discord.Embed(
                    title="❌ Failed to Add",
                    description=f"🚫 {message}",
                    color=0xe74c3c,
                )
                embed_error.set_footer(text="💡 Make sure your token and product ID are correct!")
            await ctx.send(embed=embed_error)
            return

        embed_success = discord.Embed(
            title="✅ Added Successfully!",
            description=f"🛒 **{product_id}** has been added to your cart!",
            color=0x27ae60,
        )
        embed_success.set_footer(text="🎮 Check your PlayStation Store cart!")
        await ctx.send(embed=embed_success)

    @psn_group.command(
        description="🗑️ Removes the avatar you input from your cart.")
    async def remove_avatar(
        self,
        ctx: discord.ApplicationContext,
        product_id: Option(str, description=id_desc),  # type: ignore
        region: Option(str, description=region_desc),  # type: ignore
        pdc: Option(str, description=token_desc, required=False),  # type: ignore
        npsso: Option(str, description=npsso_desc, required=False)  # type: ignore
    ) -> None:

        if not await self._ensure_allowed_guild(ctx):
            return

        embed_removing = discord.Embed(
            title="🗑️ Removing from Cart...",
            description="⏳ Please wait while we remove your avatar from cart!",
            color=0xf39c12)
        await ctx.respond(embed=embed_removing)

        try:
            region = normalize_region_input(region)
        except APIError as e:
            await ctx.respond(embed=discord.Embed(title="❌ Invalid Region", description=f"🚫 {e}", color=0xe74c3c))
            return

        cookie_arg = pdc or None
        npsso_arg = npsso or None

        request = PSNRequest(region=region,
                             product_id=product_id,
                             pdccws_p=cookie_arg,
                             npsso=npsso_arg)

        if cookie_arg:
            print(f"[psn] Using custom PDC from command for {ctx.author}: {mask_value(cookie_arg)}")
        if npsso_arg:
            masked = npsso_arg[:4] + "…" + npsso_arg[-4:] if len(npsso_arg) > 8 else "***"
            print(f"[psn] Using custom NPSSO from command for {ctx.author}: {masked}")

        try:
            await self.api.remove_from_cart(request)
        except APIError as e:
            message = e.message if getattr(e, "message", None) else str(e)
            if getattr(e, "code", None) == "auth":
                hints = getattr(e, "hints", {}) or {}
                need_cookie = hints.get("cookie", True)
                need_npsso = hints.get("npsso", True)
                if not (need_cookie or need_npsso):
                    need_cookie = need_npsso = True
                embed_error = self._auth_error_embed(
                    message,
                    cookie_arg is not None,
                    npsso_arg is not None,
                    need_cookie,
                    need_npsso,
                )
            else:
                embed_error = discord.Embed(
                    title="❌ Failed to Remove",
                    description=f"🚫 {message}",
                    color=0xe74c3c,
                )
                embed_error.set_footer(
                    text="💡 Make sure the item is in your cart!"
                )
            await ctx.respond(embed=embed_error)
            return

        embed_success = discord.Embed(
            title="✅ Removed Successfully!",
            description=f"🗑️ **{product_id}** has been removed from your cart!",
            color=0x27ae60)
        embed_success.set_footer(
            text="🎮 Item removed from PlayStation Store cart!")
        await ctx.respond(embed=embed_success)

    @commands.command(name="remove_avatar")
    async def remove_avatar_prefix(self, ctx: commands.Context, product_id: str, region: str) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return

        try:
            region = normalize_region_input(region)
        except APIError as e:
            await ctx.send(embed=discord.Embed(title="❌ Invalid Region", description=f"🚫 {e}", color=0xe74c3c))
            return

        request = PSNRequest(region=region, product_id=product_id)

        try:
            await self.api.remove_from_cart(request)
        except APIError as e:
            message = e.message if getattr(e, "message", None) else str(e)
            if getattr(e, "code", None) == "auth":
                hints = getattr(e, "hints", {}) or {}
                need_cookie = hints.get("cookie", True)
                need_npsso = hints.get("npsso", True)
                if not (need_cookie or need_npsso):
                    need_cookie = need_npsso = True
                embed_error = self._auth_error_embed(
                    message,
                    False,
                    False,
                    need_cookie,
                    need_npsso,
                )
            else:
                embed_error = discord.Embed(
                    title="❌ Failed to Remove",
                    description=f"🚫 {message}",
                    color=0xe74c3c,
                )
                embed_error.set_footer(text="💡 Make sure the item is in your cart!")
            await ctx.send(embed=embed_error)
            return

        embed_success = discord.Embed(
            title="✅ Removed Successfully!",
            description=f"🗑️ **{product_id}** has been removed from your cart!",
            color=0x27ae60,
        )
        embed_success.set_footer(text="🎮 Item removed from PlayStation Store cart!")
        await ctx.send(embed=embed_success)

    @psn_group.command(
        description="🆔 Gets the account ID from a PSN username.")
    async def account_id(self, ctx: discord.ApplicationContext,
                         username: str) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return

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

    @commands.command(name="account_id")
    async def account_id_prefix(self, ctx: commands.Context, username: str) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return

        embed_searching = discord.Embed(
            title="🔍 Searching User...",
            description=f"⏳ Looking up **{username}** on PlayStation Network...",
            color=0xf39c12,
        )
        message = await ctx.send(embed=embed_searching)

        try:
            accid = await self.api.obtain_account_id(username)
        except APIError as e:
            embed_error = discord.Embed(title="❌ User Not Found", description=f"🚫 {e}", color=0xe74c3c)
            embed_error.set_footer(text="💡 Check the username and try again!")
            await message.edit(embed=embed_error)
            return

        embed_success = discord.Embed(
            title=f"🎮 {username}",
            description=f"🆔 **Account ID:** `{accid}`",
            color=0x27ae60,
        )
        embed_success.set_footer(text="✅ Account ID retrieved successfully!")
        await message.edit(embed=embed_success)

    async def _ensure_allowed_guild(self, ctx) -> bool:
        if not self.allowed_guild_id:
            return True
        if ctx.guild is None or str(ctx.guild.id) != str(self.allowed_guild_id):
            embed = discord.Embed(
                title="🔒 Command Restricted",
                description="This bot is configured for a specific server and cannot be used here.",
                color=0xe74c3c,
            )
            if hasattr(ctx, "respond"):
                await ctx.respond(embed=embed)
            else:
                await ctx.send(embed=embed)
            return False
        return True


def setup(bot: commands.Bot) -> None:
    bot.add_cog(PSNCog(os.getenv("NPSSO"), bot, os.getenv("PDC"), os.getenv("GUILD_ID")))
