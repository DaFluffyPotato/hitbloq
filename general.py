import time
import datetime
import requests

from PIL import Image

DAY = 60 * 60 * 24

def max_score(notes):
    if notes >= 13:
        max_score = (notes - 13) * 8 * 115 + 4715
    else:
        score_table = [115,345,575,805,1035,1495,1955,2415,2875,3335,3795,4255]
        max_score = score_table[notes - 1]
    return max_score

def format_num(number):
    if number >= 1000000000:
        return str(round(number / 1000000000, 2)) + 'B'
    if number >= 1000000:
        return str(round(number / 1000000, 2)) + 'M'
    elif number >= 1000:
        return str(round(number / 1000, 2)) + 'K'
    else:
        return str(number)

diff_shorten = {
    'ExpertPlus': 'ep',
    'Expert': 'ex',
    'Hard': 'h',
    'Normal': 'n',
    'Easy': 'e',
}

char_shorten = {
    'SoloStandard': 's',
    'Solo90Degree': 's90',
    'Solo360Degree': 's360',
    'SoloOneSaber': 's1s',
    'SoloNoArrows': 'sna',
    'SoloStandardHD': 'shd',
    'SoloLawless': 'sll',
    'SoloInverseStandard': 'sit',
    'SoloHorizontalStandard': 'shs',
    'SoloVerticalStandard': 'svs',
}

diff_lengthen = {v: k for k, v in diff_shorten.items()}
char_lengthen = {v: k for k, v in char_shorten.items()}

def substrings(string):
    length = len(string)
    return [string[i:j + 1] for i in range(length) for j in range(i, length)]

def shorten_settings(settings_str):
    diff = settings_str.split('_')[1]
    char = settings_str.split('_')[2]
    return diff_shorten[diff] + '_' + char_shorten[char]

def lengthen_settings(settings_str):
    diff = settings_str.split('_')[0]
    char = settings_str.split('_')[1]
    return '_' + diff_lengthen[diff] + '_' + char_lengthen[char]

def mongo_clean(string):
    for char in ['{', '}', '.', '$']:
        string = string.replace(char, '')
    return string

def full_clean(string):
    for char in ['<', '>']:
        string = string.replace(char, '')
    string = mongo_clean(string)
    return string

def epoch_to_date(epoch):
    ts = datetime.datetime.fromtimestamp(epoch)
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    day_extensions = ['th', 'st', 'nd', 'rd', 'th', 'th', 'th', 'th', 'th', 'th']
    if ts.day in [11, 12, 13]:
        day_extensions = ['th', 'th', 'th', 'th', 'th', 'th', 'th', 'th', 'th', 'th']
    return months[ts.month - 1] + ' ' + str(ts.day) + day_extensions[ts.day % 10] + ', ' + str(ts.year)

def epoch_ago(epoch):
    time_ago = time.time() - epoch
    years_ago = int(time_ago // (DAY * 365))
    if years_ago:
        added_s = 's' if years_ago > 1 else ''
        return str(years_ago) + ' year' + added_s

    months_ago = int(time_ago // (DAY * 30))
    if months_ago:
        added_s = 's' if months_ago > 1 else ''
        return str(months_ago) + ' month' + added_s

    days_ago = int(time_ago // DAY)
    if days_ago:
        added_s = 's' if days_ago > 1 else ''
        return str(days_ago) + ' day' + added_s

    hours_ago = int(time_ago // (60 * 60))
    if hours_ago:
        added_s = 's' if hours_ago > 1 else ''
        return str(hours_ago) + ' hour' + added_s

    minutes_ago = int(time_ago // 60)
    if minutes_ago:
        added_s = 's' if minutes_ago > 1 else ''
        return str(minutes_ago) + ' minute' + added_s

    seconds_ago = int(time_ago)
    added_s = 's' if seconds_ago > 1 else ''
    return str(seconds_ago) + ' second' + added_s

def download_image(url, filename):
    img_data = requests.get(url).content
    url_extension = url.split('.')[-1].split('?')[0]
    with open(filename + '.' + url_extension, 'wb') as handler:
        handler.write(img_data)

    if url_extension != 'png':
        img = Image.open(filename + '.' + url_extension)
        img.save(filename + '.png')