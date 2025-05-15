from bdi_components import Belief, Desire, Plan, Intention


class Agent:
    """Base class for all agents in the system."""

    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.beliefs = set()  # Using a set for beliefs for easier checking
        self.desires = set()  # Using a set for desires
        self.intentions = set()  # Using a set for intentions
        self.message_queue = []  # For inter-agent communication
        self.plan_library = self._build_plan_library()  # Agent's available plans

    def add_belief(self, belief_content, strength=1.0):
        """Adds a belief to the agent's belief base."""
        belief = Belief(belief_content, strength)
        if belief not in self.beliefs:
            self.beliefs.add(belief)
            print(f"{self.agent_id} added belief: {belief.content}")

    def add_desire(self, goal_content, priority=1.0):
        """Adds a desire to the agent's desire set."""
        desire = Desire(goal_content, priority)
        if desire not in self.desires:
            self.desires.add(desire)
            print(f"{self.agent_id} added desire: {desire.goal}")

    def remove_desire(self, goal_content):
        """Removes a desire from the agent's desire set."""
        desire_to_remove = next(
            (d for d in self.desires if d.goal == goal_content), None)
        if desire_to_remove:
            self.desires.remove(desire_to_remove)
            # Uncomment for detailed desire logging
            print(f"{self.agent_id} removed desire: {goal_content}")

    def receive_message(self, message):
        """Receives a message from another agent."""
        self.message_queue.append(message)
        # Uncomment for detailed message logging
        print(f"{self.agent_id} received message: {message}")

    def process_messages(self):
        """Processes messages in the message queue."""
        while self.message_queue:
            message = self.message_queue.pop(0)
            # Uncomment for detailed message processing logging
            print(f"{self.agent_id} processing message: {message}")
            # Parse message content and update beliefs/desires based on message type
            message_type = message.get("type")
            video_id = message.get("video_id")
            sender = message.get("sender")

            if message_type == "recommendations" and video_id:
                recommendations = message.get("recommendations")
                self.add_belief(
                    f"recommendations_received({video_id}, {recommendations})")
                # Receiving recommendations creates a desire to adapt content
                self.add_desire(
                    f"adapt_content({video_id}, {recommendations})")

            elif message_type == "insights" and video_id:
                insights = message.get("insights")
                self.add_belief(f"insights_received({video_id}, {insights})")
                # Insights primarily inform beliefs, the desire to adapt comes from recommendations

            elif message_type == "feedback" and video_id:
                feedback = message.get("feedback")
                self.add_belief(f"feedback_received({video_id}, {feedback})")
                # Receiving feedback creates a desire to process it
                self.add_desire(f"process_feedback({video_id}, {feedback})")

            elif message_type == "request_suggestions" and video_id and self.agent_id == "FeedbackAgent":
                # If Feedback Agent receives a request for suggestions, it desires to collect them
                self.add_desire(f"collect_all_feedback({video_id})")

            elif message_type == "consult_platform" and video_id and self.agent_id == "PlatformOptimizationAgent":
                # If Platform Agent is consulted, it desires to generate recommendations
                platform = message.get("platform")
                goal = message.get("goal")
                self.add_desire(
                    f"generate_recommendations({video_id}, {platform}, {goal})")

            elif message_type == "consult_audience" and video_id and self.agent_id == "AudienceAnalysisAgent":
                # If Audience Agent is consulted, it desires to generate insights
                audience = message.get("audience")
                goal = message.get("goal")
                self.add_desire(
                    f"generate_audience_insights({video_id}, {audience}, {goal})")

    def _build_plan_library(self):
        """Builds the agent's plan library. To be implemented by subclasses."""
        return []

    def deliberate(self):
        """
        The deliberation cycle: choose which desires to pursue and form intentions.
        More sophisticated deliberation logic than before.
        """
        print(
            f"\n{self.agent_id} deliberating...")  # Uncomment for detailed deliberation logging
        new_intentions = set()

        # Consider current desires, prioritizing higher priority ones
        for desire in sorted(list(self.desires), key=lambda d: d.priority, reverse=True):
            # Check if the desire is already an active intention
            if not any(int.desire.goal == desire.goal and int.status == "active" for int in self.intentions):
                # Find a suitable plan for this desire
                suitable_plan = self._find_plan(desire)
                if suitable_plan:
                    new_intention = Intention(desire)
                    new_intention.plan = suitable_plan
                    new_intentions.add(new_intention)
                    # Uncomment for detailed intention logging
                    print(
                        f"{self.agent_id} formed intention: {new_intention.desire.goal} with plan {suitable_plan.name}")
                else:
                    # Uncomment if plans are missing
                    print(
                        f"{self.agent_id} could not find a plan for desire: {desire.goal}")

        # Add new intentions to the agent's set
        self.intentions.update(new_intentions)

        # Remove desires that have become intentions
        self.desires = {d for d in self.desires if not any(
            int.desire.goal == d.goal for int in self.intentions)}

        # Reconsider existing intentions (simplified: in a real system, agents might drop intentions
        # if beliefs change, goals are achieved by others, or plans fail)
        # For this simulation, we primarily rely on plan execution to mark intentions as achieved.
        pass

    def _find_plan(self, desire):
        """Finds a suitable plan from the plan library for a given desire."""
        # Simple plan selection: find the first plan whose goal predicate is contained in the desire's goal string
        for plan in self.plan_library:
            if plan.goal_predicate in desire.goal:
                return plan
        return None  # No suitable plan found

    def execute_intentions(self):
        """
        Executes the plans associated with active intentions.
        Includes more detailed simulation logic for agent interactions and state changes.
        """
        # print(f"{self.agent_id} executing intentions...") # Uncomment for detailed execution logging
        completed_intentions = set()
        # Iterate over a copy as we might modify the set
        for intention in list(self.intentions):
            if intention.status == "active" and intention.plan:
                # print(f"{self.agent_id} executing plan '{intention.plan.name}' for intention '{intention.desire.goal}'") # Uncomment for detailed execution logging
                plan = intention.plan
                goal = intention.desire.goal

                # --- Simulated Plan Step Execution Based on Intention Goal ---
                # This section simulates the outcome of executing the plan for the intention's goal.
                # In a real BDI system, plans would have explicit steps executed sequentially.

                if "upload_video" in goal:
                    parts = goal.split('(')[1].split(')')[0].split(', ')
                    video_id = parts[0]
                    platform = parts[1]
                    print(
                        f"  {self.agent_id} -> Simulating uploading {video_id} to {platform}...")
                    # Simulate success by adding a belief
                    self.add_belief(f"video_uploaded({video_id}, {platform})")
                    completed_intentions.add(intention)
                    print(
                        f"  {self.agent_id} -> Uploaded {video_id} to {platform}.")

                elif "request_suggestions" in goal:
                    video_id = goal.split('(')[1].split(')')[0]
                    print(
                        f"  {self.agent_id} -> Simulating requesting suggestions for {video_id}...")
                    # Simulate sending message to Feedback Agent
                    feedback_agent = next(
                        (a for a in agents if a.agent_id == "FeedbackAgent"), None)
                    if feedback_agent:
                        feedback_agent.receive_message(
                            {"type": "request_suggestions", "video_id": video_id, "sender": self.agent_id})
                    completed_intentions.add(intention)
                    print(
                        f"  {self.agent_id} -> Requested suggestions for {video_id}.")

                elif "consult_platform_agent" in goal:
                    parts = goal.split('(')[1].split(')')[0].split(', ')
                    video_id = parts[0]
                    platform = parts[1]
                    goal_type = parts[2]
                    print(
                        f"  {self.agent_id} -> Simulating consulting Platform Agent for {video_id} on {platform} for {goal_type}...")
                    # Simulate sending message to Platform Optimization Agent
                    platform_agent = next(
                        (a for a in agents if a.agent_id == "PlatformOptimizationAgent"), None)
                    if platform_agent:
                        platform_agent.receive_message(
                            {"type": "consult_platform", "video_id": video_id, "platform": platform, "goal": goal_type, "sender": self.agent_id})
                    completed_intentions.add(intention)
                    print(
                        f"  {self.agent_id} -> Consulted Platform Agent for {video_id}.")

                elif "consult_audience_agent" in goal:
                    parts = goal.split('(')[1].split(')')[0].split(', ')
                    video_id = parts[0]
                    audience = parts[1]
                    goal_type = parts[2]
                    print(
                        f"  {self.agent_id} -> Simulating consulting Audience Agent for {video_id} for {audience} for {goal_type}...")
                    # Simulate sending message to Audience Analysis Agent
                    audience_agent = next(
                        (a for a in agents if a.agent_id == "AudienceAnalysisAgent"), None)
                    if audience_agent:
                        audience_agent.receive_message(
                            {"type": "consult_audience", "video_id": video_id, "audience": audience, "goal": goal_type, "sender": self.agent_id})
                    completed_intentions.add(intention)
                    print(
                        f"  {self.agent_id} -> Consulted Audience Agent for {video_id}.")

                elif "generate_recommendations" in goal and self.agent_id == "PlatformOptimizationAgent":
                    parts = goal.split('(')[1].split(')')[0].split(', ')
                    video_id = parts[0]
                    platform = parts[1]
                    goal_type = parts[2]
                    print(
                        f"  {self.agent_id} -> Simulating generating recommendations for {video_id} on {platform} for {goal_type}...")
                    # Simulate generating recommendations based on beliefs and goal
                    recommendations = {}
                    if platform == "tiktok" and goal_type == "virality":
                        recommendations = {
                            "resolution": "1080x1920", "style": "fast-paced", "sound": "trending_track", "duration": "15s"}
                    elif platform == "youtube" and goal_type == "retention":
                        recommendations = {
                            "resolution": "1920x1080", "style": "detailed", "SEO": "keywords"}
                    elif platform == "instagram" and goal_type == "branding":
                        recommendations = {
                            "format": "reel", "style": "aesthetic", "hashtags": "relevant_tags"}
                    # Add more complex recommendation logic here based on beliefs

                    # Simulate sending message back to Creator Agent
                    creator_agent = next(
                        (a for a in agents if a.agent_id == "CreatorAgent"), None)
                    if creator_agent:
                        creator_agent.receive_message(
                            {"type": "recommendations", "video_id": video_id, "recommendations": recommendations, "sender": self.agent_id})
                    completed_intentions.add(intention)
                    print(
                        f"  {self.agent_id} -> Generated and sent recommendations for {video_id}.")

                elif "generate_audience_insights" in goal and self.agent_id == "AudienceAnalysisAgent":
                    parts = goal.split('(')[1].split(')')[0].split(', ')
                    video_id = parts[0]
                    audience = parts[1]
                    goal_type = parts[2]
                    print(
                        f"  {self.agent_id} -> Simulating generating insights for {video_id} for {audience} for {goal_type}...")
                    # Simulate generating insights based on beliefs and goal
                    insights = {}
                    if audience == "genz" and goal_type == "virality":
                        insights = {"engagement_pattern": "short_attention_span", "preferred_content": [
                            "dance", "challenges", "memes"]}
                    elif audience == "general" and goal_type == "retention":
                        insights = {"engagement_pattern": "longer_watch_time", "preferred_content": [
                            "educational", "vlogs", "tutorials"]}
                    elif audience == "millennials_genz" and goal_type == "branding":
                        insights = {"engagement_pattern": "visual_engagement", "preferred_content": [
                            "lifestyle", "aesthetics", "stories"]}
                    # Add more complex insight logic here based on beliefs

                    # Simulate sending message back to Creator Agent
                    creator_agent = next(
                        (a for a in agents if a.agent_id == "CreatorAgent"), None)
                    if creator_agent:
                        creator_agent.receive_message(
                            {"type": "insights", "video_id": video_id, "insights": insights, "sender": self.agent_id})
                    completed_intentions.add(intention)
                    print(
                        f"  {self.agent_id} -> Generated and sent audience insights for {video_id}.")

                elif "collect_all_feedback" in goal and self.agent_id == "FeedbackAgent":
                    video_id = goal.split('(')[1].split(')')[0]
                    # print(f"  {self.agent_id} -> Simulating collecting feedback for {video_id}...") # Uncomment for detailed feedback collection
                    # Simulate receiving feedback over time
                    received_suggestions = [
                        b.content for b in self.beliefs if f"suggestions_received({video_id}" in b.content]
                    received_comments = [
                        b.content for b in self.beliefs if f"comments_received({video_id}" in b.content]

                    # Simulate random arrival of new feedback
                    if random.random() < 0.4:  # Chance of receiving new feedback in a cycle
                        new_feedback_content = random.choice([
                            f"suggestions_received({video_id}, ['Looks good!'])",
                            f"suggestions_received({video_id}, ['Could improve audio.'])",
                            f"comments_received({video_id}, ['Loved it!'])",
                            f"comments_received({video_id}, ['What software did you use?'])",
                            f"suggestions_received({video_id}, ['Try a different hook.'])"
                        ])
                        self.add_belief(new_feedback_content)
                        # print(f"  {self.agent_id} -> Received new feedback for {video_id}: {new_feedback_content}") # Uncomment for detailed feedback logging

                    # If enough feedback is collected (simulated condition: at least 2 unique pieces of feedback)
                    all_feedback_contents = set(
                        [b.content for b in self.beliefs if f"suggestions_received({video_id}" in b.content or f"comments_received({video_id}" in b.content])
                    if len(all_feedback_contents) >= 2:
                        self.add_desire(f"consolidate_feedback({video_id})")
                        # Intention to listen is achieved when consolidation is desired
                        completed_intentions.add(intention)
                        print(
                            f"  {self.agent_id} -> Enough feedback collected for {video_id}, desiring consolidation.")
                    else:
                        # Intention remains active, keep listening in the next cycle
                        pass

                elif "consolidate_feedback" in goal and self.agent_id == "FeedbackAgent":
                    video_id = goal.split('(')[1].split(')')[0]
                    print(
                        f"  {self.agent_id} -> Simulating consolidating feedback for {video_id}...")
                    consolidated = []
                    # Gather all relevant feedback beliefs
                    for belief in self.beliefs:
                        if f"suggestions_received({video_id}" in belief.content or f"comments_received({video_id}" in belief.content:
                            # Simple consolidation: just add the content of the belief
                            consolidated.append(belief.content)

                    # Simulate sending consolidated feedback to Creator Agent
                    creator_agent = next(
                        (a for a in agents if a.agent_id == "CreatorAgent"), None)
                    if creator_agent:
                        creator_agent.receive_message(
                            {"type": "feedback", "video_id": video_id, "feedback": consolidated, "sender": self.agent_id})
                    completed_intentions.add(intention)
                    print(
                        f"  {self.agent_id} -> Consolidated and sent feedback for {video_id}.")

                elif "process_feedback" in goal and self.agent_id == "CreatorAgent":
                    parts = goal.split('(')[1].split(')')[0].split(', ')
                    video_id = parts[0]
                    # In a real system, this would involve analyzing the feedback content (parts[1])
                    print(
                        f"  {self.agent_id} -> Simulating processing feedback for {video_id}...")
                    # Based on processing feedback, the Creator Agent might decide to adapt the content
                    # Simulate adding a desire to adapt based on feedback
                    self.add_desire(
                        f"adapt_content({video_id}, 'based_on_feedback')")
                    completed_intentions.add(intention)
                    print(
                        f"  {self.agent_id} -> Processed feedback for {video_id}.")

                elif "adapt_content" in goal and self.agent_id == "CreatorAgent":
                    parts = goal.split('(')[1].split(')')[0].split(', ')
                    video_id = parts[0]
                    # In a real system, this would involve using the suggestions/feedback (parts[1])
                    print(
                        f"  {self.agent_id} -> Simulating adapting content for {video_id}...")
                    # Simulate adding a belief that the content has been adapted
                    self.add_belief(f"content_adapted({video_id})")
                    completed_intentions.add(intention)
                    print(
                        f"  {self.agent_id} -> Content adapted for {video_id}.")

                elif "achieve_virality" in goal and self.agent_id == "CreatorAgent":
                    # This is a higher-level goal. The plan involves sub-goals handled by other intentions.
                    # The 'AchieveViralityPlan' steps are simulated by other intentions being formed and executed.
                    # We can consider this intention achieved if the content has been adapted for virality
                    # and potentially if some simulated performance metric is met.
                    video_id = goal.split('(')[1].split(',')[0]
                    # Simplified check
                    if self.has_belief(f"content_adapted({video_id})"):
                        print(
                            f"  {self.agent_id} -> Simulating checking virality for {video_id}...")
                        if random.random() < 0.3:  # Simulate a chance of achieving virality
                            self.add_belief(f"content_viral({video_id})")
                            completed_intentions.add(intention)
                            print(
                                f"  {self.agent_id} -> Achieved virality for {video_id} (simulated).")
                        else:
                            # Keep monitoring or try different adaptation strategies (more complex planning)
                            pass  # Intention remains active

                elif "optimize_for_platform" in goal and self.agent_id == "CreatorAgent":
                    # Similar to virality, this goal is achieved through sub-goals (consulting agents, adapting)
                    video_id = goal.split('(')[1].split(',')[0]
                    platform = goal.split(', ')[1].split(')')[0]
                    # Simplified check
                    if self.has_belief(f"content_adapted({video_id})"):
                        completed_intentions.add(intention)
                        print(
                            f"  {self.agent_id} -> Optimized {video_id} for {platform} (simulated).")
                    else:
                        # Wait for adaptation to happen
                        pass  # Intention remains active

                elif "build_branding" in goal and self.agent_id == "CreatorAgent":
                    # This is a long-term goal. Its 'execution' involves continuously pursuing other goals
                    # like uploading, optimizing, getting feedback, etc.
                    # For simulation, we can consider it partially achieved as other content goals are met.
                    # It would likely never be 'completed' in a simple simulation.
                    pass  # Intention remains active throughout the simulation

                # Mark intention as achieved if it's in the completed set
                if intention in completed_intentions:
                    intention.status = "achieved"
                    # print(f"  Intention '{intention.desire.goal}' achieved.") # Uncomment for detailed intention status logging

        # Remove completed intentions
        self.intentions = {
            int for int in self.intentions if int.status != "achieved"}
        # if completed_intentions:
        # print(f"{self.agent_id} removed {len(completed_intentions)} completed intentions.") # Uncomment for detailed intention logging

    def has_belief(self, belief_content):
        """Helper to check if the agent has a specific belief by content."""
        return Belief(belief_content) in self.beliefs

    def run_cycle(self):
        """Runs one cycle of the agent's BDI loop."""
        self.process_messages()  # Sense/process communication
        # Sense environment (placeholder - would update beliefs based on external state)
        self.deliberate()  # Decide on intentions
        self.execute_intentions()  # Act based on intentions
        # Optional: Print current state for debugging
        # print(f"{self.agent_id} beliefs: {[b.content for b in self.beliefs]}")
        # print(f"{self.agent_id} desires: {[d.goal for d in self.desires]}")
        # print(f"{self.agent_id} intentions: {[f'{i.desire.goal} ({i.status})' for i in self.intentions]}")
