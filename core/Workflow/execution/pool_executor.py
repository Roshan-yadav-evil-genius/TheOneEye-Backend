import pickle
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Optional, TYPE_CHECKING

from Node.Core.Node.Core.Data import PoolType, NodeOutput

if TYPE_CHECKING:
    from Node.Core.Node.Core.BaseNode import BaseNode


class PoolExecutor:
    """
    Executes nodes in different execution pools (thread, process).
    
    All execution is now synchronous - nodes are executed directly
    or in thread/process pools without async/await.
    """
    
    def __init__(self, max_workers_thread: int = 10, max_workers_process: int = 4):
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        self._process_pool: Optional[ProcessPoolExecutor] = None
        self._max_workers_thread = max_workers_thread
        self._max_workers_process = max_workers_process
    
    def execute_in_pool(self, pool: PoolType, node: 'BaseNode', node_output: NodeOutput) -> NodeOutput:
        """
        Execute a node in the appropriate pool.
        
        All pool types now execute synchronously:
        - ASYNC/THREAD: Execute in ThreadPoolExecutor (since everything is sync now)
        - PROCESS: Execute in ProcessPoolExecutor
        """
        if pool == PoolType.ASYNC or pool == PoolType.THREAD:
            return self._execute_thread(node, node_output)
        elif pool == PoolType.PROCESS:
            return self._execute_process(node, node_output)
        else:
            raise ValueError(f"Unknown execution pool: {pool}")
    
    @staticmethod
    def _run_node(node: 'BaseNode', node_output: NodeOutput) -> NodeOutput:
        """Run node synchronously."""
        return node.run(node_output)
    
    def _execute_thread(self, node: 'BaseNode', node_output: NodeOutput) -> NodeOutput:
        """Execute node in thread pool."""
        if self._thread_pool is None:
            self._thread_pool = ThreadPoolExecutor(max_workers=self._max_workers_thread)
        future = self._thread_pool.submit(PoolExecutor._run_node, node, node_output)
        return future.result()
    
    @staticmethod
    def _run_in_process(serialized_node: bytes, serialized_data: bytes) -> bytes:
        """Run node in separate process (requires pickling)."""
        node = pickle.loads(serialized_node)
        node_data = pickle.loads(serialized_data)
        result = node.run(node_data)
        return pickle.dumps(result)
    
    def _execute_process(self, node: 'BaseNode', node_output: NodeOutput) -> NodeOutput:
        """Execute node in process pool."""
        if self._process_pool is None:
            self._process_pool = ProcessPoolExecutor(max_workers=self._max_workers_process)
        serialized_node = pickle.dumps(node)
        serialized_data = pickle.dumps(node_output)
        future = self._process_pool.submit(
            PoolExecutor._run_in_process, serialized_node, serialized_data
        )
        result_bytes = future.result()
        return pickle.loads(result_bytes)
    
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the executor pools."""
        if self._thread_pool:
            self._thread_pool.shutdown(wait=wait)
            self._thread_pool = None
        if self._process_pool:
            self._process_pool.shutdown(wait=wait)
            self._process_pool = None
