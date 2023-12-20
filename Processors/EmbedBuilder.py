import discord
from datetime import datetime

class EmbedBuilder:
    
    @staticmethod
    def build_embed(title, desc, username):
        url = "https://steamuserimages-a.akamaihd.net/ugc/791989302980590586/76AA157EF3CF72CF22EA2F3C94475F638DE2E459/?imw=512&&ima=fit&impolicy=Letterbox&imcolor=%23000000&letterbox=false"
        color = discord.Color.blurple()
            
        time = datetime.now()

        embed = discord.Embed(
            title=title,
            description=desc,
            color=color,
            timestamp=time
            )
        embed.set_footer(
            text=username
            )
        embed.set_author(
            icon_url=url,
            name="Pug Bot"
            )
        return embed