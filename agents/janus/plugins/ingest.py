from agents.janus.plugins.base import Plugin
class IngestPlugin(Plugin):
    name = "ingest"
    def preamble(self, spec):
        return "You build environment tensors, host density rasters, and mobility matrices from raw data."
