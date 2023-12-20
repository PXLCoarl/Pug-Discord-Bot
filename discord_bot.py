from dotenv import load_dotenv
import os
import discord
from discord.ext import commands

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

class PugBot(commands.Bot):
    def __init__(self, intents):
        super().__init__(command_prefix="#", intents=intents)

    async def on_ready(self):
        async def load():
            for filename in os.listdir("./cogs"):
                if filename.endswith("py"):
                    await self.load_extension(f"cogs.{filename[:-3]}")
        print(f'Started bot as {self.user}')
        await load()

bot = PugBot(intents=discord.Intents.all())
bot.run(token=DISCORD_TOKEN)
