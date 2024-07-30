from .inspire import Inspire


async def setup(bot):
    i = Inspire()
    await bot.add_cog(i)
