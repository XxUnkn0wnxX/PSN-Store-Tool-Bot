import discord
import os
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()

activity = discord.Activity(type=discord.ActivityType.watching,
                            name="🎮 dev by groriz11 | /tutorial ")
bot = commands.Bot(command_prefix="!", activity=activity)


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


cogs_list = ["misc", "psn", "psprices"]

if __name__ == "__main__":
    for cog in cogs_list:
        bot.load_extension(f"cogs.{cog}")

    print("Starting bot...")
    bot.run(os.getenv("TOKEN"))
