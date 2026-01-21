import asyncio
import pickle
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Optional, TYPE_CHECKING

from Node.Core.Node.Core.Data import PoolType, NodeOutput

if TYPE_CHECKING:
    from Node.Core.Node.Core.BaseNode import BaseNode


class PoolExecutor:
    """
    Executes nodes in different execution pools (async, thread, process).
    """
    
    def __init__(self, max_workers_thread: int = 10, max_workers_process: int = 4):
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        self._process_pool: Optional[ProcessPoolExecutor] = None
        self._max_workers_thread = max_workers_thread
        self._max_workers_process = max_workers_process
    
    async def execute_in_pool(self, pool: PoolType, node: 'BaseNode', node_output: NodeOutput) -> NodeOutput:
        if pool == PoolType.ASYNC:
            return await node.run(node_output)
        elif pool == PoolType.THREAD:
            return await self._execute_thread(node, node_output)
        elif pool == PoolType.PROCESS:
            return await self._execute_process(node, node_output)
        else:
            raise ValueError(f"Unknown execution pool: {pool}")
    
    @staticmethod
    def _run_in_thread(node: 'BaseNode', node_output: NodeOutput) -> NodeOutput:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(node.run(node_output))
        finally:
            new_loop.close()
    
    async def _execute_thread(self, node: 'BaseNode', node_output: NodeOutput) -> NodeOutput:
        if self._thread_pool is None:
            self._thread_pool = ThreadPoolExecutor(max_workers=self._max_workers_thread)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._thread_pool, PoolExecutor._run_in_thread, node, node_output)
    
    @staticmethod
    def _run_in_process(serialized_node: bytes, serialized_data: bytes) -> bytes:
        node = pickle.loads(serialized_node)
        node_data = pickle.loads(serialized_data)
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            result = new_loop.run_until_complete(node.run(node_data))
            return pickle.dumps(result)
        finally:
            new_loop.close()
    
    async def _execute_process(self, node: 'BaseNode', node_output: NodeOutput) -> NodeOutput:
        if self._process_pool is None:
            self._process_pool = ProcessPoolExecutor(max_workers=self._max_workers_process)
        loop = asyncio.get_event_loop()
        serialized_node = pickle.dumps(node)
        serialized_data = pickle.dumps(node_output)
        result_bytes = await loop.run_in_executor(
            self._process_pool, PoolExecutor._run_in_process, serialized_node, serialized_data
        )
        return pickle.loads(result_bytes)
    
    def shutdown(self, wait: bool = True) -> None:
        if self._thread_pool:
            self._thread_pool.shutdown(wait=wait)
            self._thread_pool = None
        if self._process_pool:
            self._process_pool.shutdown(wait=wait)
            self._process_pool = None
