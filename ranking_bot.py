import sys

import discord
from discord.utils import get

from db import database

def read_f(path):
    f = open(path,'r')
    dat = f.read()
    f.close()
    return dat

token = read_f('data/token_2.txt')
guild_id = 'Hitbloq'

COMMAND_CHAR = '!'
GENERAL_COMMANDS_CHANNEL = 'general-commands'
ADMIN_COMMANDS_CHANNEL = 'admin-commands'
POOL_ADMIN_COMMANDS_CHANNEL = 'pool-admin-commands'
PATRON_COMMANDS_CHANNEL = 'patron-commands'

client = discord.Client()

commands = {}
def register_command(command):
    command_id = command.__name__.lower()
    print('registered command:', command_id)
    commands[command_id] = command

class Command:
    def __init__(self, msg, *args):
        self.args = list(args)
        self.msg = msg
        self.channel_id = msg.channel.name
        self.author = msg.author
        self.roles = [role.name for role in msg.author.roles]
        self.guild = msg.guild

    async def reply(self, response):
        await self.msg.channel.send(self.author.mention + ' ' + response)

    def sig(self):
        return []

    async def parse_args(self):
        valid = True
        if len(self.args) != len(self.sig()):
            valid = False

        if valid:
            for i, arg in enumerate(self.args):
                arg_type = self.sig()[i][0]

                if arg_type == 'int':
                    try:
                        self.args[i] = int(arg)
                    except ValueError:
                        valid = False

                if arg_type == 'user':
                    try:
                        user_id = arg[3:-1]
                        user = await self.guild.fetch_member(int(user_id))
                        self.args[i] = user
                    except:
                        valid = False

        if not valid:
            format_str = '`' + COMMAND_CHAR + self.__class__.__name__ + ' '
            for arg in self.sig():
                format_str += '<' + arg[1] + '> '
            format_str = format_str[:-1] + '`'
            await self.reply('Invalid arguments. Command expects ' + format_str)
        return valid

    async def execute(self):
        pass

    async def cleanup(self, failed):
        pass

def get_cat_chan(channels, name, cat):
    for channel in channels:
        if channel.category:
            if channel.name == name:
                if channel.category.name == cat:
                    return channel
    return None

def get_cat(categories, name):
    for cat in categories:
        if cat.name == name:
            return cat
    return None

@register_command
class rankjor(Command):
    def sig(self):
        return [('int', 'number'), ('str', 'string'), ('user', 'user_mention')]

    async def execute(self):
        print('rankjor test', str(self.args))
        await self.reply('Hi, I\'m Rankjor. ' + str(self.args))

@register_command
class kill_rankjor(Command):
    async def execute(self):
        if self.channel_id == ADMIN_COMMANDS_CHANNEL:
            print('stopping...')
            await self.reply('Stopping...')
            sys.exit()

@register_command
class create_discussion(Command):
    def sig(self):
        return [('str', 'pool_id')]

    async def execute(self):
        if self.channel_id == POOL_ADMIN_COMMANDS_CHANNEL:
            ranking_category = get_cat(self.guild.categories, 'ranking')
            if database.is_pool_owner(self.args[0], self.author.id):
                if not database.db['discussions'].find_one({'_id': self.args[0]}):
                    new_role = self.args[0] + '_discuss'
                    await self.guild.create_role(name=new_role)
                    role = get(self.guild.roles, name=new_role)
                    await self.author.add_roles(role)
                    await self.guild.create_text_channel(new_role, category=ranking_category)
                    new_channel = get_cat_chan(self.guild.channels, new_role, 'ranking')
                    await new_channel.set_permissions(role, read_messages=True, send_messages=True)
                    await self.reply('Created the ' + new_channel.mention + ' channel.')
                    await new_channel.send('Use `!discuss_invite <pool_id> <user_mention>` in ' + get_cat_chan(self.guild.channels, 'pool-admin-commands', 'hitbloq-commands').mention + ' to invite a user to the discussion.')
                    database.db['discussions'].insert_one({'_id': self.args[0]})
                else:
                    await self.reply('This discussion already exists.')
            else:
                await self.reply('You don\'t own this pool.')

@register_command
class discuss_invite(Command):
    def sig(self):
        return [('str', 'pool_id'), ('user', 'user_mention')]

    async def execute(self):
        if self.channel_id == POOL_ADMIN_COMMANDS_CHANNEL:
            ranking_category = get_cat(self.guild.categories, 'ranking')
            if database.is_pool_owner(self.args[0], self.author.id):
                if database.db['discussions'].find_one({'_id': self.args[0]}):
                    discuss_role_name = self.args[0] + '_discuss'
                    discuss_role = get(self.guild.roles, name=discuss_role_name)
                    await self.args[1].add_roles(discuss_role)
                    discuss_channel = get_cat_chan(self.guild.channels, discuss_role_name, 'ranking')
                    await discuss_channel.send(self.args[1].mention + ' has been added to this discussion.')
                    await self.reply('Added new user to ' + discuss_channel.mention)
                else:
                    await self.reply('You need to create this discussion first.')
            else:
                await self.reply('You don\'t own this pool.')

@client.event
async def on_ready():
    for guild in client.guilds:
        if guild.name == guild_id:
            global channels, active_guild
            active_guild = guild
            channels = guild.channels
            break
    print(client.user.name + ' has connected to Discord!')

@client.event
async def on_message(message):
    for line in message.content.split('\n'):
        message_args = line.split(' ')
        if message_args[0][0] == '!':
            command_id = message_args[0][1:]
            if command_id in commands:
                print('executing', command_id)
                cmd = commands[command_id](message, *message_args[1:])
                valid_args = await cmd.parse_args()
                if valid_args:
                    #try:
                    await cmd.execute()
                    await cmd.cleanup(False)
                    '''except Exception as e:
                        print('exception on', line)
                        print(e)
                        await cmd.cleanup(True)'''

client.run(token)
