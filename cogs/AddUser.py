import discord
from discord.ext import commands
from discord import app_commands
from Processors.EmbedBuilder import EmbedBuilder
import re
import requests
from xml.etree import ElementTree as ET
import sqlite3


class AddUser(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('AddUser cog loaded.')
        
    @staticmethod
    def get_steam_id64_from_custom_url(custom_url):
        api_url = f'https://steamcommunity.com/id/{custom_url}/?xml=1'
        
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            xml_data = ET.fromstring(response.text)
            steam_id64 = xml_data.find('.//steamID64').text
            return steam_id64
        except requests.RequestException as e:
            print(f"Error retrieving SteamID64 for custom URL: {e}")
            return None

    @staticmethod
    def get_steam_id64_from_url(profile_url):
        # Define regular expressions for different profile URL formats
        patterns = [
            r'https://steamcommunity.com/profiles/(\d+)'
            ]

        # Check each pattern to find a match
        for pattern in patterns:
            match = re.search(pattern, profile_url)
            if match:
                return match.group(1)

        # If no numeric SteamID64 is found, consider the URL as a custom URL
        custom_url_match = re.search(r'https://steamcommunity.com/id/(\S+)', profile_url)
        if custom_url_match:
            custom_url = custom_url_match.group(1)
            steam_id64 = AddUser.get_steam_id64_from_custom_url(custom_url)
            return steam_id64

        # Return None if no match is found
        return None
    
    def save_user_link(self, discord_user_id, steam_id64):
        conn = sqlite3.connect('database/players.db')
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM user_links WHERE discord_id = ?", (discord_user_id,))
            user_link = cursor.fetchone()
            if user_link:
                cursor.execute("UPDATE user_links SET steam_id64 = ? WHERE discord_id = ?", (steam_id64, discord_user_id))
            else:
                # Create a new user link
                cursor.execute("INSERT INTO user_links (discord_id, steam_id64) VALUES (?, ?)", (discord_user_id, steam_id64))
            conn.commit()
        finally:
            conn.close()


    @app_commands.command(name="steam", description="set steam url")
    async def steam(self, interaction: discord.Interaction, url: str):
        steam_id64 = AddUser.get_steam_id64_from_url(url)
        username = interaction.user.name
        discord_user_id = interaction.user.id

        if steam_id64:
            # If SteamID64 is found, push it into the database:
            self.save_user_link(discord_user_id, steam_id64)

            embed = EmbedBuilder.build_embed(
                title='Success',
                desc=f'Steam Profile \"{url}\"\nhas been linked to Discord Account with the name \"{username}\"',
                username=username
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # If SteamID64 is not found, display an error message
            embed = discord.Embed(
                title='Error',
                description=f'Unable to retrieve SteamID64 for the provided Steam profile URL \"{url}\"',
                color=0xFF0000  # Red color for error
            )
            embed.set_footer(
            text=username
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AddUser(bot),guilds=[discord.Object(id=1019608824023371866), discord.Object(id=841127630564622366)])
