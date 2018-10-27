import sys


class Extension(object):
    def __init__(self, name = None):
        self.name = name

    def set_extension_name(self, name):
        if self.name:
            print('Is this a safe use-case for overwriting an extension name?')
            sys.exit(1)
        self.name = name

    def get_extension_name(self):
        return self.name
