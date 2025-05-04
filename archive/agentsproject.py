import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
from spade.template import Template
import json
import asyncio
from typing import List, Dict, Optional
from datetime import datetime

# ================== ACL Message Constants ==================


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

# ================== Data Models ==================


class VideoObject:
    def __init__(self, object_type: str, confidence: float, position: Dict[str, int]):
        self.object_type = object_type
        self.confidence = confidence
        self.position = position

    def to_dict(self):
        return {
            'type': self.object_type,
            'confidence': self.confidence,
            'position': self.position
        }


class ColorAnalysis:
    def __init__(self, dominant_colors: List[str], color_distribution: Dict[str, float]):
        self.dominant_colors = dominant_colors
        self.color_distribution = color_distribution

    def to_dict(self):
        return {
            'dominant_colors': self.dominant_colors,
            'color_distribution': self.color_distribution
        }


class VideoAnalysisResult:
    def __init__(self, objects: List[VideoObject], colors: ColorAnalysis):
        self.objects = objects
        self.colors = colors

    def to_dict(self):
        return {
            'objects': [obj.to_dict() for obj in self.objects],
            'colors': self.colors.to_dict(),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

# ================== Creator Agent (Uploader) ==================


class CreatorAgent(Agent):
    class SendVideoBehaviour(OneShotBehaviour):
        async def run(self):
            print(f"\n[{self.agent.jid}] Uploading video and requesting analysis...")

            msg = Message(to="analyzer@localhost")
            msg.set_metadata("performative", Performative.REQUEST)
            msg.set_metadata("language", ContentLanguage.JSON)
            msg.set_metadata("ontology", Ontology.VIDEO_ANALYSIS)

            msg.body = json.dumps({
                "video_reference": "http://example.com/sample.mp4",
                "analysis_types": ["object_detection", "color_analysis"]
            })

            await self.send(msg)
            print(f"[{self.agent.jid}] Request sent. Waiting for response...")

            self.agent.add_behaviour(self.agent.ReceiveResultsBehaviour())

    class ReceiveResultsBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=60)
            if msg:
                performative = msg.get_metadata("performative")
                ontology = msg.get_metadata("ontology")

                if performative == Performative.INFORM and ontology == Ontology.VIDEO_ANALYSIS:
                    print(f"\n[{self.agent.jid}] Received analysis results:")
                    try:
                        data = json.loads(msg.body)
                        print(json.dumps(data, indent=4))
                    except json.JSONDecodeError:
                        print("Error decoding response.")
                    await self.agent.stop()
                elif performative == Performative.FAILURE:
                    print(f"[{self.agent.jid}] Analysis failed: {msg.body}")
                    await self.agent.stop()
            else:
                print(f"[{self.agent.jid}] No response received within timeout.")
                await self.agent.stop()

    async def setup(self):
        print(f"[{self.jid}] CreatorAgent started")
        self.add_behaviour(self.SendVideoBehaviour())

# ================== Analyzer Agent ==================


class AnalyzerAgent(Agent):
    class AnalyzeVideoBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                print(f"\n[{self.agent.jid}] Received analysis request from {msg.sender}")
                try:
                    request = json.loads(msg.body)
                    video_url = request.get("video_reference")
                    print(f"[{self.agent.jid}] Analyzing video: {video_url}")

                    # Step 1: Agree to process
                    agree = msg.make_reply()
                    agree.set_metadata("performative", Performative.AGREE)
                    agree.set_metadata("language", ContentLanguage.JSON)
                    agree.body = json.dumps({"message": "Analysis started"})
                    await self.send(agree)

                    # Step 2: Simulate processing
                    await asyncio.sleep(2)

                    # Step 3: Send result
                    analysis = self.perform_analysis()

                    result = Message(to=str(msg.sender))
                    result.set_metadata("performative", Performative.INFORM)
                    result.set_metadata("language", ContentLanguage.JSON)
                    result.set_metadata("ontology", Ontology.VIDEO_ANALYSIS)
                    result.body = json.dumps(analysis.to_dict())
                    await self.send(result)

                    print(f"[{self.agent.jid}] Analysis results sent to {msg.sender}")

                except Exception as e:
                    print(f"Error: {e}")
                    failure = msg.make_reply()
                    failure.set_metadata("performative", Performative.FAILURE)
                    failure.set_metadata("language", ContentLanguage.JSON)
                    failure.body = json.dumps({"error": str(e)})
                    await self.send(failure)

        def perform_analysis(self) -> VideoAnalysisResult:
            objects = [
                VideoObject("person", 0.95, {'x': 100, 'y': 200, 'width': 60, 'height': 120}),
                VideoObject("dog", 0.87, {'x': 300, 'y': 250, 'width': 80, 'height': 100})
            ]
            colors = ColorAnalysis(
                dominant_colors=["#FF5733", "#33FF57", "#3357FF"],
                color_distribution={"#FF5733": 0.4, "#33FF57": 0.35, "#3357FF": 0.25}
            )
            return VideoAnalysisResult(objects, colors)

    async def setup(self):
        print(f"[{self.jid}] AnalyzerAgent started")
        template = Template()
        template.set_metadata("performative", Performative.REQUEST)
        self.add_behaviour(self.AnalyzeVideoBehaviour(), template)

# ================== Main Function ==================


async def main():
    analyzer = AnalyzerAgent("analyzer@localhost", "analyzer_password")
    await analyzer.start(auto_register=True)

    creator = CreatorAgent("creator@localhost", "creator_password")
    await creator.start(auto_register=True)

    await asyncio.sleep(5)

    while analyzer.is_alive() or creator.is_alive():
        await asyncio.sleep(1)

    print("\nAll agents have stopped. Shutting down...")

if __name__ == "__main__":
    spade.run(main())
