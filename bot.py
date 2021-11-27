import discord
from discord.ext import commands
import os


client = commands.Bot(command_prefix=".", help_command=commands.MinimalHelpCommand())

@client.event
async def on_ready():
    print("Bot is ready.")

for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        client.load_extension(f"cogs.{filename[:-3]}")
        print(filename, "cog loaded.")

client.run(TOKEN)
