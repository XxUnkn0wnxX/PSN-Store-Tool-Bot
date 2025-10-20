import os
import sys
import time
import argparse
from math import ceil
import traceback
import asyncio
from collections.abc import Awaitable, Callable, Sequence
import aiohttp
import discord
from dotenv import load_dotenv
from discord.ext import commands
from pathlib import Path


def _detect_env_source() -> tuple[bool, Path | None]:
    args = sys.argv[1:]
    use_env = False
    path: Path | None = None

    for idx, arg in enumerate(args):
        if arg == "--env":
            use_env = True
            if idx + 1 < len(args) and not args[idx + 1].startswith("-"):
                path = Path(args[idx + 1])
            break
        if arg.startswith("--env="):
            use_env = True
            value = arg.split("=", 1)[1]
            if value:
                path = Path(value)
            break

    if use_env and path is None:
        path = Path(__file__).with_name(".env")

    return use_env, path


USE_ENV_FILE, ENV_FILE_PATH = _detect_env_source()

if USE_ENV_FILE:
    if ENV_FILE_PATH:
        load_dotenv(ENV_FILE_PATH)
    else:
        load_dotenv()
    if ENV_FILE_PATH:
        os.environ["BOT_ENV_PATH"] = str(ENV_FILE_PATH)
    os.environ["BOT_USE_ENV"] = "1"
else:
    os.environ["BOT_USE_ENV"] = "0"
    os.environ.pop("BOT_ENV_PATH", None)


