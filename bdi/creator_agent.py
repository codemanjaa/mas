from bdi_components import Plan
from base_agent import Agent
import threading


class CreatorAgent(Agent):
    def __init__(self, agent_id="CreatorAgent"):
        super().__init__(agent_id)

        self._stop_event = threading.Event()
        # Initial Beliefs
        self.add_belief("tiktok_popular_genz")
        self.add_belief("instagram_popular_millennials")
        self.add_belief("youtube_popular_general")
        self.add_belief("platform_optimization_agent_available")
        self.add_belief("audience_analysis_agent_available")
        self.add_belief("feedback_agent_available")

        # Initial Desires (Scenario 1: Optimize Dance Video for TikTok Virality)
        self.add_desire(
            "achieve_virality(dance_video_01, tiktok)", priority=0.9)
        self.add_desire("upload_video(dance_video_01, tiktok)", priority=0.8)
        self.add_desire("get_suggestions(dance_video_01)",
                        priority=0.7)  # Desire feedback

        # Initial Desires (Scenario 2: Educational Snippet Feedback)
        self.add_desire("upload_video(edu_snippet_01, youtube)", priority=0.6)
        self.add_desire("get_suggestions(edu_snippet_01)",
                        priority=0.5)  # Desire feedback

        # Initial Desires (Scenario 3: Cross-Platform Branding)
        self.add_desire("build_branding", priority=1.0)
        self.add_desire(
            "optimize_for_platform(vlog_highlight_01, instagram)", priority=0.4)
        self.add_desire(
            "optimize_for_platform(vlog_highlight_01, tiktok)", priority=0.3)
        # Assume vlog_highlight_01 is already "uploaded" to YouTube for this scenario
        self.add_belief("video_uploaded(vlog_highlight_01, youtube)")

        # General Desires
        self.add_desire("monetize_content", priority=0.2)
        # Note: Monetization is a complex, long-term goal that would involve many sub-goals and plans.
        # It's included as a desire but not fully implemented in the simulation plans.

    def stop(self):
        self._stop_event.set()
        print("The creator agent is stop receving the singnal")

    def _build_plan_library(self):
        # Define plans for the Creator Agent
        plans = [
            # Basic Action Plans
            Plan(name="UploadVideoPlan", goal_predicate="upload_video",
                 steps=["perform_upload_action"]),
            Plan(name="RequestSuggestionsPlan", goal_predicate="request_suggestions", steps=[
                 "send_request_to_feedback_agent"]),
            Plan(name="ConsultPlatformAgentPlan", goal_predicate="consult_platform_agent", steps=[
                 "send_consult_message_to_platform_agent"]),
            Plan(name="ConsultAudienceAgentPlan", goal_predicate="consult_audience_agent", steps=[
                 "send_consult_message_to_audience_agent"]),
            Plan(name="ProcessFeedbackPlan", goal_predicate="process_feedback", steps=[
                 "analyze_feedback", "form_adaptation_desire"]),
            Plan(name="AdaptContentPlan", goal_predicate="adapt_content",
                 steps=["perform_editing_action", "update_content_belief"]),

            # Higher-Level Goal Plans
            # Plan for achieving virality - involves consulting other agents and adapting
            Plan(name="AchieveViralityPlan", goal_predicate="achieve_virality", steps=[
                # Triggers ConsultPlatformAgentPlan intention
                "consult_platform_agent_for_virality",
                # Triggers ConsultAudienceAgentPlan intention
                "consult_audience_agent_for_virality",
                # Handled by message processing adding adapt_content desire
                "wait_for_recommendations_and_insights",
                # Triggers AdaptContentPlan intention
                "adapt_content_based_on_recommendations_and_insights",
                # Long-term monitoring (simulated check in execute)
                "monitor_performance"
            ]),
            # Plan for optimizing for a platform - involves consulting platform agent and adapting
            Plan(name="OptimizeForPlatformPlan", goal_predicate="optimize_for_platform", steps=[
                # Triggers ConsultPlatformAgentPlan intention
                "consult_platform_agent_for_optimization",
                 # Handled by message processing adding adapt_content desire
                 "wait_for_recommendations",
                 "adapt_content_based_on_recommendations"  # Triggers AdaptContentPlan intention
                 ]),
            # Plan for building branding - a continuous process
            Plan(name="BuildBrandingPlan", goal_predicate="build_branding", steps=[
                # Would involve triggering other content creation goals
                "consistently_create_content",
                "engage_with_audience",  # Would involve interacting with platforms
                # Would involve data analysis (simulated)
                "analyze_brand_perception"
            ])
            # Add plans for monetization, etc.
        ]
        return plans
