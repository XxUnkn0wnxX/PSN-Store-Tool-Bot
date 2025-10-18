import os
import time
import argparse
from math import ceil
import traceback
import asyncio
from collections.abc import Awaitable, Callable
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

PREFIX = os.getenv("PREFIX", "$")

intents = discord.Intents.default()
intents.message_content = True

activity = discord.Activity(
    type=discord.ActivityType.watching,
    name="🎮 dev by groriz11 | /tutorial "
)

# Names of your cog modules (with or without a cogs/ package)
COGS = ["misc", "psn"]
AUTO_SYNC_DEBUG_GUILD = True
SYNC_TIMEOUT_SECS = 20
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
    command_prefix=commands.when_mentioned_or(PREFIX),
    activity=activity,
    intents=intents,
)
bot.help_command = None
if AUTO_SYNC_DEBUG_GUILD:
    bot.debug_guilds = [GUILD_ID]


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

    timeout = aiohttp.ClientTimeout(total=15)
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "PSNToolBot/1.0 (https://github.com/XxUnkn0wnxX/PSN-Store-Tool-Bot)"
    }

    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
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

    timeout = aiohttp.ClientTimeout(total=15)
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "PSNToolBot/1.0 (https://github.com/XxUnkn0wnxX/PSN-Store-Tool-Bot)",
    }

    async def _get_json(session: aiohttp.ClientSession, url: str, retries: int = 3):
        for attempt in range(retries):
            async with session.get(url) as resp:
                if resp.status == 429:
                    retry_after = resp.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after is not None else 1.0
                    delay = max(1.0, min(delay, 10.0))
                    print(f"[http] 429 on {url}; retrying in {delay:.1f}s (attempt {attempt + 1}/{retries})")
                    await asyncio.sleep(delay)
                    continue
                if resp.status == 404:
                    return None
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"HTTP {resp.status} for {url}: {text}")
                return await resp.json()
        raise RuntimeError(f"Exceeded retries for GET {url}")

    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        global_json = await _get_json(
            session, f"https://discord.com/api/v10/applications/{APPLICATION_ID}/commands"
        )
        global_cmds = {cmd.get("name", "") for cmd in (global_json or [])}

        guild_json = await _get_json(
            session, f"https://discord.com/api/v10/applications/{APPLICATION_ID}/guilds/{guild_id}/commands"
        )
        guild_cmds = {cmd.get("name", "") for cmd in guild_json} if guild_json is not None else set()

    return global_cmds, guild_cmds


async def wait_for_command_sets(
    token: str,
    guild_id: int,
    expected_global: set[str],
    expected_guild: set[str],
    timeout: float = 30.0,
    interval: float = 3.0,
    retry_callback: Callable[[set[str], set[str]], Awaitable[None]] | None = None,
    max_attempts: int = 5,
) -> bool:
    for attempt in range(1, max_attempts + 1):
        end_at = time.monotonic() + timeout
        while time.monotonic() < end_at:
            existing_global, existing_guild = await fetch_command_sets(token, guild_id)
            missing_global = expected_global - existing_global
            missing_guild = expected_guild - existing_guild

            if not missing_global and not missing_guild:
                return True

            remaining = max(0.0, end_at - time.monotonic())
            print(
                "[sync] Verifying (retry in "
                f"{interval:.0f}s, {ceil(remaining)}s left)… "
                f"missing_global={sorted(missing_global)} "
                f"missing_guild={sorted(missing_guild)}",
                flush=True,
            )
            await asyncio.sleep(interval)

        if retry_callback is not None:
            print(f"[sync] Attempt {attempt}/{max_attempts} timed out — retrying manual sync…", flush=True)
            try:
                await retry_callback(missing_global, missing_guild)
            except Exception as exc:
                print(f"[sync] Retry sync failed: {exc}", flush=True)
        else:
            print(f"[sync] Attempt {attempt}/{max_attempts} timed out.", flush=True)

    print("[sync] Command verification failed after maximum attempts.", flush=True)
    return False


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

    retry_callback: Callable[[set[str], set[str]], Awaitable[None]] | None = None

    if AUTO_SYNC_DEBUG_GUILD and not _force_sync:
        print("[sync] Using debug_guilds auto-sync; skipping manual sync.", flush=True)
    else:
        async def _do_sync(force_global: bool, force_guild: bool) -> None:
            if force_global:
                start = time.perf_counter()
                print("[sync] Syncing global commands…", flush=True)
                await bot.sync_commands()
                duration = time.perf_counter() - start
                print(f"[sync] Syncing global commands… (completed in {duration:.2f}s)", flush=True)
            else:
                print("[sync] Global commands already up to date; skipping sync.", flush=True)

            if force_guild:
                start = time.perf_counter()
                print("[sync] Syncing guild commands…", flush=True)
                await bot.sync_commands(guild_ids=[GUILD_ID])
                duration = time.perf_counter() - start
                print(f"[sync] Syncing guild commands… (completed in {duration:.2f}s)", flush=True)
            else:
                print("[sync] Guild commands already up to date; skipping sync.", flush=True)

        initial_force_global = _need_sync_global or _force_sync
        initial_force_guild = _need_sync_guild or _force_sync

        try:
            await asyncio.wait_for(
                _do_sync(initial_force_global, initial_force_guild),
                timeout=SYNC_TIMEOUT_SECS,
            )
        except asyncio.TimeoutError:
            print(
                f"[sync] Manual sync timed out after {SYNC_TIMEOUT_SECS}s — continuing; verification will confirm state.",
                flush=True,
            )

        async def retry_callback_fn(missing_global: set[str], missing_guild: set[str]) -> None:
            force_global = bool(missing_global) or _force_sync
            force_guild = bool(missing_guild) or _force_sync
            if not force_global and not force_guild:
                return
            try:
                await asyncio.wait_for(
                    _do_sync(force_global, force_guild), timeout=SYNC_TIMEOUT_SECS
                )
            except asyncio.TimeoutError:
                print(
                    f"[sync] Retry manual sync timed out after {SYNC_TIMEOUT_SECS}s; will re-check commands.",
                    flush=True,
                )

        retry_callback = retry_callback_fn

    success = await wait_for_command_sets(
        _bot_token,
        GUILD_ID,
        _expected_global,
        _expected_guild,
        retry_callback=retry_callback,
    )
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
    all_cmd_names = {cmd.name for cmd in bot.application_commands}

    if AUTO_SYNC_DEBUG_GUILD:
        _expected_global = set()
        _expected_guild = set(all_cmd_names)
    else:
        global_commands = {
            cmd.name for cmd in bot.application_commands if not getattr(cmd, "guild_ids", None)
        }
        guild_commands = {
            cmd.name for cmd in bot.application_commands if getattr(cmd, "guild_ids", None)
        }
        _expected_global = global_commands
        _expected_guild = guild_commands

    return _expected_global, _expected_guild


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

    if AUTO_SYNC_DEBUG_GUILD and not _force_sync:
        print("[sync] Auto guild sync enabled; relying on Pycord debug_guilds.")
        if missing_guild:
            print(f"[sync] Waiting for guild commands: {sorted(missing_guild)}")
        if missing_global:
            print(f"[sync] Unexpected global commands missing: {sorted(missing_global)}")
        _need_sync_global = False
        _need_sync_guild = False
    else:
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
