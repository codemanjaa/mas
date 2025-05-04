import asyncio
from spade.agent import Agent

class FixedAgent(Agent):
    async def _async_connect(self):
        await self.client.connect(host=self.jid.host, port=self.xmpp_port)  

class MyAgent(FixedAgent):
    async def setup(self):
        print("Agent connected successfully!")

async def main():
    agent = MyAgent("your_jid@localhost", "your_password")
    await agent.start()
    await asyncio.sleep(5)
    await agent.stop()

asyncio.run(main())