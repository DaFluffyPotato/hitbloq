def max_score(notes):
    if notes >= 13:
        max_score = (notes - 13) * 8 * 115 + 4715
    else:
        score_table = [115,345,575,805,1035,1495,1955,2415,2875,3335,3795,4255]
        max_score = score_table[notes - 1]
    return max_score

diff_shorten = {
    'ExpertPlus': 'ep',
    'Expert': 'ex',
    'Hard': 'h',
    'Normal': 'n',
    'Easy': 'e',
}

char_shorten = {
    'SoloStandard': 's',
}

diff_lengthen = {v: k for k, v in diff_shorten.items()}
char_lengthen = {v: k for k, v in char_shorten.items()}

def shorten_settings(settings_str):
    diff = settings_str.split('_')[1]
    char = settings_str.split('_')[2]
    return diff_shorten[diff] + '_' + char_shorten[char]

def lengthen_settings(settings_str):
    diff = settings_str.split('_')[0]
    char = settings_str.split('_')[1]
    return '_' + diff_lengthen[diff] + '_' + char_lengthen[char]
