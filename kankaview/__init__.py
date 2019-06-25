from .kankaview import KankaView


def setup(bot):
    kv = KankaView()
    bot.add_cog(kv)
