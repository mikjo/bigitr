import os
import string
import ConfigParser

class Config(ConfigParser.SafeConfigParser):
    def __init__(self, configFile, defaults={}):
        ConfigParser.SafeConfigParser.__init__(self, defaults)
        if isinstance(configFile, str):
            self.readConfig(self.openConfig(configFile))
        else:
            self.readConfig(configFile)
        self.requireAbsolutePaths()

    optionxform = str # case sensitive

    def requireAbsolutePaths(self, *sections):
        sections = set(sections)
        for section in self.sections():
            for option in self.options(section):
                if option in sections or option.endswith('dir'):
                    value = self.get(section, option)
                    if not value.startswith('/'):
                        raise ValueError('"[%s] %s = %s":'
                            ' Value must resolve to absolute path starting with /'
                            %(section, option, value))

    def get(self, *args, **kwargs):
        # cannot use the "var" argument because the environment overrides
        # content in the file.  Using ${} instead of %()s syntax for that
        # reason.
        v = ConfigParser.SafeConfigParser.get(self, *args, **kwargs)
        t = string.Template(v)
        return t.substitute(os.environ)

    def items(self, *args, **kwargs):
        # cannot use the "var" argument because it adds a keyword for
        # each environment variable, so we have to restrict it to the
        # keywords actually present and then interpolate
        i = ConfigParser.SafeConfigParser.items(self, *args, **kwargs)
        return [(x[0], self.get(args[0], x[0])) for x in i]

    def openConfig(self, configFileName):
        return open(configFileName)

    def readConfig(self, configFile):
        self.readfp(configFile)
