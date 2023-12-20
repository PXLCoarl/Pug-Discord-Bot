from socket import timeout
import discord
from discord.ext import commands
from discord import app_commands, ButtonStyle
from discord.ui import Button, View
from Processors.EmbedBuilder import EmbedBuilder
import asyncio
import sqlite3

maps = ["de_dust2", "de_mirage", "de_vertigo", "de_nuke", "cs_italy", "de_overpass", "de_ancient", "cs_office", "de_anubis", "de_inferno"]
match_id = 0
people_in_queue = {}
queue_flag = False
conn = sqlite3.connect('database/players.db')
cursor = conn.cursor()

class QueueButton(Button):
    def __init__(self, label, style, id):
        super().__init__(label=label, style=style)
        self.id = id
        
    async def callback(self, interaction: discord.Interaction):
        if self.id == 0:
            await interaction.response.defer()
            
            user_name = interaction.user.name   

            cursor.execute("SELECT steam_id64 FROM user_links WHERE discord_id = ?", (interaction.user.id,))
            result = cursor.fetchone()
            if result:
                discord_id = interaction.user.id
                if interaction.user.id not in people_in_queue:
                    people_in_queue[discord_id] = user_name
                    #handle Join


                original_msg = await interaction.message.fetch()
                embed = original_msg.embeds[0]
                queue_names = '\n'.join(people_in_queue.values())
                embed.set_field_at(0, name='People in Queue:', value=queue_names)
                await interaction.edit_original_response(embed=embed)
            else:
                await interaction.followup.send("you need to link your steam account to join the queue! Use /steam", ephemeral=True)
        elif self.id == 1:
            await interaction.response.defer()
            #handle Leave
            user_name = interaction.user.name
            
            if interaction.user.id in people_in_queue:
                del people_in_queue[interaction.user.id]
                
            original_msg = await interaction.message.fetch()
            embed = original_msg.embeds[0]
            queue_names = '\n'.join(people_in_queue.values())
            embed.set_field_at(0, name='People in Queue:', value=queue_names)
            await interaction.edit_original_response(embed=embed)
        elif self.id == 2:
            if len(people_in_queue) < 2:
                # Queue is empty, handle accordingly
                await interaction.response.send_message("Need at least 2 people in queue!", ephemeral=True)
            #handle force pug start
            else:
                from Processors.QueuePop import QueuePop
                await interaction.response.defer()
                #queue_pop = QueuePop(interaction, people_in_queue, match_id=1)
                #await queue_pop.on_queue_full()
                await QueuePop.on_queue_full(interaction=interaction, people_in_queue=people_in_queue, match_id=1)


        else:
            print("something went wrong")
        
class QueueView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(QueueButton(label='Join', style=ButtonStyle.green,id= 0))
        self.add_item(QueueButton(label='Leave', style=ButtonStyle.red,id= 1))
        self.add_item(QueueButton(label='Force Start', style=ButtonStyle.grey, id=2))
        


class StartQueue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pug_embed = None

    @commands.Cog.listener()
    async def on_ready(self):
        print('StartQueue cog loaded.')
        
    @app_commands.command(name="pug", description="start a pug queue")
    @app_commands.checks.has_role("Pug Leader")
    async def pug(self, interaction: discord.Interaction):
        
        embed = EmbedBuilder.build_embed(title='PUG Queue', desc='To join the queue press the button below.\nMake sure you linked your Steam Account!',username='Started')
        embed.add_field(
            name='People in Queue:',
            value='',
            inline=False
            )
        await interaction.response.send_message(embed=embed, view=QueueView())
        
    @pug.error
    async def pug_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        #if isinstance(error, app_commands.MissingAnyRole):
        await interaction.response.send_message(str(error), ephemeral=True)
    
    def get_steam_id(discord_id):
        cursor.execute("SELECT steam_id64 FROM user_links WHERE discord_id = ?", (discord_id,))
        result = cursor.fetchone()
        return result[0] if result else None
        
            
    async def check_queue_status(self):
        while True:
            asyncio.sleep(5)
            if len(people_in_queue) >= 10:
                await StartQueue.on_queue_full()
        
                
        



async def setup(bot):
    await bot.add_cog(StartQueue(bot), guilds=[discord.Object(id=1019608824023371866), discord.Object(id=841127630564622366)])
