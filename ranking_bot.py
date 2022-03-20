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
guild_id = 629691988027113513

COMMAND_CHAR = '!'
GENERAL_COMMANDS_CHANNEL = 'general-commands'
ADMIN_COMMANDS_CHANNEL = 'admin-commands'
POOL_ADMIN_COMMANDS_CHANNEL = 'pool-admin-commands'
PATRON_COMMANDS_CHANNEL = 'patron-commands'

intents = discord.Intents.all()
client = discord.Client(intents=intents)

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
        self.channel = msg.channel
        self.author = msg.author
        self.roles = [role.name for role in msg.author.roles]
        self.guild = msg.guild

    async def reply(self, response):
        await self.msg.channel.send(self.author.mention + ' ' + response)

    def sig(self):
        return []

    async def parse_args(self):
        valid = True
        if len(self.args) < len(self.sig()):
            valid = False

        if valid:
            for i, arg in enumerate(self.args):
                if i < len(self.sig()):
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
class pin(Command):
    async def execute(self):
        if self.channel.category in [get_cat(self.guild.categories, cat) for cat in ['ranking', 'pool discussion', 'pool updates']]:
            pool_id = self.channel_id.split('-')[0]
            if database.is_pool_owner(pool_id, self.author.id):
                if not self.msg.reference:
                    await self.reply('Please reply to the message you want to pin.')
                else:
                    pin_msg = await self.channel.fetch_message(self.msg.reference.message_id)
                    await pin_msg.pin()
                    await self.msg.add_reaction('✅')
            else:
                await self.reply('You do not own this pool.')

@register_command
class unpin(Command):
    async def execute(self):
        if self.channel.category in [get_cat(self.guild.categories, cat) for cat in ['ranking', 'pool discussion', 'pool updates']]:
            pool_id = self.channel_id.split('-')[0]
            if database.is_pool_owner(pool_id, self.author.id):
                if not self.msg.reference:
                    await self.reply('Please reply to the message you want to unpin.')
                else:
                    pin_msg = await self.channel.fetch_message(self.msg.reference.message_id)
                    await pin_msg.unpin()
                    await self.msg.add_reaction('✅')
            else:
                await self.reply('You do not own this pool.')

@register_command
class nominate(Command):
    def sig(self):
        return [('str', 'pool_id'), ('str', 'beatsaver_map')]
    async def execute(self):
        if self.channel_id == GENERAL_COMMANDS_CHANNEL:
            if database.db['communities'].find_one({'_id': self.args[0]}):
                beatsaver_key = self.args[1].split('/')[-1]
                try:
                    int(beatsaver_key, 16)
                    ranking_channel = get_cat_chan(self.guild.channels, self.args[0] + '-ranking', 'ranking')
                    await ranking_channel.send('Ranking Request from ' + self.author.display_name + ':\nhttps://beatsaver.com/maps/' + beatsaver_key)
                    await self.reply('The ranking team has been notified.')
                except ValueError:
                    await self.reply('This beatsaver map appears to be invalid.')
            else:
                await self.reply('This community is not accepting nominations.')

@register_command
class list_communities(Command):
    async def execute(self):
        if self.channel_id == GENERAL_COMMANDS_CHANNEL:
            community_ids = [c['_id'] for c in database.db['communities'].find({})]
            await self.reply('```' + '\n'.join(community_ids) + '```')

@register_command
class join_pool(Command):
    def sig(self):
        return [('str', 'pool_id')]

    async def execute(self):
        if self.channel_id == GENERAL_COMMANDS_CHANNEL:
            updates_category = get_cat(self.guild.categories, 'pool updates')
            discussion_category = get_cat(self.guild.categories, 'pool discussion')
            if database.db['communities'].find_one({'_id': self.args[0]}):
                channels = [get_cat_chan(self.guild.channels, self.args[0] + '-updates', 'pool updates'), get_cat_chan(self.guild.channels, self.args[0] + '-discuss', 'pool discussion')]
                for i, channel in enumerate(channels):
                    perms = channel.overwrites_for(self.author)
                    if i != 0:
                        perms.send_messages = True
                    perms.read_messages = True
                    await channel.set_permissions(self.author, overwrite=perms)
                await channels[1].send(self.author.mention + ' has joined the `' + self.args[0] + '` community.')
                await self.msg.add_reaction('✅')
            else:
                await self.reply('This community does not exist.')

