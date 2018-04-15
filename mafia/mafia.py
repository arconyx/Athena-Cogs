import discord
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
        self.minimum = 0
        self.players = []


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
        self.gameRunning = False
        self.isNight = False
        self.roles = [Town(), Mafiaso()]
        self.players_per_role = {}
        self.living = []
        self.mafiaVote = {}

    async def find_player(self, member):
        for player in self.game.players:
            if player.user == member:
                index = self.game.players.index(player.user)
                return player.user, index

    async def start(self):
        self.lobbyOpen = False
        await self.assign_roles()

    async def assign_roles(self):
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
                roldex = self.roles.index(role)
                self.roles[roldex].players.append(self.players[index])
                index += 1
                amount -= 1


class MafiaBoss:
    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/mafia/settings.json')

    # Interal functions
    async def role_alert(self):
        for player in self.game.players:
            role = player.role
            name = player.role.name.lower()
            if isinstance(role, Mafiaso):
                fellows = []
                for player in role.players:
                    fellows.append(player.name)
                mafia = ', '.join(fellows)
                await self.bot.send_message(player.user,
                                            'You are a {}.'
                                            .format(name))
                if fellows == '':
                    await self.bot.send_message(player.user,
                                                'You are the only mafiaso.')
                else:
                    await self.bot.send_message(player.user,
                                                'Your companions are {}.'
                                                .format(mafia))

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
        self.game = Game(uuid())
        await self.bot.say('Mafia game starting! Use `!mafia join` to'
                           ' join the lobby.')
        await asyncio.sleep(self.settings['LOBBY_DURATION'])
        if len(self.game.players) < self.settings['MIN_PLAYERS']:
            # This should do more, like close the lobby or something
            await self.bot.say('Unable to start game.'
                               ' A minimum of {} players are needed.'
                               .format(self.settings['MIN_PLAYERS']))
            return
        await self.bot.say('Game started.')
        await self.game.start()
        await self.role_alert()
#        await self.gameLoop(ctx.message.channel)

    @_mafia.command(pass_context=True)
    async def join(self, ctx):
        """Join the mafia lobby"""
        player = ctx.message.author
        for person in self.game.players:
            if person.user == player:
                await self.bot.say('Player {} already in game'
                                   .format(player.name))
                break
        else:
            self.game.players.append(Player(player))
            await self.bot.say('{} added to players.'.format(player.name))

    # Acutal game running stuff
#    async def gameLoop(self, channel):
        self.game.living = self.game.players

    async def night(self):
        self.bot.send_message(self.channel, 'Night has fallen. PM me actions.')
        self.game.isNight = True
        await asyncio.sleep(self.settings['ROUND_LENGTH'])

    # Commands for game actions
    @_mafia.command(pass_context=True)
    async def kill(self, ctx, member: discord.Member):
        player = self.game.find_player(member)
        if not isinstance(player.role, Mafiaso):
            await self.bot.say('Hey, you aren\'t in the mafia!')
        elif self.game.isNight is False:
            await self.bot.say('You can only do that at night.')
        else:
            self.mafiaVote[player] += 1

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
    async def min_players(self, min: int):
        """Minimum number of players to start game."""
        self.settings['MIN_PLAYERS'] = min
        dataIO.save_json('data/mafia/settings.json', self.settings)
        await self.bot.say('Minimum players updated.')

    @_mafiaset.command(name='round')
    async def round_length(self, time: int):
        """Set the length of night/day."""
        self.settings['ROUND_LENGTH'] = time
        dataIO.save_json('data/mafia/settings.json', self.settings)
        await self.bot.say('Round Length updated.')


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
    data['ROUND_LENGTH'] = 120
    f = 'data/mafia/settings.json'
    if not dataIO.is_valid_json(f):
        print('Creating default settings.json...')
        dataIO.save_json(f, data)