def _load_config() -> dict[str, str]:
    config_path = Path(__file__).with_name(".config")
    if not config_path.exists():
        raise SystemExit("Missing .config file. Copy .config.template to .config and fill TOKEN, GUILD_ID, and PREFIX.")

    config: dict[str, str] = {}
    with config_path.open("r", encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise SystemExit(f"Invalid line in .config (line {lineno}): {raw.rstrip()}")
            key, value = line.split("=", 1)
            config[key.strip().upper()] = value.strip()
    return config


config_values = _load_config()

token_config = config_values.get("TOKEN", "").strip()
guild_config_raw = config_values.get("GUILD_ID", "").strip()
prefix_config = config_values.get("PREFIX", "").strip() or "$"

if not token_config or not guild_config_raw:
    raise SystemExit(".config must define TOKEN and at least one GUILD_ID.")

os.environ["TOKEN"] = token_config
os.environ["GUILD_ID"] = guild_config_raw
os.environ["PREFIX"] = prefix_config

guild_config_parts = [part.strip() for part in guild_config_raw.split(",") if part.strip()]
if not guild_config_parts:
    raise SystemExit("GUILD_ID must define at least one Discord server ID.")

try:
    GUILD_IDS: list[int] = [int(part) for part in guild_config_parts]
except ValueError as exc:
    raise SystemExit("GUILD_ID entries must be numeric Discord server IDs separated by commas") from exc

if any(guild_id <= 0 for guild_id in GUILD_IDS):
    raise SystemExit("GUILD_ID entries must be positive Discord server IDs")

GUILD_ID = GUILD_IDS[0]

PREFIX = prefix_config or "$"

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
    bot.debug_guilds = list(GUILD_IDS)


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


async def ensure_guild_membership(token: str, guild_ids: Sequence[int]) -> list[int]:
    global APPLICATION_ID

    normalized_ids = list(dict.fromkeys(guild_ids))
    if not normalized_ids:
        return []

    timeout = aiohttp.ClientTimeout(total=15)
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "PSNToolBot/1.0 (https://github.com/XxUnkn0wnxX/PSN-Store-Tool-Bot)"
    }

    accessible: list[int] = []
    missing: list[int] = []

    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        async with session.get("https://discord.com/api/v10/oauth2/applications/@me") as resp:
            if resp.status != 200:
                text = await resp.text()
                raise SystemExit(f"Failed to validate bot token (status {resp.status}): {text}")
            data = await resp.json()
            APPLICATION_ID = data.get("id")

        for guild_id in normalized_ids:
            async with session.get(f"https://discord.com/api/v10/guilds/{guild_id}") as resp:
                if resp.status == 200:
                    accessible.append(guild_id)
                    continue
                if resp.status in {403, 404}:
                    missing.append(guild_id)
                    continue

                text = await resp.text()
                raise SystemExit(
                    f"Unexpected response when checking guild {guild_id} (status {resp.status}): {text}"
                )

    if missing:
        invite = (
            "https://discord.com/api/oauth2/authorize?"
            f"client_id={APPLICATION_ID}&scope=bot%20applications.commands&permissions=8&integration_type=0"
        )
        missing_csv = ", ".join(str(g) for g in missing)
        print(
            f"[warn] Bot is not invited to guild(s): {missing_csv}.\n\n"
            f"Invite it using:\n\n{invite}\n",
            flush=True,
        )

    return accessible


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
    guild_ids: Sequence[int],
    expected_global: set[str],
    expected_guild: set[str],
    timeout: float = 30.0,
    interval: float = 3.0,
    retry_callback: Callable[[set[str], set[str]], Awaitable[None]] | None = None,
    max_attempts: int = 5,
) -> bool:
    guild_id_list = list(dict.fromkeys(guild_ids))
    if not guild_id_list:
        return True

    for attempt in range(1, max_attempts + 1):
        end_at = time.monotonic() + timeout
        while time.monotonic() < end_at:
            missing_global_total: set[str] = set()
            missing_guilds: dict[int, set[str]] = {}

            for guild_id in guild_id_list:
                existing_global, existing_guild = await fetch_command_sets(token, guild_id)
                missing_global_total |= expected_global - existing_global
                guild_missing = expected_guild - existing_guild
                if guild_missing:
                    missing_guilds[guild_id] = guild_missing

            if not missing_global_total and not missing_guilds:
                return True

            remaining = max(0.0, end_at - time.monotonic())
            combined_guild_missing = {
                gid: sorted(missing) for gid, missing in sorted(missing_guilds.items())
            }
            print(
                "[sync] Verifying (retry in "
                f"{interval:.0f}s, {ceil(remaining)}s left)… "
                f"missing_global={sorted(missing_global_total)} "
                f"missing_guild={combined_guild_missing}",
                flush=True,
            )
            await asyncio.sleep(interval)

        if retry_callback is not None:
            print(f"[sync] Attempt {attempt}/{max_attempts} timed out — retrying manual sync…", flush=True)
            try:
                aggregated_missing_guild = set().union(*missing_guilds.values()) if missing_guilds else set()
                await retry_callback(missing_global_total, aggregated_missing_guild)
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
    retry_callback: Callable[[set[str], set[str]], Awaitable[None]] | None = None

    if AUTO_SYNC_DEBUG_GUILD and not _force_sync:
        guild_list_display = _format_guild_list(GUILD_IDS)
        print(f"[sync] Using debug_guilds auto-sync for guilds [{guild_list_display}]; skipping manual sync.", flush=True)
    else:
        async def _do_sync(force_global: bool, force_guild: bool) -> None:
            guild_list_display = _format_guild_list(GUILD_IDS)
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
                print(f"[sync] Syncing guild commands for guilds [{guild_list_display}]…", flush=True)
                await bot.sync_commands(guild_ids=list(GUILD_IDS))
                duration = time.perf_counter() - start
                print(
                    f"[sync] Syncing guild commands for guilds [{guild_list_display}]… "
                    f"(completed in {duration:.2f}s)",
                    flush=True,
                )
            else:
                print(
                    f"[sync] Guild commands already up to date for guilds [{guild_list_display}]; skipping sync.",
                    flush=True,
                )

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
        GUILD_IDS,
        _expected_global,
        _expected_guild,
        retry_callback=retry_callback,
    )
    if success:
        print("[sync] Command verification succeeded.", flush=True)
    else:
        print("[sync] Command verification timed out; check Discord developer portal.", flush=True)

    for scope_name, commands_list in _summarize_commands():
        print(f"[ready] Commands ({scope_name}): {commands_list}", flush=True)
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


