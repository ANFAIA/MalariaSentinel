from agents.deepagents.plugins.base import Plugin
class DownloadPlugin(Plugin):
    name = "download"
    def preamble(self, spec):
        return "You manage data downloads via the mal_core.download registry. Use manifest to track state."
