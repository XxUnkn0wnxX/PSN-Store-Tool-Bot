import os
import traceback
import asyncio
import aiohttp
import discord
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()

from pathlib import Path
load_dotenv(Path(__file__).with_name(".env"))  # resolve .env next to bot.py

required = ["TOKEN", "NPSSO", "GUILD_ID"]
missing = [k for k in required if not os.getenv(k)]
if missing:
    raise SystemExit(f"Missing env var(s): {', '.join(missing)}")

try:
    GUILD_ID = int(os.getenv("GUILD_ID", "0"))
except ValueError as exc:
    raise SystemExit("GUILD_ID must be a numeric Discord server ID") from exc

if GUILD_ID <= 0:
    raise SystemExit("GUILD_ID must be a positive Discord server ID")

intents = discord.Intents.default()
intents.message_content = True

activity = discord.Activity(
    type=discord.ActivityType.watching,
    name="🎮 dev by groriz11 | /tutorial "
)

# Names of your cog modules (with or without a cogs/ package)
COGS = ["misc", "psn", "psprices"]
APPLICATION_ID: str | None = None
_banner_printed = False
_cogs_loaded = False


bot = commands.Bot(
    command_prefix=commands.when_mentioned,
    activity=activity,
    intents=intents,
)


async def load_extensions() -> None:
    global _cogs_loaded
    if _cogs_loaded:
        return
    print("[setup] loading cogs…", flush=True)
    for name in COGS:
        loaded = False
        for mod_path in (f"cogs.{name}", name):
            try:
                bot.load_extension(mod_path)
                print(f"[cog] loaded {mod_path}", flush=True)
                loaded = True
                break
            except ModuleNotFoundError:
                continue
            except Exception:
                print(f"[cog] ERROR loading {mod_path}:\n{traceback.format_exc()}")
                break
        if not loaded:
            print(f"[cog] FAILED to load {name} (tried cogs.{name} and {name})")

    print("[setup] finished loading cogs", flush=True)
    _cogs_loaded = True


async def ensure_guild_membership(token: str, guild_id: int) -> bool:
    global APPLICATION_ID

    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "PSNToolBot/1.0 (https://github.com/XxUnkn0wnxX/PSN-Store-Tool-Bot)"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get("https://discord.com/api/v10/oauth2/applications/@me") as resp:
            if resp.status != 200:
                text = await resp.text()
                raise SystemExit(f"Failed to validate bot token (status {resp.status}): {text}")
            data = await resp.json()
            APPLICATION_ID = data.get("id")

        async with session.get(f"https://discord.com/api/v10/guilds/{guild_id}") as resp:
            if resp.status == 200:
                return True
            if resp.status in {403, 404}:
                invite = (
                    "https://discord.com/api/oauth2/authorize?"
                    f"client_id={APPLICATION_ID}&scope=bot%20applications.commands&permissions=8&integration_type=0"
                )
                print(
                    f"[warn] Bot is not invited to guild {guild_id}.\n\n"
                    f"Invite it using:\n\n{invite}\n"
                )
                return False

            text = await resp.text()
            raise SystemExit(
                f"Unexpected response when checking guild {guild_id} (status {resp.status}): {text}"
            )


@bot.event
async def on_ready() -> None:
    global _banner_printed
    if _banner_printed:
        return
    print(f"[lib] Pycord version: {discord.__version__}")
    print(f"[lib] module path  : {discord.__file__}")
    print(f"[ready] Logged in as {bot.user} ({bot.user.id})")
    invite_url = (
        f"https://discord.com/api/oauth2/authorize?"
        f"client_id={(APPLICATION_ID or bot.user.id)}&scope=bot%20applications.commands&permissions=8&integration_type=0"
    )
    print("[sync] Syncing global commands…", flush=True)
    global_commands = await bot.sync_commands()
    print("[sync] Syncing guild commands…", flush=True)
    guild_commands = await bot.sync_commands(guild_ids=[GUILD_ID])
    print(f"[sync] Global commands: {[cmd.qualified_name for cmd in global_commands]}", flush=True)
    print(f"[sync] Guild commands ({GUILD_ID}): {[cmd.qualified_name for cmd in guild_commands]}", flush=True)
    available = [c.qualified_name for c in bot.application_commands]
    print(f"[ready] Commands   : {available}", flush=True)
    print(f"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                                  🎮 PSNTOOLBOT 🎮                                     ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║  🤖 PSNToolBot is ready!                                                              ║
║  🔗 Invite: {invite_url}
║  🎮 Original creator: https://github.com/groriz11                                     ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
    """, flush=True)
    _banner_printed = True


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return
    if message.content.lower() == "hello":
        embed = discord.Embed(
            title="👋 Hello there!",
            description="🎮 I'm PSNToolBot! Use `/tutorial` to get started!",
            color=0x2c3e50,
        )
        embed.set_footer(text="💻 Created by groriz11")
        await message.channel.send(embed=embed)
    await bot.process_commands(message)


async def main() -> None:
    token = os.getenv("TOKEN")
    if not token:
        raise SystemExit("Missing TOKEN in .env")
    # Optional: ensure NPSSO exists too if your cogs need it
    if not os.getenv("NPSSO"):
        print("[warn] NPSSO not set; PSN commands may error at runtime.")

    has_access = await ensure_guild_membership(token, GUILD_ID)
    if not has_access:
        return

    await load_extensions()
    print("Starting bot...")
    try:
        await bot.start(token)
    finally:
        await bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down gracefully…")
