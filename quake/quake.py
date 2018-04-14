from discord.ext import commands
import discord

# This cog is only possible because of GeoNet.

try:
    import requests
except:
    requests = False

class Quake:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def quake(self, context, mmi: int = 4):
        """Polls GeoNet for their latest quake and publishes the info"""
        if mmi < -1 or mmi > 8:
            await self.bot.say('The Modified Mercalli Intensity given must be between -1 and 8 inclusive. Defaults to 4 when left blank.')
        else:
            # Call the GeoNet API https://api.geonet.org.nz
            # Returns quakes with MMI >= 4 in the New Zealand region during the last 365 days up to a maximum of 100 quakes.
            recentquakes = requests.get('https://api.geonet.org.nz/quake', params={'MMI':mmi}, headers={'accept':'application/vnd.geo+json;version=2'}, timeout=3)
            # Grabs the most recent of said quakes
            shake = recentquakes.json()['features'][0]['properties']

            em = discord.Embed(title=shake['publicID'], description='Most recent quake with MMI>={} on GeoNet'.format(mmi), url='https://www.geonet.org.nz/quakes/region/newzealand/{}'.format(shake['publicID']), colour=discord.Color.orange())
            em.add_field(name='Magnitude', value=shake['magnitude'])
            em.add_field(name='Time', value=shake['time'])
            em.add_field(name='Quality', value=shake['quality'])
            em.add_field(name='Location', value=shake['locality'])
            em.add_field(name='MMI', value=shake['mmi'])
            em.add_field(name='Depth', value=str(shake['depth'])+' km')

            await self.bot.say(embed=em)

def setup(bot):
    if requests is False:
        raise RuntimeError('requests is not installed. Do \'pip3 install requests\' to use this cog.')
    else:
        n = Quake(bot)
        bot.add_cog(n)
