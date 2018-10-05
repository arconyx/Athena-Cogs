from __future__ import unicode_literals
from discord.ext import commands
import discord
from .utils.dataIO import dataIO
from .utils import checks
import os
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer
from chatterbot.trainers import ChatterBotCorpusTrainer

# This bot requires MongoDB to be running.


class Chatterbot:
    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/chatterbot/settings.json')
        self.chatterbot = ChatBot('Athena',
                                  database='LanLogFour',
                                  storage_adapter='chatterbot.storage.'
                                  'MongoDatabaseAdapter',
                                  input_adapter='chatterbot.input.'
                                  'VariableInputTypeAdapter',
                                  output_adapter='chatterbot.output.'
                                  'OutputAdapter',
                                  output_format='text',
                                  logic_adapters=[
                                      {'import_path': 'chatterbot.logic.'
                                       'BestMatch',
                                       'statement_comparison_function':
                                       'chatterbot.comparisons.'
                                       'levenshtein_distance',
                                       'response_selection_method':
                                       'chatterbot.response_selection.'
                                       'get_most_frequent_response'},
                                      'chatterbot.logic.MathematicalEvaluation'
                                      ]
                                  )
        self.conversations = {}
        self.previous_statement = {}

    @commands.command(pass_context=True)
    async def chat(self, ctx):
        """Reads messages from chat"""
        message = ctx.message.content[6:]
        conversation_id = self._get_conversation(ctx.message.channel.id)
        response = await self._get_response(message, conversation_id)
        await self.bot.say(response)

    @commands.command()
    @checks.serverowner_or_permissions(manage_server=True)
    async def chattertraindocs(self):
        """Runs training on the docs"""
        self.chatterbot.set_trainer(ListTrainer)
        with open('data/chatterbot/doc1.txt') as f:
            doc1 = f.readlines()
        with open('data/chatterbot/doc2.txt') as f:
            doc2 = f.readlines()
        docData = doc1 + doc2
        docData = [x.strip(',') for x in docData]
        docData = [x.strip('\'') for x in docData]
        docData = [x.strip('\n') for x in docData]
        self.chatterbot.train(docData)
        await self.bot.say("Training complete.")

    @commands.command()
    @checks.serverowner_or_permissions(manage_server=True)
    async def chattertrain(self):
        self.chatterbot.set_trainer(ChatterBotCorpusTrainer)
        self.chatterbot.train("chatterbot.corpus.english")
        await self.bot.say("Training complete")

    @commands.command(no_pm=True, pass_context=True)
    @checks.serverowner_or_permissions(manage_server=True)
    async def chatchannel(self, context, channel: discord.Channel = None):
        """
        Set the channel to which the bot will sent its continues updates.
        Example: [p]chatchannel #talk
        """
        if channel:
            self.settings['CHANNEL_ID'] = str(channel.id)
            dataIO.save_json('data/chatterbot/settings.json', self.settings)
            message = 'Channel set to {}'.format(channel.mention)
        elif not self.settings['CHANNEL_ID']:
            message = 'No Channel set'
        else:
            channel = discord.utils.get(
                self.bot.get_all_channels(), id=self.settings['CHANNEL_ID'])
            if channel:
                message = 'Current channel is {}'.format(channel.mention)
            else:
                self.settings['CHANNEL_ID'] = None
                message = 'No channel set'

        await self.bot.say(message)

    @commands.command(pass_context=True)
    @checks.serverowner_or_permissions(manage_server=True)
    async def chatterignore(self, context, channel: discord.Channel = None):
        if channel:
            self.settings['BLOCKED_CHANNELS'].append(channel.id)
            # TODO: Check if already in list
            dataIO.save_json('data/chatterbot/settings.json', self.settings)
            message = '{} added to blocked channels.'.format(channel.mention)
        elif not self.settings['BLOCKED_CHANNELS']:
            message = 'No channels blocked'
        # else:
        #    channel = discord.utils.get(
        #        self.bot.get_all_channels(),
        #        id=self.settings['BLOCKED_CHANNELS'])
        #    if channel:
        #        message = 'Current channel is {}'.format(channel.mention)
        #    else:
        #        self.settings['CHANNEL_ID'] = None
        #        message = 'No channel set'

        await self.bot.say(message)

    async def listener(self, message):
        if message.author.id == self.bot.user.id:
            pass
        elif message.content == '':
            pass
        elif message.content[0] == '!':  # Kludge
            pass
        elif message.mention_everyone is True:
            pass
        elif message.mentions != []:
            pass
        elif message.role_mentions != []:
            pass
        elif message.channel.id == self.settings['CHANNEL_ID']:
            conversation_id = self._get_conversation(message.channel.id)
            response = await self._get_response(message.content,
                                                conversation_id)
            await self.bot.send_message(message.channel, response)
        elif message.channel.id not in self.settings['BLOCKED_CHANNELS']:
            conversation_id = self._get_conversation(message.channel.id)
            input_statement = self.chatterbot.input.process_input_statement(
                message.content)
            if conversation_id in self.previous_statement:
                self.chatterbot.learn_response(
                    input_statement, self.previous_statement[conversation_id])
                self.previous_statement[conversation_id] = input_statement
            else:
                self.previous_statement[conversation_id] = input_statement
        else:
            pass

    async def _get_response(self, input_item, conversation_id):
        input_statement = self.chatterbot.input.process_input_statement(
            input_item)
        # Preprocess the input statement
        for preprocessor in self.chatterbot.preprocessors:
            input_statement = preprocessor(self.chatterbot, input_statement)
        statement, response = self.chatterbot.generate_response(
            input_statement, conversation_id)
        # Learn that the user's input was a valid response to the chat bot's
        # previous output
        if not self.chatterbot.read_only:
            if conversation_id in self.previous_statement:
                prev = self.previous_statement[conversation_id]
            else:
                prev = None
            self.chatterbot.learn_response(statement, prev)
            self.chatterbot.storage.add_to_conversation(conversation_id,
                                                        statement, response)
            self.previous_statement[conversation_id] = response
        # Process the response output with the output adapter
        return str(response)

    def _get_conversation(self, channel_id):
        try:
            conversation_id = self.conversations[channel_id]
        except KeyError:
            conversation_id = self.chatterbot.storage.create_conversation()
            self.conversations[channel_id] = conversation_id
        return conversation_id


def setup(bot):
    check_folder()
    check_file()
    chatty = Chatterbot(bot)
    bot.add_listener(chatty.listener, "on_message")
    bot.add_cog(chatty)


def check_folder():
    if not os.path.exists('data/chatterbot'):
        print('Creating data/chatterbot folder...')
        os.makedirs('data/chatterbot')


def check_file():
    data = {}
    data['CHANNEL_ID'] = ''
    data['BLOCKED_CHANNELS'] = []
    f = 'data/chatterbot/settings.json'
    if not dataIO.is_valid_json(f):
        print('Creating default settings.json...')
        dataIO.save_json(f, data)
