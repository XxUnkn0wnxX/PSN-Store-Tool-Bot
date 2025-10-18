import discord
import os
from discord import Option
from discord.ext import commands
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
            description_lines.append(
                "• Refresh the `pdccws_p` cookie you supplied with this command."
                if cookie_override
                else "• Refresh the `PDC` value stored in your `.env` file."
            )

        if need_npsso:
            description_lines.append(
                "• Refresh the NPSSO token you supplied with this command."
                if npsso_override
                else "• Refresh the `NPSSO` value stored in your `.env` file."
            )

        description_lines.append("After updating, restart the bot or re-run the command with the new values.")

        embed = discord.Embed(
            title="🔐 Authentication Required",
            description="\n".join(description_lines),
            color=0xe67e22,
        )
        embed.set_footer(text="Need help? Run /tutorial for step-by-step token instructions.")
        return embed

    def _is_app_context(self, ctx) -> bool:
        return isinstance(ctx, discord.ApplicationContext)

    @staticmethod
    def _prefix_has_extra_args(ctx: commands.Context) -> bool:
        view = getattr(ctx, "view", None)
        if view is None or not hasattr(view, "buffer"):
            return False
        remaining = view.buffer[view.index :].strip()
        return bool(remaining)

    async def _send_embed(self, ctx, embed: discord.Embed, *, followup: bool = False) -> None:
        if self._is_app_context(ctx):
            app_ctx = ctx  # type: ignore[assignment]
            if followup or app_ctx.response.is_done():
                await app_ctx.followup.send(embed=embed)
            else:
                await app_ctx.respond(embed=embed)
        else:
            await ctx.send(embed=embed)

    async def _handle_check(
        self,
        ctx,
        product_id: str,
        region: str,
        cookie_arg: str | None = None,
        npsso_arg: str | None = None,
        *,
        cookie_override: bool = False,
        npsso_override: bool = False,
    ) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return

        try:
            region = normalize_region_input(region)
        except APIError as e:
            await self._send_embed(
                ctx,
                discord.Embed(
                    title="❌ Invalid Region",
                    description=f"🚫 {e}",
                    color=0xe74c3c,
                ),
            )
            return

        request = PSNRequest(
            region=region,
            product_id=product_id,
            pdccws_p=cookie_arg,
            npsso=npsso_arg,
        )

        if cookie_arg:
            print(f"[psn] Using custom PDC from command for {ctx.author}: {mask_value(cookie_arg)}")
        if npsso_arg:
            masked = npsso_arg[:4] + "…" + npsso_arg[-4:] if len(npsso_arg) > 8 else "***"
            print(f"[psn] Using custom NPSSO from command for {ctx.author}: {masked}")

        await self._send_embed(
            ctx,
            discord.Embed(
                title="🔍 Checking Avatar...",
                description="⏳ Please wait while we fetch your avatar!",
                color=0xffa726,
            ),
        )

        try:
            avatar_url = await self.api.check_avatar(request)
        except APIError as e:
            message = e.message if getattr(e, "message", None) else str(e)
            followup = self._is_app_context(ctx)
            if getattr(e, "code", None) == "auth":
                hints = getattr(e, "hints", {}) or {}
                need_cookie = hints.get("cookie", True)
                need_npsso = hints.get("npsso", True)
                embed_error = self._auth_error_embed(
                    message,
                    cookie_override,
                    npsso_override,
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
            await self._send_embed(ctx, embed_error, followup=followup)
            return

        embed_success = discord.Embed(
            title="✅ Avatar Found!",
            description="🖼️ Here's your PlayStation avatar preview:",
            color=0x27ae60,
        )
        embed_success.set_image(url=avatar_url)
        embed_success.set_footer(text="🎮 Ready to add to cart!")
        await self._send_embed(ctx, embed_success, followup=self._is_app_context(ctx))

    async def _handle_add_or_remove(
        self,
        ctx,
        *,
        product_id: str,
        region: str,
        cookie_arg: str | None,
        npsso_arg: str | None,
        cookie_override: bool,
        npsso_override: bool,
        operation: str,
    ) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return

        try:
            region = normalize_region_input(region)
        except APIError as e:
            await self._send_embed(
                ctx,
                discord.Embed(
                    title="❌ Invalid Region",
                    description=f"🚫 {e}",
                    color=0xe74c3c,
                ),
            )
            return

        request = PSNRequest(
            region=region,
            product_id=product_id,
            pdccws_p=cookie_arg,
            npsso=npsso_arg,
        )

        if cookie_arg:
            print(f"[psn] Using custom PDC from command for {ctx.author}: {mask_value(cookie_arg)}")
        if npsso_arg:
            masked = npsso_arg[:4] + "…" + npsso_arg[-4:] if len(npsso_arg) > 8 else "***"
            print(f"[psn] Using custom NPSSO from command for {ctx.author}: {masked}")

        action_text = "Adding to Cart" if operation == "add" else "Removing from Cart"
        progress_description = (
            "⏳ Please wait while we add your avatar to cart!"
            if operation == "add"
            else "⏳ Please wait while we remove your avatar from cart!"
        )

        await self._send_embed(
            ctx,
            discord.Embed(
                title=f"{'🛒' if operation == 'add' else '🗑️'} {action_text}...",
                description=progress_description,
                color=0xf39c12,
            ),
        )

        try:
            if operation == "add":
                await self.api.add_to_cart(request)
            else:
                await self.api.remove_from_cart(request)
        except APIError as e:
            message = e.message if getattr(e, "message", None) else str(e)
            followup = self._is_app_context(ctx)
            if getattr(e, "code", None) == "auth":
                hints = getattr(e, "hints", {}) or {}
                need_cookie = hints.get("cookie", True)
                need_npsso = hints.get("npsso", True)
                embed_error = self._auth_error_embed(
                    message,
                    cookie_override,
                    npsso_override,
                    need_cookie,
                    need_npsso,
                )
            else:
                title = "❌ Failed to Add" if operation == "add" else "❌ Failed to Remove"
                footer = (
                    "💡 Make sure your token and product ID are correct!"
                    if operation == "add"
                    else "💡 Make sure the item is in your cart!"
                )
                embed_error = discord.Embed(
                    title=title,
                    description=f"🚫 {message}",
                    color=0xe74c3c,
                )
                embed_error.set_footer(text=footer)
            await self._send_embed(ctx, embed_error, followup=followup)
            return

        if operation == "add":
            success_title = "✅ Added Successfully!"
            success_description = f"🛒 **{product_id}** has been added to your cart!"
            footer = "🎮 Check your PlayStation Store cart!"
        else:
            success_title = "✅ Removed Successfully!"
            success_description = f"🗑️ **{product_id}** has been removed from your cart!"
            footer = "🎮 Item removed from PlayStation Store cart!"

        embed_success = discord.Embed(
            title=success_title,
            description=success_description,
            color=0x27ae60,
        )
        embed_success.set_footer(text=footer)
        await self._send_embed(ctx, embed_success, followup=self._is_app_context(ctx))

    async def _handle_account(self, ctx, username: str) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return

        await self._send_embed(
            ctx,
            discord.Embed(
                title="🔍 Searching User...",
                description=f"⏳ Looking up **{username}** on PlayStation Network...",
                color=0xf39c12,
            ),
        )

        try:
            accid = await self.api.obtain_account_id(username)
        except APIError as e:
            embed_error = discord.Embed(
                title="❌ User Not Found",
                description=f"🚫 {e}",
                color=0xe74c3c,
            )
            embed_error.set_footer(text="💡 Check the username and try again!")
            await self._send_embed(ctx, embed_error, followup=self._is_app_context(ctx))
            return

        embed_success = discord.Embed(
            title=f"🎮 {username}",
            description=f"🆔 **Account ID:** `{accid}`",
            color=0x27ae60,
        )
        embed_success.set_footer(text="✅ Account ID retrieved successfully!")
        await self._send_embed(ctx, embed_success, followup=self._is_app_context(ctx))

    psn_group = discord.SlashCommandGroup(
        "psn", description="PlayStation Store avatar utilities."
    )

    @psn_group.command(name="check", description="🔍 Checks an avatar for you.")
    async def psn_slash_check(
        self,
        ctx: discord.ApplicationContext,
        product_id: Option(str, description=id_desc),  # type: ignore
        region: Option(str, description=region_desc),  # type: ignore
        pdc: Option(str, description=token_desc, default=None),  # type: ignore
        npsso: Option(str, description=npsso_desc, default=None),  # type: ignore
    ) -> None:
        await self._handle_check(
            ctx,
            product_id=product_id,
            region=region,
            cookie_arg=pdc,
            npsso_arg=npsso,
            cookie_override=pdc is not None,
            npsso_override=npsso is not None,
        )

    @psn_group.command(name="add", description="🛒 Adds the avatar you input into your cart.")
    async def psn_slash_add(
        self,
        ctx: discord.ApplicationContext,
        product_id: Option(str, description=id_desc),  # type: ignore
        region: Option(str, description=region_desc),  # type: ignore
        pdc: Option(str, description=token_desc, default=None),  # type: ignore
        npsso: Option(str, description=npsso_desc, default=None),  # type: ignore
    ) -> None:
        await self._handle_add_or_remove(
            ctx,
            product_id=product_id,
            region=region,
            cookie_arg=pdc,
            npsso_arg=npsso,
            cookie_override=pdc is not None,
            npsso_override=npsso is not None,
            operation="add",
        )

    @psn_group.command(name="remove", description="🗑️ Removes the avatar you input from your cart.")
    async def psn_slash_remove(
        self,
        ctx: discord.ApplicationContext,
        product_id: Option(str, description=id_desc),  # type: ignore
        region: Option(str, description=region_desc),  # type: ignore
        pdc: Option(str, description=token_desc, default=None),  # type: ignore
        npsso: Option(str, description=npsso_desc, default=None),  # type: ignore
    ) -> None:
        await self._handle_add_or_remove(
            ctx,
            product_id=product_id,
            region=region,
            cookie_arg=pdc,
            npsso_arg=npsso,
            cookie_override=pdc is not None,
            npsso_override=npsso is not None,
            operation="remove",
        )

    @psn_group.command(name="account", description="🆔 Gets the account ID from a PSN username.")
    async def psn_slash_account(
        self,
        ctx: discord.ApplicationContext,
        username: Option(str, description="PSN username to resolve."),  # type: ignore
    ) -> None:
        await self._handle_account(ctx, username)

    @commands.group(name="psn", invoke_without_command=True)
    async def psn_prefix(self, ctx: commands.Context) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return

        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🎮 PSN Commands",
                description=(
                    "Use `/psn check`, `/psn add`, `/psn remove`, or `/psn account`.\n"
                    "Prefix usage: `$psn <subcommand>` or legacy aliases like `$check_avatar`."
                ),
                color=0x3498db,
            )
            await self._send_embed(ctx, embed)

    @psn_prefix.command(name="check")
    async def psn_prefix_check(self, ctx: commands.Context, product_id: str, region: str) -> None:
        if self._prefix_has_extra_args(ctx):
            await self._send_embed(
                ctx,
                discord.Embed(
                    title="⚠️ Overrides Not Available",
                    description="Prefix commands only accept `product_id` and `region`. Use `/psn check` if you need to supply NPSSO or PDC overrides.",
                    color=0xf1c40f,
                ),
            )
            return
        await self._handle_check(
            ctx,
            product_id=product_id,
            region=region,
            cookie_arg=None,
            npsso_arg=None,
            cookie_override=False,
            npsso_override=False,
        )

    @psn_prefix.command(name="add")
    async def psn_prefix_add(self, ctx: commands.Context, product_id: str, region: str) -> None:
        if self._prefix_has_extra_args(ctx):
            await self._send_embed(
                ctx,
                discord.Embed(
                    title="⚠️ Overrides Not Available",
                    description="Prefix commands only accept `product_id` and `region`. Use `/psn add` if you need to supply NPSSO or PDC overrides.",
                    color=0xf1c40f,
                ),
            )
            return
        await self._handle_add_or_remove(
            ctx,
            product_id=product_id,
            region=region,
            cookie_arg=None,
            npsso_arg=None,
            cookie_override=False,
            npsso_override=False,
            operation="add",
        )

    @psn_prefix.command(name="remove")
    async def psn_prefix_remove(self, ctx: commands.Context, product_id: str, region: str) -> None:
        if self._prefix_has_extra_args(ctx):
            await self._send_embed(
                ctx,
                discord.Embed(
                    title="⚠️ Overrides Not Available",
                    description="Prefix commands only accept `product_id` and `region`. Use `/psn remove` if you need to supply NPSSO or PDC overrides.",
                    color=0xf1c40f,
                ),
            )
            return
        await self._handle_add_or_remove(
            ctx,
            product_id=product_id,
            region=region,
            cookie_arg=None,
            npsso_arg=None,
            cookie_override=False,
            npsso_override=False,
            operation="remove",
        )

    @psn_prefix.command(name="account")
    async def psn_prefix_account(self, ctx: commands.Context, username: str) -> None:
        if self._prefix_has_extra_args(ctx):
            await self._send_embed(
                ctx,
                discord.Embed(
                    title="⚠️ Extra Arguments Ignored",
                    description="Prefix account lookup only needs the username. Remove additional arguments or use `/psn account`.",
                    color=0xf1c40f,
                ),
            )
            return
        await self._handle_account(ctx, username)

    @commands.command(name="check_avatar")
    async def check_avatar_prefix(self, ctx: commands.Context, product_id: str, region: str) -> None:
        if self._prefix_has_extra_args(ctx):
            await self._send_embed(
                ctx,
                discord.Embed(
                    title="⚠️ Overrides Not Available",
                    description="Prefix commands only accept `product_id` and `region`. Use `/psn check` if you need to supply NPSSO or PDC overrides.",
                    color=0xf1c40f,
                ),
            )
            return
        await self._handle_check(
            ctx,
            product_id=product_id,
            region=region,
            cookie_arg=None,
            npsso_arg=None,
            cookie_override=False,
            npsso_override=False,
        )

    @commands.command(name="add_avatar")
    async def add_avatar_prefix(self, ctx: commands.Context, product_id: str, region: str) -> None:
        if self._prefix_has_extra_args(ctx):
            await self._send_embed(
                ctx,
                discord.Embed(
                    title="⚠️ Overrides Not Available",
                    description="Prefix commands only accept `product_id` and `region`. Use `/psn add` if you need to supply NPSSO or PDC overrides.",
                    color=0xf1c40f,
                ),
            )
            return
        await self._handle_add_or_remove(
            ctx,
            product_id=product_id,
            region=region,
            cookie_arg=None,
            npsso_arg=None,
            cookie_override=False,
            npsso_override=False,
            operation="add",
        )

    @commands.command(name="remove_avatar")
    async def remove_avatar_prefix(self, ctx: commands.Context, product_id: str, region: str) -> None:
        if self._prefix_has_extra_args(ctx):
            await self._send_embed(
                ctx,
                discord.Embed(
                    title="⚠️ Overrides Not Available",
                    description="Prefix commands only accept `product_id` and `region`. Use `/psn remove` if you need to supply NPSSO or PDC overrides.",
                    color=0xf1c40f,
                ),
            )
            return
        await self._handle_add_or_remove(
            ctx,
            product_id=product_id,
            region=region,
            cookie_arg=None,
            npsso_arg=None,
            cookie_override=False,
            npsso_override=False,
            operation="remove",
        )

    @commands.command(name="account_id")
    async def account_id_prefix(self, ctx: commands.Context, username: str) -> None:
        if self._prefix_has_extra_args(ctx):
            await self._send_embed(
                ctx,
                discord.Embed(
                    title="⚠️ Extra Arguments Ignored",
                    description="Prefix account lookup only needs the username. Remove additional arguments or use `/psn account`.",
                    color=0xf1c40f,
                ),
            )
            return
        await self._handle_account(ctx, username)

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
    for command in list(bot.application_commands):
        if command.name == "psn":
            bot.remove_application_command(command)
    cog = PSNCog(os.getenv("NPSSO"), bot, os.getenv("PDC"), os.getenv("GUILD_ID"))
    bot.add_cog(cog)
