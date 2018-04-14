from discord.ext import commands
import os
from .utils.dataIO import dataIO
from uuid import uuid4 as uuid
import asyncio


class Player:
    def __init__(self, discord_user):
        self.user = discord_user
        self.role = None
        self.name = self.user.name


class Role:
    def __init__(self, name, percentage):
        self.name = name
        self.percentage = percentage
        self.amount = 0  # later set as percentage * total population


class Game:
    def __init__(self, game_ID):
        self.id = game_ID
        self.players = []
        self.lobbyOpen = True
        self.roles = [Role('Town', 0.8), Role('Mafia', 0.2)]

    def add_player(self, discord_user):
        if discord_user in self.players:
            raise ValueError('Player already in list.')
        else:
            self.players.append(Player(discord_user))

    def close_lobby(self):
        self.lobbyOpen = False

    def start(self):
        self.close_lobby()
        self.assign_roles()

    def assign_roles(self):
        total_players = len(self.players)
        divisions = {}
        for i in enumerate(self.roles):  # TODO: Improve wit variables
            self.role(i).amount = total_players * self.role(i).percentage
            divisions[self.role(i)] = total_players * self.role(i).percentage
        for player in self.players:
            for role, amount in divisions.items():
                if amount > 0:
                    player.role = role
                    divisions[role] -= 1
                    break
                    # TODO: Verify this works
                    # TODO: Randomise assignment of roles


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
        for user in self.game.players:
            clean.append(user.name)
        player_lst = ', '.join(clean)
        await self.bot.say('**Current Mafia Players:**\n{}'.format(player_lst))

    # Commands to start game
    @_mafia.command(pass_context=True, no_PM=True)
    async def create(self, ctx):
        """Creates a new game of mafia"""
        self.game = Game(uuid)
        await self.bot.say('''@here Mafia game starting! Use `!mafia join` to
 join the lobby.''')
        await asyncio.sleep(self.settings['LOBBY_DURATION'])
        self.start_game(self.game)

    @_mafia.command(pass_context=True)
    async def join(self, ctx):
        """Join the mafia lobby"""
        player = ctx.message.author
        try:
            self.game.add_player(player)
        except ValueError:
            'Player {} already in game'.format(player)
            return
        await self.bot.say('{} added to players.'.format(player))

    async def start_game(self, game):
        """Closes lobby and begins game. What else did you expect?"""
        game.start()
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
