import asyncio
import json
import logging
import time  # Using time.sleep for simulation delays, in async code prefer asyncio.sleep
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Any
import threading  # Import the threading module

import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
from spade.template import Template

# ================== Setup Logging ==================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================== FIPA ACL params ==================
# These are kept from your provided SPADE code for message metadata


class Performative:
    INFORM = "inform"
    REQUEST = "request"
    AGREE = "agree"
    REFUSE = "refuse"
    FAILURE = "failure"
    PROPOSE = "propose"


class ContentLanguage:
    JSON = "application/json"
    SL = "text/sl"


class Ontology:
    VIDEO_ANALYSIS = "video-analysis"
    TASK_REQUEST = "task-request"
    BDI_STATE = "bdi-state"  # New ontology for requesting BDI state


# ================== Data Models (from your SPADE code) ==================


@dataclass
class Position:
    x: int
    y: int
    width: int
    height: int


@dataclass
class VideoObject:
    object_type: str
    confidence: float
    position: Position

    def to_dict(self) -> Dict:
        return {
            'type': self.object_type,
            'confidence': self.confidence,
            'position': vars(self.position)
        }


@dataclass
class ColorAnalysis:
    dominant_colors: List[str]
    color_distribution: Dict[str, float]

    def to_dict(self) -> Dict:
        return {
            'dominant_colors': self.dominant_colors,
            'color_distribution': self.color_distribution
        }


