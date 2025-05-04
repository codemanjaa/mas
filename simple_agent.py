import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional

import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
from spade.template import Template

# ================== FIPA ACL params ==================
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


# ================== Base Agent Class ==================
class BaseAgent(Agent):
    async def _async_connect(self):
        """Fix SPADE 4.x connection issue"""
        await self.client.connect(host=self.jid.host, port=self.xmpp_port)


# ================== Creator Agent ==================
class CreatorAgent(BaseAgent):
    class SendVideoBehaviour(OneShotBehaviour):
        async def run(self) -> None:
            print(f"\n[{self.agent.jid}] Uploading video and requesting analysis...")

            msg = Message(to="analyzer@localhost")
            msg.set_metadata("performative", Performative.REQUEST)
            msg.set_metadata("language", ContentLanguage.JSON)
            msg.set_metadata("ontology", Ontology.VIDEO_ANALYSIS)

            msg.body = json.dumps({
                "video_reference": "/Users/mselvaxy/dev/@abercrombie_video_7123592311925345582.mp4",
                "analysis_types": ["object_detection", "color_analysis"]
            })

            await self.send(msg)
            print(f"[{self.agent.jid}] Request sent. Waiting for response...")
            self.agent.add_behaviour(self.agent.ReceiveResultsBehaviour())

    class ReceiveResultsBehaviour(CyclicBehaviour):
        async def run(self) -> None:
            msg = await self.receive(timeout=60)
            if not msg:
                print(f"[{self.agent.jid}] No response received within timeout.")
                await self.agent.stop()
                return

            performative = msg.get_metadata("performative")
            ontology = msg.get_metadata("ontology")

            if performative == Performative.INFORM and ontology == Ontology.VIDEO_ANALYSIS:
                print(f"\n[{self.agent.jid}] Received analysis results:")
                try:
                    data = json.loads(msg.body)
                    print(json.dumps(data, indent=4))
                except json.JSONDecodeError as e:
                    print(f"Error decoding response: {e}")
            elif performative == Performative.FAILURE:
                print(f"[{self.agent.jid}] Analysis failed: {msg.body}")

            await self.agent.stop()

    async def setup(self) -> None:
        print(f"[{self.jid}] CreatorAgent started")
        self.add_behaviour(self.SendVideoBehaviour())


# ================== Analyzer Agent ==================
class AnalyzerAgent(BaseAgent):
    class AnalyzeVideoBehaviour(CyclicBehaviour):
        async def run(self) -> None:
            msg = await self.receive(timeout=30)
            if not msg:
                return

            print(f"\n[{self.agent.jid}] Received analysis request from {msg.sender}")
            
            try:
                request = json.loads(msg.body)
                video_url = request.get("video_reference")
                print(f"[{self.agent.jid}] Analyzing video: {video_url}")

                # Send agreement
                await self._send_response(
                    msg, 
                    Performative.AGREE, 
                    {"message": "Analysis started"}
                )

                # Simulate processing
                await asyncio.sleep(2)

                # Send results
                analysis = self._perform_analysis()
                await self._send_response(
                    msg,
                    Performative.INFORM,
                    analysis.to_dict(),
                    Ontology.VIDEO_ANALYSIS,
                    str(msg.sender)
                )

                print(f"[{self.agent.jid}] Analysis results sent to {msg.sender}")

            except Exception as e:
                print(f"Error: {e}")
                await self._send_response(
                    msg,
                    Performative.FAILURE,
                    {"error": str(e)}
                )

        async def _send_response(
            self,
            original_msg: Message,
            performative: str,
            body: Dict,
            ontology: Optional[str] = None,
            to: Optional[str] = None
        ) -> None:
            """Helper method to send standardized responses"""
            response = original_msg.make_reply() if to is None else Message(to=to)
            response.set_metadata("performative", performative)
            response.set_metadata("language", ContentLanguage.JSON)
            if ontology:
                response.set_metadata("ontology", ontology)
            response.body = json.dumps(body)
            await self.send(response)

        def _perform_analysis(self) -> VideoAnalysisResult:
            """Simulate video analysis processing"""
            objects = [
                VideoObject(
                    object_type="person",
                    confidence=0.95,
                    position=Position(x=100, y=200, width=60, height=120)
                ),
                VideoObject(
                    object_type="dog",
                    confidence=0.87,
                    position=Position(x=300, y=250, width=80, height=100)
                )
            ]
            colors = ColorAnalysis(
                dominant_colors=["#FF5733", "#33FF57", "#3357FF"],
                color_distribution={"#FF5733": 0.4, "#33FF57": 0.35, "#3357FF": 0.25}
            )
            return VideoAnalysisResult(objects=objects, colors=colors)

    async def setup(self) -> None:
        print(f"[{self.jid}] AnalyzerAgent started")
        template = Template()
        template.set_metadata("performative", Performative.REQUEST)
        self.add_behaviour(self.AnalyzeVideoBehaviour(), template)


# ================== Main Function ==================
async def run_agents():
    analyzer = AnalyzerAgent("analyzer@localhost", "analyzer_password")
    creator = CreatorAgent("creator@localhost", "creator_password")

    await asyncio.gather(
        analyzer.start(auto_register=True),
        creator.start(auto_register=True)
    )

    # Keep running while agents are alive
    while analyzer.is_alive() or creator.is_alive():
        await asyncio.sleep(1)

    print("\nAll agents have stopped. Shutting down...")

if __name__ == "__main__":
    spade.run(run_agents())