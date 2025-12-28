# Execution System

The Execution System handles the actual execution of nodes in different execution pools (ASYNC, THREAD, PROCESS). This document explains FlowRunner (LoopManager) and PoolExecutor, which work together to execute workflows in Production Mode.

## Navigation

- [← Back to Development Documentation](Development.md)
- [← Previous: Workflow Engine](02-Workflow-Engine.md)
- [Next: Node System →](04-Node-System.md)

## Overview

The Execution System consists of two main components:

1. **FlowRunner**: Manages a single loop's execution cycle in Production Mode
2. **PoolExecutor**: Handles execution of nodes in different execution pools

## FlowRunner (LoopManager)

FlowRunner is the concrete implementation of the LoopManager concept. It manages one loop at a time, executing nodes sequentially until reaching a NonBlockingNode.

### Architecture

```mermaid
classDiagram
    class FlowRunner {
        -FlowNode producer_flow_node
        -ProducerNode producer
        -PoolExecutor executor
        -WorkflowEventEmitter events
        -bool running
        -int loop_count
        +start()
        -_init_nodes()
        -_process_next_nodes(current, input_data)
        +shutdown(force)
        +kill_producer()
    }
    
    class PoolExecutor {
        -ThreadPoolExecutor _thread_pool
        -ProcessPoolExecutor _process_pool
        +execute_in_pool(pool_type, node, node_output)
        -_execute_async(node, node_output)
        -_execute_thread(node, node_output)
        -_execute_process(node, node_output)
        +shutdown()
    }
    
    FlowRunner --> PoolExecutor
```

### Execution Flow

```mermaid
flowchart TD
    A[FlowRunner.start] --> B[Initialize Nodes]
    B --> C{Loop Running?}
    C -->|Yes| D[Execute Producer]
    D --> E[Process Next Nodes]
    E --> F{NonBlockingNode?}
    F -->|No| G[Execute BlockingNode]
    G --> H[Process Next Nodes]
    H --> F
    F -->|Yes| I[End Iteration]
    I --> C
    C -->|No| J[Shutdown]
    
    style D fill:#e1f5ff
    style G fill:#fff4e1
    style I fill:#ffe1f5
```

### Loop Execution Sequence

```mermaid
sequenceDiagram
    participant FR as FlowRunner
    participant PE as PoolExecutor
    participant PN as ProducerNode
    participant BN as BlockingNode
    participant NBN as NonBlockingNode

    FR->>FR: start()
    FR->>FR: _init_nodes()
    
    loop Each Iteration
        FR->>PE: execute_in_pool(Producer)
        PE->>PN: await execute()
        PN-->>PE: NodeOutput
        PE-->>FR: NodeOutput
        
        FR->>FR: _process_next_nodes()
        FR->>PE: execute_in_pool(BlockingNode)
        PE->>BN: await execute()
        BN-->>PE: NodeOutput
        PE-->>FR: NodeOutput
        
        FR->>FR: _process_next_nodes()
        FR->>PE: execute_in_pool(NonBlockingNode)
        PE->>NBN: await execute()
        NBN-->>PE: NodeOutput
        PE-->>FR: NodeOutput
        
        Note over FR: Iteration complete,<br/>return to Producer
    end
```

### Node Initialization

Before the loop starts, all nodes in the flow are initialized recursively:

```python
async def _init_nodes(self):
    """Initialize all nodes in the flow by calling their init() method."""
    visited = set()
    await self._init_node_recursive(self.producer_flow_node, visited)

async def _init_node_recursive(self, flow_node: FlowNode, visited: set):
    if flow_node.id in visited:
        return
    visited.add(flow_node.id)
    
    await flow_node.instance.init()  # Calls is_ready() + setup()
    
    for branch_nodes in flow_node.next.values():
        for next_node in branch_nodes:
            await self._init_node_recursive(next_node, visited)
```

### Branch Selection Logic

FlowRunner handles branching based on node type:

```mermaid
flowchart TD
    A[Get Next Nodes] --> B{ExecutionCompleted?}
    B -->|Yes| C[Broadcast to ALL branches]
    B -->|No| D{ConditionalNode?}
    D -->|Yes| E[Follow selected branch]
    D -->|No| F[Follow default branch]
    E --> G[Execute Selected Nodes]
    F --> G
    C --> G
```

**Branch Selection Rules:**

1. **ExecutionCompleted (Sentinel)**: Broadcasts to ALL downstream nodes regardless of logic
2. **ConditionalNode**: Follows the branch specified by `instance.output` ("yes" or "no")
3. **Other Nodes**: Follows the "default" branch

