import time
import random
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from queue import Queue  # For thread-safe communication
from creator_agent import CreatorAgent
from audience_analysis_agent import AudienceAnalysisAgent
from feedback_agent import FeedbackAgent
from platform_optimization_agent import PlatformOptimizationAgent


class SimulationEnvironment:
    """Manages the agents and the simulation loop."""

    def __init__(self, agents):
        self.agents = {agent.agent_id: agent for agent in agents}
        self._running = False
        self._simulation_thread = None

    def add_agent(self, agent):
        """Adds an agent to the environment."""
        self.agents[agent.agent_id] = agent

    def get_agent(self, agent_id):
        """Gets an agent by its ID."""
        return self.agents.get(agent_id)

    def run_simulation(self, num_cycles=None):
        """Runs the main simulation loop in a separate thread."""
        self._running = True

        def simulation_loop():
            cycle_count = 0
            while self._running and (num_cycles is None or cycle_count < num_cycles):
                # print(f"\n--- Simulation Cycle {cycle_count + 1} ---") # Uncomment for detailed cycle logging
                for agent_id in list(self.agents.keys()):  # Iterate over a copy
                    agent = self.agents.get(agent_id)
                    if agent and not agent._stop_event.is_set():
                        agent.run_cycle()  # Agent runs its BDI loop
                cycle_count += 1
                time.sleep(0.1)  # Control simulation speed

            # Signal agents to stop when simulation ends
            for agent in self.agents.values():
                agent.stop()
            print("\n--- Simulation Loop Finished ---")

        self._simulation_thread = threading.Thread(target=simulation_loop)
        self._simulation_thread.start()

    def stop_simulation(self):
        """Stops the simulation."""
        self._running = False
        if self._simulation_thread and self._simulation_thread.is_alive():
            # Wait for thread to finish
            self._simulation_thread.join(timeout=1.0)

# --- 4. GUI Module (Conceptual Separation) ---


