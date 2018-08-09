from discord.ext import commands
import discord
import aiohttp

# Unoffical Discord intergration for the hilarious InspiroBot http://inspirobot.me/

class Inspire:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def inspire(self):
        async with aiohttp.get('http://inspirobot.me/api?generate=true') as quote:
            await self.bot.say(quote)


def setup(bot):
    bot.add_cog(Inspire(bot))
