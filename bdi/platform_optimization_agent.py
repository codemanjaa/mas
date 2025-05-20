from base_agent import Agent
from bdi_components import Plan
import threading


class PlatformOptimizationAgent(Agent):
    def __init__(self, agent_id="PlatformOptimizationAgent"):
        super().__init__(agent_id)
        self._stop_event = threading.Event()
        # Initial Beliefs (simplified)
        self.add_belief("platform_requirements(tiktok, short_video, vertical)")
        self.add_belief(
            "platform_requirements(instagram, visual_focus, varied_formats)")
        self.add_belief(
            "platform_requirements(youtube, longer_form, horizontal)")
        self.add_belief(
            "platform_algorithm_factors(tiktok, [trend_participation, watch_time, sound_usage])")
        self.add_belief(
            "platform_algorithm_factors(instagram, [visual_appeal, engagement, hashtags])")
        self.add_belief(
            "platform_algorithm_factors(youtube, [watch_time, SEO, topic_authority])")
        self.add_belief(
            "current_trends(tiktok, [dance_challenges, lip_syncs])")
        self.add_belief(
            "current_trends(youtube, [vlogs, educational_snippets])")
        self.add_belief("current_trends(instagram, [lifestyle_posts, reels])")

    def stop(self):
        self._stop_event.set()
        print("The platform optimization agent is stop receving the singnal")

    def _build_plan_library(self):
        # Define plans for the Platform Optimization Agent
        plans = [
            Plan(name="GenerateRecommendationsPlan", goal_predicate="generate_recommendations", steps=[
                 "analyze_video", "consult_beliefs", "formulate_recommendations", "send_recommendations_to_creator"])
        ]
        return plans