class AgentGUI:
    """Basic GUI to visualize agent states."""

    def __init__(self, master, environment):
        self.master = master
        master.title("SPADE BDI Agent Simulation")

        self.environment = environment
        self.agent_frames = {}
        self.update_interval = 200  # Update every 200ms

        self._create_widgets()
        self._update_display()  # Start periodic updates

    def _create_widgets(self):
        """Creates the main GUI layout and agent frames."""
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        # Control Frame
        control_frame = ttk.LabelFrame(
            main_frame, text="Controls", padding="10")
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))

        self.start_button = ttk.Button(
            control_frame, text="Start Simulation", command=self._start_simulation)
        self.start_button.grid(row=0, column=0, padx=5, pady=5)

        self.stop_button = ttk.Button(
            control_frame, text="Stop Simulation", command=self._stop_simulation, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5)

        # Agent Display Frame
        agent_display_frame = ttk.LabelFrame(
            main_frame, text="Agent States", padding="10")
        agent_display_frame.grid(
            row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.rowconfigure(1, weight=1)

        # Use a canvas and scrollbar for agent frames
        canvas = tk.Canvas(agent_display_frame)
        scrollbar = ttk.Scrollbar(
            agent_display_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Create frames for each agent
        for i, agent in enumerate(self.environment.agents.values()):
            frame = ttk.LabelFrame(
                scrollable_frame, text=agent.agent_id, padding="10")
            frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=5)
            scrollable_frame.columnconfigure(0, weight=1)

            # Labels to display BDI counts
            belief_label = ttk.Label(frame, text="Beliefs: 0")
            belief_label.grid(row=0, column=0, sticky=tk.W)

            desire_label = ttk.Label(frame, text="Desires: 0")
            desire_label.grid(row=1, column=0, sticky=tk.W)

            intention_label = ttk.Label(frame, text="Intentions: 0")
            intention_label.grid(row=2, column=0, sticky=tk.W)

            # Optional: Add a text area to show recent activity or full BDI state
            activity_log = scrolledtext.ScrolledText(
                frame, width=50, height=5, wrap=tk.WORD)
            activity_log.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)

            self.agent_frames[agent.agent_id] = {
                "frame": frame,
                "belief_label": belief_label,
                "desire_label": desire_label,
                "intention_label": intention_label,
                "activity_log": activity_log,
                "last_bdi_state": (0, 0, 0)  # To track changes
            }

            # Add a button to show details (optional)
            # details_button = ttk.Button(frame, text="Details", command=lambda a=agent: self._show_agent_details(a))
            # details_button.grid(row=0, column=1, sticky=tk.E)

    def _start_simulation(self):
        """Starts the simulation thread."""
        print("Starting simulation...")
        # Run for a fixed number of cycles or None for infinite
        self.environment.run_simulation(num_cycles=200)
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self._update_display()  # Ensure updates continue

    def _stop_simulation(self):
        """Stops the simulation thread."""
        print("Stopping simulation...")
        self.environment.stop_simulation()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def _update_display(self):
        """Periodically updates the GUI with agent states."""
        for agent_id, agent_info in self.agent_frames.items():
            agent = self.environment.get_agent(agent_id)
            if agent:
                # Get thread-safe copies of BDI lists
                current_beliefs = agent.beliefs
                current_desires = agent.desires
                current_intentions = agent.intentions

                num_beliefs = len(current_beliefs)
                num_desires = len(current_desires)
                num_intentions = len(current_intentions)

                agent_info["belief_label"].config(
                    text=f"Beliefs: {num_beliefs}")
                agent_info["desire_label"].config(
                    text=f"Desires: {num_desires}")
                agent_info["intention_label"].config(
                    text=f"Intentions: {num_intentions}")

                # Update activity log only if BDI state changed
                current_state = (num_beliefs, num_desires, num_intentions)
                if current_state != agent_info["last_bdi_state"]:
                    agent_info["activity_log"].insert(
                        tk.END, f"Cycle Update:\n")
                    agent_info["activity_log"].insert(
                        tk.END, f"  Beliefs ({num_beliefs}): {[b.content for b in current_beliefs]}\n")
                    agent_info["activity_log"].insert(
                        tk.END, f"  Desires ({num_desires}): {[d.goal for d in current_desires]}\n")
                    agent_info["activity_log"].insert(
                        tk.END, f"  Intentions ({num_intentions}): {[f'{i.desire.goal} ({i.status})' for i in current_intentions]}\n\n")
                    agent_info["activity_log"].see(
                        tk.END)  # Auto-scroll to the end
                    agent_info["last_bdi_state"] = current_state

        # Schedule the next update
        self.master.after(self.update_interval, self._update_display)

    def _show_agent_details(self, agent):
        """(Placeholder) Opens a new window with detailed agent information."""
        # This would require creating a new Toplevel window and populating it
        # with lists/trees of beliefs, desires, intentions, and plans.
        print(f"Showing details for {agent.agent_id}")
        # Example: Print full details to console for now
        print(f"Beliefs: {agent.beliefs}")
        print(f"Desires: {agent.desires}")
        print(f"Intentions: {agent.intentions}")
        print(f"Plan Library: {agent._plan_library}")


# --- 5. Main Application Entry Point (Conceptual Separation) ---

if __name__ == "__main__":
    # Create agents
    agent_list = [
        CreatorAgent(),
        PlatformOptimizationAgent(),
        AudienceAnalysisAgent(),
        FeedbackAgent()
    ]

    # Create simulation environment
    environment = SimulationEnvironment(agent_list)

    # Setup the GUI
    root = tk.Tk()
    gui = AgentGUI(root, environment)

    # Start the Tkinter event loop
    # The simulation loop runs in a separate thread started by the GUI
    root.protocol("WM_DELETE_WINDOW", lambda: (environment.stop_simulation(
    ), root.destroy()))  # Stop simulation when window is closed
    root.mainloop()
