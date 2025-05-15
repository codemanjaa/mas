import time
import random

# --- Core BDI Components ---


class Belief:
    """Represents a belief held by an agent."""

    def __init__(self, content, strength=1.0):
        self.content = content  # The information or proposition
        self.strength = strength  # Confidence in the belief (optional)

    def __repr__(self):
        return f"Belief(content='{self.content}', strength={self.strength})"

    def __eq__(self, other):
        if isinstance(other, Belief):
            return self.content == other.content
        return False

    def __hash__(self):
        return hash(self.content)


class Desire:
    """Represents a desired state of affairs for an agent."""

    def __init__(self, goal, priority=1.0):
        self.goal = goal  # The state to be achieved
        self.priority = priority  # How important this desire is (optional)

    def __repr__(self):
        return f"Desire(goal='{self.goal}', priority={self.priority})"

    def __eq__(self, other):
        if isinstance(other, Desire):
            return self.goal == other.goal
        return False

    def __hash__(self):
        return hash(self.goal)


class Intention:
    """Represents a desire that the agent has committed to achieving."""

    def __init__(self, desire):
        self.desire = desire  # The desire being pursued
        self.status = "active"  # e.g., "active", "suspended", "achieved", "failed"
        self.plan = None  # The plan chosen to achieve this intention

    def __repr__(self):
        return f"Intention(desire={self.desire.goal}, status='{self.status}')"

    def __eq__(self, other):
        if isinstance(other, Intention):
            return self.desire == other.desire and self.status == other.status
        return False

    def __hash__(self):
        return hash((self.desire, self.status))

# --- Plan Structure ---


class Plan:
    """Represents a sequence of actions to achieve an intention."""

    def __init__(self, name, goal_predicate, steps):
        self.name = name
        self.goal_predicate = goal_predicate  # The goal this plan aims to achieve
        # List of actions or sub-goals (not explicitly executed in this simulation)
        self.steps = steps

    def __repr__(self):
        return f"Plan(name='{self.name}', goal='{self.goal_predicate}')"