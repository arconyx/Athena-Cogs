from discord.ext import commands
import aiohttp

# Unoffical Discord intergration for the hilarious http://inspirobot.me/


class Inspire:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def inspire(self):
        async with aiohttp.get(
                'http://inspirobot.me/api?generate=true') as quote:
            await self.bot.say(await quote.text())


def setup(bot):
    bot.add_cog(Inspire(bot))
