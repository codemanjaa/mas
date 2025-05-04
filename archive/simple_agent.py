import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
import aiodns # Recommended dependency for better XMPP connection reliability
#import aioxmpp # SPADE's core XMPP library
import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
from spade.template import Template

# Configure logging for better visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger("AgentSystem")

# ================== Constants ==================
class Performative:
    """FIPA ACL Performatives used in this system."""
    INFORM = "inform"
    REQUEST = "request"
    AGREE = "agree"
    REFUSE = "refuse"
    FAILURE = "failure"
    PROPOSE = "propose"
    NOT_UNDERSTOOD = "not-understood" # Added for better error handling

class ContentLanguage:
    """Content languages used in messages."""
    JSON = "application/json"
    SL = "text/sl" # Semantic Language (SL) - often used for FIPA content

class Ontology:
    """Ontologies defining the concepts used in message content."""
    VIDEO_ANALYSIS = "video-analysis"
    TASK_REQUEST = "task-request"
    ERROR = "error" # Ontology for error messages

# ================== Data Models ==================
# Using dataclasses for structured message content
@dataclass
class Position:
    """Represents the position and size of an object in a video frame."""
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> Dict[str, int]:
        """Converts the Position object to a dictionary."""
        return field(default_factory=lambda: vars(self)) # Use field for dataclass conversion

@dataclass
class VideoObject:
    """Represents a detected object in a video."""
    object_type: str
    confidence: float
    position: Position

    def to_dict(self) -> Dict[str, Any]:
        """Converts the VideoObject object to a dictionary."""
        return {
            'type': self.object_type,
            'confidence': self.confidence,
            'position': vars(self.position) # Use vars() for simple dataclass to dict
        }

@dataclass
class ColorAnalysis:
    """Represents the color analysis results for a video."""
    dominant_colors: List[str]
    color_distribution: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Converts the ColorAnalysis object to a dictionary."""
        return vars(self) # Use vars() for simple dataclass to dict

@dataclass
class VideoAnalysisResult:
    """Represents the complete video analysis result."""
    objects: List[VideoObject]
    colors: ColorAnalysis
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z') # Auto-generate timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Converts the VideoAnalysisResult object to a dictionary."""
        return {
            'objects': [obj.to_dict() for obj in self.objects],
            'colors': self.colors.to_dict(),
            'timestamp': self.timestamp
        }

@dataclass
class AnalysisRequest:
    """Represents a request for video analysis."""
    video_reference: str # URL or path to the video
    analysis_types: List[str] # Types of analysis requested (e.g., "object_detection", "color_analysis")

    def to_dict(self) -> Dict[str, Any]:
        """Converts the AnalysisRequest object to a dictionary."""
        return vars(self)

@dataclass
class ErrorMessage:
    """Standard format for error messages."""
    code: str # Error code (e.g., "INVALID_FORMAT", "PROCESSING_ERROR")
    message: str # Human-readable error description
    details: Optional[Dict[str, Any]] = None # Optional additional details

    def to_dict(self) -> Dict[str, Any]:
        """Converts the ErrorMessage object to a dictionary."""
        return vars(self)

# ================== Base Agent Class ==================
class BaseAgent(Agent):
    """Base class for all agents, can include common utilities or overrides."""
    # SPADE 4.x generally handles connections well without the _async_connect override
    # Remove the override unless specific server issues require it.
    pass