### Error Handling

```python
try:
    # Execute nodes
    await self.executor.execute_in_pool(...)
except asyncio.CancelledError:
    logger.info("FlowRunner loop cancelled")
    self.running = False
    raise
except Exception as e:
    logger.exception("Error in loop", error=str(e))
    await asyncio.sleep(1)  # Brief pause before retry
```

**Error Recovery:**
- Logs exception
- Pauses briefly (1 second)
- Continues to next iteration
- Failed payloads are not automatically retried (fail-fast policy)

## PoolExecutor

PoolExecutor handles the actual execution of nodes in different execution pools. It supports three pool types: ASYNC, THREAD, and PROCESS.

### Pool Types

```mermaid
flowchart LR
    A[PoolExecutor] --> B[ASYNC Pool]
    A --> C[THREAD Pool]
    A --> D[PROCESS Pool]
    
    B --> E[Direct await]
    C --> F[ThreadPoolExecutor]
    D --> G[ProcessPoolExecutor]
    
    style B fill:#e1f5ff
    style C fill:#fff4e1
    style D fill:#ffe1f5
```

### Execution Methods

| Pool Type | Method | Mechanism | Use Case |
|-----------|--------|-----------|----------|
| **ASYNC** | Direct await | `await node.run(node_output)` | I/O-bound operations (HTTP, DB, file) |
| **THREAD** | ThreadPoolExecutor | Runs in thread with new event loop | CPU-bound tasks that can release GIL |
| **PROCESS** | ProcessPoolExecutor | Serializes node/data via pickle | CPU-intensive tasks, true parallelism |

### ASYNC Execution (Default)

```python
if pool == PoolType.ASYNC:
    return await node.run(node_output)
```

**Characteristics:**
- Direct async execution in current event loop
- Best for I/O-bound operations
- No serialization overhead
- Shares memory space

### THREAD Execution

```python
@staticmethod
def _run_in_thread(node: BaseNode, node_output: NodeOutput) -> NodeOutput:
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    try:
        return new_loop.run_until_complete(node.run(node_output))
    finally:
        new_loop.close()

async def _execute_thread(self, node, node_output):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        self._thread_pool, 
        PoolExecutor._run_in_thread, 
        node, 
        node_output
    )
```

**Characteristics:**
- Creates new event loop in thread
- Uses ThreadPoolExecutor
- Good for CPU-bound tasks that can release GIL
- Shares memory but separate execution context

### PROCESS Execution

```python
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

async def _execute_process(self, node, node_output):
    serialized_node = pickle.dumps(node)
    serialized_data = pickle.dumps(node_output)
    result_bytes = await loop.run_in_executor(
        self._process_pool,
        PoolExecutor._run_in_process,
        serialized_node,
        serialized_data
    )
    return pickle.loads(result_bytes)
```

**Characteristics:**
- True parallelism (bypasses GIL)
- Requires serialization (pickle)
- Isolated memory space
- Best for CPU-intensive tasks

### Pool Selection

The execution pool for a loop is determined dynamically by the FlowRunner:

```mermaid
flowchart TD
    A[FlowRunner] --> B[Inspect All Nodes in Loop]
    B --> C[Collect execution_pool Preferences]
    C --> D[Select Highest Priority]
    D --> E{PROCESS?}
    E -->|Yes| F[Use ProcessPool]
    E -->|No| G{THREAD?}
    G -->|Yes| H[Use ThreadPool]
    G -->|No| I[Use AsyncPool]
    
    style F fill:#ffe1f5
    style H fill:#fff4e1
    style I fill:#e1f5ff
```

**Priority Order:**
1. **PROCESS** (highest) - True parallelism
2. **THREAD** (medium) - Parallel execution possible
3. **ASYNC** (lowest) - Default, best for I/O

**Example:**
If a loop contains nodes with preferences `[ASYNC, THREAD, ASYNC]`, the entire loop will run in a **ThreadPool** for that cycle.

### Serialization Requirements

**Process Pool Constraints:**

- Node classes must be **picklable**:
  - No lambdas, closures, or unpicklable attributes
  - Resources (connections, file handles) cannot be serialized
- `NodeOutput` and all nested data must be:
  - JSON-serializable, or
  - Picklable
- Resources must be initialized in-process:
  - Use `setup()` method to initialize connections, clients, etc.

