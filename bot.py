import os
import time
import argparse
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
_expected_global: set[str] = set()
_expected_guild: set[str] = set()
_need_sync_global = True
_need_sync_guild = True
_force_sync = False
_bot_token: str = ""


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


async def fetch_command_sets(token: str, guild_id: int) -> tuple[set[str], set[str]]:
    if APPLICATION_ID is None:
        raise RuntimeError("Application ID not set; ensure ensure_guild_membership() ran first")

    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "PSNToolBot/1.0 (https://github.com/XxUnkn0wnxX/PSN-Store-Tool-Bot)",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(f"https://discord.com/api/v10/applications/{APPLICATION_ID}/commands") as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Failed to fetch global commands (status {resp.status}): {text}")
            global_cmds = {cmd.get("name", "") for cmd in await resp.json()}

        async with session.get(
            f"https://discord.com/api/v10/applications/{APPLICATION_ID}/guilds/{guild_id}/commands"
        ) as resp:
            if resp.status not in (200, 404):
                text = await resp.text()
                raise RuntimeError(f"Failed to fetch guild commands (status {resp.status}): {text}")
            guild_cmds = {cmd.get("name", "") for cmd in await resp.json()} if resp.status == 200 else set()

    return global_cmds, guild_cmds


async def wait_for_command_sets(
    token: str,
    guild_id: int,
    expected_global: set[str],
    expected_guild: set[str],
    timeout: float = 60.0,
    interval: float = 5.0,
) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        existing_global, existing_guild = await fetch_command_sets(token, guild_id)

        missing_global = expected_global - existing_global
        missing_guild = expected_guild - existing_guild

        if not missing_global and not missing_guild:
            return True

        if time.monotonic() >= deadline:
            if missing_global:
                print(f"[sync] Global commands still missing after timeout: {sorted(missing_global)}")
            if missing_guild:
                print(f"[sync] Guild commands still missing after timeout: {sorted(missing_guild)}")
            return False

        await asyncio.sleep(interval)


@bot.event
async def on_ready() -> None:
    global _banner_printed
    if _banner_printed:
        return
    print(f"[lib] Pycord version: {discord.__version__}")
    print(f"[lib] module path: {discord.__file__}")
    print(f"[ready] Logged in as {bot.user} ({bot.user.id})")
    invite_url = (
        f"https://discord.com/api/oauth2/authorize?"
        f"client_id={(APPLICATION_ID or bot.user.id)}&scope=bot%20applications.commands&permissions=8&integration_type=0"
    )
    available = [c.qualified_name for c in bot.application_commands]

    if _need_sync_global or _force_sync:
        print("[sync] Syncing global commands…", flush=True)
        try:
            await bot.sync_commands()
        except Exception as exc:
            print(f"[sync] Global sync failed: {exc}")
            raise
    else:
        print("[sync] Global commands already up to date; skipping sync.", flush=True)

    if _need_sync_guild or _force_sync:
        print("[sync] Syncing guild commands…", flush=True)
        try:
            await bot.sync_commands(guild_ids=[GUILD_ID])
        except Exception as exc:
            print(f"[sync] Guild sync failed: {exc}")
            raise
    else:
        print("[sync] Guild commands already up to date; skipping sync.", flush=True)

    success = await wait_for_command_sets(_bot_token, GUILD_ID, _expected_global, _expected_guild)
    if success:
        print("[sync] Command verification succeeded.", flush=True)
    else:
        print("[sync] Command verification timed out; check Discord developer portal.", flush=True)

    available = [c.qualified_name for c in bot.application_commands]
    print(f"[ready] Commands: {available}", flush=True)
    print(
        """
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                                  🎮 PSNTOOLBOT 🎮                                     ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║  🤖 PSNToolBot is ready!                                                              ║
║  🎮 Original creator: https://github.com/groriz11                                     ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
    """,
        flush=True,
    )
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


async def prepare_expected_commands() -> tuple[set[str], set[str]]:
    global _expected_global, _expected_guild
    global_commands = {
        cmd.name for cmd in bot.application_commands if not getattr(cmd, "guild_ids", None)
    }
    guild_commands = {
        cmd.name for cmd in bot.application_commands if getattr(cmd, "guild_ids", None)
    }
    _expected_global = global_commands
    _expected_guild = guild_commands
    return global_commands, guild_commands


async def main(args: argparse.Namespace) -> None:
    token = os.getenv("TOKEN")
    if not token:
        raise SystemExit("Missing TOKEN in .env")
    if not os.getenv("NPSSO"):
        print("[warn] NPSSO not set; PSN commands may error at runtime.")

    global _bot_token, _force_sync, _need_sync_global, _need_sync_guild
    _bot_token = token
    _force_sync = bool(getattr(args, "force_sync", False))

    has_access = await ensure_guild_membership(token, GUILD_ID)
    if not has_access:
        return

    await load_extensions()
    expected_global, expected_guild = await prepare_expected_commands()

    try:
        existing_global, existing_guild = await fetch_command_sets(token, GUILD_ID)
    except Exception as exc:
        print(f"[warn] Unable to fetch existing command sets: {exc}")
        existing_global, existing_guild = set(), set()

    missing_global = expected_global - existing_global
    missing_guild = expected_guild - existing_guild

    _need_sync_global = _force_sync or bool(missing_global)
    _need_sync_guild = _force_sync or bool(missing_guild)

    if _need_sync_global:
        if missing_global:
            print(f"[sync] Global commands missing: {sorted(missing_global)}")
        else:
            print("[sync] Global commands will be force-synced.")
    else:
        print("[sync] Global commands already present; will skip sync unless forced.")

    if _need_sync_guild:
        if missing_guild:
            print(f"[sync] Guild commands missing: {sorted(missing_guild)}")
        else:
            print("[sync] Guild commands will be force-synced.")
    else:
        print("[sync] Guild commands already present; will skip sync unless forced.")

    print("Starting bot...")
    try:
        await bot.start(token)
    finally:
        await bot.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run PSNToolBot with optional command sync controls.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--force-sync",
        dest="force_sync",
        action="store_true",
        help="Force sync slash commands even if they already match",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\nShutting down gracefully…")