# ================== Creator Agent ==================
class CreatorAgent(BaseAgent):
    """Agent responsible for requesting video analysis."""

    class SendVideoBehaviour(OneShotBehaviour):
        """Sends a request message to the Analyzer Agent."""
        async def run(self) -> None:
            logger.info(f"[{self.agent.jid}] Uploading video and requesting analysis...")

            # --- Define the analysis request ---
            # Example: A valid video URL
            valid_video_url = "http://example.com/sample.mp4"
            # Example: An invalid video URL (e.g., wrong extension)
            invalid_video_url = "http://example.com/document.txt"
            # Example: Another invalid URL (e.g., non-existent or unsupported protocol)
            unsupported_url = "ftp://example.com/video.mp4"

            # Choose which video reference to send for testing
            video_to_send = valid_video_url # Change this to test error handling

            request_content = AnalysisRequest(
                video_reference=video_to_send,
                analysis_types=["object_detection", "color_analysis"]
            )

            # --- Create and send the message ---
            # IMPORTANT: Replace "analyzer@your_xmpp_server.com" with the actual JID of your Analyzer Agent
            # on the remote XMPP server.
            analyzer_jid = "analyzer@your_xmpp_server.com"
            msg = Message(to=analyzer_jid)
            msg.set_metadata("performative", Performative.REQUEST)
            msg.set_metadata("language", ContentLanguage.JSON)
            msg.set_metadata("ontology", Ontology.VIDEO_ANALYSIS) # Ontology for the request content
            msg.body = json.dumps(request_content.to_dict())

            await self.send(msg)
            logger.info(f"[{self.agent.jid}] Analysis request sent for {video_to_send}. Waiting for response...")

            # Add the behavior to receive results
            # Use a template to filter for relevant responses (INFORM or FAILURE related to the request)
            template = Template()
            template.set_metadata("ontology", Ontology.VIDEO_ANALYSIS)
            # We expect either INFORM (success) or FAILURE (error) related to VIDEO_ANALYSIS
            # A more robust approach might track conversation ID or use a dedicated reply template
            # For simplicity here, we filter by ontology.
            self.agent.add_behaviour(self.agent.ReceiveResultsBehaviour(), template)


    class ReceiveResultsBehaviour(CyclicBehaviour):
        """Handles incoming messages from the Analyzer Agent."""
        async def run(self) -> None:
            # Receive messages matching the template added in SendVideoBehaviour
            msg = await self.receive(timeout=60) # Wait up to 60 seconds for a response

            if not msg:
                logger.warning(f"[{self.agent.jid}] No response received within timeout.")
                # Optionally, try resending the request or stop the agent
                await self.agent.stop() # Stop the agent after timeout for this example
                return

            performative = msg.get_metadata("performative")
            ontology = msg.get_metadata("ontology")
            sender = str(msg.sender) # Get sender JID as string

            logger.info(f"[{self.agent.jid}] Received message from {sender} with performative '{performative}' and ontology '{ontology}'")

            if performative == Performative.INFORM and ontology == Ontology.VIDEO_ANALYSIS:
                logger.info(f"[{self.agent.jid}] Received analysis results:")
                try:
                    data = json.loads(msg.body)
                    # Optional: Validate received data against VideoAnalysisResult model
                    # analysis_result = VideoAnalysisResult(**data) # Requires careful handling of nested dicts
                    logger.info(json.dumps(data, indent=4))
                except json.JSONDecodeError as e:
                    logger.error(f"[{self.agent.jid}] Error decoding analysis results from {sender}: {e}")
                except Exception as e:
                     logger.error(f"[{self.agent.jid}] Error processing analysis results from {sender}: {e}", exc_info=True)

                # Analysis successful, stop receiving results for this request
                self.kill() # Stop this specific behavior instance
                await self.agent.stop() # Stop the agent after receiving results for this example

            elif performative == Performative.FAILURE:
                 logger.warning(f"[{self.agent.jid}] Analysis failed for request from {sender}:")
                 try:
                     error_data = json.loads(msg.body)
                     # Attempt to parse the error message using the ErrorMessage model
                     error_msg = ErrorMessage(**error_data)
                     logger.error(f"Error Code: {error_msg.code}, Message: {error_msg.message}")
                     if error_msg.details:
                         logger.error(f"Details: {error_msg.details}")
                 except json.JSONDecodeError:
                     # If body is not JSON or doesn't match ErrorMessage format
                     logger.error(f"Could not parse error message body: {msg.body}")
                 except Exception as e:
                      logger.error(f"[{self.agent.jid}] Error processing failure message from {sender}: {e}", exc_info=True)

                 # Analysis failed, stop receiving results for this request
                 self.kill() # Stop this specific behavior instance
                 await self.agent.stop() # Stop the agent after receiving failure for this example

            elif performative == Performative.AGREE:
                 logger.info(f"[{self.agent.jid}] Analyzer agent agreed to perform analysis.")
                 # Continue waiting for the INFORM or FAILURE message

            elif performative == Performative.NOT_UNDERSTOOD:
                 logger.warning(f"[{self.agent.jid}] Analyzer agent did not understand the request.")
                 logger.warning(f"Original message body sent: {msg.body}")
                 # Handle the not-understood scenario, potentially resend or log
                 self.kill() # Stop this specific behavior instance
                 await self.agent.stop() # Stop the agent for this example

            # For other performatives or ontologies, the message is ignored by this behavior
            # due to the template, but if the template was broader, you'd add more elif blocks.


        async def on_end(self):
            """Called when the behavior is killed."""
            logger.info(f"[{self.agent.jid}] ReceiveResultsBehaviour finished.")


    async def setup(self) -> None:
        """Agent setup method, called when the agent starts and connects."""
        logger.info(f"[{self.jid}] CreatorAgent started and connected.")
        # Add the behavior to send the initial request
        self.add_behaviour(self.SendVideoBehaviour())


