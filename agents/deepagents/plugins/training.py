from agents.deepagents.plugins.base import Plugin
class TrainingPlugin(Plugin):
    name = "training"
    def preamble(self, spec):
        return "You manage U-Net model training, datasets, and the trainer pipeline."
