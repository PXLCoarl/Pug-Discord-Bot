from discord.ext import commands

class sync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        print("sync cog loaded")
        
    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx) -> None:
        fmt = await ctx.bot.tree.sync(guild=ctx.guild)
        await ctx.message.delete()
        await ctx.send(
            f"Synced {len(fmt)} commands to the current guild",
            ephemeral=True
            )
        return
    
async def setup(bot):
    await bot.add_cog(sync(bot))