import aiohttp
from redbot.core import commands

# Unoffical Discord intergration for the hilarious http://inspirobot.me/


class Inspire(commands.Cog):
    @commands.command()
    async def inspire(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get("http://inspirobot.me/api?generate=true") as quote:
                await ctx.send(await quote.text())
