from base_agent import Agent
from bdi_components import Plan

class AudienceAnalysisAgent(Agent):
    def __init__(self, agent_id="AudienceAnalysisAgent"):
        super().__init__(agent_id)
        # Initial Beliefs (simplified)
        self.add_belief("audience_demographics(tiktok, genz)")
        self.add_belief("audience_demographics(instagram, millennials_genz)")
        self.add_belief("audience_demographics(youtube, general)")
        self.add_belief(
            "audience_content_preferences(genz, tiktok, [dance, challenges, memes])")
        self.add_belief(
            "audience_content_preferences(millennials_genz, instagram, [lifestyle, aesthetics, stories])")
        self.add_belief(
            "audience_content_preferences(general, youtube, [educational, vlogs, tutorials])")
        self.add_belief(
            "audience_engagement_patterns(genz, tiktok, short_attention_span)")
        self.add_belief(
            "audience_engagement_patterns(general, youtube, longer_watch_time)")

    def _build_plan_library(self):
        # Define plans for the Audience Analysis Agent
        plans = [
            Plan(name="GenerateAudienceInsightsPlan", goal_predicate="generate_audience_insights", steps=[
                 "analyze_video_potential", "consult_beliefs", "formulate_insights", "send_insights_to_creator"])
        ]
        return plans

