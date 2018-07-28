from __future__ import unicode_literals
from discord.ext import commands
import discord
from .utils.dataIO import dataIO
from .utils import checks
import os
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer

class Chatterbot:
    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/chatterbot/settings.json')
        self.chatterbot = ChatBot('Athena',
                      database='LanLogOne',
                      storage_adapter='chatterbot.storage.MongoDatabaseAdapter',
                      input_adapter="chatterbot.input.VariableInputTypeAdapter",
                      output_adapter="chatterbot.output.OutputAdapter",
                      output_format="text",
                      logic_adapter=['chatterbot.logic.BestMatch']
                      )

    @commands.command(pass_context=True)
    async def chat(self, ctx):
        """Reads messages from chat"""
        message = ctx.message.content[6:]
        await self.bot.say(self.chatterbot.get_response(message))

    @commands.command()
    async def chattertrain(self):
        """Runs training on English corpus"""
        self.chatterbot.set_trainer(ListTrainer)
        with open('data/chatterbot/doc1.txt') as f:
            doc1 = f.readlines()
        with open ('data/chatterbot/doc2.txt') as f:
            doc2 = f.readlines()
        docData = doc1 + doc2
        docData = [x.strip(',') for x in docData]
        docData = [x.strip('\'') for x in docData]
        docData = [x.strip('\n') for x in docData]
        self.chatterbot.train(docData)
        await self.bot.say("Training complete.")

    @commands.command(no_pm=True, pass_context=True)
    @checks.serverowner_or_permissions(manage_server=True)
    async def chatchannel(self, context, channel: discord.Channel=None):
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
            await send_cmd_help(context)
        else:
            channel = discord.utils.get(
                self.bot.get_all_channels(), id=self.settings['CHANNEL_ID'])
            if channel:
                message = 'Current channel is {}'.format(channel.mention)
                await send_cmd_help(context)
            else:
                self.settings['CHANNEL_ID'] = None
                message = 'No channel set'
                await send_cmd_help(context)

        await self.bot.say(message)

    async def listener(self, message):
        if message.author.id == self.bot.user.id:
            pass
        elif message.content[0] == '!': # Kludge
            pass
        elif message.mention_everyone == True or message.mentions != [] or message.role_mentions != []:
            pass
        elif message.channel.id == self.settings['CHANNEL_ID']:
            await self.bot.send_message(message.channel, self.chatterbot.get_response(message.content))
        else:
            pass

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
    f = 'data/chatterbot/settings.json'
    if not dataIO.is_valid_json(f):
        print('Creating default settings.json...')
        dataIO.save_json(f, data)
