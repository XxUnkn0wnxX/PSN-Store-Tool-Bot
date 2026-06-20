import os
from typing import Iterable, Set

import discord
from discord.ext import commands

tutorialstring = (
    "🎮 **1**. First go to playstation.com\n"
    "🌍 **2**. When you have loaded check the link and you will see your region\n"
    "🔐 **3**. Now login to your account\n"
    "🔍 **4**. Open Chrome's Dev Tools\n"
    "📱 **5**. Click on the __Application__ option\n"
    "🍪 **6**. Navigate to cookies for playstation.com and look for the `pdccws_p` cookie. That cookie is your token\n"
    "🆔 **7**. You will find the avatar id by using /psprices product_id with the url to the avatar page on psprices\n\n"
    "> ℹ️ **Browser note:** These instructions are for Chromium-based browsers such as Chrome. "
    "If you use another browser, you'll need to find its cookie storage tab yourself.\n"
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

help_embed_description = (
    "Slash commands are the recommended way to run the bot, but every feature also has a "
    "matching prefix command for quick text usage. Slash add/remove commands always require the "
    "`pdccws_p` cookie field; prefix commands can fall back to the `.env` value when the bot runs "
    "with `--env`. Here's a quick reference:"
)


def _parse_allowed_guilds(raw: str | None) -> Set[int]:
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


def build_help_embed(prefix: str) -> discord.Embed:
    embed = discord.Embed(
        title="🆘 **Command Reference**",
        description=help_embed_description,
        color=0x1abc9c,
    )
    embed.add_field(
        name="🎮 PSN Avatar Tools",
        value=(
            f"> `/psn check <region> <product_id> [up to 3 more IDs]`\n"
            f"> `{prefix}psn check <region> <product_id> [more IDs…]`\n\n"
            f"> `/psn add <region> <product_id> [up to 3 more IDs]` *(PDC required)*\n"
            f"> `{prefix}psn add <region> <product_id> [more IDs…] --pdc YOUR_COOKIE` *(required if the bot wasn't started with `--env`)*\n\n"
            f"> `/psn remove <region> <product_id> [up to 3 more IDs]` *(PDC required)*\n"
            f"> `{prefix}psn remove <region> <product_id> [more IDs…] --pdc YOUR_COOKIE` *(required if the bot wasn't started with `--env`)*\n\n"
            f"> `/psn account <username> <npsso_token>` *(NPSSO required for lookups)*\n"
            f"> `{prefix}psn account <username> --npsso YOUR_TOKEN`\n"
        ),
        inline=False,
    )
    embed.add_field(
        name="🛠️ Utilities",
        value=(
            f"> `/ping`\n"
            f"> `{prefix}ping`\n\n"
            f"> `/tutorial`\n"
            f"> `{prefix}tutorial`\n\n"
            f"> `/credits`\n"
            f"> `{prefix}credits`\n\n"
            f"> `/help`\n"
            f"> `{prefix}help`\n"
        ),
        inline=False,
    )
    embed.set_footer(text="Tip: Prefix defaults to '$'. Prefix commands auto-delete your message; add `--pdc YOUR_COOKIE` (unless running with `--env`) and include `--npsso YOUR_TOKEN` for account lookups.")
    return embed


class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot, allowed_guild_ids: Iterable[int] | None = None) -> None:
        self.bot = bot
        self.allowed_guild_ids: set[int] = set(allowed_guild_ids or [])

    @discord.slash_command(description="🏓 Pings the bot to check latency.")
    async def ping(self, ctx: discord.ApplicationContext) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return
        latency = self.bot.latency * 1000
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"⚡ **Latency:** {latency:.2f}ms",
            color=0x2ecc71
        )
        embed.set_footer(text="🤖 Bot is running smoothly!")
        await ctx.respond(embed=embed)

    @commands.command(name="ping")
    async def ping_command(self, ctx: commands.Context) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return
        latency = self.bot.latency * 1000
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"⚡ **Latency:** {latency:.2f}ms",
            color=0x2ecc71,
        )
        embed.set_footer(text="🤖 Bot is running smoothly!")
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass
        await ctx.send(embed=embed)

    @discord.slash_command(description="📚 Shows how to use the bot.")
    async def tutorial(self, ctx: discord.ApplicationContext) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return
        await ctx.respond(embed=tutorialemb)

    @commands.command(name="tutorial")
    async def tutorial_command(self, ctx: commands.Context) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass
        await ctx.send(embed=tutorialemb)

    @discord.slash_command(description="👥 Shows credits and bot information.")
    async def credits(self, ctx: discord.ApplicationContext) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return
        await ctx.respond(embed=creditsemb)

    @commands.command(name="credits")
    async def credits_command(self, ctx: commands.Context) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass
        await ctx.send(embed=creditsemb)

    @discord.slash_command(description="🆘 Shows slash commands and their prefix equivalents.")
    async def help(self, ctx: discord.ApplicationContext) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return
        prefix = os.getenv("PREFIX", "$")
        await ctx.respond(embed=build_help_embed(prefix))

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context) -> None:
        if not await self._ensure_allowed_guild(ctx):
            return
        prefix = os.getenv("PREFIX", "$")
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass
        await ctx.send(embed=build_help_embed(prefix))

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
    bot.add_cog(Misc(bot, _parse_allowed_guilds(os.getenv("GUILD_ID"))))
