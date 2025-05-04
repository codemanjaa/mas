import asyncio
from spade.agent import Agent

class DummyAgent(Agent):
    async def setup(self):
        print("Agent initialized. Connecting...")

async def run_agent():
    agent = DummyAgent("your_jid@example.com", "your_password")
    await agent.start()
    
    # ✅ Use 'host' instead of 'address'
    await agent.connect(host="xmpp.example.com", port=5222)  
    
    print("Connected!")
    await asyncio.sleep(5)
    await agent.stop()

asyncio.run(run_agent())