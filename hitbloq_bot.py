import asyncio
import json
import time
import sys
import os

import discord
from discord.utils import get
from discord.ext import tasks

import create_action
from db import database
import beatsaver
from cr_formulas import curves
from general import full_clean, format_num
from matchmaking import DEFAULT_RATING
from actions import get_web_img_b64
from file_io import write_f

beatsaver_interface = beatsaver.BeatSaverInterface()

def read_f(path):
    f = open(path,'r')
    dat = f.read()
    f.close()
    return dat

token = read_f('data/token.txt')
guild_id = 'Hitbloq'

client = discord.Client(intents=discord.Intents.all())

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
        
    client.loop.create_task(check_notifications())
    print(client.user.name + ' has connected to Discord!')

@client.event
async def on_message(message):
    global channels, active_guild
    for line in message.content.split('\n'):
        message_args = [v for v in line.split(' ') if v != '']
        if message.channel.name == PATRON_COMMANDS_CHANNEL:
            if message_args[0] == '!link_account':
                user_id = int(message_args[1])
                database.update_discord_tags({message.author.id: message.author.name + "#" + message.author.discriminator})
                if database.link_discord_account(message.author.id, user_id):
                    await message.channel.send(message.author.mention + ' the following account has been linked to your Discord account:\nhttps://hitbloq.com/user/' + str(user_id))
                else:
                    await message.channel.send(message.author.mention + ' you appear to have already claimed an account. Contact and admin for assistance if you believe this is an error.')

            if message_args[0] in ['!set_banner', '!set_profile_banner', '!set_profile_background']:
                field = {'!set_banner': 'score_banner', '!set_profile_banner': 'profile_banner', '!set_profile_background': 'profile_background'}[message_args[0]]
                banner_url = message_args[1]
                if (banner_url[:20] == 'https://i.imgur.com/') and (banner_url.split('.')[-1] in ['png', 'jpeg', 'jpg']):
                    user_id = database.get_linked_account(message.author.id)
                    if user_id == -1:
                        await message.channel.send(message.author.mention + ' please link your Hitbloq account using `!link_account` first.')
                    else:
                        users = database.get_users([user_id])
                        if len(users):
                            database.update_user(users[0], {'$set': {field: banner_url}})
                            await message.channel.send(message.author.mention + ' a new score banner has been set!')
                else:
                    await message.channel.send(message.author.mention + ' banner URLs must be https://i.imgur.com links and they must be png or jpeg/jpg. You can get these by right clicking the image and clicking "open image in new tab".')

            if message_args[0] == '!set_color':
                custom_color = message_args[1]
                invalid_color = False
                if (custom_color[0] != '#') or (len(custom_color) != 7):
                    invalid_color = True
                try:
                    a = int(custom_color[1:], 16)
                except ValueError:
                    invalid_color = True

                if invalid_color:
                    await message.channel.send(message.author.mention + ' that hex color is invalid. Must be between `#000000` and `#ffffff`.')
                else:
                    user_id = database.get_linked_account(message.author.id)
                    if user_id == -1:
                        await message.channel.send(message.author.mention + ' please link your Hitbloq account using `!link_account` first.')
                    else:
                        users = database.get_users([user_id])
                        if len(users):
                            database.update_user(users[0], {'$set': {'custom_color': custom_color}})
                        await message.channel.send(message.author.mention + ' updated your custom color to `' + custom_color + '`.')

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
            if message_args[0] == '!stats':
                stats = {
                    'Website Views': format_num(int(database.get_counter('views')['count'])),
                    'API Requests': format_num(int(database.get_counter('api_reqs')['count'])),
                    'Users': format_num(int(database.db['users'].find({}).count())),
                    'New Users (24h)': format_num(int(database.db['users'].find({'date_created': {'$gt': time.time() - (60 * 60 * 24)}}).count())),
                    'Scores': format_num(int(database.db['scores'].find({}).count())),
                    'Leaderboards': format_num(int(database.db['leaderboards'].find({}).count())),
                    'Pools': format_num(int(database.db['ranked_lists'].find({}).count())),
                }
                msg_text = message.author.mention + '\nHitbloq Stats:```'
                for stat in ['Website Views', 'API Requests', 'Users', 'Scores', 'Leaderboards', 'Pools', 'New Users (24h)']:
                    msg_text += '\n' + stat + ': ' + stats[stat]
                msg_text += '```'
                await message.channel.send(msg_text)
        if message.channel.name == ADMIN_COMMANDS_CHANNEL:
            if message_args[0] == '!reset_ratelimits':
                database.reset_rate_limits(message_args[1])
                await message.channel.send(message.author.mention + ' cleared ratelimits for the address ' + message_args[1] + '.')
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
                await message.channel.send(message.author.mention + ' attempting to delete the `' + pool_id + '` map pool.')
                database.delete_map_pool(pool_id)
                await message.channel.send(message.author.mention + ' deleted the `' + pool_id + '` map pool.')

            if message_args[0] == '!copy_pool':
                src_pool_id = message_args[1]
                new_pool_id = message_args[2]
                await message.channel.send(message.author.mention + ' attempting to copy the `' + src_pool_id + '` map pool to `' + new_pool_id + '`.')
                database.copy_map_pool(src_pool_id, new_pool_id)
                await message.channel.send(message.author.mention + ' copied the `' + src_pool_id + '` map pool to `' + new_pool_id + '`.')

            if message_args[0] == '!add_pool_reference':
                src_pool_id = message_args[1]
                target_pool_id = message_args[2]
                database.create_pool_reference(src_pool_id, target_pool_id)
                await message.channel.send(message.author.mention + ' created a pool reference from the `' + src_pool_id + '` map pool to `' + target_pool_id + '`.')


            if message_args[0] == '!delete_user':
                user_id = message_args[1]
                database.delete_user(int(user_id))
                await message.channel.send(message.author.mention + ' deleted user `' + str(user_id) + '`.')

            if message_args[0] == '!ban_user':
                user_id = message_args[1]
                database.ban_user(int(user_id))
                await message.channel.send(message.author.mention + ' banned user `' + str(user_id) + '`.')

            if message_args[0] == '!set_pool_ratelimits':
                user_list = message_args[2:]
                new_count = int(message_args[1])
                database.db['ratelimits'].update_many({'_id': {'$in': [int(v) for v in user_list]}}, {'$set': {'pools_created': new_count}})
                await message.channel.send(message.author.mention + ' updated ratelimits for\n' + '\n'.join(user_list))

            if message_args[0] == '!api_stats':
                output_text = '```'
                endpoints = sorted(list(database.db['counters'].find({'type': 'api_endpoint_unique'})), key=lambda x: x['count'], reverse=True)
                for endpoint in endpoints:
                    output_text += endpoint['_id'].replace('api_endpoint_', '') + ': ' + format_num(endpoint['count']) + '\n'
                if len(endpoints):
                    output_text = output_text[:-1]
                output_text += '```'
                await message.channel.send(message.author.mention + '\n' + output_text)

            if message_args[0] == '!error_groups':
                output_text = '```'
                for error_log in os.listdir('logs'):
                    output_text += error_log + '\n'
                output_text += '```'
                await message.channel.send(message.author.mention + '\n' + output_text)

            if message_args[0] == '!errors':
                error_group = message_args[1]
                error_group = error_group.replace('/', '').replace('..', '')
                f = open('logs/' + error_group, 'r')
                dat = f.read()
                f.close()
                output_text = '```py\n' + dat[-1900:] + '```'
                await message.channel.send(message.author.mention + '\n' + output_text)

            if message_args[0] == '!stop_bot':
                await message.channel.send(message.author.mention + ' stopping... :(')
                sys.exit()

            if message_args[0] == '!recalculate_cr':
                map_pools = message_args[1].split(',')
                map_pools = map_pools[0] # hack
                print('recalculating cr:', map_pools)
                create_action.recalculate_cr(map_pools, queue_id=0)
                await message.channel.send(message.author.mention + ' a cr recalculation for `' + str(map_pools) + '` has been added to the action queue.\nhttps://hitbloq.com/actions')

            if message_args[0] == '!update_rank_histories':
                for pool_id in database.get_pool_ids(False):
                    create_action.update_rank_histories(pool_id)
                await message.channel.send(message.author.mention + ' a full player history update has been added to the action queue.\nhttps://hitbloq.com/actions')

            if message_args[0] == '!set_mm_pools':
                pool_list = message_args[1:]
                database.db['config'].update_one({'_id': 'mm_pools'}, {'$set': {'pools': pool_list}})
                for pool in pool_list:
                    print('updating ratings for', pool)
                    database.db['mm_users'].update_many({'rating.' + pool: {'$exists': False}}, {'$set': {'rating.' + pool: DEFAULT_RATING}})
                await message.channel.send(message.author.mention + ' updated to `' + str(pool_list) + '`.')

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
            
            if message_args[0] == '!drewind':
                rewind_id = int(message_args[1])
                rewind_amount = int(message_args[2])
                rewind_amount = max(0, rewind_amount)
                rewind_to = time.time() - rewind_amount
                database.db['users'].update_one({'_id': rewind_id}, {'$set': {'last_update': rewind_to}})
                database.db['scores'].delete_many({'user': rewind_id, 'time_set': {'$gt': rewind_to}})
                create_action.update_user(rewind_id)
                await message.channel.send(message.author.mention + ' user ' + str(rewind_id) + ' will be rewinded and updated (with deletion).')

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

            if message_args[0] == '!reimport':
                leaderboard_id = message_args[1]
                database.reimport_song(leaderboard_id)
                await message.channel.send(message.author.mention + ' attempted map reimport.')

            if message_args[0] == '!regenerate_playlists':
                create_action.regenerate_playlists()
                await message.channel.send(message.author.mention + ' hashlist generation has been added to the action queue.\nhttps://hitbloq.com/actions')

            if message_args[0] == '!set_playlist_cover':
                valid_host = 'https://i.imgur.com/'
                pool_id = message_args[1]
                if pool_id in database.get_pool_ids(True):
                    if database.is_pool_owner(pool_id, message.author.id):
                        if len(message.attachments):
                            cover_url = message.attachments[0].url
                            if cover_url.split('.')[-1] == 'png':
                                print('downloading cover:', cover_url)
                                cover_b64 = get_web_img_b64(cover_url)
                                if cover_b64:
                                    write_f('static/hashlists/' + pool_id + '.cover', cover_b64)
                                    await message.channel.send(message.author.mention + ' the playlist cover has been updated.')
                                else:
                                    await message.channel.send(message.author.mention + ' the cover appears to be invalid.')
                            else:
                                await message.channel.send(message.author.mention + ' the image must be a PNG.')
                        else:
                            await message.channel.send(message.author.mention + ' you must attach an image to be used as a cover.')
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
                        print('recalculating cr:', pool_id)
                        create_action.recalculate_cr([pool_id], queue_id=0)
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
                    song_data, bs_error = beatsaver_interface.verify_song_id(song_id)
                    if song_data:
                        if database.is_pool_owner(pool_id, message.author.id):
                            create_action.rank_song(song_id, pool_id)
                            await message.channel.send(message.author.mention + ' the action queue has been updated with the rank request for:\n' + song_data['metadata']['songName'] + ' - ' + song_id.split('|')[-1][1:] + '\n(<https://beatsaver.com/beatmap/' + song_data['id'] + '>)!\nhttps://hitbloq.com/actions')
                        else:
                            await message.channel.send(message.author.mention + ' you don\'t have permissions to modify this pool')
                    else:
                        await message.channel.send(message.author.mention + ' that song ID appears to be invalid')
                        await message.channel.send(bs_error)
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

@client.event
async def check_notifications():
    while not client.is_closed():
        for guild in client.guilds:
            if guild.name == guild_id:
                channel = get(guild.channels, name='admin-notifications')
                notifications = database.fetch_notifications()
                for notification in notifications:
                    notification_text = 'Category **' + notification['category'] + '**\n```py\n' + notification['content'] + '```'
                    await channel.send(notification_text)
        await asyncio.sleep(10)
        
client.run(token)