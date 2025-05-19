from base_agent import Agent
from bdi_components import Plan


class FeedbackAgent(Agent):
    def __init__(self, agent_id="FeedbackAgent"):
        super().__init__(agent_id)
        # Feedback Agent primarily reacts to messages/requests
        self.add_belief("feedback_source(tiktok, quick_comments)")
        self.add_belief("feedback_source(youtube, detailed_comments)")
        self.add_belief("feedback_source(instagram, story_reactions)")
        self.add_belief("feedback_quality(high_engagement_posts, valuable)")

        # Desires
        self.add_desire("monitor_tiktok_feedback(video_id)", priority=0.8)
        self.add_desire("monitor_youtube_feedback(video_id)", priority=0.9)
        self.add_desire("monitor_instagram_feedback(video_id)", priority=0.7)
        self.add_desire("evaluate_feedback_quality(video_id)", priority=0.95)

    def _build_plan_library(self):
        # Define plans for the Feedback Agent
        plans = [
            Plan(name="CollectFeedbackPlan", goal_predicate="collect_all_feedback", steps=[
                "monitor_feedback_sources", "receive_suggestions", "receive_comments"]),
            Plan(name="ConsolidateFeedbackPlan", goal_predicate="consolidate_feedback", steps=[
                "gather_feedback_beliefs", "structure_feedback", "send_feedback_to_creator"]),
            Plan(name="MonitorTikTokFeedbackPlan", goal_predicate="monitor_tiktok_feedback", steps=[
                "retrieve_comments", "filter_quick_comments", "store_feedback_beliefs"]),
            Plan(name="MonitorYouTubeFeedbackPlan", goal_predicate="monitor_youtube_feedback", steps=[
                "retrieve_comments", "analyze_detailed_comments", "store_feedback_beliefs"]),
            Plan(name="MonitorInstagramFeedbackPlan", goal_predicate="monitor_instagram_feedback", steps=[
                "retrieve_story_reactions", "filter_relevant_reactions", "store_feedback_beliefs"]),
            Plan(name="EvaluateFeedbackQualityPlan", goal_predicate="evaluate_feedback_quality", steps=[
                "collect_high_engagement_feedback", "assess_feedback_value", "update_feedback_quality_beliefs"])
        ]
        return plans
