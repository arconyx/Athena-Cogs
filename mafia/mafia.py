import discord
from discord.ext import commands
import os
from .utils.dataIO import dataIO
from uuid import uuid4 as uuid
import asyncio

class Game:
    def __init__(self, game_ID):
        self.id = game_ID
        self.players = []

    def add_player(self, discord_user):
        if discord_user in self.players:
            raise ValueError('Player already in list.')
        else:
            self.players.append(Player(discord_user))

    def get_players(self):
        return self.players

class Player:
    def __init__(self, discord_user):
        self.user = discord_user
        self.role = None
        self.name = self.user.name

    def get_name(self):
        return self.name

class MafiaBoss:
    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/mafia/settings.json')

    # Game commands group
    @commands.group(name="mafia", pass_context=True)
    async def _mafia(self, ctx):
        """This cog runs the mafia."""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    # Utility/general commands
    @_mafia.command(name="list", pass_context=True)
    async def list_players(self, ctx):
        clean = []
        for user in self.game.players.get_players():
            clean.append(user.getname())
        player_list = ', '.join(clean)
        await self.bot.say('**Current Players:**\n{}'.format(player_list))

    # Commands to start game
    @_mafia.command(pass_context=True, no_PM=True)
    async def create(self, ctx):
        """Creates a new game of mafia"""
        self.game = Game(uuid)
        await self.bot.say('@here Mafia game starting! Use `!mafia join` to join the lobby.')
        await asyncio.sleep(self.settings['LOBBY_DURATION'])
        start_game(self.game)

    @_mafia.command(pass_context=True)
    async def join(self, ctx):
        """Join the mafia lobby"""
        player = ctx.message.author
        try:
            self.game.add_player(player)
        except ValueError:
            'Player {} already in game'.format(player.mention)
            return
        await self.bot.say('{} added to players.'.format(player.mention))

    # Command group to set settings
    @commands.group(pass_context=True, name='mafiaset')
    async def _mafiaset(self, ctx):
        """Edit mafia settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_mafiaset.command(name='lobby')
    async def lobby_duration(self, time: int):
        """Set time before game starts"""
        self.settings['LOBBY_DURATION'] = time
        dataIO.save_json('data/mafia/settings.json', self.settings)
        await self.bot.say('Lobby period updated.')


# Installation/Setup
def setup(bot):
    check_folder()
    check_file()
    n = MafiaBoss(bot)
    bot.add_cog(n)

def check_folder():
    if not os.path.exists('data/mafia'):
        print('Creating data/mafia folder...')
        os.makedirs('data/mafia')

def check_file():
    data = {}
    data['CHANNEL_ID'] = ''
    f = 'data/mafia/settings.json'
    if not dataIO.is_valid_json(f):
        print('Creating default settings.json...')
        dataIO.save_json(f, data)
