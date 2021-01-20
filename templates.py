import os

from file_io import read_f

class Templates:
    def __init__(self, path):
        self.templates = {}

        for template in os.listdir(path):
            self.templates[template.split('.')[0]] = read_f(path + '/' + template)

    def inject(self, template_id, insert_map):
        template_html = self.templates[template_id]
        for key in insert_map:
            template_html = template_html.replace('\\@' + key, insert_map[key])
        return template_html

templates = Templates('data/templates')
