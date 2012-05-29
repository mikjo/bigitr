import ConfigParser

class Config(ConfigParser.SafeConfigParser):
    def __init__(self, configFile, defaults={}):
        ConfigParser.SafeConfigParser.__init__(self, defaults)
        if isinstance(configFile, str):
            self.readConfig(self.openConfig(configFile))
        else:
            self.readConfig(configFile)
        self.requireAbsolutePaths()

    def requireAbsolutePaths(self, *sections):
        sections = set(sections)
        for section in self.sections():
            for option in self.options(section):
                if option in sections or option.endswith('dir'):
                    value = self.get(section, option)
                    if not value.startswith('/'):
                        raise ValueError('"[%s] %s = %s":'
                            ' Value must be absolute path starting with /'
                            %(section, option, value))

    def openConfig(self, configFileName):
        return open(configFileName)

    def readConfig(self, configFile):
        self.readfp(configFile)
