from .quake import Quake


async def setup(bot):
    n = Quake()
    await bot.add_cog(n)
