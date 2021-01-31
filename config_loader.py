import json

def load_config():
    try:
        f = open('data/config.json', 'r')
        dat = json.load(f)
        f.close()
    except FileNotFoundError:
        f = open('data/config_default.json', 'r')
        dat = json.load(f)
        f.close()
        f = open('data/config.json', 'w')
        f.write(json.dumps(dat))
        f.close()
    return dat

config = load_config()
