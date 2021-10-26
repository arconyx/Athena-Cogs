from redbot.core import commands
import discord
import aiohttp
from dateutil import parser as dtparse

# This cog is only possible because of GeoNet (https://www.geonet.org.nz).


class Quake(commands.Cog):
    @commands.command()
    async def quake(self, ctx, mmi: int = 3):
        """Polls GeoNet for their latest quake and publishes the info"""
        if mmi < -1 or mmi > 8:
            await ctx.send('The Modified Mercalli Intensity given must be'
                           'between -1 and 8 inclusive. Defaults to 3 when'
                           'left blank.')
        else:
            # Call the GeoNet API https://api.geonet.org.nz
            # Returns quakes with MMI >= 3 in the New Zealand region during the
            # last 365 days up to a maximum of 100 quakes.
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.geonet.org.nz/quake',
                                       params={'MMI': mmi},
                                       headers={
                                           'accept': 'application/vnd.geo+json;version=2',
                                           'Accept-Encoding': 'gzip'}
                                       ) as recentquakes:
                    # Convert to json
                    jsonified = await recentquakes.json()

                    # Grabs the most recent quake that hasn't been deleted
                    # Possibly quality levels are best, preliminary, automatic, deleted
                    shake = {'quality': 'deleted'}
                    i = 0
                    while shake['quality'] == 'deleted':
                        shake = jsonified['features'][i]['properties']
                        i += 1

                    # Get a timestamp for use with Discord time formatting
                    timestamp = round(dtparse.parse(shake['time']).timestamp())

                    # Create the embed
                    em = discord.Embed(title=shake['publicID'],
                                       description='Most recent quake with MMI>={} '
                                       'on GeoNet'.format(mmi),
                                       url='https://www.geonet.org.nz/quakes/'
                                       'region/newzealand/{}'.format(
                                           shake['publicID']),
                                       colour=discord.Color.orange())
                    em.add_field(name='Magnitude', value=shake['magnitude'])
                    em.add_field(name='Time', value=f'<t:{timestamp}:R>')
                    em.add_field(name='Quality', value=shake['quality'])
                    em.add_field(name='Location', value=shake['locality'])
                    em.add_field(name='MMI', value=shake['mmi'])
                    em.add_field(name='Depth', value=str(shake['depth'])+' km')

                    await ctx.send(embed=em)
