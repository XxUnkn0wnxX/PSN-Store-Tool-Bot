import os
from typing import Iterable

import discord
from discord import Option
from discord.ext import commands
from discord.utils import MISSING
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

token_desc = "PDC cookie (required unless the bot started with --env)"
id_desc = "ID from psprices product_id command"
region_desc = "Region code (e.g. 'en-US' or 'US')"

PDC_REQUIRED = os.getenv("BOT_USE_ENV") != "1"
PDC_OPTION_KWARGS: dict[str, object]
if PDC_REQUIRED:
    PDC_OPTION_KWARGS = {"required": True}
else:
    PDC_OPTION_KWARGS = {"required": False, "default": None}

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


def _parse_allowed_guilds(raw: str | None) -> set[int]:
    if not raw:
        return set()
    guild_ids: set[int] = set()
    for chunk in raw.split(","):
        piece = chunk.strip()
        if not piece:
            continue
        try:
            guild_ids.add(int(piece))
        except ValueError:
            continue
    return guild_ids


def mask_value(value: str, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible * 2:
        return value[:visible] + "…" if len(value) > visible else "***"
    return f"{value[:visible]}…{value[-visible:]}"


def collect_product_ids(*ids: str | None) -> list[str]:
    collected: list[str] = []
    for value in ids:
        if value:
            stripped = value.strip()
            if stripped:
                collected.append(stripped)
    return collected

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

    def __init__(
        self,
        secret: str,
        bot: commands.Bot,
        default_pdc: str | None = None,
        allowed_guild_ids: Iterable[int] | None = None,
        env_path: str | None = None,
    ) -> None:
        self.bot = bot
        self.api = PSN(secret, default_pdc, env_path)
        self.allowed_guild_ids: set[int] = set(allowed_guild_ids or [])

    @staticmethod
    def _auth_error_embed(
        base_message: str | None,
        cookie_override: bool,
        need_cookie: bool = True,
        need_npsso: bool = True,
    ) -> discord.Embed:
        headline = base_message or "PlayStation rejected the provided credentials."
        needs_guidance = need_cookie or need_npsso or cookie_override

        if needs_guidance:
            description_lines = [f"🚫 {headline}", "", "Please refresh the affected PlayStation credentials:"]
        else:
            description_lines = [f"🚫 {headline}"]

        need_cookie = bool(need_cookie)
        need_npsso = bool(need_npsso)

        if not needs_guidance:
            embed = discord.Embed(
                title="🔐 Authentication Required",
                description="\n".join(description_lines),
                color=0xe67e22,
            )
            embed.set_footer(text="Need help? Run /tutorial for step-by-step token instructions.")
            return embed

        if need_cookie and need_npsso:
            description_lines.insert(
                len(description_lines) - 1,
                "Detected issue with both the pdccws_p cookie and the bot-generated NPSSO token.",
            )
        elif need_cookie:
            description_lines.insert(
                len(description_lines) - 1,
                "Detected issue with the pdccws_p cookie.",
            )
        elif need_npsso:
            description_lines.insert(
                len(description_lines) - 1,
                "Detected issue with the bot-generated NPSSO token.",
            )

        if need_cookie:
            description_lines.append(
                "• Refresh the `pdccws_p` cookie you supplied with this command."
                if cookie_override
                else "• Refresh the `PDC` value stored in your `.env` file."
            )

        if need_npsso:
            description_lines.append("• The bot will generate a new NPSSO token automatically; retry the command or restart the bot if the issue continues.")

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

    async def _prepare_prefix_batch(
        self,
        ctx: commands.Context,
        payload: str,
        operation: str,
        allow_cookie: bool = False,
    ) -> tuple[str, list[str], str | None] | None:
        payload = (payload or "").strip()
        if not payload:
            usage = f"{ctx.prefix or ''}{ctx.invoked_with} <region> <product_id> [more_ids...]"
            embed = discord.Embed(
                title="ℹ️ Missing Arguments",
                description=f"Provide a region followed by one or more product IDs.\nExample: `{usage}`",
                color=0xf1c40f,
            )
            await ctx.send(embed=embed)
            return None

        tokens: list[str] = []
        for line in payload.replace("\r", "\n").splitlines():
            tokens.extend(part.strip() for part in line.split())

        tokens = [t for t in tokens if t]
        if len(tokens) < 2:
            usage = f"{ctx.prefix or ''}{ctx.invoked_with} <region> <product_id> [more_ids...]"
            embed = discord.Embed(
                title="ℹ️ Not Enough Arguments",
                description=f"You need to supply at least one product ID after the region.\nExample: `{usage}`",
                color=0xf1c40f,
            )
            await ctx.send(embed=embed)
            return None

        cookie_value: str | None = None
        if allow_cookie and tokens:
            lowered_last = tokens[-1].lower()
            if lowered_last.startswith("--pdc="):
                cookie_value = tokens[-1].split("=", 1)[1]
                tokens = tokens[:-1]
            elif lowered_last == "--pdc":
                embed = discord.Embed(
                    title="⚠️ Missing Cookie Value",
                    description="Provide the cookie as `--pdc YOUR_COOKIE` or `--pdc=YOUR_COOKIE` at the end of the command.",
                    color=0xf39c12,
                )
                await ctx.send(embed=embed, silent=True)
                return None
            elif len(tokens) >= 2 and tokens[-2].lower() == "--pdc":
                cookie_value = tokens[-1]
                tokens = tokens[:-2]

        if cookie_value is not None:
            cookie_value = cookie_value.strip()
            if not cookie_value:
                embed = discord.Embed(
                    title="⚠️ Missing Cookie Value",
                    description="Provide the cookie as `--pdc YOUR_COOKIE` or `--pdc=YOUR_COOKIE` at the end of the command.",
                    color=0xf39c12,
                )
                await ctx.send(embed=embed, silent=True)
                return None

        try:
            normalize_region_input(tokens[0])
        except APIError:
            if len(tokens) >= 2:
                try:
                    normalize_region_input(tokens[1])
                except APIError:
                    pass
                else:
                    tokens = [tokens[1], tokens[0], *tokens[2:]]

        region = tokens[0]
        product_ids = tokens[1:]

        if not allow_cookie:
            cookie_like = [
                pid for pid in product_ids if any(symbol in pid for symbol in ("%", "=", ";"))
            ]
            if cookie_like:
                slash_equiv = {
                    "add": "add",
                    "remove": "remove",
                    "check": "check",
                }.get(operation, "check")
                embed = discord.Embed(
                    title="⚠️ Cookie Detected",
                    description=(
                        "Prefix commands cannot accept cookie overrides. "
                        f"Use the slash command variant (e.g. `/psn {slash_equiv}`) to supply the pdccws_p cookie."
                    ),
                    color=0xe67e22,
                )
                await ctx.send(embed=embed)
                return None

        return region, product_ids, cookie_value

    @staticmethod
    def _mention(ctx) -> str:
        author = getattr(ctx, "author", None) or getattr(ctx, "user", None)
        return author.mention if author else ""

    @staticmethod
    def _actor_label(ctx) -> str:
        user = getattr(ctx, "author", None) or getattr(ctx, "user", None)
        if not user:
            return "unknown user"
        display = getattr(user, "display_name", None) or getattr(user, "name", None) or str(user)
        username = getattr(user, "name", None) or display
        if display == username:
            return f"{display} ({user.id})"
        return f"{display} ({username} / {user.id})"

    async def _send_embed(
        self,
        ctx,
        embed: discord.Embed,
        *,
        followup: bool = False,
        content: str | None = None,
        silent: bool = True,
    ) -> None:
        if self._is_app_context(ctx):
            app_ctx = ctx  # type: ignore[assignment]
            if followup or app_ctx.response.is_done():
                kwargs = {"embed": embed}
                if content:
                    kwargs["content"] = content
                await app_ctx.followup.send(**kwargs)
            else:
                kwargs = {"embed": embed}
                if content:
                    kwargs["content"] = content
                await app_ctx.respond(**kwargs)
        else:
            kwargs = {"embed": embed}
            if content:
                kwargs["content"] = content
            if silent:
                kwargs["silent"] = True
            await ctx.send(**kwargs)

    async def _delete_prefix_message(self, ctx) -> None:
        if self._is_app_context(ctx):
            return
        message = getattr(ctx, "message", None)
        if message is None:
            return
        try:
            await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def _handle_check(
        self,
        ctx,
        *,
        product_ids: list[str],
        region: str,
    ) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return

        ids = [pid.strip() for pid in product_ids if pid.strip()]
        mention = self._mention(ctx)
        actor = self._actor_label(ctx)

        if not ids:
            embed = discord.Embed(
                title="ℹ️ Missing Product IDs",
                description="Provide at least one product ID to check.",
                color=0xf1c40f,
            )
            await self._send_embed(ctx, embed, content=mention)
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
                content=mention,
            )
            return

        is_app_context = self._is_app_context(ctx)
        is_batch = len(ids) > 1
        progress_title = "🔍 Checking Avatars..." if is_batch else "🔍 Checking Avatar..."
        progress_desc = (
            f"⏳ Fetching {len(ids)} avatar(s)…" if is_batch else "⏳ Please wait while we fetch your avatar!"
        )

        if is_app_context:
            await ctx.respond(
                content=mention,
                embed=discord.Embed(
                    title=progress_title,
                    description=progress_desc,
                    color=0xffa726,
                ),
            )
            progress_message = None
        else:
            progress_message = await ctx.send(
                content=mention,
                embed=discord.Embed(
                    title=progress_title,
                    description=progress_desc,
                    color=0xffa726,
                ),
                silent=True,
            )

        successes: list[tuple[str, str]] = []
        failures: list[tuple[str, str]] = []

        for pid in ids:
            request = PSNRequest(
                region=region,
                product_id=pid,
                requested_by=actor,
            )

            try:
                avatar_url = await self.api.check_avatar(request)
                successes.append((pid, avatar_url))
            except APIError as e:
                message = e.message if getattr(e, "message", None) else str(e)
                failures.append((pid, message))

        followup = self._is_app_context(ctx)

        def make_success_embed(pid: str, avatar_url: str, index: int, total: int) -> discord.Embed:
            embed = discord.Embed(
                title="✅ Avatar Found!" if total == 1 else f"✅ Avatar Found ({index}/{total})",
                description=f"🖼️ Preview for **{pid}**:",
                color=0x27ae60,
            )
            embed.set_image(url=avatar_url)
            embed.set_footer(text="🎮 Ready to add to cart!")
            return embed

        async def update_progress(embed: discord.Embed) -> None:
            if is_app_context:
                await ctx.edit(embed=embed)
            elif progress_message is not None:
                await progress_message.edit(embed=embed)
            else:
                await self._send_embed(ctx, embed, content=mention)

        if successes:
            first_pid, first_url = successes[0]
            await update_progress(make_success_embed(first_pid, first_url, 1, len(successes)))
            for index, (pid, avatar_url) in enumerate(successes[1:], start=2):
                await self._send_embed(ctx, make_success_embed(pid, avatar_url, index, len(successes)), followup=followup)
        else:
            failure_lines = [f"• **{pid}** — {msg}" for pid, msg in failures] or ["No avatars matched the provided IDs."]
            embed_error = discord.Embed(
                title="❌ Failed to Fetch Avatars",
                description="\n".join(failure_lines),
                color=0xe74c3c,
            )
            embed_error.set_footer(text="💡 Check the inputs and try again!")
            await update_progress(embed_error)
            return

        if failures:
            failure_summary = discord.Embed(
                title="⚠️ Some Avatars Failed",
                description="\n".join(f"• **{pid}** — {msg}" for pid, msg in failures),
                color=0xf1c40f,
            )
            failure_summary.set_footer(text="💡 Review the failed entries and try again.")
            await self._send_embed(ctx, failure_summary, followup=followup)

    async def _handle_add_or_remove(
        self,
        ctx,
        *,
        product_ids: list[str],
        region: str,
        cookie_arg: str | None,
        cookie_override: bool,
        operation: str,
    ) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return

        cleaned_ids = [pid.strip() for pid in product_ids if pid.strip()]
        if not cleaned_ids:
            embed = discord.Embed(
                title="ℹ️ Missing Product IDs",
                description="Provide at least one product ID to process.",
                color=0xf1c40f,
            )
            await self._send_embed(ctx, embed, content=self._mention(ctx))
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
                content=self._mention(ctx),
            )
            return

        mention = self._mention(ctx)
        actor = self._actor_label(ctx)

        if cookie_arg is None and not self.api.has_pdc_fallback():
            guidance = (
                "Provide your `pdccws_p` cookie with `--pdc YOUR_COOKIE` at the end of the command, "
                "or restart the bot with `--env` so the bot can read PDC from your .env file."
            )
            embed = discord.Embed(
                title="🍪 Cookie Required",
                description=guidance,
                color=0xe67e22,
            )
            await self._send_embed(ctx, embed, content=mention)
            return

        if cookie_arg:
            print(f"[psn] Using custom PDC from command for {actor}: {mask_value(cookie_arg)}")

        action_text = "Adding to Cart" if operation == "add" else "Removing from Cart"
        progress_description = f"⏳ Processing {len(cleaned_ids)} item(s)..."

        is_app_context = self._is_app_context(ctx)

        progress_embed = discord.Embed(
            title=f"{'🛒' if operation == 'add' else '🗑️'} {action_text}...",
            description=progress_description,
            color=0xf39c12,
        )

        progress_message = None
        if is_app_context:
            await ctx.respond(content=mention, embed=progress_embed)
        else:
            progress_message = await ctx.send(content=mention, embed=progress_embed, silent=True)

        results: list[tuple[str, bool, str | None]] = []
        successes: list[str] = []
        failures: list[tuple[str, str]] = []

        for pid in cleaned_ids:
            request = PSNRequest(
                region=region,
                product_id=pid,
                pdccws_p=cookie_arg,
                requested_by=actor,
            )

            try:
                if operation == "add":
                    await self.api.add_to_cart(request)
                else:
                    await self.api.remove_from_cart(request)
                successes.append(pid)
                results.append((pid, True, None))
            except APIError as e:
                message = e.message if getattr(e, "message", None) else str(e)
                if getattr(e, "code", None) == "auth":
                    hints = getattr(e, "hints", {}) or {}
                    need_cookie = hints.get("cookie", True)
                    need_npsso = hints.get("npsso", True)
                    embed_error = self._auth_error_embed(
                        message,
                        cookie_override,
                        need_cookie,
                        need_npsso,
                    )
                    if is_app_context:
                        await ctx.edit(embed=embed_error)
                    elif progress_message is not None:
                        await progress_message.edit(embed=embed_error)
                    else:
                        await self._send_embed(ctx, embed_error, content=mention)
                    return
                failures.append((pid, message))
                results.append((pid, False, message))

        if successes and not failures:
            title = "✅ Added Successfully!" if operation == "add" else "✅ Removed Successfully!"
            description = "• " + "\n• ".join(successes)
            color = 0x27ae60
        elif failures and not successes:
            title = "❌ Failed to Add" if operation == "add" else "❌ Failed to Remove"
            description = "\n".join(f"• {pid} — {msg}" for pid, msg in failures)
            color = 0xe74c3c
        else:
            title = "⚠️ Partial Success"
            parts = [
                "✅ Processed:\n" + "\n".join(f"• {pid}" for pid in successes),
                "⚠️ Failed:\n" + "\n".join(f"• {pid} — {msg}" for pid, msg in failures),
            ]
            description = "\n\n".join(parts)
            color = 0xf1c40f

        footer = (
            "🎮 Check your PlayStation Store cart!"
            if operation == "add"
            else "🎮 Item removed from PlayStation Store cart!"
        )

        lines: list[str] = []
        for pid, succeeded, message in results:
            if succeeded:
                status_text = "added to cart" if operation == "add" else "removed from cart"
                lines.append(f"✅ **{pid}** *({status_text})*")
            else:
                lowered = (message or "").lower()
                if "already" in lowered and "cart" in lowered:
                    reason = "already in cart" if operation == "add" else "already removed"
                else:
                    reason = message or "failed"
                lines.append(f"❌ **{pid}** *({reason})*")

        embed_result = discord.Embed(
            title=title,
            description="\n".join(lines) if lines else description,
            color=color,
        )
        embed_result.set_footer(text=footer)
        if is_app_context:
            await ctx.edit(embed=embed_result)
        elif progress_message is not None:
            await progress_message.edit(embed=embed_result)
        else:
            await self._send_embed(ctx, embed_result, content=mention)

    async def _handle_account(self, ctx, username: str) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return

        progress_embed = discord.Embed(
            title="🔍 Searching User...",
            description=f"⏳ Looking up **{username}** on PlayStation Network...",
            color=0xf39c12,
        )

        is_app_context = self._is_app_context(ctx)
        if is_app_context:
            await ctx.respond(embed=progress_embed)
            progress_message = None
        else:
            progress_message = await ctx.send(embed=progress_embed)

        try:
            accid = await self.api.obtain_account_id(username)
        except APIError as e:
            embed_error = discord.Embed(
                title="❌ User Not Found",
                description=f"🚫 {e}",
                color=0xe74c3c,
            )
            embed_error.set_footer(text="💡 Check the username and try again!")
            if is_app_context:
                await ctx.edit(embed=embed_error)
            elif progress_message is not None:
                await progress_message.edit(embed=embed_error)
            else:
                await ctx.send(embed=embed_error)
            return

        embed_success = discord.Embed(
            title=f"🎮 {username}",
            description=f"🆔 **Account ID:** `{accid}`",
            color=0x27ae60,
        )
        embed_success.set_footer(text="✅ Account ID retrieved successfully!")
        if is_app_context:
            await ctx.edit(embed=embed_success)
        elif progress_message is not None:
            await progress_message.edit(embed=embed_success)
        else:
            await ctx.send(embed=embed_success)

    psn_group = discord.SlashCommandGroup(
        "psn", description="PlayStation Store avatar utilities."
    )

    @psn_group.command(name="check", description="🔍 Checks an avatar for you.")
    async def psn_slash_check(
        self,
        ctx: discord.ApplicationContext,
        region: Option(str, description=region_desc),  # type: ignore
        product_id: Option(str, description=id_desc),  # type: ignore
        product_id2: Option(str, description="Additional product ID (optional)", default=None) = None,  # type: ignore[arg-type]
        product_id3: Option(str, description="Additional product ID (optional)", default=None) = None,  # type: ignore[arg-type]
        product_id4: Option(str, description="Additional product ID (optional)", default=None) = None,  # type: ignore[arg-type]
    ) -> None:
        optional_ids = collect_product_ids(product_id2, product_id3, product_id4)
        product_ids = [product_id] + optional_ids
        await self._handle_check(
            ctx,
            product_ids=product_ids,
            region=region,
        )

    @psn_group.command(name="add", description="🛒 Adds the avatar you input into your cart.")
    async def psn_slash_add(
        self,
        ctx: discord.ApplicationContext,
        region: Option(str, description=region_desc),  # type: ignore
        product_id: Option(str, description=id_desc),  # type: ignore
        product_id2: Option(str, description="Additional product ID (optional)", default=None) = None,  # type: ignore[arg-type]
        product_id3: Option(str, description="Additional product ID (optional)", default=None) = None,  # type: ignore[arg-type]
        product_id4: Option(str, description="Additional product ID (optional)", default=None) = None,  # type: ignore[arg-type]
        pdc: Option(str, description=token_desc, **PDC_OPTION_KWARGS) = None,  # type: ignore[arg-type]
    ) -> None:
        if pdc is None and not self.api.has_pdc_fallback():
            await ctx.respond(
                embed=discord.Embed(
                    title="🍪 Cookie Required",
                    description=(
                        "Provide your `pdccws_p` cookie in the PDC field, or restart the bot with `--env` so it "
                        "can read PDC from your .env file."
                    ),
                    color=0xe67e22,
                ),
            )
            return
        product_ids = [product_id] + collect_product_ids(product_id2, product_id3, product_id4)
        await self._handle_add_or_remove(
            ctx,
            product_ids=product_ids,
            region=region,
            cookie_arg=pdc,
            cookie_override=pdc is not None,
            operation="add",
        )

    @psn_group.command(name="remove", description="🗑️ Removes the avatar you input from your cart.")
    async def psn_slash_remove(
        self,
        ctx: discord.ApplicationContext,
        region: Option(str, description=region_desc),  # type: ignore
        product_id: Option(str, description=id_desc),  # type: ignore
        product_id2: Option(str, description="Additional product ID (optional)", default=None) = None,  # type: ignore[arg-type]
        product_id3: Option(str, description="Additional product ID (optional)", default=None) = None,  # type: ignore[arg-type]
        product_id4: Option(str, description="Additional product ID (optional)", default=None) = None,  # type: ignore[arg-type]
        pdc: Option(str, description=token_desc, **PDC_OPTION_KWARGS) = None,  # type: ignore[arg-type]
    ) -> None:
        if pdc is None and not self.api.has_pdc_fallback():
            await ctx.respond(
                embed=discord.Embed(
                    title="🍪 Cookie Required",
                    description=(
                        "Provide your `pdccws_p` cookie in the PDC field, or restart the bot with `--env` so it "
                        "can read PDC from your .env file."
                    ),
                    color=0xe67e22,
                ),
            )
            return
        product_ids = [product_id] + collect_product_ids(product_id2, product_id3, product_id4)
        await self._handle_add_or_remove(
            ctx,
            product_ids=product_ids,
            region=region,
            cookie_arg=pdc,
            cookie_override=pdc is not None,
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
        await self._delete_prefix_message(ctx)

        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🎮 PSN Commands",
                description=(
                    "Use `/psn check`, `/psn add`, `/psn remove`, or `/psn account`.\n"
                    "Prefix usage: `$psn <subcommand>` (your original message is auto-deleted)."
                ),
                color=0x3498db,
            )
            await self._send_embed(ctx, embed)

    @psn_prefix.command(name="check")
    async def psn_prefix_check(self, ctx: commands.Context, *, entries: str = "") -> None:
        await self._delete_prefix_message(ctx)
        parsed = await self._prepare_prefix_batch(ctx, entries, "check")
        if parsed is None:
            return
        region, product_ids, _ = parsed
        await self._handle_check(
            ctx,
            product_ids=product_ids,
            region=region,
        )

    @psn_prefix.command(name="add")
    async def psn_prefix_add(self, ctx: commands.Context, *, entries: str = "") -> None:
        await self._delete_prefix_message(ctx)
        parsed = await self._prepare_prefix_batch(ctx, entries, "add", allow_cookie=True)
        if parsed is None:
            return
        region, product_ids, cookie = parsed
        await self._handle_add_or_remove(
            ctx,
            product_ids=product_ids,
            region=region,
            cookie_arg=cookie,
            cookie_override=cookie is not None,
            operation="add",
        )

    @psn_prefix.command(name="remove")
    async def psn_prefix_remove(self, ctx: commands.Context, *, entries: str = "") -> None:
        await self._delete_prefix_message(ctx)
        parsed = await self._prepare_prefix_batch(ctx, entries, "remove", allow_cookie=True)
        if parsed is None:
            return
        region, product_ids, cookie = parsed
        await self._handle_add_or_remove(
            ctx,
            product_ids=product_ids,
            region=region,
            cookie_arg=cookie,
            cookie_override=cookie is not None,
            operation="remove",
        )

    @psn_prefix.command(name="account")
    async def psn_prefix_account(self, ctx: commands.Context, username: str) -> None:
        await self._delete_prefix_message(ctx)
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
        if not self.allowed_guild_ids:
            return True
        guild = ctx.guild
        if guild is None or guild.id not in self.allowed_guild_ids:
            embed = discord.Embed(
                title="🔒 Command Restricted",
                description="This bot is configured for specific server(s) and cannot be used here.",
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
    use_env = os.getenv("BOT_USE_ENV") == "1"
    env_path = os.getenv("BOT_ENV_PATH") if use_env else None
    default_pdc = os.getenv("PDC") if use_env else None
    cog = PSNCog(
        os.getenv("NPSSO"),
        bot,
        default_pdc,
        _parse_allowed_guilds(os.getenv("GUILD_ID")),
        env_path=env_path,
    )
    bot.add_cog(cog)
