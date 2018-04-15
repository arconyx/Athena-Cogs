from discord.ext import commands
import os
from .utils.dataIO import dataIO
from uuid import uuid4 as uuid
import asyncio
from random import shuffle


class Player:
    def __init__(self, discord_user):
        self.user = discord_user
        self.role = None
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
        self.players = self.assign_roles()

    def assign_roles(self):
        total_players, unassigned = len(self.players)
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
        players = shuffle(self.players)
        index = 0
        for role, amount in self.players_per_role.items():
            while amount > 0 and index < total_players:
                players[index].role = role
                index += 1
                amount -= 1
        return players


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
        self.start_game(self.game)

        # TODO: Set minimum no of players

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

    async def start_game(self, game):
        """Closes lobby and begins game. What else did you expect?"""
        game.start()
        await self.bot.say('Game started.')
        # Wait, if all it does is this, why is is seperate?
        # Good question.
        # I suspect I will want to do more stuff here later

    # Command group to set settings
    @commands.group(pass_context=True, name='mafiaset')
    async def _mafiaset(self, ctx):
        """Edit mafia settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_mafiaset.command(name='lobbytimeout')
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
