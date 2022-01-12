import asyncio
import json
import time
import sys

import discord
from discord.utils import get

import create_action
from db import database
import beatsaver
from cr_formulas import curves
from general import full_clean

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
PATRON_COMMANDS_CHANNEL = 'patron-commands'
channels = []

def safe_string(s):
    valid_chars = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
    valid_chars += ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '_']
    for char in s:
        if char not in valid_chars:
            return False
    if s == '':
        return False
    return True

def is_admin(user):
    if 'admin' in [role.name for role in user.roles]:
        return True
    else:
        return False

def invalid_curve_data(json_data):
    if json_data['type'] == 'basic':
        if 'cutoff' in json_data:
            if json_data['cutoff'] == 0:
                return 'The cutoff may not be 0.'
    if json_data['type'] == 'linear':
        if 'points' in json_data:
            json_data['points'].sort()
            if len(json_data['points']) > 15:
                return 'You may not have more than 15 points in your curve.'
            if (json_data['points'][0] != [0, 0]) or (json_data['points'][-1] != [1, 1]):
                return 'The first and last points must be `[0, 0]` and `[1, 1]` respectively.'
            if len(set([p[0] for p in json_data['points']])) != len(json_data['points']):
                return 'The x values for every point must be unique.'

    # valid
    return None

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
    for line in message.content.split('\n'):
        message_args = line.split(' ')
        if message.channel.name == PATRON_COMMANDS_CHANNEL:
            if message_args[0] in ['!set_banner', '!set_profile_banner', '!set_profile_background']:
                field = {'!set_banner': 'score_banner', '!set_profile_banner': 'profile_banner', '!set_profile_background': 'profile_background'}[message_args[0]]
                banner_url = message_args[1]
                if (banner_url[:20] == 'https://i.imgur.com/') and (banner_url.split('.')[-1] in ['png', 'jpeg', 'jpg']):
                    user_id = int(message_args[2])
                    users = database.get_users([user_id])
                    if len(users):
                        database.update_user(users[0], {'$set': {field: banner_url}})
                        await message.channel.send(message.author.mention + ' a new score banner has been set!')
                else:
                    await message.channel.send(message.author.mention + ' banner URLs must be https://i.imgur.com links and they must be png or jpeg/jpg. You can get these by right clicking the image and clicking "open image in new tab".')
            if message_args[0] == '!create_pool':
                try:
                    new_pool_id = message_args[1]
                    valid_creation_roles = ['CR Farmer', 'CR Grinder']
                    highest_role = None
                    for valid_role in valid_creation_roles:
                        if valid_role in [role.name for role in message.author.roles]:
                            highest_role = valid_role

                    if highest_role:
                        threshold = 1
                        if highest_role == 'CR Grinder':
                            threshold = 3
                        if new_pool_id not in database.get_pool_ids(True):
                            if safe_string(new_pool_id):
                                if database.get_rate_limits(message.author.id, hash=False)['pools_created'] < threshold:
                                    role = get(active_guild.roles, name='map pool people')
                                    pool_channel = get(active_guild.channels, name='pool-admin-commands')
                                    await message.author.add_roles(role)
                                    database.ratelimit_add(message.author.id, 'pools_created', hash=False)
                                    database.create_map_pool(new_pool_id)
                                    database.set_pool_owners(new_pool_id, [message.author.id])
                                    await message.channel.send(message.author.mention + ' created the map pool `' + new_pool_id + '`! Head over to ' + pool_channel.mention + ' to manage your new pool.')
                                else:
                                    await message.channel.send(message.author.mention + ' You\'ve already created too many pools.')
                            else:
                                await message.channel.send(message.author.mention + ' This pool ID contains forbidden characters. It may only include lowercase letters, numbers, and underscores.')
                        else:
                            await message.channel.send(message.author.mention + ' This pool ID has been taken.')
                    else:
                        await message.channel.send(message.author.mention + ' You must be a CR Farmer or CR Grinder patron to use this command.')

                except IndexError:
                    await message.channel.send(message.author.mention + ' invalid arguments. Should be `!create_pool <new_pool_id>`.')
        if message.channel.name == GENERAL_COMMANDS_CHANNEL:
            if message_args[0] == '!add':
                scoresaber_id = message_args[1]
                create_action.create_user(scoresaber_id)
                await message.channel.send(message.author.mention + ' user ' + scoresaber_id + ' has been added to the action queue.\nhttps://hitbloq.com/actions')
            if message_args[0] == '!views':
                await message.channel.send(message.author.mention + ' Hitbloq has accumulated ' + '{:,}'.format(int(database.get_counter('views')['count'])) + ' views!')
        if message.channel.name == ADMIN_COMMANDS_CHANNEL:
            if message_args[0] == '!create_badge':
                badge_id = message_args[1]
                badge_description = ' '.join(message_args[2:])
                database.create_badge(badge_id, badge_description)
                await message.channel.send(message.author.mention + ' the `' + badge_id + '` badge has been created.')

            if message_args[0] == '!give_badge':
                badge_id = message_args[1]
                user_id = int(message_args[2])
                database.give_badge(user_id, badge_id)
                await message.channel.send(message.author.mention + ' user `' + str(user_id) + '` has been given the `' + badge_id + '` badge.')

            if message_args[0] == '!set_event':
                event_data = ' '.join(message_args[1:])
                if event_data == '':
                    database.db['events'].update_one({'_id': 'current_event'}, {'$set': {'event_id': -1}})
                    await message.channel.send(message.author.mention + ' the current event has been updated to `none`.')
                else:
                    try:
                        event_data = json.loads(event_data.replace('\'', '"'))
                        event_data = {
                            '_id': int(event_data['_id']),
                            'title': str(event_data['title']),
                            'image': str(event_data['image']),
                            'description': str(event_data['description']),
                            'pool': str(event_data['pool']),
                            'urt_description': str(event_data['description']) if 'urt_description' not in event_data else str(event_data['urt_description']),
                            'urt_title': str(event_data['title']) if 'urt_title' not in event_data else str(event_data['urt_title']),
                        }
                        database.db['events'].replace_one({'_id': event_data['_id']}, event_data, upsert=True)
                        database.db['events'].update_one({'_id': 'current_event'}, {'$set': {'event_id': event_data['_id']}})
                        await message.channel.send(message.author.mention + ' the current event has been updated to `' + str(event_data['_id']) + '`.')
                    except:
                        await message.channel.send(message.author.mention + ' there was an error in the formatting of the event data.')

            if message_args[0] == '!delete_pool':
                pool_id = message_args[1]
                database.delete_map_pool(pool_id)
                await message.channel.send(message.author.mention + ' deleted the `' + pool_id + '` map pool.')
            if message_args[0] == '!stop_bot':
                await message.channel.send(message.author.mention + ' stopping... :(')
                sys.exit()
            if message_args[0] == '!recalculate_cr':
                map_pools = message_args[1].split(',')
                create_action.recalculate_cr(map_pools)
                await message.channel.send(message.author.mention + ' a cr recalculation for `' + str(map_pools) + '` has been added to the action queue.\nhttps://hitbloq.com/actions')
            if message_args[0] == '!update_rank_histories':
                for pool_id in database.get_pool_ids(False):
                    create_action.update_rank_histories(pool_id)
                await message.channel.send(message.author.mention + ' a full player history update has been added to the action queue.\nhttps://hitbloq.com/actions')
            if message_args[0] == '!set_announcement':
                announcement_html = ' '.join(message_args[1:])
                if announcement_html == '':
                    database.db['config'].update_one({'_id': 'announcement'}, {'$set': {'html': None}})
                else:
                    database.db['config'].update_one({'_id': 'announcement'}, {'$set': {'html': announcement_html}})
            if message_args[0] == '!rewind':
                rewind_id = int(message_args[1])
                rewind_amount = int(message_args[2])
                rewind_amount = max(0, rewind_amount)
                rewind_to = time.time() - rewind_amount
                database.db['users'].update_one({'_id': rewind_id}, {'$set': {'last_update': rewind_to}})
                create_action.update_user(rewind_id)
                await message.channel.send(message.author.mention + ' user ' + str(rewind_id) + ' will be rewinded and updated.')
        if message.channel.name == POOL_ADMIN_COMMANDS_CHANNEL:
            if message_args[0] in ['!set_short_desc', '!set_long_desc']:
                pool_id = message_args[1]
                desc = ' '.join(message_args[2:]).replace('<', '').replace('>', '')[:2000]
                if message_args[0] == '!set_long_desc':
                    desc = desc.replace('!newline!','<br>')
                print(desc)
                if pool_id in database.get_pool_ids(True):
                    if database.is_pool_owner(pool_id, message.author.id):
                        if message_args[0] == '!set_short_desc':
                            database.db['ranked_lists'].update_one({'_id': pool_id}, {'$set': {'short_description': desc}})
                        if message_args[0] == '!set_long_desc':
                            database.db['ranked_lists'].update_one({'_id': pool_id}, {'$set': {'long_description': desc}})
                        await message.channel.send(message.author.mention + ' updated the description for the `' + pool_id + '` map pool.')
                    else:
                        await message.channel.send(message.author.mention + ' you don\'t have permissions to modify this pool')
                else:
                    await message.channel.send(message.author.mention + ' that pool ID appears to be invalid')

            if message_args[0] == '!regenerate_playlists':
                create_action.regenerate_playlists()
                await message.channel.send(message.author.mention + ' hashlist generation has been added to the action queue.\nhttps://hitbloq.com/actions')

            if message_args[0] == '!set_playlist_cover':
                valid_host = 'https://i.imgur.com/'
                pool_id = message_args[1]
                image_url = message_args[2]
                if pool_id in database.get_pool_ids(True):
                    if database.is_pool_owner(pool_id, message.author.id):
                        if (image_url[:len(valid_host)] != valid_host) or (image_url.split('.')[-1] != 'png'):
                            await message.channel.send(message.author.mention + ' the image URL must come from ' + valid_host + ' and be a PNG')
                        else:
                            database.db['ranked_lists'].update_one({'_id': pool_id}, {'$set': {'playlist_cover': image_url}})
                            await message.channel.send(message.author.mention + ' the pool image has been updated')
                    else:
                        await message.channel.send(message.author.mention + ' you don\'t have permissions to modify this pool')
                else:
                    await message.channel.send(message.author.mention + ' that pool ID appears to be invalid')

            if message_args[0] == '!set_banner_title_hide':
                try:
                    pool_id = message_args[1]
                    boolean = message_args[2].lower()
                    if database.is_pool_owner(pool_id, message.author.id) or is_admin(message.author):
                        if boolean in ['true', 'false']:
                            if boolean == 'true':
                                hide = True
                            else:
                                hide = False
                            database.db['ranked_lists'].update_one({'_id': pool_id}, {'$set': {'banner_title_hide': hide}})
                            await message.channel.send(message.author.mention + ' set banner title visibility to `' + str(hide) + '`.')
                        else:
                            await message.channel.send(message.author.mention + ' invalid arguments. Should be `!set_banner_title_hide <pool_id> true/false`')
                    else:
                        await message.channel.send(message.author.mention + ' You do not have permissions to modify this pool.')
                except IndexError:
                    await message.channel.send(message.author.mention + ' invalid arguments. Should be `!set_banner_title_hide <pool_id> true/false`')
            if message_args[0] == '!set_accumulation_constant':
                try:
                    pool_id = message_args[1]
                    accumulation_constant = float(message_args[2])
                    if database.is_pool_owner(pool_id, message.author.id) or is_admin(message.author):
                        database.db['ranked_lists'].update_one({'_id': pool_id}, {'$set': {'accumulation_constant': accumulation_constant}})
                        await message.channel.send(message.author.mention + ' The accumulation constant for the ' + pool_id + ' pool has been set to `' + str(accumulation_constant) + '`.')
                    else:
                        await message.channel.send(message.author.mention + ' You do not have permissions to modify this pool.')
                except IndexError:
                    await message.channel.send(message.author.mention + ' invalid arguments. Should be `!set_accumulation_constant <pool_id> <constant>`')
            if message_args[0] == '!set_shown_name':
                try:
                    pool_id = message_args[1]
                    shown_name = ' '.join(message_args[2:]).replace('<', '').replace('>', '')[:40]
                    if shown_name == '':
                        await message.channel.send(message.author.mention + ' shown name must not be an empty string.')
                    elif database.is_pool_owner(pool_id, message.author.id) or is_admin(message.author):
                        database.db['ranked_lists'].update_one({'_id': pool_id}, {'$set': {'shown_name': full_clean(shown_name)}})
                        await message.channel.send(message.author.mention + ' The shown name for the ' + pool_id + ' pool has been set to `' + shown_name + '`.')
                    else:
                        await message.channel.send(message.author.mention + ' You do not have permissions to modify this pool.')
                except IndexError:
                    await message.channel.send(message.author.mention + ' invalid arguments. Should be `!set_shown_name <pool_id> <shown_name>`')
            if message_args[0] == '!set_owners':
                try:
                    pool_id = message_args[1]
                    valid_permissions = False
                    if is_admin(message.author):
                        valid_permissions = True
                    else:
                        if database.is_pool_owner(pool_id, message.author.id):
                            valid_permissions = True

                    if valid_permissions:
                        owner_list = [user.id for user in message.mentions]
                        owner_tags = {user.id : user.name + "#" + user.discriminator for user in message.mentions}
                        if message.author.id in owner_list:
                            database.set_pool_owners(pool_id, owner_list)
                            database.update_discord_tags(owner_tags)

                            # add map pool people role to all owners
                            role = get(active_guild.roles, name='map pool people')
                            for user in message.mentions:
                                await user.add_roles(role)

                            await message.channel.send(' '.join([user.mention for user in message.mentions]) + ' You have been set to the owner(s) of the `' + pool_id + '` pool.')
                        else:
                            await message.channel.send(message.author.mention + ' You must list yourself as an owner. If you would like to delete the pool, please contact an admin.')
                    else:
                        await message.channel.send(message.author.mention + ' Sorry, but you don\'t have permissions to modify this pool.')
                except IndexError:
                    await message.channel.send(message.author.mention + ' invalid arguments. Should be `!set_owners <pool_id> @owner1 @owner2 etc.`')

            if message_args[0] == '!set_img':
                valid_host = 'https://i.imgur.com/'
                pool_id = message_args[1]
                image_url = message_args[2]
                if pool_id in database.get_pool_ids(True):
                    if database.is_pool_owner(pool_id, message.author.id):
                        if (image_url[:len(valid_host)] != valid_host) or (image_url.split('.')[-1] != 'png'):
                            await message.channel.send(message.author.mention + ' the image URL must come from ' + valid_host + ' and be a PNG')
                        else:
                            database.db['ranked_lists'].update_one({'_id': pool_id}, {'$set': {'cover': image_url}})
                            await message.channel.send(message.author.mention + ' the pool image has been updated')
                    else:
                        await message.channel.send(message.author.mention + ' you don\'t have permissions to modify this pool')
                else:
                    await message.channel.send(message.author.mention + ' that pool ID appears to be invalid')

            if message_args[0] == '!recalculate_cr':
                pool_id = message_args[1]
                if pool_id in database.get_pool_ids(True):
                    if database.is_pool_owner(pool_id, message.author.id):
                        create_action.recalculate_cr([pool_id])
                        await message.channel.send(message.author.mention + ' the action queue has been updated with the recalc request for ' + pool_id + '.\nhttps://hitbloq.com/actions')
                    else:
                        await message.channel.send(message.author.mention + ' you don\'t have permissions to modify this pool')
                else:
                    await message.channel.send(message.author.mention + ' that pool ID appears to be invalid')

            if message_args[0] == '!set_manual':
                song_id = message_args[1]
                pool_id = message_args[2]
                forced_rating = float(message_args[3])
                if pool_id in database.get_pool_ids(True):
                    matched_leaderboards = database.get_leaderboards([song_id])
                    if not len(matched_leaderboards):
                        await message.channel.send(message.author.mention + ' that song ID appears to be invalid')
                    else:
                        if database.is_pool_owner(pool_id, message.author.id):
                            database.db['leaderboards'].update_one({'_id': song_id}, {'$set': {'forced_star_rating.' + pool_id: forced_rating}})
                            await message.channel.send(message.author.mention + ' switched the leaderboard to manual star ratings (' + str(forced_rating) + ').')
                        else:
                            await message.channel.send(message.author.mention + ' you don\'t have permissions to modify this pool')
                else:
                    await message.channel.send(message.author.mention + ' that pool ID appears to be invalid')

            if message_args[0] == '!set_automatic':
                song_id = message_args[1]
                pool_id = message_args[2]
                if pool_id in database.get_pool_ids(True):
                    matched_leaderboards = database.get_leaderboards([song_id])
                    if not len(matched_leaderboards):
                        await message.channel.send(message.author.mention + ' that song ID appears to be invalid')
                    else:
                        if database.is_pool_owner(pool_id, message.author.id):
                            database.db['leaderboards'].update_one({'_id': song_id}, {'$unset': {'forced_star_rating.' + pool_id: 1}})
                            await message.channel.send(message.author.mention + ' switched the leaderboard to automatic star ratings.')
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
                        if database.is_pool_owner(pool_id, message.author.id):
                            create_action.rank_song(song_id, pool_id)
                            await message.channel.send(message.author.mention + ' the action queue has been updated with the rank request for:\n' + song_data['metadata']['songName'] + ' - ' + song_id.split('|')[-1][1:] + '\n(<https://beatsaver.com/beatmap/' + song_data['id'] + '>)!\nhttps://hitbloq.com/actions')
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
                    if database.is_pool_owner(pool_id, message.author.id):
                        create_action.unrank_song(song_id, pool_id)
                        await message.channel.send(message.author.mention + ' the action queue has been updated with the unrank request for:\n' + song_id + '\nhttps://hitbloq.com/actions')
                    else:
                        await message.channel.send(message.author.mention + ' you don\'t have permissions to modify this pool')
                else:
                    await message.channel.send(message.author.mention + ' that pool ID appears to be invalid')

            if message_args[0] == '!set_curve':
                pool_id = message_args[1]
                if pool_id in database.get_pool_ids(True):
                    if database.is_pool_owner(pool_id, message.author.id):
                        try:
                            json_data = json.loads(' '.join(message_args[2:]))
                            if json_data['type'] in curves:
                                if invalid_curve_data(json_data):
                                    await message.channel.send(message.author.mention + ' Invalid curve config: ' + invalid_curve_data(json_data))
                                else:
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