@register_command
class join_all_pools(Command):
    async def execute(self):
        if self.channel_id == GENERAL_COMMANDS_CHANNEL:
            pool_ids = [c['_id'] for c in database.db['communities'].find({})]
            for pool in pool_ids:
                updates_category = get_cat(self.guild.categories, 'pool updates')
                discussion_category = get_cat(self.guild.categories, 'pool discussion')

                channels = [get_cat_chan(self.guild.channels, pool + '-updates', 'pool updates'), get_cat_chan(self.guild.channels, pool + '-discuss', 'pool discussion')]
                for i, channel in enumerate(channels):
                    perms = channel.overwrites_for(self.author)
                    if i != 0:
                        perms.send_messages = True
                    perms.read_messages = True
                    await channel.set_permissions(self.author, overwrite=perms)
                await channels[1].send(self.author.display_name + ' has joined the `' + pool + '` community.')
            await self.msg.add_reaction('✅')

@register_command
class leave_all_pools(Command):
    async def execute(self):
        if self.channel_id == GENERAL_COMMANDS_CHANNEL:
            pool_ids = [c['_id'] for c in database.db['communities'].find({})]
            for pool in pool_ids:
                updates_category = get_cat(self.guild.categories, 'pool updates')
                discussion_category = get_cat(self.guild.categories, 'pool discussion')

                channels = [get_cat_chan(self.guild.channels, pool + '-updates', 'pool updates'), get_cat_chan(self.guild.channels, pool + '-discuss', 'pool discussion')]
                for i, channel in enumerate(channels):
                    perms = channel.overwrites_for(self.author)
                    perms.send_messages = False
                    perms.read_messages = False
                    await channel.set_permissions(self.author, overwrite=perms)
            await self.msg.add_reaction('✅')

@register_command
class leave_pool(Command):
    def sig(self):
        return [('str', 'pool_id')]

    async def execute(self):
        if self.channel_id == GENERAL_COMMANDS_CHANNEL:
            updates_category = get_cat(self.guild.categories, 'pool updates')
            discussion_category = get_cat(self.guild.categories, 'pool discussion')
            if database.db['communities'].find_one({'_id': self.args[0]}):
                channels = [get_cat_chan(self.guild.channels, self.args[0] + '-updates', 'pool updates'), get_cat_chan(self.guild.channels, self.args[0] + '-discuss', 'pool discussion')]
                for i, channel in enumerate(channels):
                    perms = channel.overwrites_for(self.author)
                    perms.send_messages = False
                    perms.read_messages = False
                    await channel.set_permissions(self.author, overwrite=perms)
                await self.msg.add_reaction('✅')
            else:
                await self.reply('This community does not exist.')

@register_command
class ranking_discuss_invite(Command):
    def sig(self):
        return [('str', 'pool_id'), ('user', 'user_mention')]

    async def execute(self):
        if self.channel_id == POOL_ADMIN_COMMANDS_CHANNEL:
            ranking_category = get_cat(self.guild.categories, 'ranking')
            if database.is_pool_owner(self.args[0], self.author.id):
                if database.db['communities'].find_one({'_id': self.args[0]}):
                    ranking_channel = get_cat_chan(self.guild.channels, self.args[0] + '-ranking', 'ranking')
                    perms = ranking_channel.overwrites_for(self.args[1])
                    perms.send_messages = True
                    perms.read_messages = True
                    await ranking_channel.set_permissions(self.args[1], overwrite=perms)
                    await ranking_channel.send(self.args[1].mention + ' has been added to this channel.')
                    await self.reply('Added new user to ' + ranking_channel.mention + '.')

                    updates_channel = get_cat_chan(self.guild.channels, self.args[0] + '-updates', 'pool updates')
                    perms = ranking_channel.overwrites_for(self.args[1])
                    perms.send_messages = True
                    perms.read_messages = True
                    await updates_channel.set_permissions(self.args[1], overwrite=perms)
                else:
                    await self.reply('You need to create this community first.')
            else:
                await self.reply('You don\'t own this pool.')

