from socket import timeout
import discord
from discord.ext import commands
from discord import SelectOption, app_commands, ButtonStyle
from discord.ui import Button, View, Select
from Processors.EmbedBuilder import EmbedBuilder
import asyncio
import sqlite3
import os
import requests
import json
from dotenv import load_dotenv

maps = ["de_dust2", "de_mirage", "de_vertigo", "de_nuke", "cs_italy", "de_overpass", "de_ancient", "cs_office", "de_anubis", "de_inferno"]
match_id = 0
people_in_queue = {}
queue_flag = False
conn = sqlite3.connect('database/players.db')
cursor = conn.cursor()

class VoteView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VoteSelect())
        
class VoteSelect(Select):
    def __init__(self):
        global maps
        options=[SelectOption(label=cs_map, description=f'Map {cs_map}') for cs_map in maps]
        super().__init__(placeholder='Ban a Map', max_values=1, min_values=1, options=options)
        



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
                await interaction.response.defer()
                await StartQueue.on_queue_full(interaction=interaction)


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




    async def on_queue_full(interaction: discord.Interaction):
        await interaction.edit_original_response(view=VoteView())
        player_data = []
        global people_in_queue
        global match_id
        for discord_id in people_in_queue:
            cursor.execute("SELECT steam_id64 FROM user_links WHERE discord_id = ?", (discord_id,))
            result = cursor.fetchone()
            steam_id = result[0]
            load_dotenv()
            FACEIT_TOKEN = os.getenv("FACEIT_TOKEN")
            header = {
                "Authorization": f"Bearer {FACEIT_TOKEN}",
                "Accept": "application/json"
                }
            response = requests.get(f"https://open.faceit.com/data/v4/players?game=cs2&game_player_id={steam_id}", headers=header)
            if response.status_code == 200:
                data = response.json()
                faceit_elo = data.get("games", {}).get("cs2", {}).get("faceit_elo", 800)
            else: faceit_elo = 800
            player_data.append((discord_id, faceit_elo))
            

        sorted_players = sorted(player_data, key=lambda x: x[1])
            
        team1 = []
        team2 = []
        for i, (discord_id, faceit_elo) in enumerate(sorted_players):
            if i % 2 == 0:
                team1.append((discord_id, faceit_elo))
            else:
                team2.append((discord_id, faceit_elo))
                

        team1_members = [interaction.guild.get_member(int(discord_id)) for discord_id, _ in team1 if interaction.guild.get_member(int(discord_id))]
        team2_members = [interaction.guild.get_member(int(discord_id)) for discord_id, _ in team2 if interaction.guild.get_member(int(discord_id))]
        people_in_queue = {}        

        original_msg = await interaction.message.fetch()
        embed = original_msg.embeds[0]
        embed.title = 'Match'
        embed.description = 'The teams are as followed:'
        embed.set_field_at(0, name=f'Team {team1_members[0]}', value='\n'.join([f'{member.name}' for member in team1_members]), inline=True)
        embed.add_field(name=f'Team {team2_members[0]}', value='\n'.join([f'{member.name}' for member in team2_members]), inline=True)
        await interaction.edit_original_response(embed=embed, view=VoteView)
        match_id += 1        

        team1_formatted = {StartQueue.get_steam_id(discord_id): interaction.guild.get_member(int(discord_id)).name for discord_id, _ in team1}
        team2_formatted = {StartQueue.get_steam_id(discord_id): interaction.guild.get_member(int(discord_id)).name for discord_id, _ in team2}
        
        match_data = {
            "matchid": f"{match_id}",
            "team1": {"name": f"Team_{team1_members[0]}", "players": dict(team1_formatted)},
            "team2": {"name": f"Team_{team2_members[0]}", "players": dict(team2_formatted)},
            "num_maps": 1,
            "maplist": ["de_inferno"],
            "map_sides": ["team1_ct", "team2_t", "knife"],
            "spectators": {"players": {}},
            "clinch_series": True,
            "min_players_to_ready": len(player_data),
            "cvars": {"hostname": f"Munich eSports Pug: Team {team1_members[0]} vs Team {team2_members[0]}", "mp_friendlyfire": "0"}
        }
        with open(f'./api/match_{match_id}.json', 'w') as file:
            json.dump(match_data, file, indent=4)
        
        

        
            
    async def check_queue_status(self):
        while True:
            asyncio.sleep(5)
            if len(people_in_queue) >= 10:
                await StartQueue.on_queue_full()
        
                
        



async def setup(bot):
    await bot.add_cog(StartQueue(bot), guilds=[discord.Object(id=1019608824023371866), discord.Object(id=841127630564622366)])
