import asyncio
import json

import discord

import create_action
from db import database
import beatsaver
from cr_formulas import curves

beatsaver_interface = beatsaver.BeatSaverInterface()

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
POOL_ADMIN_COMMANDS_CHANNEL = 'pool-admin-commands'
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
    if message.channel.name == ADMIN_COMMANDS_CHANNEL:
        if message_args[0] == '!recalculate_cr':
            map_pools = message_args[1].split(',')
            create_action.recalculate_cr(map_pools)
            await message.channel.send(message.author.mention + ' a cr recalculation for `' + str(map_pools) + '` has been added to the action queue.\nhttps://hitbloq.com/actions')
        if message_args[0] == '!update_rank_histories':
            for pool_id in database.get_pool_ids(False):
                create_action.update_rank_histories(pool_id)
            await message.channel.send(message.author.mention + ' a full player history update has been added to the action queue.\nhttps://hitbloq.com/actions')
        if message_args[0] == '!regenerate_playlists':
            create_action.regenerate_playlists()
    if message.channel.name == POOL_ADMIN_COMMANDS_CHANNEL:
        if message_args[0] == '!recalculate_cr':
            pool_id = message_args[1]
            if pool_id in database.get_pool_ids(True):
                if pool_id in [role.name for role in message.author.roles]:
                    create_action.recalculate_cr([pool_id])
                    await message.channel.send(message.author.mention + ' the action queue has been updated with the recalc request for ' + pool_id + '.\nhttps://hitbloq.com/actions')
                else:
                    await message.channel.send(message.author.mention + ' you don\'t have permissions to modify this pool')
            else:
                await message.channel.send(message.author.mention + ' that pool ID appears to be invalid')
        if message_args[0] == '!rank':
            song_id = message_args[1]
            pool_id = message_args[2]
            if pool_id in database.get_pool_ids(True):
                song_data = beatsaver_interface.verify_song_id(song_id)
                if song_data:
                    if pool_id in [role.name for role in message.author.roles]:
                        create_action.rank_song(song_id, pool_id)
                        await message.channel.send(message.author.mention + ' the action queue has been updated with the rank request for:\n' + song_data['metadata']['songName'] + ' - ' + song_id.split('|')[-1][1:] + '\n(<https://beatsaver.com/beatmap/' + song_data['key'] + '>)!\nhttps://hitbloq.com/actions')
                    else:
                        await message.channel.send(message.author.mention + ' you don\'t have permissions to modify this pool')
                else:
                    await message.channel.send(message.author.mention + ' that song ID appears to be invalid')
            else:
                await message.channel.send(message.author.mention + ' that pool ID appears to be invalid')
        if message_args[0] == '!unrank':
            song_id = message_args[1]
            pool_id = message_args[2]
            if pool_id in database.get_pool_ids(True):
                if pool_id in [role.name for role in message.author.roles]:
                    create_action.unrank_song(song_id, pool_id)
                    await message.channel.send(message.author.mention + ' the action queue has been updated with the unrank request for:\n' + song_id + '\nhttps://hitbloq.com/actions')
                else:
                    await message.channel.send(message.author.mention + ' you don\'t have permissions to modify this pool')
            else:
                await message.channel.send(message.author.mention + ' that pool ID appears to be invalid')
        if message_args[0] == '!set_curve':
            pool_id = message_args[1]
            if pool_id in database.get_pool_ids(True):
                if pool_id in [role.name for role in message.author.roles]:
                    try:
                        json_data = json.loads(' '.join(message_args[2:]))
                        if json_data['type'] in curves:
                            database.set_pool_curve(pool_id, json_data)
                            await message.channel.send(message.author.mention + ' the curve for ' + pool_id + ' has been updated. You may want to run `!recalculate_cr ' + pool_id + '`.')
                        else:
                            await message.channel.send(message.author.mention + ' the specified curve does not exist.')
                    except:
                        await message.channel.send(message.author.mention + ' the JSON formatting is invalid.')
                else:
                    await message.channel.send(message.author.mention + ' you don\'t have permissions to modify this pool')
            else:
                await message.channel.send(message.author.mention + ' that pool ID appears to be invalid')

client.run(token)
