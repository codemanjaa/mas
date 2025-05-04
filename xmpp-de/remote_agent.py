import asyncio
from spade.agent import Agent
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("XMPP_Connection")

class DummyAgent(Agent):
    async def setup(self):
        """Agent initialization"""
        logger.info("Agent initialized successfully")

    async def _async_connect(self):
        """Absolute minimal connection method"""
        try:
            logger.info(f"Connecting to {self.jid}")
            
            # This is the most basic connection that should work everywhere
            await self.client.connect()
            
            logger.info("Connection established successfully")
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            raise

async def run_agent():
    try:
        # Configuration - replace with your actual credentials
        jid = "murugan@5222.de"  # Must be full JID with server
        password = "quick2025"
        
        logger.info(f"Starting agent {jid}")
        
        agent = DummyAgent(jid, password)
        
        # Start agent with minimal parameters
        await agent.start(auto_register=False)
        
        logger.info("Authentication successful!")
        
        # Keep agent running
        while agent.is_alive():
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        if 'agent' in locals():
            await agent.stop()

if __name__ == "__main__":
    asyncio.run(run_agent())