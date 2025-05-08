import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional

import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
from spade.template import Template

# ================== Setup Logging ==================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# ================== Base Agent ==================


class BaseAgent(Agent):
    async def _async_connect(self):
        await self.client.connect(host=self.jid.host, port=self.xmpp_port)

# ================== Creator Agent ==================


class CreatorAgent(BaseAgent):
    REQUEST_THREAD = "video_analysis_001"

    class SendVideoBehaviour(OneShotBehaviour):
        async def run(self) -> None:
            logger.info(
                f"[{self.agent.jid}] Uploading video and requesting analysis...")

            msg = Message(to="analyzer@localhost")
            msg.set_metadata("performative", Performative.REQUEST)
            msg.set_metadata("language", ContentLanguage.JSON)
            msg.set_metadata("ontology", Ontology.VIDEO_ANALYSIS)
            msg.thread = self.agent.REQUEST_THREAD

            msg.body = json.dumps({
                "video_reference": "/Users/mselvaxy/dev/@abercrombie_video_7123592311925345582.mp4",
                "analysis_types": ["object_detection", "color_analysis"]
            })

            await self.send(msg)
            logger.info(
                f"[{self.agent.jid}] Request sent. Waiting for response...")

    class ReceiveResultsBehaviour(CyclicBehaviour):
        async def run(self) -> None:
            msg = await self.receive(timeout=60)
            if not msg:
                logger.warning(
                    f"[{self.agent.jid}] No response received within timeout.")
                await self.agent.stop()
                return

            performative = msg.get_metadata("performative")
            ontology = msg.get_metadata("ontology")

            if performative == Performative.INFORM and ontology == Ontology.VIDEO_ANALYSIS:
                logger.info(f"[{self.agent.jid}] Received analysis results:")
                try:
                    data = json.loads(msg.body)
                    print(json.dumps(data, indent=4))
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding response: {e}")
            elif performative == Performative.FAILURE:
                logger.error(f"[{self.agent.jid}] Analysis failed: {msg.body}")

            await self.agent.stop()

    async def setup(self) -> None:
        logger.info(f"[{self.jid}] CreatorAgent started")

        # Add receiver behaviours with appropriate templates
        inform_template = Template()
        inform_template.set_metadata("performative", Performative.INFORM)
        inform_template.set_metadata("ontology", Ontology.VIDEO_ANALYSIS)
        inform_template.thread = self.REQUEST_THREAD

        failure_template = Template()
        failure_template.set_metadata("performative", Performative.FAILURE)
        failure_template.thread = self.REQUEST_THREAD

        self.add_behaviour(self.ReceiveResultsBehaviour(), inform_template)
        self.add_behaviour(self.ReceiveResultsBehaviour(), failure_template)

        # Add sending behaviour
        self.add_behaviour(self.SendVideoBehaviour())

# ================== Analyzer Agent ==================


class AnalyzerAgent(BaseAgent):
    class AnalyzeVideoBehaviour(CyclicBehaviour):
        async def run(self) -> None:
            logger.info(
                f"[{self.agent.jid}] Waiting for video analysis request...")
            msg = await self.receive(timeout=30)
            if not msg:
                logger.warning(
                    f"[{self.agent.jid}] No request received in 30s.")
                return
            logger.info(
                f"[{self.agent.jid}] Received analysis request from {msg.sender}")

            try:
                request = json.loads(msg.body)
                video_url = request.get("video_reference")
                logger.info(f"[{self.agent.jid}] Analyzing video: {video_url}")

                # Send agreement
                await self._send_response(
                    original_msg=msg,
                    performative=Performative.AGREE,
                    body={"message": "Analysis started"},
                    ontology=Ontology.VIDEO_ANALYSIS
                )

                await asyncio.sleep(2)  # Simulated analysis delay

                analysis = self._perform_analysis()
                await self._send_response(
                    original_msg=msg,
                    performative=Performative.INFORM,
                    body=analysis.to_dict(),
                    ontology=Ontology.VIDEO_ANALYSIS,
                    to=str(msg.sender)
                )

                logger.info(
                    f"[{self.agent.jid}] Analysis results sent to {msg.sender}")

            except Exception as e:
                logger.error(f"Error: {e}")
                await self._send_response(
                    original_msg=msg,
                    performative=Performative.FAILURE,
                    body={"error": str(e)},
                    ontology=Ontology.VIDEO_ANALYSIS,
                    to=str(msg.sender)
                )

        async def _send_response(
            self,
            original_msg: Message,
            performative: str,
            body: Dict,
            ontology: Optional[str] = None,
            to: Optional[str] = None
        ) -> None:
            response = original_msg.make_reply() if to is None else Message(to=to)
            response.set_metadata("performative", performative)
            response.set_metadata("language", ContentLanguage.JSON)
            if ontology:
                response.set_metadata("ontology", ontology)
            response.thread = original_msg.thread  # Preserve thread
            response.body = json.dumps(body)
            await self.send(response)

        def _perform_analysis(self) -> VideoAnalysisResult:
            objects = [
                VideoObject("person", 0.95, Position(100, 200, 60, 120)),
                VideoObject("dog", 0.87, Position(300, 250, 80, 100))
            ]
            colors = ColorAnalysis(
                dominant_colors=["#FF5733", "#33FF57", "#3357FF"],
                color_distribution={"#FF5733": 0.4,
                                    "#33FF57": 0.35, "#3357FF": 0.25}
            )
            return VideoAnalysisResult(objects=objects, colors=colors)

    async def setup(self) -> None:
        logger.info(f"[{self.jid}] AnalyzerAgent started")

        request_template = Template()
        request_template.set_metadata("performative", Performative.REQUEST)
        request_template.set_metadata("ontology", Ontology.VIDEO_ANALYSIS)

        self.add_behaviour(self.AnalyzeVideoBehaviour(), request_template)

# ================== Main ==================


async def run_agents():
    analyzer = AnalyzerAgent("analyzer@localhost", "analyzer_password")
    creator = CreatorAgent("creator@localhost", "creator_password")

    await analyzer.start(auto_register=True)
    await asyncio.sleep(1)  # Allow Analyzer to initialize
    await creator.start(auto_register=True)
    while analyzer.is_alive() or creator.is_alive():
        await asyncio.sleep(1)

    logger.info("All agents have stopped. Shutting down...")

if __name__ == "__main__":
    spade.run(run_agents())
