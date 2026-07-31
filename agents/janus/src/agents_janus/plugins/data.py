from agents_janus.plugins.base import Plugin
class DataPlugin(Plugin):
    name = "data"
    def preamble(self, spec):
        return "You manage the data manifest, naming conventions, and completeness validation."
