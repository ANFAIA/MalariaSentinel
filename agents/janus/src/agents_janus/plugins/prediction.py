from agents_janus.plugins.base import Plugin
class PredictionPlugin(Plugin):
    name = "prediction"
    def preamble(self, spec):
        return "You generate risk raster predictions using the trained U-Net model."
