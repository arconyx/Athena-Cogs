from discord.ext import commands
import os
from .utils.dataIO import dataIO
from uuid import uuid4 as uuid
import asyncio
from random import shuffle


class Player:
    def __init__(self, discord_user):
        self.user = discord_user
        self.role = Role()
        self.name = self.user.name


class Role:
    def __init__(self):
        self.name = 'GenericRole'
        self.percentage = '0'


class Town(Role):
    def __init__(self):
        super(Town, self).__init__()
        self.name = 'Town'
        self.percentage = 0.8
        self.minimum = 0


class Mafiaso(Role):
    def __init__(self):
        super(Mafiaso, self).__init__()
        self.name = 'Mafiaso'
        self.percentage = 0.2
        self.minimum = 1


class Detective(Role):
    def __init__(self):
        super(Detective, self).__init__()
        self.name = 'Detective'
        self.percentage = 0.1
        self.minimum = 1


class Game:
    def __init__(self, game_ID):
        self.id = game_ID
        self.players = []
        self.lobbyOpen = True
        self.roles = [Town(), Mafiaso()]
        self.players_per_role = {}

    def add_player(self, discord_user):
        if discord_user in self.players:
            raise ValueError('Player is already in list.')
        else:
            self.players.append(Player(discord_user))

    def start(self):
        self.lobbyOpen = False
        self.assign_roles()

    def assign_roles(self):
        total_players = unassigned = len(self.players)
        for role in self.roles:
            if isinstance(role, Town):
                town = role
            else:
                amount = round(total_players * role.percentage)
                if amount < role.minimum:
                    amount = role.minimum
                self.players_per_role[role] = amount
                unassigned -= amount
        self.players_per_role[town] = unassigned
        shuffle(self.players)
        index = 0
        for role, amount in self.players_per_role.items():
            while amount > 0 and index < total_players:
                self.players[index].role = role
                index += 1
                amount -= 1


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
    @_mafia.command(name="players", pass_context=True)
    async def list_players(self, ctx):
        """Lists all players in the game by name."""
        clean = []
        for user in self.game.players:
            clean.append(user.name)
        player_lst = ', '.join(clean)
        await self.bot.say('**Current Mafia Players:**\n{}'.format(player_lst))

    # For testing only
    @_mafia.command(name="roles", pass_context=True, no_PM=True)
    async def print_roles(self, ctx):
        """Lists the name and role of all players in the game."""
        clean = []
        for user in self.game.players:
            clean.append(user.name + ' (' + user.role.name + ')')
        player_lst = ', '.join(clean)
        await self.bot.say('**Current Mafia Players:**\n{}'.format(player_lst))

    # Commands to start game
    @_mafia.command(pass_context=True, no_PM=True)
    async def create(self, ctx):
        """Creates a new game of mafia"""
        self.game = Game(uuid)
        await self.bot.say('@here Mafia game starting! Use `!mafia join` to'
                           ' join the lobby.')
        await asyncio.sleep(self.settings['LOBBY_DURATION'])
        if len(self.game.players) >= self.settings['MIN_PLAYERS']:
            self.game.start()
            for player in self.game.players:
                await self.bot.send_message(player.user,
                                            'You are a {}.'
                                            .format(player.role.name.lower()))
            await self.bot.say('Game started.')
        else:
            await self.bot.say('Unable to start game.'
                               'A minimum of {} players are needed.'
                               .format(self.settings['MIN_PLAYERS']))

    @_mafia.command(pass_context=True)
    async def join(self, ctx):
        """Join the mafia lobby"""
        player = ctx.message.author
        try:
            self.game.add_player(player)
        except ValueError:
            'Player {} already in game'.format(player.name)
            return
        await self.bot.say('{} added to players.'.format(player.name))

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

    @_mafiaset.command(name='min')
    async def min_players(self, time: int):
        """Minimum number of players to start game."""
        self.settings['MIN_PLAYERS'] = time
        dataIO.save_json('data/mafia/settings.json', self.settings)
        await self.bot.say('Minimum players updated.')


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
    data['LOBBY_DURATION'] = 60
    data['MIN_PLAYERS'] = 4
    f = 'data/mafia/settings.json'
    if not dataIO.is_valid_json(f):
        print('Creating default settings.json...')
        dataIO.save_json(f, data)
