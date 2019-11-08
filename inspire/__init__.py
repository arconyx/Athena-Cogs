from .inspire import Inspire


def setup(bot):
    i = Inspire()
    bot.add_cog(i)
