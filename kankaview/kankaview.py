from discord.ext import commands
import discord
import aiohttp
import os
from .utils.dataIO import dataIO

DEFAULT_SETTINGS = {'token': None}


class KankaView:
    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/kankaview/settings.json')

    @commands.group(name='kanka', pass_context=True)
    async def kanka(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @commands.group(name='kankaset', pass_context=True)
    async def kankset(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @commands.command(name='token')
    async def set_token(self, token: str):
        """Set API token ('Personal Access Token'). Do not included 'Bearer '.
        Be aware that this token is stored in plaintext by the bot."""
        if token[:7] != 'Bearer ':
            token = 'Bearer ' + token
        self.settings['token'] = token
        await self.bot.say('API token set.')

    @commands.command(name='reset')
    async def restore_default_settings(self):
        """Return to default settings and forget API key."""
        self.settings = DEFAULT_SETTINGS
        await self.bot.say('API token cleared and settings reset to default.')



def check_folder():
    if not os.path.exists('data/kankaview'):
        print('Creating data/kankaview folder...')
        os.makedirs('data/kankaview')


def check_file():
    file = 'data/mafia/settings.json'
    if not dataIO.is_valid_json(file):
        print('Creating default settings.json...')
        dataIO.save_json(file, DEFAULT_SETTINGS)


def setup(bot):
    check_folder()
    check_file()
    kankaview = KankaView(bot)
    bot.add_cog(kankaview)
