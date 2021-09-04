from flask import request

from templates import templates

new_pages = {}

def page(page_func):
    new_pages[page_func.__name__] = page_func

def generate_header(title='Hitbloq', desc='a competitive beat saber service', image='https://hitbloq.com/static/hitbloq.png', additional_css=[], additional_js=[]):
    header = '<title>' + title + '</title>\n'
    header += '<link rel="icon" href="https://hitbloq.com/static/hitbloq.png">\n'
    header += '<meta property="og:image" content="' + image + '">\n'
    header += '<meta property="og:image:secure_url" content="' + image + '">\n'
    header += '<meta property="og:title" content="' + title + '">\n'
    header += '<meta property="og:description" content="' + desc + '">\n'
    header += '<meta property="og:type" content="website">\n'
    header += '<meta property="og:url" content="' + request.path + '">\n'
    header += '<meta property="og:site_name" content="Hitbloq">\n'
    for css_file in additional_css:
        header += '<link rel="stylesheet" href="/static/css/' + css_file + '">\n'
    for js_file in additional_css:
        header += '<script src="/static/js/' + js_file + '"></script>\n'
    return header

def page_setup():
    setup_data = {}
    return setup_data

@page
def home():
    header = generate_header(additional_css=['new_home.css'])
    setup_data = page_setup()
    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_home', {})})
    return html

@page
def about():
    header = generate_header(additional_css=['new_about.css'])
    setup_data = page_setup()
    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_about', {})})
    return html

@page
def map_pools():
    header = generate_header(additional_css=['new_map_pools.css'], additional_js=['new_map_pools.js'])
    setup_data = page_setup()
    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_map_pools', {})})
    return html
