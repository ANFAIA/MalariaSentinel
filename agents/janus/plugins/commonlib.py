from agents.janus.plugins.base import Plugin
class CommonlibPlugin(Plugin):
    name = "commonlib"
    def preamble(self, spec):
        return "You manage shared config, paths, and AOI primitives in mal-commonlib."