# ================== Analyzer Agent ==================
class AnalyzerAgent(BaseAgent):
    """Agent responsible for analyzing videos upon request."""

    class AnalyzeVideoBehaviour(CyclicBehaviour):
        """Listens for and handles video analysis requests."""
        async def run(self) -> None:
            # Wait for messages matching the template set in agent.setup()
            msg = await self.receive(timeout=30)

            if not msg:
                # No message received within timeout, just continue waiting
                return

            logger.info(f"[{self.agent.jid}] Received analysis request from {msg.sender}")

            # --- Validate and process the request ---
            try:
                # 1. Validate message format and content
                performative = msg.get_metadata("performative")
                language = msg.get_metadata("language")
                ontology = msg.get_metadata("ontology")

                if performative != Performative.REQUEST or language != ContentLanguage.JSON or ontology != Ontology.VIDEO_ANALYSIS:
                    logger.warning(f"[{self.agent.jid}] Received message with unexpected format: performative={performative}, language={language}, ontology={ontology}")
                    await self._send_response(
                         msg,
                         Performative.NOT_UNDERSTOOD,
                         ErrorMessage(code="BAD_MESSAGE_FORMAT", message="Message format, language, or ontology is incorrect.").to_dict(),
                         Ontology.ERROR # Use error ontology for NOT_UNDERSTOOD details
                    )
                    return # Stop processing this message

                try:
                    request_data = json.loads(msg.body)
                    # Optional: Validate request_data against AnalysisRequest model
                    request = AnalysisRequest(**request_data)
                except json.JSONDecodeError:
                     logger.warning(f"[{self.agent.jid}] Received message with invalid JSON body from {msg.sender}")
                     await self._send_response(
                          msg,
                          Performative.NOT_UNDERSTOOD,
                          ErrorMessage(code="INVALID_JSON", message="Message body is not valid JSON.").to_dict(),
                          Ontology.ERROR
                     )
                     return # Stop processing this message
                except TypeError as e: # Catches errors if JSON structure doesn't match AnalysisRequest dataclass
                     logger.warning(f"[{self.agent.jid}] Received message with incorrect content structure from {msg.sender}: {e}")
                     await self._send_response(
                          msg,
                          Performative.NOT_UNDERSTOOD,
                          ErrorMessage(code="INVALID_CONTENT_STRUCTURE", message=f"Message content structure is incorrect: {e}").to_dict(),
                          Ontology.ERROR
                     )
                     return # Stop processing this message


                video_url = request.video_reference
                logger.info(f"[{self.agent.jid}] Received request to analyze video: {video_url}")

                # 2. Send agreement (optional, but good practice for requests)
                await self._send_response(
                    msg,
                    Performative.AGREE,
                    {"message": "Analysis request received and accepted."}
                )

                # 3. Perform the actual analysis (including format validation)
                # This method now handles the invalid format check
                analysis_result = await self._perform_analysis(video_url, request.analysis_types)

                # 4. Send results or failure based on analysis outcome
                if "error" in analysis_result:
                    # Analysis failed (e.g., invalid format)
                    await self._send_response(
                        msg,
                        Performative.FAILURE,
                        analysis_result["error"], # Send the error details from _perform_analysis
                        Ontology.ERROR # Use error ontology for failure details
                    )
                    logger.warning(f"[{self.agent.jid}] Sent FAILURE message for video {video_url} to {msg.sender}")
                else:
                    # Analysis successful
                    await self._send_response(
                        msg,
                        Performative.INFORM,
                        analysis_result, # Send the analysis result dictionary
                        Ontology.VIDEO_ANALYSIS # Use video analysis ontology for results
                    )
                    logger.info(f"[{self.agent.jid}] Sent INFORM message with analysis results for video {video_url} to {msg.sender}")

            except Exception as e:
                # Catch any unexpected errors during request handling or analysis
                logger.error(f"[{self.agent.jid}] Unexpected error processing request from {msg.sender}: {e}", exc_info=True)
                # Send a general failure message
                try:
                    await self._send_response(
                        msg,
                        Performative.FAILURE,
                        ErrorMessage(code="INTERNAL_ERROR", message=f"An internal processing error occurred: {e}").to_dict(),
                        Ontology.ERROR
                    )
                except Exception as send_e:
                     logger.error(f"[{self.agent.jid}] Failed to send FAILURE message back to {msg.sender}: {send_e}", exc_info=True)


        async def _send_response(
            self,
            original_msg: Message,
            performative: str,
            body: Dict[str, Any], # Body is now expected to be a dictionary
            ontology: Optional[str] = None,
            to: Optional[str] = None # Allows sending to a different recipient if needed
        ) -> None:
            """Helper method to send standardized responses."""
            # Create a reply message to the original sender, or a new message to a specified recipient
            response = original_msg.make_reply() if to is None else Message(to=to)

            # Set standard FIPA ACL parameters
            response.set_metadata("performative", performative)
            response.set_metadata("language", ContentLanguage.JSON) # Assuming JSON content for responses
            if ontology:
                response.set_metadata("ontology", ontology)

            # Set conversation ID to maintain conversation context
            if original_msg.get_metadata("conversation-id"):
                 response.set_metadata("conversation-id", original_msg.get_metadata("conversation-id"))
            # Optionally, use in-reply-to and reply-with for stricter protocol adherence

            # Set the message body (must be a string)
            try:
                response.body = json.dumps(body)
            except TypeError as e:
                logger.error(f"[{self.agent.jid}] Failed to serialize response body to JSON: {e}", exc_info=True)
                # Fallback or raise error - sending a failure might be appropriate here
                response.body = json.dumps({"error": "Failed to serialize response body"}) # Simple fallback


            await self.send(response)


        async def _perform_analysis(self, video_url: str, analysis_types: List[str]) -> Dict[str, Any]:
            """
            Simulate video analysis processing, including format validation.
            Returns analysis result dict or an error dict.
            """
            logger.info(f"[{self.agent.jid}] Simulating analysis for {video_url}")

            # --- Simulate Invalid Format Handling ---
            # Check for common invalid file extensions or patterns
            invalid_extensions = ['.txt', '.doc', '.pdf', '.jpg', '.png'] # Add more as needed
            if any(video_url.lower().endswith(ext) for ext in invalid_extensions):
                 logger.warning(f"[{self.agent.jid}] Detected potentially invalid video format based on extension: {video_url}")
                 return {"error": ErrorMessage(code="INVALID_FORMAT", message=f"Unsupported video format based on extension: {os.path.splitext(video_url)[1]}").to_dict()}

            # Add a check for unsupported protocols (e.g., ftp)
            if not video_url.startswith('http://') and not video_url.startswith('https://'):
                 logger.warning(f"[{self.agent.jid}] Detected unsupported protocol in video reference: {video_url}")
                 return {"error": ErrorMessage(code="UNSUPPORTED_PROTOCOL", message=f"Unsupported protocol in video reference: {video_url.split('://')[0]}").to_dict()}

            # In a real implementation, you would use libraries like OpenCV, moviepy, or ffmpeg
            # to attempt to open and read the video file from the URL.
            # If opening fails, that's your indication of an invalid or inaccessible file.
            # Example (conceptual, requires actual download/access logic):
            # try:
            #     cap = cv2.VideoCapture(video_url) # cv2 can sometimes open URLs
            #     if not cap.isOpened():
            #          raise ValueError("Could not open video stream")
            #     # Read a frame to confirm it's a valid video
            #     ret, frame = cap.read()
            #     if not ret:
            #          raise ValueError("Could not read video frame")
            #     cap.release()
            # except Exception as e:
            #     logger.warning(f"[{self.agent.jid}] Failed to open/read video {video_url}: {e}")
            #     return {"error": ErrorMessage(code="VIDEO_ACCESS_ERROR", message=f"Could not access or read video file: {e}").to_dict()}


            # --- Simulate Successful Analysis ---
            logger.info(f"[{self.agent.jid}] Simulating successful analysis for {video_url}")
            await asyncio.sleep(5) # Simulate processing time

            # Generate dummy analysis results based on requested types
            simulated_objects = []
            simulated_colors = ColorAnalysis(dominant_colors=[], color_distribution={})

            if "object_detection" in analysis_types:
                simulated_objects = [
                    VideoObject(
                        object_type="person",
                        confidence=0.95,
                        position=Position(x=100, y=200, width=60, height=120)
                    ),
                    VideoObject(
                        object_type="car",
                        confidence=0.80,
                        position=Position(x=400, y=300, width=150, height=100)
                    )
                ]
            if "color_analysis" in analysis_types:
                 simulated_colors = ColorAnalysis(
                    dominant_colors=["#FF5733", "#33FF57"],
                    color_distribution={"#FF5733": 0.6, "#33FF57": 0.4}
                 )

            # Return the simulated analysis result
            return VideoAnalysisResult(objects=simulated_objects, colors=simulated_colors).to_dict()


    async def setup(self) -> None:
        """Agent setup method, called when the agent starts and connects."""
        logger.info(f"[{self.jid}] AnalyzerAgent started and connected.")
        # Define a template to filter incoming messages:
        # We only want messages that are a REQUEST for VIDEO_ANALYSIS.
        template = Template()
        template.set_metadata("performative", Performative.REQUEST)
        template.set_metadata("ontology", Ontology.VIDEO_ANALYSIS)

        # Add the behavior to handle these requests
        self.add_behaviour(self.AnalyzeVideoBehaviour(), template)


