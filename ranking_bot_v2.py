import discord
from discord.ext import commands

from db import database

def read_f(path):
    f = open(path, 'r')
    data = f.read()
    f.close()
    return data

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

def get_channel(ctx, name):
    return discord.utils.get(ctx.guild.channels, name=name)

@bot.event
async def on_message(message):
    await bot.process_commands(message)

@bot.command(name='create_community', brief='creates forum channels for a pool')
async def new_community(ctx, pool_id):
    if ctx.message.channel.name != 'pool-admin-commands':
        return
    if not database.is_pool_owner(pool_id, ctx.message.author.id):
        await ctx.message.channel.send('You don\'t own this pool.')
        return
    if not database.db['threads'].find_one({'_id': pool_id}):
        pool_updates = get_channel(ctx, 'pool-updates')
        pool_ranking = get_channel(ctx, 'pool-ranking')
        pool_discuss = get_channel(ctx, 'pool-discuss')
        updates_thread = await pool_updates.create_thread(name=pool_id + ' updates', content='The updates channel for the {} pool.'.format(pool_id))
        ranking_thread = await pool_ranking.create_thread(name=pool_id + ' ranking', content='The ranking channel for the {} pool.'.format(pool_id))
        discuss_thread = await pool_discuss.create_thread(name=pool_id + ' discuss', content='The discussion channel for the {} pool.'.format(pool_id))
        database.db['threads'].insert_one({'_id': pool_id, 'updates': updates_thread.thread.id, 'discuss': discuss_thread.thread.id, 'ranking': ranking_thread.thread.id})
        await ctx.message.channel.send('Created `{}` channels.'.format(pool_id))
    else:
        await ctx.message.channel.send('`{}` channels already exit.'.format(pool_id))
        
@bot.command(name='nominate', brief='nominate a map for a pool')
async def pool_nominate(ctx, pool_id, map_id):
    if ctx.message.channel.name != 'general-commands':
        return
    beatsaver_key = map_id.split('/')[-1]
    threads = database.db['threads'].find_one({'_id': pool_id})
    if threads:
        ranking_channel = bot.get_channel(threads['ranking'])
        await ranking_channel.send('Ranking Request from ' + ctx.message.author.display_name + ':\nhttps://beatsaver.com/maps/' + beatsaver_key)
        await ctx.message.channel.send('The ranking team has been notified.')
    else:
        await ctx.message.channel.send('Community doesn\'t exist.')
        
@bot.command(name='pool_announcement', brief='post an announcement for a pool')
async def pool_announcement(ctx, pool_id):
    if ctx.message.channel.name != 'pool-admin-commands':
        return
    if not database.is_pool_owner(pool_id, ctx.message.author.id):
        await ctx.message.channel.send('You don\'t own this pool.')
        return
    message_text = ' '.join(ctx.message.content.split(' ')[2:])
    message_embeds = [embed.url for embed in ctx.message.embeds]
    message_attachments = [attachment.url for attachment in ctx.message.attachments]
    new_message = message_text + '\n' + '\n'.join(message_embeds + message_attachments)
    threads = database.db['threads'].find_one({'_id': pool_id})
    if threads:
        updates_channel = bot.get_channel(threads['updates'])
        await updates_channel.send(new_message)
        await ctx.message.channel.send('Sent {} update.'.format(pool_id))
    else:
        await ctx.message.channel.send('Community doesn\'t exist.')
    
@bot.command(name='delete_pool_announcement', brief='deletes the last announcement for a pool')
async def delete_pool_announcement(ctx, pool_id):
    if ctx.message.channel.name != 'pool-admin-commands':
        return
    if not database.is_pool_owner(pool_id, ctx.message.author.id):
        await ctx.message.channel.send('You don\'t own this pool.')
        return
    threads = database.db['threads'].find_one({'_id': pool_id})
    if threads:
        updates_channel = bot.get_channel(threads['updates'])
        messages = [message async for message in updates_channel.history(limit=1)]
        message = messages[0]
        await message.delete()
        await ctx.message.channel.send('Deleted {} update.'.format(pool_id))
    else:
        await ctx.message.channel.send('Community doesn\'t exist.')
    
bot.run(read_f('data/token_2.txt'))