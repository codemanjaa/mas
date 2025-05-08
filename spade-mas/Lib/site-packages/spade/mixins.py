import asyncio
import multiprocessing as mp
from typing import Optional
from spade.agent import Agent

class StandaloneMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._process: Optional[mp.Process] = None
        self._start_error = mp.Queue()
        # Store initialization parameters
        self._init_args = args
        self._init_kwargs = kwargs

    async def start(self, auto_register: bool = True) -> None:
        """
        Starts the agent in a new process.
        """
        # If we are in child process, do normal start
        if self._process and self._process.pid == mp.current_process().pid:
            await super().start(auto_register=auto_register)
            return

        # Create and launch process
        ctx = mp.get_context('spawn')
        self._process = ctx.Process(
            target=self._run_in_process,
            args=(self.__class__, self._init_args, self._init_kwargs, 
                  auto_register, self._start_error),
            daemon=True
        )
        self._process.start()

        # Wait for possible startup errors
        try:
            error = self._start_error.get(timeout=10)
            if error:
                self._process.terminate()
                self._process = None
                raise error
        except mp.queues.Empty:
            pass

    @staticmethod
    def _run_in_process(cls, args, kwargs, auto_register: bool, 
                       error_queue: mp.Queue) -> None:
        """Helper method to run the agent in a new process."""
        try:
            # Create a fresh instance in the child process
            agent = cls(*args, **kwargs)
            asyncio.run(agent.start(auto_register=auto_register))
        except Exception as e:
            error_queue.put(e)
            raise

    async def stop(self) -> None:
        """Stops the agent and its process."""
        import os
        if self._process and os.getpid() == self._process.pid:
            # In child process, do normal stop
            await super().stop()
        elif self._process:
            # In parent process, terminate the process
            self._process.terminate()
            self._process.join(timeout=5)
            if self._process.is_alive():
                self._process.kill()
            self._process = None
