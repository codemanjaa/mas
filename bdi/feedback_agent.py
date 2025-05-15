from base_agent import Agent
from bdi_components import Plan


class FeedbackAgent(Agent):
    def __init__(self, agent_id="FeedbackAgent"):
        super().__init__(agent_id)
        # Feedback Agent primarily reacts to messages/requests

    def _build_plan_library(self):
        # Define plans for the Feedback Agent
        plans = [
            # This plan would ideally be triggered by a request or run continuously
            Plan(name="CollectFeedbackPlan", goal_predicate="collect_all_feedback", steps=[
                 "monitor_feedback_sources", "receive_suggestions", "receive_comments"]),
            Plan(name="ConsolidateFeedbackPlan", goal_predicate="consolidate_feedback", steps=[
                 "gather_feedback_beliefs", "structure_feedback", "send_feedback_to_creator"])
        ]
        return plans
