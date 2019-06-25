from .quake import Quake


def setup(bot):
    n = Quake()
    bot.add_cog(n)
