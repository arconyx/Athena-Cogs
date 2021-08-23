from .kankaview import KankaView


def setup(bot):
    kv = KankaView(bot)
    bot.add_cog(kv)