### Pool Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Uninitialized
    Uninitialized --> LazyInit: First use
    LazyInit --> ThreadPool: THREAD requested
    LazyInit --> ProcessPool: PROCESS requested
    LazyInit --> AsyncPool: ASYNC requested
    ThreadPool --> Running
    ProcessPool --> Running
    AsyncPool --> Running
    Running --> Shutdown: shutdown()
    Shutdown --> [*]
```

**Lazy Initialization:**
Pools are created on first use to conserve resources:

```python
def __init__(self, max_workers_thread: int = 10, max_workers_process: int = 4):
    self._thread_pool: Optional[ThreadPoolExecutor] = None
    self._process_pool: Optional[ProcessPoolExecutor] = None
```

## Production Mode Execution

### Complete Execution Flow

```mermaid
sequenceDiagram
    participant FE as FlowEngine
    participant FR as FlowRunner
    participant PE as PoolExecutor
    participant PN as ProducerNode
    participant BN as BlockingNode
    participant NBN as NonBlockingNode
    participant QM as QueueManager

    FE->>FR: create_loop(producer)
    FE->>FR: start()
    FR->>FR: _init_nodes()
    
    loop Each Iteration
        FR->>PE: execute_in_pool(Producer)
        PE->>PN: await execute()
        PN-->>PE: NodeOutput
        PE-->>FR: NodeOutput
        
        FR->>PE: execute_in_pool(BlockingNode)
        PE->>BN: await execute()
        BN-->>PE: NodeOutput
        PE-->>FR: NodeOutput
        
        FR->>PE: execute_in_pool(NonBlockingNode)
        PE->>NBN: await execute()
        NBN->>QM: push(queue_name, data)
        NBN-->>PE: NodeOutput
        PE-->>FR: NodeOutput
        
        Note over FR: Iteration complete,<br/>return to Producer
    end
```

### Loop Characteristics

- **Isolation**: Each loop runs in its own execution pool
- **Continuous**: Loops run until explicitly stopped
- **Sequential**: Nodes execute in order within a loop
- **Async**: All operations use async/await
- **Fail-Fast**: Errors don't stop the loop, failed payloads go to DLQ

## Development Mode Execution

In Development Mode, FlowRunner is not used. FlowEngine directly executes nodes:

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant API as API Endpoint
    participant FE as FlowEngine
    participant Cache as CacheStore
    participant Node as Node

    Dev->>API: POST /dev/execute (node_id)
    API->>FE: run_development_node(node_id, input_data)
    FE->>FE: Get upstream nodes
    FE->>Cache: get(node_output_key)
    Cache-->>FE: Cached output (or None)
    FE->>Node: await run(input_data)
    Node-->>FE: NodeOutput
    FE->>Cache: set(node_output_key, output)
    FE-->>API: NodeOutput
    API-->>Dev: 200 OK
```

**Key Differences:**
- No FlowRunner/LoopManager
- Direct node execution
- Redis cache for state
- Dependency resolution from cache

## Cleanup and Shutdown

### Graceful Shutdown

```python
def shutdown(self, force: bool = False):
    self.running = False
    if force:
        # Cancel all running tasks
        # Force shutdown executors
    else:
        # Wait for current iteration to complete
        # Shutdown executors gracefully
```

### Pool Cleanup

```python
def shutdown(self) -> None:
    if self._thread_pool:
        self._thread_pool.shutdown(wait=True)
    if self._process_pool:
        self._process_pool.shutdown(wait=True)
```

## Best Practices

### Choosing Execution Pools

1. **Use ASYNC** for:
   - HTTP requests
   - Database operations
   - File I/O
   - Queue operations

2. **Use THREAD** for:
   - CPU-bound tasks that can release GIL
   - External process calls
   - Image processing (with PIL)

3. **Use PROCESS** for:
   - CPU-intensive Python code
   - Heavy computation
   - Tasks requiring true parallelism

### Node Implementation

- Always use `async def execute()`
- Use `setup()` for resource initialization
- Ensure picklability if using PROCESS pool
- Handle errors gracefully (don't crash the loop)

## Related Documentation

- [Workflow Engine](02-Workflow-Engine.md) - FlowEngine and graph management
- [Node System](04-Node-System.md) - Node architecture and lifecycle
- [Storage System](06-Storage-System.md) - QueueManager and cross-loop communication
- [Development Workflow](10-Development-Workflow.md) - Development practices

---

[← Back to Development Documentation](Development.md) | [← Previous: Workflow Engine](02-Workflow-Engine.md) | [Next: Node System →](04-Node-System.md)