# ================== Main Function ==================
async def run_agents(xmpp_server: str, creator_jid: str, creator_password: str, analyzer_jid: str, analyzer_password: str):
    """Initializes and runs the Creator and Analyzer agents."""
    logger.info(f"Connecting to XMPP server: {xmpp_server}")

    analyzer = AnalyzerAgent(analyzer_jid, analyzer_password)
    creator = CreatorAgent(creator_jid, creator_password)

    # Start agents. auto_register=True attempts to register the JID if it doesn't exist,
    # but this depends on the XMPP server configuration.
    # For remote servers, JIDs usually need to be pre-registered.
    # If using a public server or one where you can't auto-register, remove auto_register=True.
    # You might need to manually register the JIDs on the server first.
    await asyncio.gather(
        analyzer.start(), # Removed auto_register=True for typical remote server use
        creator.start()   # Removed auto_register=True for typical remote server use
    )

    logger.info("Agents started. Waiting for them to finish...")

    # Keep running while agents are alive
    while analyzer.is_alive() or creator.is_alive():
        await asyncio.sleep(1)

    logger.info("All agents have stopped. Shutting down...")

if __name__ == "__main__":
    # --- Configuration for your XMPP Server and Agents ---
    # IMPORTANT: Replace these with your actual details.
    # The XMPP server address (e.g., "your_xmpp_server.com")
    # You might need to specify the port if it's not the standard 5222.
    # SPADE often handles SRV records to find the port, but explicit host/port might be needed.
    # If your server is "example.com" and agent JIDs are "user@example.com",
    # then xmpp_server should be "example.com".
    XMPP_SERVER = "your_xmpp_server.com" # Replace with your XMPP server domain

    # Creator Agent details
    CREATOR_JID = f"creator@{XMPP_SERVER}" # Replace with your creator agent's full JID
    CREATOR_PASSWORD = "your_creator_password" # Replace with your creator agent's password

    # Analyzer Agent details
    ANALYZER_JID = f"analyzer@{XMPP_SERVER}" # Replace with your analyzer agent's full JID
    ANALYZER_PASSWORD = "your_analyzer_password" # Replace with your analyzer agent's password
    # ----------------------------------------------------

    # Ensure you have aiodns and aioxmpp installed:
    # pip install aiodns aioxmpp

    # Run the main function
    spade.run(run_agents(XMPP_SERVER, CREATOR_JID, CREATOR_PASSWORD, ANALYZER_JID, ANALYZER_PASSWORD))

