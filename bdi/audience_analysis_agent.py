from base_agent import Agent
from bdi_components import Plan


class AudienceAnalysisAgent(Agent):
    def __init__(self, agent_id="AudienceAnalysisAgent"):
        super().__init__(agent_id)
        # Initial Beliefs (expanded)
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
        self.add_belief(
            "audience_trending_topics(tiktok, ['music_challenges', 'viral_dances'])")
        self.add_belief(
            "audience_trending_topics(youtube, ['tech_reviews', 'travel_vlogs'])")
        self.add_belief(
            "audience_trending_topics(instagram, ['fashion_trends', 'wellness_tips'])")

        # Additional Desires
        self.add_desire(
            "analyze_engagement_trends(tiktok, genz)", priority=0.8)
        self.add_desire(
            "predict_future_content_preferences(youtube, general)", priority=0.7)
        self.add_desire(
            "evaluate_effectiveness_of_content_styles(instagram, millennials_genz)", priority=0.6)
        self.add_desire(
            "identify_influential_audience_segments(tiktok)", priority=0.9)
        self.add_desire("track_emerging_trends(youtube)", priority=0.85)

    def _build_plan_library(self):
        # Define plans for the Audience Analysis Agent
        plans = [
            Plan(name="GenerateAudienceInsightsPlan", goal_predicate="generate_audience_insights", steps=[
                "analyze_video_potential", "consult_beliefs", "formulate_insights", "send_insights_to_creator"]),
            Plan(name="AnalyzeEngagementTrendsPlan", goal_predicate="analyze_engagement_trends", steps=[
                "collect_recent_engagement_data", "identify_trends", "update_beliefs_with_trends"]),
            Plan(name="PredictFutureContentPreferencesPlan", goal_predicate="predict_future_content_preferences", steps=[
                "analyze_historical_data", "apply_prediction_model", "update_beliefs_with_predictions"]),
            Plan(name="EvaluateContentStylesPlan", goal_predicate="evaluate_effectiveness_of_content_styles", steps=[
                "gather_style_performance_data", "analyze_effectiveness", "send_style_evaluation_to_creator"]),
            Plan(name="IdentifyInfluentialSegmentsPlan", goal_predicate="identify_influential_audience_segments", steps=[
                "collect_audience_interaction_data", "identify_key_segments", "update_beliefs_with_segments"]),
            Plan(name="TrackEmergingTrendsPlan", goal_predicate="track_emerging_trends", steps=[
                "monitor_new_content", "identify_new_trends", "update_beliefs_with_emerging_trends"])
        ]
        return plans
