from venv import create
import discord
import sqlite3
import requests
import itertools
import os
import json
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpVariable, LpInteger
from dotenv import load_dotenv
from discord import SelectOption
from discord.ui import View, Select
from rcon.source import Client

maps = ["de_dust2", "de_mirage", "de_vertigo", "de_nuke", "cs_italy", "de_overpass", "de_ancient", "cs_office", "de_anubis", "de_inferno"]
queue_flag = False

class EmptyView(View):
    def __init__(self):
        super().__init__(timeout=None)


class VoteView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VoteSelect())
        
class VoteSelect(Select):
    def __init__(self):
        global maps
        options=[SelectOption(label=cs_map, description=f'Map {cs_map}') for cs_map in maps]
        super().__init__(placeholder='Ban a Map', max_values=1, min_values=1, options=options)
        


class QueuePop():
    async def on_queue_full(interaction: discord.Interaction, people_in_queue, match_id):
        await interaction.edit_original_response(view=EmptyView())
        team1_members, team2_members, team1_formatted, team2_formatted, avg_elo_team1, avg_elo_team2 = await CreateMatch.create_match(people_in_queue, interaction)
        
        original_msg = await interaction.message.fetch()
        embed = original_msg.embeds[0]
        embed.title = 'Match'
        embed.description = 'The teams are as followed:'
        embed.set_field_at(0, name=f'Team {team1_members[0]}', value=f'avg elo: {avg_elo_team1}\n' + '\n'.join([f'{member.name}' for member in team1_members]), inline=True)
        embed.add_field(name=f'Team {team2_members[0]}', value=f'avg_elo: {avg_elo_team2}\n' + '\n'.join([f'{member.name}' for member in team2_members]), inline=True)
        # todo:
        # - somehow handle match_id (dunno how yet, or if i even should)
        # - make highest elo player captain
        # - make map vote available for captains
        # - create match.json after map veto (already done, just need to implement variable for maps)
        # - push match.json onto free server using rcon (function already done, just needs to be called)
        # - far future: maybe implement choice between bo1, bo3 and bo3?
        # - implement multiple map pools (eg: active duty, all cs2 maps, list of workshop maps usw... (maybe make map pool votable by all players?))
        
        
        await interaction.edit_original_response(embed=embed, view=VoteView())
        

        
        
        # maybe shouldnt even be in here but in a separate def called by QueuePop:

        # match_file = await CreateMatch.create_match_json(team1_members, team2_members, team1_formatted, team2_formatted, player_data, match_id)
        # RconClient.create_rcon_client(server_id=1, match_file=match_file)




class RconClient:
    def load_server_data(server_id):
        with open('servers.json', 'r') as file:
            data = json.load(file)
        #server_data = next((server for server in data["servers"] if server["server_id"] == self.server_id), None)
        for server in data["servers"]:
            if server["server_id"] == server_id:
                server_data = server
                break
        if server_data:
            return server_data["server_ip"],server_data["rcon_port"],server_data["rcon_password"]
        else:
            return None

    def create_rcon_client(server_id, match_file):
        rcon_ip, rcon_port, rcon_password = RconClient.load_server_data(server_id)
        
        if rcon_ip and rcon_port and rcon_password != None:
            try:
                with Client(rcon_ip, rcon_port, passwd=rcon_password) as client:
                    response = client.run('matchzy_loadmatch_url', f'https://pugs.pxlcoarl.de/api/v1/{match_file}')
                    print(response)
            except Exception as e:
                print(f"Error creating RCON client: {e}")
                raise
        else:
            raise ValueError("Invalid server data or server not found.")


class CreateMatch():
    async def get_faceit_elo(steam_id):
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
        return faceit_elo


    def get_steam_id(discord_id):
        conn2 = sqlite3.connect('database/players.db')
        cursor = conn2.cursor()
        cursor.execute("SELECT steam_id64 FROM user_links WHERE discord_id = ?", (discord_id,))
        result = cursor.fetchone()
        conn2.close()        
        return result[0] if result else None
    
    async def matchmaking(player_data):
        # Batshit insane matchmaking algorithm
        num_players = len(player_data)
        num_teams = 2
        players_per_team = num_players // num_teams
        # Create LP problem
        prob = LpProblem("TeamBalancing", LpMinimize)
        # Decision variables
        x = {(i, j): LpVariable(f"x_{i}_{j}", 0, 1, LpInteger) for i in range(num_players) for j in range(num_teams)}
        z = LpVariable("z", 0)
        # Objective function
        prob += z, "Objective"
        # Constraints
        for i in range(num_players):
            prob += lpSum(x[i, j] for j in range(num_teams)) <= 1  # Each player assigned to only one team
        for j in range(num_teams):
            prob += lpSum(x[i, j] for i in range(num_players)) == players_per_team  # Each team should ideally have 5 players
        for j in range(num_teams):
            prob += (lpSum(player_data[i][1] * x[i, j] for i in range(num_players)) / players_per_team) - z <= z  # Minimize the difference in average Elo
        # Solve the problem
        prob.solve()
        # Extract results
        teams = {j: [i for i in range(num_players) if x[i, j].value() == 1] for j in range(num_teams)}
        avg_elo = {j: sum(player_data[i][1] for i in teams[j]) / players_per_team for j in range(num_teams)}

        return teams, avg_elo

    async def create_teams(interaction: discord.Interaction, player_data):
        teams, avg_elo = await CreateMatch.matchmaking(player_data)
                
        team1_members = [interaction.guild.get_member(int(player_data[player_index][0])) for player_index in teams[0]]
        team2_members = [interaction.guild.get_member(int(player_data[player_index][0])) for player_index in teams[1]]

        team1_formatted = {CreateMatch.get_steam_id(player_data[player_index][0]): interaction.guild.get_member(int(player_data[player_index][0])).name for player_index in teams[0]}
        team2_formatted = {CreateMatch.get_steam_id(player_data[player_index][0]): interaction.guild.get_member(int(player_data[player_index][0])).name for player_index in teams[1]}
        
        avg_elo_team1 = avg_elo[0]
        avg_elo_team2 = avg_elo[1]
        
        return team1_members, team2_members, team1_formatted, team2_formatted, avg_elo_team1, avg_elo_team2


  
    async def create_match_json(team1_members, team2_members, team1_formatted, team2_formatted, player_data, match_id):
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
            
        return f'match_{match_id}.json'
    



    async def create_match(people_in_queue, interaction):
        player_data = []
        conn = sqlite3.connect('database/players.db')
        cursor = conn.cursor()
        for discord_id in people_in_queue:
            cursor.execute("SELECT steam_id64 FROM user_links WHERE discord_id = ?", (discord_id,))
            result = cursor.fetchone()
            steam_id = result[0]
            faceit_elo = await CreateMatch.get_faceit_elo(steam_id)
            player_data.append((discord_id, faceit_elo))
        conn.close()
        people_in_queue.clear() #Make room for a new queue     
        
        team1_members, team2_members, team1_formatted, team2_formatted, avg_elo_team1, avg_elo_team2 = await CreateMatch.create_teams(interaction,player_data)
        return team1_members, team2_members, team1_formatted, team2_formatted, avg_elo_team1, avg_elo_team2
        
        

        
        