@register_command
class ranking_discuss_remove(Command):
    def sig(self):
        return [('str', 'pool_id'), ('user', 'user_mention')]

    async def execute(self):
        if self.channel_id == POOL_ADMIN_COMMANDS_CHANNEL:
            ranking_category = get_cat(self.guild.categories, 'ranking')
            if database.is_pool_owner(self.args[0], self.author.id):
                if database.db['communities'].find_one({'_id': self.args[0]}):
                    ranking_channel = get_cat_chan(self.guild.channels, self.args[0] + '-ranking', 'ranking')
                    perms = ranking_channel.overwrites_for(self.args[1])
                    perms.send_messages = False
                    perms.read_messages = False
                    await ranking_channel.send(self.args[1].mention + ' has been removed from this channel.')
                    await ranking_channel.set_permissions(self.args[1], overwrite=perms)
                    await self.reply('Removed user from ' + ranking_channel.mention + '.')

                    updates_channel = get_cat_chan(self.guild.channels, self.args[0] + '-updates', 'pool updates')
                    perms = ranking_channel.overwrites_for(self.args[1])
                    perms.send_messages = False
                    perms.read_messages = False
                    await updates_channel.set_permissions(self.args[1], overwrite=perms)
                else:
                    await self.reply('You need to create this community first.')
            else:
                await self.reply('You don\'t own this pool.')

@register_command
class create_community(Command):
    def sig(self):
        return [('str', 'pool_id')]

    async def execute(self):
        if self.channel_id in [POOL_ADMIN_COMMANDS_CHANNEL, ADMIN_COMMANDS_CHANNEL]:
            pool_updates_category = get_cat(self.guild.categories, 'pool updates')
            pool_discuss_category = get_cat(self.guild.categories, 'pool discussion')
            ranking_category = get_cat(self.guild.categories, 'ranking')
            if (self.channel_id == ADMIN_COMMANDS_CHANNEL) or database.is_pool_owner(self.args[0], self.author.id):
                if not database.db['communities'].find_one({'_id': self.args[0]}):
                    new_channels = []
                    permission_overwrites = {self.author: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
                    existing_channel = get_cat_chan(self.guild.channels, self.args[0] + '-ranking', 'ranking')
                    if not existing_channel:
                        await self.guild.create_text_channel(self.args[0] + '-ranking', category=ranking_category)
                    new_channels.append(get_cat_chan(self.guild.channels, self.args[0] + '-ranking', 'ranking'))
                    await self.guild.create_text_channel(self.args[0] + '-updates', category=pool_updates_category)
                    new_channels.append(get_cat_chan(self.guild.channels, self.args[0] + '-updates', 'pool updates'))
                    await new_channels[-1].set_permissions(self.guild.default_role, send_messages=False)
                    await self.guild.create_text_channel(self.args[0] + '-discuss', category=pool_discuss_category)
                    new_channels.append(get_cat_chan(self.guild.channels, self.args[0] + '-discuss', 'pool discussion'))

                    for channel in new_channels:
                        perms = channel.overwrites_for(self.author)
                        perms.send_messages = True
                        perms.read_messages = True
                        await channel.set_permissions(self.author, overwrite=perms)

                    await new_channels[0].send('Use `!ranking_discuss_invite <pool_id> <user_mention>` in ' + get_cat_chan(self.guild.channels, 'pool-admin-commands', 'hitbloq-commands').mention + ' to invite a user to the ranking discussion.')

                    database.db['communities'].insert_one({'_id': self.args[0]})
                    await self.reply('Created the `' + self.args[0] + '` community.')
                else:
                    await self.reply('This community already exists.')
            else:
                await self.reply('You don\'t own this pool.')

@register_command
class delete_community(Command):
    def sig(self):
        return [('str', 'pool_id')]

    async def execute(self):
        if self.channel_id == ADMIN_COMMANDS_CHANNEL:
            if database.db['communities'].find_one({'_id': self.args[0]}):
                pool_updates_category = get_cat(self.guild.categories, 'pool updates')
                pool_discuss_category = get_cat(self.guild.categories, 'pool discussion')
                ranking_category = get_cat(self.guild.categories, 'ranking')
                try:
                    await get_cat_chan(self.guild.channels, self.args[0] + '-updates', 'pool updates').delete()
                    await get_cat_chan(self.guild.channels, self.args[0] + '-discuss', 'pool discussion').delete()
                    await get_cat_chan(self.guild.channels, self.args[0] + '-ranking', 'ranking').delete()
                except:
                    print('missing channels')
                database.db['communities'].delete_one({'_id': self.args[0]})
                await self.reply('Deleted.')
            else:
                await self.reply('This community does not exist.')

@client.event
async def on_ready():
    print(client.guilds)
    for guild in client.guilds:
        if guild.id == guild_id:
            global channels, active_guild
            active_guild = guild
            channels = guild.channels
            break
    print(client.user.name + ' has connected to Discord!')

@client.event
async def on_message(message):
    for line in message.content.split('\n'):
        try:
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
        except IndexError:
            pass

client.run(token)
