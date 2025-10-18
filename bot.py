import discord
import os
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

activity = discord.Activity(type=discord.ActivityType.watching,
                            name="🎮 dev by groriz11 | /tutorial ")

cogs_list = ["misc", "psn", "psprices"]


class PSNBot(commands.Bot):
    async def setup_hook(self) -> None:
        for cog in cogs_list:
            await self.load_extension(f"cogs.{cog}")
        await self.sync_commands()


bot = PSNBot(
    command_prefix=commands.when_mentioned,
    activity=activity,
    intents=intents,
    debug_guilds=[361510651375648771]
)


@bot.event
async def on_ready() -> None:
    print(f"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                                  🎮 PSNTOOLBOT 🎮                                     ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  🤖 PSNToolBot is ready!                                                              ║
║  🔗 Invite: https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot
║  🎮 Original creator: https://github.com/groriz11                                    ║
║                                                                                       ║
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
            color=0x2c3e50)
        embed.set_footer(text="💻 Created by groriz11")
        await message.channel.send(embed=embed)

    await bot.process_commands(message)


if __name__ == "__main__":
    print("Starting bot...")
    bot.run(os.getenv("TOKEN"))
