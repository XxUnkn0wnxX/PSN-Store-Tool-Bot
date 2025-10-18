import os
import traceback
import asyncio
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


bot = commands.Bot(
    command_prefix=commands.when_mentioned,
    activity=activity,
    intents=intents,
    debug_guilds=[GUILD_ID],
)


async def load_extensions() -> None:
    print("[setup] loading cogs…")
    for name in COGS:
        loaded = False
        for mod_path in (f"cogs.{name}", name):
            try:
                bot.load_extension(mod_path)
                print(f"[cog] loaded {mod_path}")
                loaded = True
                break
            except ModuleNotFoundError:
                continue
            except Exception:
                print(f"[cog] ERROR loading {mod_path}:\n{traceback.format_exc()}")
                break
        if not loaded:
            print(f"[cog] FAILED to load {name} (tried cogs.{name} and {name})")

    print("[setup] finished loading cogs")


@bot.event
async def on_ready() -> None:
    print(f"[lib] Pycord version: {discord.__version__}")
    print(f"[lib] module path  : {discord.__file__}")
    print(f"[ready] Logged in as {bot.user} ({bot.user.id})")
    print(f"[ready] Commands   : {[c.qualified_name for c in bot.application_commands]}")
    print(f"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                                  🎮 PSNTOOLBOT 🎮                                     ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║  🤖 PSNToolBot is ready!                                                              ║
║  🔗 Invite: https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&scope=bot%20applications.commands&permissions=8&integration_type=0
║  🎮 Original creator: https://github.com/groriz11                                     ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
    """)


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
    await load_extensions()
    print("Starting bot...")
    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