@dataclass
class VideoAnalysisResult:
    objects: List[VideoObject]
    colors: ColorAnalysis

    def to_dict(self) -> Dict:
        return {
            'objects': [obj.to_dict() for obj in self.objects],
            'colors': self.colors.to_dict(),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

# ================== BDI Elements (from previous BDI code) ==================
# These are adapted to be used as internal state within SPADE agents


class Belief:
    """Represents a belief held by an agent."""

    def __init__(self, content: str, strength: float = 1.0):
        # The information or proposition (e.g., "video_uploaded(id, platform)")
        self.content = content
        self.strength = strength  # Confidence in the belief (optional)

    def __repr__(self):
        return f"Belief('{self.content}', strength={self.strength})"

    def __eq__(self, other):
        if isinstance(other, Belief):
            return self.content == other.content
        return False

    def __hash__(self):
        return hash(self.content)


class Desire:
    """Represents a desired state of affairs for an agent."""

    def __init__(self, goal: str, priority: float = 1.0):
        # The state to be achieved (e.g., "achieve_virality(id, platform)")
        self.goal = goal
        self.priority = priority  # How important this desire is (optional)

    def __repr__(self):
        return f"Desire('{self.goal}', priority={self.priority})"

    def __eq__(self, other):
        if isinstance(other, Desire):
            return self.goal == other.goal
        return False

    def __hash__(self):
        return hash(self.goal)


class Intention:
    """Represents a desire that the agent has committed to achieving."""

    def __init__(self, desire: Desire):
        self.desire = desire  # The desire being pursued
        self.status = "active"  # e.g., "active", "suspended", "achieved", "failed"
        # The plan chosen to achieve this intention (Plan object)
        self.plan = None

    def __repr__(self):
        return f"Intention(desire='{self.desire.goal}', status='{self.status}')"

    def __eq__(self, other):
        if isinstance(other, Intention):
            return self.desire == other.desire and self.status == other.status
        return False

    def __hash__(self):
        return hash((self.desire, self.status))


class Plan:
    """Represents a sequence of actions to achieve an intention."""

    def __init__(self, name: str, goal_predicate: str, steps: List[str]):
        self.name = name
        # The goal this plan aims to achieve (e.g., "upload_video")
        self.goal_predicate = goal_predicate
        # List of actions or sub-goals (used conceptually here)
        self.steps = steps

    def __repr__(self):
        return f"Plan('{self.name}', goal='{self.goal_predicate}')"


# --- 3. Base SPADE Agent with BDI Integration ---

class BaseBDI_SPADE_Agent(Agent):
    """
    A base SPADE agent that integrates BDI components and a deliberation cycle.
    The BDI cycle runs within a CyclicBehaviour.
    """

    def __init__(self, jid: str, password: str, verify_security: bool = False):
        super().__init__(jid, password, verify_security)
        self._beliefs = set()  # Internal BDI state
        self._desires = set()
        self._intentions = set()
        self._plan_library = self._build_plan_library()  # Agent's available plans
        # Event to signal the BDI behaviour to stop
        self._stop_bdi_cycle = threading.Event()

    # --- BDI State Management (Thread-safe access) ---
    # Using properties to expose copies of the internal sets for external access (e.g., monitoring)
    @property
    def beliefs(self) -> List[Belief]:
        return list(self._beliefs)

    @property
    def desires(self) -> List[Desire]:
        return list(self._desires)

    @property
    def intentions(self) -> List[Intention]:
        return list(self._intentions)

    def add_belief(self, belief_content: str, strength: float = 1.0):
        """Adds a belief to the agent's belief base."""
        belief = Belief(belief_content, strength)
        if belief not in self._beliefs:
            self._beliefs.add(belief)
            # Use debug for frequent updates
            logger.debug(f"[{self.jid}] Added belief: {belief.content}")

    def add_desire(self, goal_content: str, priority: float = 1.0):
        """Adds a desire to the agent's desire set."""
        desire = Desire(goal_content, priority)
        if desire not in self._desires:
            self._desires.add(desire)
            # Use debug for frequent updates
            logger.debug(f"[{self.jid}] Added desire: {desire.goal}")

    def remove_desire(self, goal_content: str):
        """Removes a desire from the agent's desire set."""
        desire_to_remove = next(
            (d for d in self._desires if d.goal == goal_content), None)
        if desire_to_remove:
            self._desires.remove(desire_to_remove)
            # Use debug for frequent updates
            logger.debug(f"[{self.jid}] Removed desire: {goal_content}")

    def has_belief(self, belief_content: str) -> bool:
        """Helper to check if the agent has a specific belief by content string."""
        return Belief(belief_content) in self._beliefs

    # --- BDI Cycle Methods ---

    async def process_incoming_messages(self):
        """
        Processes messages received by the agent's behaviours.
        This method is called from within the BDI cycle behaviour.
        """
        # In SPADE, messages are received by behaviours. This method
        # would typically be called by a behaviour after receiving a message.
        # For this integrated approach, we'll simulate processing messages
        # that a behaviour *would have* received and added to a queue or similar.
        # A more robust implementation might have behaviours put messages
        # into a thread-safe queue that the BDI cycle behaviour reads from.

        # For simplicity in this example, we assume behaviours that receive messages
        # directly call methods on the agent to update beliefs/desires.
        # The BDI cycle primarily focuses on deliberation and execution based on
        # the state resulting from message processing (and sensing the environment).
        pass  # Message processing is handled by specific behaviours in SPADE

    def deliberate(self):
        """
        The deliberation cycle: choose which desires to pursue and form intentions.
        This is a synchronous method called from the async BDI behaviour.
        """
        # logger.debug(f"[{self.jid}] Deliberating...")
        new_intentions = set()

        # Consider current desires, prioritizing higher priority ones
        for desire in sorted(list(self._desires), key=lambda d: d.priority, reverse=True):
            # Check if the desire is already an active intention
            if not any(int.desire.goal == desire.goal and int.status == "active" for int in self._intentions):
                # Find a suitable plan for this desire
                suitable_plan = self._find_plan(desire)
                if suitable_plan:
                    new_intention = Intention(desire)
                    new_intention.plan = suitable_plan
                    new_intentions.add(new_intention)
                    logger.info(
                        f"[{self.jid}] Formed intention: {new_intention.desire.goal} with plan {suitable_plan.name}")
                # else:
                    # logger.debug(f"[{self.jid}] Could not find a plan for desire: {desire.goal}") # Uncomment if plans are missing

        # Add new intentions to the agent's set
        self._intentions.update(new_intentions)

        # Remove desires that have become intentions
        self._desires = {d for d in self._desires if not any(
            int.desire.goal == d.goal for int in self._intentions)}

        # Reconsider existing intentions (simplified)
        # Agents might drop intentions if beliefs change, goals are achieved by others, or plans fail.
        # This simulation primarily relies on plan execution to mark intentions as achieved.
        pass

    async def execute_intentions(self):
        """
        Executes the plans associated with active intentions.
        This is an asynchronous method called from the BDI behaviour.
        """
        # logger.debug(f"[{self.jid}] Executing intentions...")
        completed_intentions = set()
        # Iterate over a copy as we might modify the set
        for intention in list(self._intentions):
            if intention.status == "active" and intention.plan:
                # print(f"[{self.jid}] Executing plan '{intention.plan.name}' for intention '{intention.desire.goal}'") # Uncomment for detailed execution logging
                plan = intention.plan
                goal = intention.desire.goal

                # --- Simulated Plan Step Execution Based on Intention Goal ---
                # This section simulates the outcome of executing the plan for the intention's goal.
                # In a real BDI system, plans would have explicit steps executed sequentially.
                # Here, we map intention goals to simulated actions or message sending.

                if "upload_video" in goal:
                    parts = goal.split('(')[1].split(')')[0].split(', ')
                    video_id = parts[0].strip()
                    platform = parts[1].strip()
                    logger.info(
                        f"[{self.jid}] -> Simulating uploading {video_id} to {platform}...")
                    await asyncio.sleep(0.1)  # Simulate async work
                    self.add_belief(f"video_uploaded({video_id}, {platform})")
                    completed_intentions.add(intention)
                    logger.info(
                        f"[{self.jid}] -> Uploaded {video_id} to {platform}.")

                elif "request_suggestions" in goal:
                    video_id = goal.split('(')[1].split(')')[0].strip()
                    logger.info(
                        f"[{self.jid}] -> Requesting suggestions for {video_id}...")
                    await asyncio.sleep(0.1)  # Simulate async work
                    # Simulate sending message to Feedback Agent using SPADE's messaging
                    # Assuming FeedbackAgent JID
                    msg = Message(to="feedback@localhost")
                    msg.set_metadata("performative", Performative.REQUEST)
                    # Using a generic task request ontology
                    msg.set_metadata("ontology", Ontology.TASK_REQUEST)
                    msg.body = json.dumps(
                        {"task": "get_suggestions", "video_id": video_id})
                    await self.send(msg)
                    completed_intentions.add(intention)
                    logger.info(
                        f"[{self.jid}] -> Requested suggestions for {video_id}.")

                elif "consult_platform_agent" in goal:
                    parts = goal.split('(')[1].split(')')[0].split(', ')
                    video_id = parts[0].strip()
                    platform = parts[1].strip()
                    goal_type = parts[2].strip()
                    logger.info(
                        f"[{self.jid}] -> Consulting Platform Agent for {video_id} on {platform} for {goal_type}...")
                    await asyncio.sleep(0.1)  # Simulate async work
                    # Simulate sending message to Platform Optimization Agent using SPADE's messaging
                    # Assuming PlatformOptimizationAgent JID
                    msg = Message(to="platform@localhost")
                    msg.set_metadata("performative", Performative.REQUEST)
                    msg.set_metadata("ontology", Ontology.TASK_REQUEST)
                    msg.body = json.dumps(
                        {"task": "get_recommendations", "video_id": video_id, "platform": platform, "goal": goal_type})
                    await self.send(msg)
                    completed_intentions.add(intention)
                    logger.info(
                        f"[{self.jid}] -> Consulted Platform Agent for {video_id}.")

                elif "consult_audience_agent" in goal:
                    parts = goal.split('(')[1].split(')')[0].split(', ')
                    video_id = parts[0].strip()
                    audience = parts[1].strip()
                    goal_type = parts[2].strip()
                    logger.info(
                        f"[{self.jid}] -> Consulting Audience Agent for {video_id} for {audience} for {goal_type}...")
                    await asyncio.sleep(0.1)  # Simulate async work
                    # Simulate sending message to Audience Analysis Agent using SPADE's messaging
                    # Assuming AudienceAnalysisAgent JID
                    msg = Message(to="audience@localhost")
                    msg.set_metadata("performative", Performative.REQUEST)
                    msg.set_metadata("ontology", Ontology.TASK_REQUEST)
                    msg.body = json.dumps(
                        {"task": "get_insights", "video_id": video_id, "audience": audience, "goal": goal_type})
                    await self.send(msg)
                    completed_intentions.add(intention)
                    logger.info(
                        f"[{self.jid}] -> Consulted Audience Agent for {video_id}.")

                elif "process_feedback" in goal:
                    parts = goal.split('(')[1].split(')')[0].split(', ')
                    video_id = parts[0].strip()
                    # In a real system, this would involve analyzing the feedback content (parts[1])
                    logger.info(
                        f"[{self.jid}] -> Processing feedback for {video_id}...")
                    await asyncio.sleep(0.1)  # Simulate async work
                    # Based on processing feedback, the Creator Agent might decide to adapt the content
                    self.add_desire(
                        f"adapt_content({video_id}, 'based_on_feedback')")
                    completed_intentions.add(intention)
                    logger.info(
                        f"[{self.jid}] -> Processed feedback for {video_id}.")

                elif "adapt_content" in goal:
                    parts = goal.split('(')[1].split(')')[0].split(', ')
                    video_id = parts[0].strip()
                    # In a real system, this would involve using the suggestions/feedback (parts[1])
                    logger.info(
                        f"[{self.jid}] -> Adapting content for {video_id}...")
                    await asyncio.sleep(0.2)  # Simulate async work
                    self.add_belief(f"content_adapted({video_id})")
                    completed_intentions.add(intention)
                    logger.info(
                        f"[{self.jid}] -> Content adapted for {video_id}.")

                elif "achieve_virality" in goal:
                    # This is a higher-level goal. Its plan involves sub-goals handled by other intentions.
                    # We consider this intention achieved if the content has been adapted for virality
                    # AND a simulated performance metric is met.
                    video_id = goal.split('(')[1].split(',')[0].strip()
                    if self.has_belief(f"content_adapted({video_id})"):
                        logger.info(
                            f"[{self.jid}] -> Checking virality for {video_id} after adaptation...")
                        await asyncio.sleep(0.1)  # Simulate async check
                        if random.random() < 0.4:  # Higher chance of achieving virality after adaptation
                            self.add_belief(f"content_viral({video_id})")
                            completed_intentions.add(intention)
                            logger.info(
                                f"[{self.jid}] -> !!! Achieved VIRALITY for {video_id} (simulated) !!!")
                        else:
                            # Virality not achieved yet, intention remains active.
                            pass  # Keep intention active

                elif "optimize_for_platform" in goal:
                    # Similar to virality, this goal is achieved through sub-goals (consulting agents, adapting)
                    video_id = goal.split('(')[1].split(',')[0].strip()
                    platform = goal.split(', ')[1].split(')')[0].strip()
                    # Simplified check: achieved if adapted
                    if self.has_belief(f"content_adapted({video_id})"):
                        completed_intentions.add(intention)
                        logger.info(
                            f"[{self.jid}] -> Optimized {video_id} for {platform} (simulated).")
                    else:
                        # Wait for adaptation to happen
                        pass  # Intention remains active

                elif "build_branding" in goal:
                    # This is a long-term, continuous goal. It might never be 'completed' in this simulation.
                    # Its 'execution' involves continuously pursuing other goals like uploading, optimizing, etc.
                    # We'll just keep it active.
                    pass

                # --- Analyzer Agent Specific Executions ---
                elif "generate_recommendations" in goal and self.jid.localpart == "platform":
                    parts = goal.split('(')[1].split(')')[0].split(', ')
                    video_id = parts[0].strip()
                    platform = parts[1].strip()
                    goal_type = parts[2].strip()
                    logger.info(
                        f"[{self.jid}] -> Simulating generating recommendations for {video_id} on {platform} for {goal_type}...")
                    await asyncio.sleep(0.2)  # Simulate async work
                    # Generate recommendations based on beliefs (simplified)
                    recommendations = {}
                    if platform == "tiktok" and goal_type == "virality":
                        recommendations = {
                            "resolution": "1080x1920", "style": "fast-paced", "sound": "trending_track", "duration": "15s"}
                    # ... add other platform/goal logic ...

                    # Simulate sending message back to Creator Agent
                    msg = Message(to="creator@localhost")
                    msg.set_metadata("performative", Performative.INFORM)
                    # Using video analysis ontology for results
                    msg.set_metadata("ontology", Ontology.VIDEO_ANALYSIS)
                    msg.body = json.dumps({"type": "recommendations", "video_id": video_id,
                                          "recommendations": recommendations, "sender": self.jid.bare()})
                    await self.send(msg)
                    completed_intentions.add(intention)
                    logger.info(
                        f"[{self.jid}] -> Generated and sent recommendations for {video_id}.")

                elif "generate_audience_insights" in goal and self.jid.localpart == "audience":
                    parts = goal.split('(')[1].split(')')[0].split(', ')
                    video_id = parts[0].strip()
                    audience = parts[1].strip()
                    goal_type = parts[2].strip()
                    logger.info(
                        f"[{self.jid}] -> Simulating generating insights for {video_id} for {audience} for {goal_type}...")
                    await asyncio.sleep(0.2)  # Simulate async work
                    # Generate insights based on beliefs (simplified)
                    insights = {}
                    if audience == "genz" and goal_type == "virality":
                        insights = {"engagement_pattern": "short_attention_span", "preferred_content": [
                            "dance", "challenges", "memes"]}
                    # ... add other audience/goal logic ...

                    # Simulate sending message back to Creator Agent
                    msg = Message(to="creator@localhost")
                    msg.set_metadata("performative", Performative.INFORM)
                    # Using video analysis ontology for results
                    msg.set_metadata("ontology", Ontology.VIDEO_ANALYSIS)
                    msg.body = json.dumps(
                        {"type": "insights", "video_id": video_id, "insights": insights, "sender": self.jid.bare()})
                    await self.send(msg)
                    completed_intentions.add(intention)
                    logger.info(
                        f"[{self.jid}] -> Generated and sent audience insights for {video_id}.")

                # --- Feedback Agent Specific Executions ---
                elif "collect_all_feedback" in goal and self.jid.localpart == "feedback":
                    video_id = goal.split('(')[1].split(')')[0].strip()
                    # logger.debug(f"[{self.jid}] -> Simulating collecting feedback for {video_id}...") # Uncomment for detailed feedback collection
                    # Simulate receiving feedback over time. In a real system, this would involve
                    # receiving messages from users or other agents, or polling a feedback source.
                    # For this simulation, we'll randomly add feedback beliefs.
                    received_feedback_contents = {
                        b.content for b in self._beliefs if f"suggestions_received({video_id}" in b.content or f"comments_received({video_id}" in b.content}

                    # Simulate random arrival of new feedback
                    if random.random() < 0.2:  # Chance of receiving new feedback in a cycle
                        new_feedback_content_str = random.choice([
                            f"suggestions_received({video_id}, ['Looks good!'])",
                            f"suggestions_received({video_id}, ['Could improve audio.'])",
                            f"comments_received({video_id}, ['Loved it!'])",
                            f"comments_received({video_id}, ['What software did you use?'])",
                            f"suggestions_received({video_id}, ['Try a different hook.'])"
                        ])
                        new_belief = Belief(new_feedback_content_str)
                        if new_belief not in self._beliefs:  # Only add if unique content
                            self.add_belief(new_belief_content_str)
                            logger.debug(
                                f"[{self.jid}] -> Received NEW feedback for {video_id}: {new_belief_content_str}")
                            received_feedback_contents.add(
                                new_belief_content_str)

                    # If enough feedback is collected (simulated condition: at least 2 unique pieces of feedback)
                    if len(received_feedback_contents) >= 2:
                        self.add_desire(f"consolidate_feedback({video_id})")
                        # Intention to listen is achieved when consolidation is desired
                        completed_intentions.add(intention)
                        logger.info(
                            f"[{self.jid}] -> Enough feedback collected for {video_id}, desiring consolidation.")
                    else:
                        # Intention remains active, keep listening in the next cycle
                        pass  # No asyncio.sleep here as it's waiting

                elif "consolidate_feedback" in goal and self.jid.localpart == "feedback":
                    video_id = goal.split('(')[1].split(')')[0].strip()
                    logger.info(
                        f"[{self.jid}] -> Consolidating feedback for {video_id}...")
                    await asyncio.sleep(0.1)  # Simulate async work
                    consolidated = []
                    # Gather all relevant feedback beliefs
                    for belief in self._beliefs:
                        if f"suggestions_received({video_id}" in belief.content or f"comments_received({video_id}" in belief.content:
                            # Simple consolidation: just add the content of the belief
                            consolidated.append(belief.content)

                    # Simulate sending consolidated feedback to Creator Agent
                    msg = Message(to="creator@localhost")
                    msg.set_metadata("performative", Performative.INFORM)
                    # Using video analysis ontology for results
                    msg.set_metadata("ontology", Ontology.VIDEO_ANALYSIS)
                    msg.body = json.dumps(
                        {"type": "feedback", "video_id": video_id, "feedback": consolidated, "sender": self.jid.bare()})
                    await self.send(msg)
                    completed_intentions.add(intention)
                    logger.info(
                        f"[{self.jid}] -> Consolidated and sent feedback for {video_id}.")

                # Mark intention as achieved if it's in the completed set
                if intention in completed_intentions:
                    intention.status = "achieved"
                    # logger.debug(f"[{self.jid}] Intention '{intention.desire.goal}' achieved.")

        # Remove completed intentions
        self._intentions = {
            int for int in self._intentions if int.status != "achieved"}
        # if completed_intentions:
        # logger.debug(f"[{self.jid}] Removed {len(completed_intentions)} completed intentions.") # Uncomment for detailed intention logging

    def _find_plan(self, desire: Desire) -> Optional[Plan]:
        """Finds a suitable plan from the plan library for a given desire."""
        # Simple plan selection: find the first plan whose goal predicate is contained in the desire's goal string
        for plan in self._plan_library:
            if plan.goal_predicate in desire.goal:
                return plan
        return None  # No suitable plan found

    def _build_plan_library(self) -> List[Plan]:
        """Builds the agent's plan library. To be implemented by subclasses."""
        return []

    # --- SPADE Behaviours ---

    class BDILoopBehaviour(CyclicBehaviour):
        """Runs the core BDI deliberation and execution cycle."""

        async def run(self):
            # Process any messages received by other behaviours
            # In this integrated model, message processing is handled by specific behaviours
            # that update the agent's BDI state. The BDI loop acts on this state.
            # await self.agent.process_incoming_messages() # Not needed here as behaviours handle receiving

            # Run deliberation
            self.agent.deliberate()

            # Run execution of intentions
            await self.agent.execute_intentions()

            # Sleep briefly to allow other agents/tasks to run
            await asyncio.sleep(0.1)

            # Check if the stop event is set
            if self.agent._stop_bdi_cycle.is_set():
                self.kill()  # Kill the behaviour

        async def on_end(self):
            logger.info(f"[{self.agent.jid}] BDI Loop Behaviour ended.")

    class BDIStateRequestBehaviour(CyclicBehaviour):
        """Handles requests for the agent's current BDI state."""

        async def run(self):
            # Listen for messages requesting BDI state
            template = Template()
            template.set_metadata("performative", Performative.REQUEST)
            template.set_metadata("ontology", Ontology.BDI_STATE)

            msg = await self.receive(timeout=1)  # Short timeout
            if msg:
                logger.info(
                    f"[{self.agent.jid}] Received BDI state request from {msg.sender}")
                # Prepare the BDI state data
                bdi_state = {
                    "beliefs": [b.content for b in self.agent.beliefs],
                    "desires": [d.goal for d in self.agent.desires],
                    "intentions": [{"goal": i.desire.goal, "status": i.status, "plan": i.plan.name if i.plan else None} for i in self.agent.intentions]
                }

                # Send the response
                reply = msg.make_reply()
                reply.set_metadata("performative", Performative.INFORM)
                reply.set_metadata("ontology", Ontology.BDI_STATE)
                reply.set_metadata("language", ContentLanguage.JSON)
                reply.body = json.dumps(bdi_state)
                await self.send(reply)
                logger.info(
                    f"[{self.agent.jid}] Sent BDI state to {msg.sender}")

    async def setup(self):
        """Agent setup method - initialize BDI and add behaviours."""
        logger.info(f"[{self.jid}] BaseBDI_SPADE_Agent started")

        # Add the core BDI loop behaviour
        self.add_behaviour(self.BDILoopBehaviour())

        # Add behaviour to handle BDI state requests
        self.add_behaviour(self.BDIStateRequestBehaviour())

    def stop_bdi(self):
        """Signals the BDI loop behaviour to stop."""
        self._stop_bdi_cycle.set()
        logger.info(f"[{self.jid}] Signaled BDI loop to stop.")


# --- 4. Specific Agent Implementations (Inheriting from BaseBDI_SPADE_Agent) ---

class CreatorAgent(BaseBDI_SPADE_Agent):
    def __init__(self, jid: str, password: str, verify_security: bool = False):
        super().__init__(jid, password, verify_security)

        # --- Initial Beliefs ---
        # Beliefs about platforms and agent availability
        self.add_belief("tiktok_popular_genz")
        self.add_belief("instagram_popular_millennials")
        self.add_belief("youtube_popular_general")
        # Beliefs about other agents' availability (assuming they will be running)
        self.add_belief("platform_optimization_agent_available")
        self.add_belief("audience_analysis_agent_available")
        self.add_belief("feedback_agent_available")

        # Assume vlog_highlight_01 is already "uploaded" to YouTube for Scenario 3
        self.add_belief("video_uploaded(vlog_highlight_01, youtube)")

        # --- Initial Desires ---
        # Scenario 1: Optimize Dance Video for TikTok Virality
        self.add_desire(
            "achieve_virality(dance_video_01, tiktok)", priority=0.9)
        self.add_desire("upload_video(dance_video_01, tiktok)", priority=0.8)
        # Desire feedback for this video
        self.add_desire("get_suggestions(dance_video_01)", priority=0.7)

        # Scenario 2: Educational Snippet Feedback
        self.add_desire("upload_video(edu_snippet_01, youtube)", priority=0.6)
        # Desire feedback for this video
        self.add_desire("get_suggestions(edu_snippet_01)", priority=0.5)

        # Scenario 3: Cross-Platform Branding
        # High priority long-term goal
        self.add_desire("build_branding", priority=1.0)
        self.add_desire(
            "optimize_for_platform(vlog_highlight_01, instagram)", priority=0.4)
        self.add_desire(
            "optimize_for_platform(vlog_highlight_01, tiktok)", priority=0.3)

        # General Desires
        # Lower priority in this sim
        self.add_desire("monetize_content", priority=0.2)

    def _build_plan_library(self) -> List[Plan]:
        # Define plans for the Creator Agent
        plans = [
            # Basic Action Plans - these are the 'steps' in higher-level plans,
            # simulated directly in execute_intentions or handled by sending messages.
            Plan(name="UploadVideoPlan", goal_predicate="upload_video", steps=[]),
            Plan(name="RequestSuggestionsPlan",
                 goal_predicate="request_suggestions", steps=[]),
            Plan(name="ConsultPlatformAgentPlan",
                 goal_predicate="consult_platform_agent", steps=[]),
            Plan(name="ConsultAudienceAgentPlan",
                 goal_predicate="consult_audience_agent", steps=[]),
            Plan(name="ProcessFeedbackPlan",
                 goal_predicate="process_feedback", steps=[]),
            Plan(name="AdaptContentPlan",
                 goal_predicate="adapt_content", steps=[]),

            # Higher-Level Goal Plans - these represent complex goals achieved by
            # forming and executing desires/intentions for basic actions.
            # The 'steps' are indicative of the process flow.
            Plan(name="AchieveViralityPlan", goal_predicate="achieve_virality", steps=[
                "consult_platform_agent_for_virality",
                "consult_audience_agent_for_virality",
                "wait_for_recommendations_and_insights",
                "adapt_content_based_on_recommendations_and_insights",
                "monitor_performance"
            ]),
            # Plan for optimizing for a platform - involves consulting platform agent and adapting
            Plan(name="OptimizeForPlatformPlan", goal_predicate="optimize_for_platform", steps=[
                "consult_platform_agent_for_optimization",
                 "wait_for_recommendations",
                 "adapt_content_based_on_recommendations"
                 ]),
            # Plan for building branding - a continuous process
            Plan(name="BuildBrandingPlan", goal_predicate="build_branding", steps=[
                "consistently_create_content",
                "engage_with_audience",
                "analyze_brand_perception"
            ])
        ]
        return plans

    # --- SPADE Behaviours specific to CreatorAgent ---
    # These behaviours handle incoming messages relevant to the CreatorAgent
    # and update the agent's BDI state accordingly.

    class ReceiveAnalysisResults(CyclicBehaviour):
        """Receives analysis results (recommendations, insights, feedback)."""

        async def run(self):
            # Listen for INFORM messages with the VIDEO_ANALYSIS ontology
            template = Template()
            template.set_metadata("performative", Performative.INFORM)
            template.set_metadata("ontology", Ontology.VIDEO_ANALYSIS)

            # Short timeout to not block the BDI loop
            msg = await self.receive(timeout=1)
            if msg:
                logger.info(
                    f"[{self.agent.jid}] Received analysis result from {msg.sender}")
                try:
                    content = json.loads(msg.body)
                    result_type = content.get("type")
                    video_id = content.get("video_id")

                    if result_type == "recommendations" and video_id:
                        recommendations = content.get("recommendations")
                        self.agent.add_belief(
                            f"recommendations_received({video_id}, {recommendations})")
                        # Receiving recommendations creates a desire to adapt content
                        self.agent.add_desire(
                            f"adapt_content({video_id}, {recommendations})")
                        logger.info(
                            f"[{self.agent.jid}] Processed recommendations for {video_id}.")

                    elif result_type == "insights" and video_id:
                        insights = content.get("insights")
                        self.agent.add_belief(
                            f"insights_received({video_id}, {insights})")
                        logger.info(
                            f"[{self.agent.jid}] Processed insights for {video_id}.")

                    elif result_type == "feedback" and video_id:
                        feedback = content.get("feedback")
                        self.agent.add_belief(
                            f"feedback_received({video_id}, {feedback})")
                        # Receiving feedback creates a desire to process it
                        self.agent.add_desire(
                            f"process_feedback({video_id}, {feedback})")
                        logger.info(
                            f"[{self.agent.jid}] Processed feedback for {video_id}.")

                    else:
                        logger.warning(
                            f"[{self.agent.jid}] Received unknown analysis result type: {result_type}")

                except json.JSONDecodeError as e:
                    logger.error(
                        f"[{self.agent.jid}] Error decoding analysis result message: {e}")
                except Exception as e:
                    logger.error(
                        f"[{self.agent.jid}] Error processing analysis result message: {e}")

    class ReceiveAnalysisFailure(CyclicBehaviour):
        """Handles failure messages from analysis agents."""

        async def run(self):
            # Listen for FAILURE messages
            template = Template()
            template.set_metadata("performative", Performative.FAILURE)
            # You might want to filter by ontology if failures can come from different types of tasks
            # template.set_metadata("ontology", Ontology.VIDEO_ANALYSIS)

            msg = await self.receive(timeout=1)  # Short timeout
            if msg:
                logger.warning(
                    f"[{self.agent.jid}] Received failure message from {msg.sender}: {msg.body}")
                # Agent could update beliefs about agent reliability or task feasibility

    async def setup(self):
        """CreatorAgent setup - adds BDI loop and message handling behaviours."""
        await super().setup()  # Call the base class setup

        logger.info(f"[{self.jid}] CreatorAgent specific setup completed.")

        # Add behaviours to receive messages relevant to CreatorAgent
        self.add_behaviour(self.ReceiveAnalysisResults())
        self.add_behaviour(self.ReceiveAnalysisFailure())


class PlatformOptimizationAgent(BaseBDI_SPADE_Agent):
    def __init__(self, jid: str, password: str, verify_security: bool = False):
        super().__init__(jid, password, verify_security)
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

    def _build_plan_library(self) -> List[Plan]:
        # Define plans for the Platform Optimization Agent
        plans = [
            # This plan is executed when the agent has the desire to generate recommendations
            Plan(name="GenerateRecommendationsPlan",
                 goal_predicate="generate_recommendations", steps=[]),
        ]
        return plans

    # --- SPADE Behaviours specific to PlatformOptimizationAgent ---

    class HandleConsultPlatformRequest(CyclicBehaviour):
        """Handles requests from the CreatorAgent to consult for platform optimization."""

        async def run(self):
            # Listen for REQUEST messages with the TASK_REQUEST ontology and specific task
            template = Template()
            template.set_metadata("performative", Performative.REQUEST)
            template.set_metadata("ontology", Ontology.TASK_REQUEST)
            # You could add a content filter here if the task type is always in the body
            # template.set_content({"task": "get_recommendations"}) # This requires exact match

            msg = await self.receive(timeout=1)  # Short timeout
            if msg:
                logger.info(
                    f"[{self.agent.jid}] Received consultation request from {msg.sender}")
                try:
                    content = json.loads(msg.body)
                    task = content.get("task")
                    video_id = content.get("video_id")
                    platform = content.get("platform")
                    goal = content.get("goal")

                    if task == "get_recommendations" and video_id and platform and goal:
                        # Receiving this request creates the desire to generate recommendations
                        self.agent.add_desire(
                            f"generate_recommendations({video_id}, {platform}, {goal})")
                        logger.info(
                            f"[{self.agent.jid}] Added desire to generate recommendations for {video_id}.")

                        # Optionally send an AGREE message immediately
                        reply = msg.make_reply()
                        reply.set_metadata("performative", Performative.AGREE)
                        reply.set_metadata("ontology", Ontology.TASK_REQUEST)
                        reply.body = json.dumps(
                            {"message": "Request received, processing."})
                        await self.send(reply)

                    else:
                        logger.warning(
                            f"[{self.agent.jid}] Received unknown task request: {content}")
                        reply = msg.make_reply()
                        reply.set_metadata("performative", Performative.REFUSE)
                        reply.set_metadata("ontology", Ontology.TASK_REQUEST)
                        reply.body = json.dumps({"error": "Unknown task"})
                        await self.send(reply)

                except json.JSONDecodeError as e:
                    logger.error(
                        f"[{self.agent.jid}] Error decoding consultation request message: {e}")
                    reply = msg.make_reply()
                    reply.set_metadata("performative", Performative.FAILURE)
                    reply.set_metadata("ontology", Ontology.TASK_REQUEST)
                    reply.body = json.dumps({"error": f"Invalid JSON: {e}"})
                    await self.send(reply)
                except Exception as e:
                    logger.error(
                        f"[{self.agent.jid}] Error handling consultation request: {e}")
                    reply = msg.make_reply()
                    reply.set_metadata("performative", Performative.FAILURE)
                    reply.set_metadata("ontology", Ontology.TASK_REQUEST)
                    reply.body = json.dumps({"error": str(e)})
                    await self.send(reply)

    async def setup(self):
        """PlatformOptimizationAgent setup - adds BDI loop and request handling behaviours."""
        await super().setup()  # Call the base class setup

        logger.info(
            f"[{self.jid}] PlatformOptimizationAgent specific setup completed.")

        # Add behaviour to handle consultation requests
        self.add_behaviour(self.HandleConsultPlatformRequest())


class AudienceAnalysisAgent(BaseBDI_SPADE_Agent):
    def __init__(self, jid: str, password: str, verify_security: bool = False):
        super().__init__(jid, password, verify_security)
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

    def _build_plan_library(self) -> List[Plan]:
        # Define plans for the Audience Analysis Agent
        plans = [
            # This plan is executed when the agent has the desire to generate insights
            Plan(name="GenerateAudienceInsightsPlan",
                 goal_predicate="generate_audience_insights", steps=[]),
        ]
        return plans

    # --- SPADE Behaviours specific to AudienceAnalysisAgent ---

    class HandleConsultAudienceRequest(CyclicBehaviour):
        """Handles requests from the CreatorAgent to consult for audience analysis."""

        async def run(self):
            # Listen for REQUEST messages with the TASK_REQUEST ontology and specific task
            template = Template()
            template.set_metadata("performative", Performative.REQUEST)
            template.set_metadata("ontology", Ontology.TASK_REQUEST)
            # template.set_content({"task": "get_insights"}) # Requires exact match

            msg = await self.receive(timeout=1)  # Short timeout
            if msg:
                logger.info(
                    f"[{self.agent.jid}] Received audience analysis request from {msg.sender}")
                try:
                    content = json.loads(msg.body)
                    task = content.get("task")
                    video_id = content.get("video_id")
                    audience = content.get("audience")
                    goal = content.get("goal")

                    if task == "get_insights" and video_id and audience and goal:
                        # Receiving this request creates the desire to generate insights
                        self.agent.add_desire(
                            f"generate_audience_insights({video_id}, {audience}, {goal})")
                        logger.info(
                            f"[{self.agent.jid}] Added desire to generate insights for {video_id}.")

                        # Optionally send an AGREE message immediately
                        reply = msg.make_reply()
                        reply.set_metadata("performative", Performative.AGREE)
                        reply.set_metadata("ontology", Ontology.TASK_REQUEST)
                        reply.body = json.dumps(
                            {"message": "Request received, processing."})
                        await self.send(reply)

                    else:
                        logger.warning(
                            f"[{self.agent.jid}] Received unknown task request: {content}")
                        reply = msg.make_reply()
                        reply.set_metadata("performative", Performative.REFUSE)
                        reply.set_metadata("ontology", Ontology.TASK_REQUEST)
                        reply.body = json.dumps({"error": "Unknown task"})
                        await self.send(reply)

                except json.JSONDecodeError as e:
                    logger.error(
                        f"[{self.agent.jid}] Error decoding audience analysis request message: {e}")
                    reply = msg.make_reply()
                    reply.set_metadata("performative", Performative.FAILURE)
                    reply.set_metadata("ontology", Ontology.TASK_REQUEST)
                    reply.body = json.dumps({"error": f"Invalid JSON: {e}"})
                    await self.send(reply)
                except Exception as e:
                    logger.error(
                        f"[{self.agent.jid}] Error handling audience analysis request: {e}")
                    reply = msg.make_reply()
                    reply.set_metadata("performative", Performative.FAILURE)
                    reply.set_metadata("ontology", Ontology.TASK_REQUEST)
                    reply.body = json.dumps({"error": str(e)})
                    await self.send(reply)

    async def setup(self):
        """AudienceAnalysisAgent setup - adds BDI loop and request handling behaviours."""
        await super().setup()  # Call the base class setup

        logger.info(
            f"[{self.jid}] AudienceAnalysisAgent specific setup completed.")

        # Add behaviour to handle consultation requests
        self.add_behaviour(self.HandleConsultAudienceRequest())


class FeedbackAgent(BaseBDI_SPADE_Agent):
    def __init__(self, jid: str, password: str, verify_security: bool = False):
        super().__init__(jid, password, verify_security)
        # Feedback Agent primarily reacts to messages/requests.
        # Initial beliefs/desires are added when requests are received.

    def _build_plan_library(self) -> List[Plan]:
        # Define plans for the Feedback Agent
        plans = [
            # This plan is executed when the agent has the desire to collect feedback
            Plan(name="CollectFeedbackPlan",
                 goal_predicate="collect_all_feedback", steps=[]),
            # This plan is executed when the agent has the desire to consolidate feedback
            Plan(name="ConsolidateFeedbackPlan",
                 goal_predicate="consolidate_feedback", steps=[]),
        ]
        return plans

    # --- SPADE Behaviours specific to FeedbackAgent ---

    class HandleSuggestionRequest(CyclicBehaviour):
        """Handles requests from the CreatorAgent for suggestions."""

        async def run(self):
            # Listen for REQUEST messages with the TASK_REQUEST ontology and specific task
            template = Template()
            template.set_metadata("performative", Performative.REQUEST)
            template.set_metadata("ontology", Ontology.TASK_REQUEST)
            # template.set_content({"task": "get_suggestions"}) # Requires exact match

            msg = await self.receive(timeout=1)  # Short timeout
            if msg:
                logger.info(
                    f"[{self.agent.jid}] Received suggestion request from {msg.sender}")
                try:
                    content = json.loads(msg.body)
                    task = content.get("task")
                    video_id = content.get("video_id")

                    if task == "get_suggestions" and video_id:
                        # Receiving this request creates the desire to collect feedback
                        self.agent.add_desire(
                            f"collect_all_feedback({video_id})")
                        logger.info(
                            f"[{self.agent.jid}] Added desire to collect feedback for {video_id}.")

                        # Optionally send an AGREE message immediately
                        reply = msg.make_reply()
                        reply.set_metadata("performative", Performative.AGREE)
                        reply.set_metadata("ontology", Ontology.TASK_REQUEST)
                        reply.body = json.dumps(
                            {"message": "Request received, processing."})
                        await self.send(reply)

                    else:
                        logger.warning(
                            f"[{self.agent.jid}] Received unknown task request: {content}")
                        reply = msg.make_reply()
                        reply.set_metadata("performative", Performative.REFUSE)
                        reply.set_metadata("ontology", Ontology.TASK_REQUEST)
                        reply.body = json.dumps({"error": "Unknown task"})
                        await self.send(reply)

                except json.JSONDecodeError as e:
                    logger.error(
                        f"[{self.agent.jid}] Error decoding suggestion request message: {e}")
                    reply = msg.make_reply()
                    reply.set_metadata("performative", Performative.FAILURE)
                    reply.set_metadata("ontology", Ontology.TASK_REQUEST)
                    reply.body = json.dumps({"error": f"Invalid JSON: {e}"})
                    await self.send(reply)
                except Exception as e:
                    logger.error(
                        f"[{self.agent.jid}] Error handling suggestion request: {e}")
                    reply = msg.make_reply()
                    reply.set_metadata("performative", Performative.FAILURE)
                    reply.set_metadata("ontology", Ontology.TASK_REQUEST)
                    reply.body = json.dumps({"error": str(e)})
                    await self.send(reply)

    async def setup(self):
        """FeedbackAgent setup - adds BDI loop and request handling behaviours."""
        await super().setup()  # Call the base class setup

        logger.info(f"[{self.jid}] FeedbackAgent specific setup completed.")

        # Add behaviour to handle suggestion requests
        self.add_behaviour(self.HandleSuggestionRequest())


# --- 5. Main Execution ---

async def main():
    # IMPORTANT: For SPADE agents to communicate, they need to connect to an XMPP server.
    # For local testing, you can use an in-memory server provided by SPADE or a local server like Openfire.
    # The JIDs (e.g., "creator@localhost") assume a server running at "localhost".
    # Replace "localhost" and passwords with your actual XMPP server details if not using in-memory.

    # Using an in-memory server for this example:
    # You would typically run this in a separate process or configure SPADE to use it.
    # For simplicity here, we assume the agents can connect to 'localhost'.
    # A real deployment requires a running XMPP server.

    logger.info("Starting SPADE BDI Agents...")

    # Create agent instances
    # Pass JID and password
    creator_agent = CreatorAgent("creator@localhost", "creator_password")
    platform_agent = PlatformOptimizationAgent(
        "platform@localhost", "platform_password")
    audience_agent = AudienceAnalysisAgent(
        "audience@localhost", "audience_password")
    feedback_agent = FeedbackAgent("feedback@localhost", "feedback_password")

    # Start the agents
    # auto_register=True attempts to register the JID if it doesn't exist (requires server support)
    await creator_agent.start(auto_register=True)
    await platform_agent.start(auto_register=True)
    await audience_agent.start(auto_register=True)
    await feedback_agent.start(auto_register=True)

    logger.info("All agents started. Running simulation...")

    # Keep the main loop running while agents are alive
    # In a real application, you might have a control agent or external system
    # that manages the lifecycle and goals of these agents.
    # For this simulation, we'll let them run for a while and then stop them.

    run_duration = 30  # seconds
    await asyncio.sleep(run_duration)

    logger.info(
        f"Simulation duration ({run_duration}s) elapsed. Stopping agents...")

    # Stop the agents
    # This signals the agents' behaviours to stop gracefully
    await creator_agent.stop()
    await platform_agent.stop()
    await audience_agent.stop()
    await feedback_agent.stop()

    logger.info("All agents stopped. Simulation finished.")

if __name__ == "__main__":
    # To run this code, you need to have SPADE installed (`pip install spade`).
    # You also need an XMPP server running that the agents can connect to at 'localhost'.
    # For simple testing, you can use SPADE's built-in in-memory server or a local installation.

    # If you are running this without a local XMPP server, the agents will likely fail to connect.
    # To use the in-memory server for basic testing within a single script execution:
    # You would typically run the SPADE platform itself, which manages the asyncio loop and agent startup/shutdown.

    spade.run(main())
