"""ScorerPlugin — adds ABM scoring tools and after_task hook for auto-scoring."""
from agents.deepagents.plugins.base import Plugin

class ScorerPlugin(Plugin):
    name = "scoring"
    
    def preamble(self, spec):
        return (
            "After any ABM code change, the scoring pipeline runs automatically. "
            "You do NOT need to invoke it manually. The ScorerPlugin handles this via after_task hook."
        )
    
    def hooks(self, spec):
        def after_task(ctx):
            """Auto-run score_then_compare after any ABM task."""
            # Import here to avoid circular
            from agents.deepagents.cycles.score_then_compare import score_then_compare
            return score_then_compare(ctx)
        return {"after_task": after_task}
