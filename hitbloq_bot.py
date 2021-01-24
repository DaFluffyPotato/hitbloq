import asyncio

import discord

import create_action

def read_f(path):
    f = open(path,'r')
    dat = f.read()
    f.close()
    return dat

token = read_f('data/token.txt')
guild_id = 'Hitbloq'

client = discord.Client()

GENERAL_COMMANDS_CHANNEL = 'general-commands'
ADMIN_COMMANDS_CHANNEL = 'admin-commands'
channels = []

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
    global channels, active_guild
    message_args = message.content.split(' ')
    if message.channel.name == GENERAL_COMMANDS_CHANNEL:
        if message_args[0] == '!add':
            scoresaber_id = message_args[1]
            create_action.create_user(scoresaber_id)
            await message.channel.send(message.author.mention + ' user ' + scoresaber_id + ' has been added to the action queue.\nhttps://hitbloq.com/actions')
    if message.channel.name == 'admin-commands':
        if message_args[0] == '!recalculate_cr':
            map_pools = message_args[1].split(',')
            create_action.recalculate_cr(map_pools)
            await message.channel.send(message.author.mention + ' a cr recalculation for' + str(map_pools) + 'has been added to the action queue.\nhttps://hitbloq.com/actions')

client.run(token)