def _summarize_commands() -> list[tuple[str, list[str]]]:
    scopes: dict[str, set[str]] = {}
    for command in bot.application_commands:
        name = command.qualified_name
        guild_ids = getattr(command, "guild_ids", None)
        if guild_ids:
            try:
                iterator = list(guild_ids)
            except TypeError:
                iterator = [guild_ids]
            for guild_id in iterator:
                key = f"Guild {guild_id}"
                scopes.setdefault(key, set()).add(name)
        else:
            scopes.setdefault("Global", set()).add(name)

    ordered: list[tuple[str, list[str]]] = []
    if "Global" in scopes:
        ordered.append(("Global", sorted(scopes.pop("Global"))))

    for guild_id in GUILD_IDS:
        key = f"Guild {guild_id}"
        names = sorted(scopes.pop(key, set()))
        ordered.append((key, names))

    for key in sorted(scopes):
        ordered.append((key, sorted(scopes[key])))

    return ordered


def _format_guild_list(guild_ids: Sequence[int]) -> str:
    return ", ".join(str(gid) for gid in guild_ids) if guild_ids else "none"


async def main(args: argparse.Namespace) -> None:
    token = os.getenv("TOKEN")
    if not token:
        raise SystemExit("Missing TOKEN in configuration (.config)")

    global _bot_token, _force_sync, _need_sync_global, _need_sync_guild, GUILD_IDS, GUILD_ID
    _bot_token = token
    _force_sync = bool(getattr(args, "force_sync", False))

    if os.getenv("BOT_USE_ENV") != "1":
        print("[config] .env fallback disabled; supply PDC with each command.")
    else:
        env_display = os.getenv("BOT_ENV_PATH") or ".env"
        print(f"[config] Using .env fallback from {env_display}")

    accessible_guild_ids = await ensure_guild_membership(token, GUILD_IDS)
    if not accessible_guild_ids:
        print("[warn] Bot is not a member of any configured guilds; exiting.", flush=True)
        return

    if accessible_guild_ids != GUILD_IDS:
        GUILD_IDS = accessible_guild_ids
        GUILD_ID = GUILD_IDS[0]
        if AUTO_SYNC_DEBUG_GUILD:
            bot.debug_guilds = list(GUILD_IDS)

    await load_extensions()
    expected_global, expected_guild = await prepare_expected_commands()

    missing_global: set[str] = set()
    missing_guild_by_id: dict[int, set[str]] = {}

    for guild_id in GUILD_IDS:
        try:
            existing_global, existing_guild = await fetch_command_sets(token, guild_id)
        except Exception as exc:
            print(f"[warn] Unable to fetch existing command sets for guild {guild_id}: {exc}")
            existing_global, existing_guild = set(), set()

        missing_global |= expected_global - existing_global
        guild_missing = expected_guild - existing_guild
        if guild_missing:
            missing_guild_by_id[guild_id] = guild_missing

    aggregated_missing_guild = set().union(*missing_guild_by_id.values()) if missing_guild_by_id else set()

    _need_sync_global = _force_sync or bool(missing_global)
    _need_sync_guild = _force_sync or bool(aggregated_missing_guild)

    if AUTO_SYNC_DEBUG_GUILD and not _force_sync:
        guild_list_display = _format_guild_list(GUILD_IDS)
        print(f"[sync] Auto guild sync enabled for guilds [{guild_list_display}]; relying on Pycord debug_guilds.")
        if missing_guild_by_id:
            for guild_id, names in sorted(missing_guild_by_id.items()):
                print(f"[sync] Waiting for guild {guild_id} commands: {sorted(names)}")
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
            if missing_guild_by_id:
                for guild_id, names in sorted(missing_guild_by_id.items()):
                    print(f"[sync] Guild {guild_id} commands missing: {sorted(names)}")
            else:
                guild_list_display = _format_guild_list(GUILD_IDS)
                print(f"[sync] Guild commands will be force-synced for guilds [{guild_list_display}].")
        else:
            guild_list_display = _format_guild_list(GUILD_IDS)
            print(
                f"[sync] Guild commands already present for guilds [{guild_list_display}]; "
                "will skip sync unless forced."
            )

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
    parser.add_argument(
        "--env",
        dest="env_path",
        nargs="?",
        const="__DEFAULT__",
        metavar="PATH",
        help="Load credentials from a .env file (optional PATH). Without this flag, provide PDC via command options.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\nShutting down gracefully…")
