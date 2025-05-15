from creator_agent import CreatorAgent
from platform_optimization_agent import PlatformOptimizationAgent
from audience_analysis_agent import AudienceAnalysisAgent
from feedback_agent import FeedbackAgent
import time

# --- Simulation Setup ---

# Create agent instances
agents = [
    CreatorAgent(),
    PlatformOptimizationAgent(),
    AudienceAnalysisAgent(),
    FeedbackAgent()
]

# --- Main Simulation Loop ---

print("--- Starting Agent Simulation ---")

# --- Test Case: Creator Agent wants to make a dance video viral on TikTok ---
# The initial state set in CreatorAgent __init__ includes desires for this scenario,
# as well as the other two scenarios (Educational Snippet Feedback, Cross-Platform Branding).
# The simulation will show the agents pursuing these goals concurrently.

num_cycles = 2  # Run for a sufficient number of cycles to see interactions

for cycle in range(num_cycles):
    print(f"\n--- Simulation Cycle {cycle + 1} ---")
    for agent in agents:
        agent.run_cycle()
    time.sleep(0.1)  # Pause briefly between cycles for readability

print("\n--- Simulation Ended ---")

# --- Check Final State (Simplified Test Case Verification) ---
creator_agent = next((a for a in agents if a.agent_id == "CreatorAgent"), None)

print("\n--- Final Agent States (Partial) ---")
if creator_agent:
    print(f"CreatorAgent Beliefs: {[b.content for b in creator_agent.beliefs if any(keyword in b.content for keyword in ['video_uploaded', 'recommendations_received', 'insights_received', 'feedback_received', 'content_adapted', 'content_viral'])]}")
    print(f"CreatorAgent Desires: {[d.goal for d in creator_agent.desires]}")
    print(
        f"CreatorAgent Intentions: {[f'{i.desire.goal} ({i.status})' for i in creator_agent.intentions]}")

# Add checks for other agents' final states if needed

# --- Expected Outcome for Test Cases ---
# Scenario 1 (TikTok Virality):
# - CreatorAgent should have the belief 'video_uploaded(dance_video_01, tiktok)'.
# - CreatorAgent should have received recommendations and insights (simulated by beliefs).
# - CreatorAgent should have formed and potentially completed the 'adapt_content(dance_video_01, ...)' intention.
# - CreatorAgent might have the belief 'content_adapted(dance_video_01)'.
# - CreatorAgent might have the belief 'content_viral(dance_video_01)' (if simulated success occurs).
#
# Scenario 2 (Educational Snippet Feedback):
# - CreatorAgent should have the belief 'video_uploaded(edu_snippet_01, youtube)'.
# - CreatorAgent should have requested suggestions.
# - FeedbackAgent should have received the request and potentially collected/consolidated simulated feedback.
# - CreatorAgent should have received feedback (simulated by belief 'feedback_received').
# - CreatorAgent should have processed feedback and potentially formed 'adapt_content(edu_snippet_01, ...)' desire/intention.
#
# Scenario 3 (Cross-Platform Branding):
# - CreatorAgent starts with 'video_uploaded(vlog_highlight_01, youtube)'.
# - CreatorAgent should have consulted PlatformOptimizationAgent for Instagram and TikTok optimization.
# - CreatorAgent should have received recommendations for Instagram and TikTok.
# - CreatorAgent should have formed and potentially completed 'adapt_content(vlog_highlight_01, ...)' intentions for both platforms.
# - The 'build_branding' intention will likely remain active throughout the simulation as it's a long-term goal.
