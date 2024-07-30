from .kankaview import KankaView


async def setup(bot):
    kv = KankaView(bot)
    await bot.add_cog(kv)
