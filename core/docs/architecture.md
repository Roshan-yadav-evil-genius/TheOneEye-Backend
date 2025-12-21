# Workflow Orchestrator Requirements

<iframe style="border: 1px solid rgba(0, 0, 0, 0.1);" width="800" height="450" src="https://embed.figma.com/board/ipiIPvsqG17Is2kzJJkv08/Node-Architecture?node-id=0-1&embed-host=share" allowfullscreen></iframe>

## 1. Overview

The Workflow Orchestrator is the central coordination system responsible for running workflows. It can be executed in two distinct modes: **Production Mode** for running complete, autonomous workflows, and **Development Mode** for iterative, developer-driven execution of single nodes.

The orchestrator ensures that nodes inside one loop and nodes across different loops communicate predictably while preserving each node's execution semantics, with different mechanisms applying to each mode.

### 1.1 Operating Modes

The Orchestrator has two modes that fundamentally change its behavior:

#### Production Mode
*   **Goal:** High-performance, autonomous execution of complete workflows.
*   **Mechanism:** The Orchestrator launches and manages `LoopManagers`. Each `LoopManager` is responsible for running an entire loop of nodes continuously.
*   **Execution:** The `LoopManager` determines the execution pool for the *entire loop* by selecting the highest-priority pool requested by any node within that loop.

#### Development Mode
*   **Goal:** Flexible, iterative testing and debugging of individual nodes.
*   **Mechanism:** The `LoopManager` concept is not used. The Orchestrator directly handles execution requests from the developer.
*   **Execution:** The Orchestrator executes nodes one at a time, in the *specific execution pool* requested by that individual node. It uses Redis as a cache to pass outputs from one step to the next.

### 1.2 Key Principles

* **Isolation:** Loops are fully isolated execution tracks running in separate pools (asyncio, threads, or processes).
* **Adaptive Execution:** The execution pool for a loop is determined dynamically based on the requirements of its constituent nodes, ensuring optimal resource usage.
* **Decoupling:** Cross-loop data flow is handled exclusively via an abstracted, multi-process safe queue system (Redis).
* **Predictability:** Node execution behavior is strictly determined by the **node type** and the **LoopManager**'s async execution strategy.
* **Fail-Fast:** Immediate failure policy with zero retries to preserve throughput and isolate problematic payloads.
* **Async-First:** The entire codebase uses async/await patterns throughout for optimal I/O performance and scalability.

---

## 2. Core Concepts

### 2.1 Node (BaseNode)

A **Node** is the smallest executable unit in a workflow. Each node inherits from `BaseNode`.

* Each node receives two objects:
  * `NodeConfig` — static initialization/config settings
  * `NodeData` — runtime payload for the iteration
* Each node also defines a preferred **`ExecutionPool`** (e.g., `ASYNC`, `THREAD`, `PROCESS`) via an enum property, indicating the ideal environment for its execution.
* All nodes implement an **async `execute()` method**: the executing agent (LoopManager or Orchestrator) **awaits** `await node.execute(...)` before moving on.
* Nodes use `async/await` throughout their implementation for I/O operations, queue access, and any asynchronous work.
* Nodes never manage their own concurrency; they simply "run" when invoked (by the LoopManager in Production Mode, or the Orchestrator in Development Mode) via async execution.

### 2.2 Node Types

The orchestrator supports three fundamental node types:

#### ProducerNode

* Marks loop start. Called first each iteration.
* Starts and controls the loop. Controls timing and triggers downstream nodes.
* Produces or fetches work units that drive the loop.
* When an iteration completes (per execution flow rules), the LoopManager returns control to Producer to begin next iteration.
* Designed to allow other parallel loops to run independently.

#### BlockingNode

* Performs work that must be completed prior to continuation.
* Executes work that must be completed *before* upstream nodes (like the Producer) continue.
* The LoopManager awaits the Blocking node **and all downstream Blocking children** in its async chain to complete before proceeding.
* Runs asynchronously and passes output to the next node if it exists.
* Awaits the entire downstream chain to complete before returning control.
* Forms strict **sequential async paths** within the workflow.

#### Non-Blocking Node

* Semantically marks loop-end in the execution model.
* Performs a computation or transformation but does not force the Producer to wait for downstream operations.
* From the LoopManager's perspective it awaits the node's execution, then the iteration ends and control returns to Producer.
* Nodes can offload long side-effects asynchronously — the node must ensure its `execute()` completes in a way consistent with loop semantics.
* Useful for creating **async boundaries** within the workflow.

> **Important:** Although we keep the names (Blocking / Non-Blocking) for intent and developer guidance, the final rule is that **the LoopManager awaits each node's `execute()`**; Non-Blocking nodes are treated as the iteration end marker.

#### LogicalNode

* Extends **BlockingNode** for conditional branching operations.
* Used for decision-making nodes that route execution to different branches based on conditions.
* Provides a `set_output(bool)` method that sets the branch direction:
  * `set_output(True)` routes to the `"yes"` branch.
  * `set_output(False)` routes to the `"no"` branch.
* The `output` property holds the string value (`"yes"` or `"no"`) used by the FlowRunner to select the next node.
* Example implementation: `IfCondition` node that evaluates conditions and routes accordingly.

```python
class LogicalNode(BlockingNode, ABC):
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        self.output: Optional[str] = None
        self.test_result = False

    def set_output(self, output: bool):
        self.test_result = output
        self.output = "yes" if output else "no"
```

### 2.3 Example of Producer and NonBlockingNode 

**QueueNode**

* Inherits from **NonBlockingNode**.
* Writes/publishes data to a Redis-backed queue via `await QueueManager.push()`.
* Acts as the **loop end marker** in the execution model.
* Executes asynchronously using `async/await`.
* After its execution completes, the LoopManager immediately returns to the Producer to start the next iteration.
* Pushes data to a queue, enabling data to be consumed in a different loop.

**QueueReader**

* Inherits from **ProducerNode**.
* Begins a new loop iteration by reading from a Redis queue using `await QueueManager.pop()`.
* Awaits data from a queue (`pop`) and starts a new loop iteration.
* Internal logic (async pop, timeouts, backoff) is up to the developer.
* The orchestrator treats it as the **loop entry point** (Producer).

### 2.4 Loop

A **Loop** is a continuous execution track controlled by a single **ProducerNode**. It contains a chain of Blocking and NonBlocking nodes.

* A loop's execution pool is determined **dynamically** by the **LoopManager** before execution begins.
* The LoopManager inspects the preferred `ExecutionPool` of every node within the loop. It then selects the pool with the highest-priority requirement among all nodes for executing the entire loop cycle.
* The priority order is: `PROCESS` (highest) > `THREAD` (medium) > `ASYNC` (lowest).
* For example, if a loop contains nodes with preferences `[ASYNC, THREAD, ASYNC]`, the entire loop will run in a **ThreadPool** for that cycle.
* Loops behave like async pipelines with timing rules defined by the node types.
* Loops are fully isolated execution tracks.

### 2.5 Node Lifecycle

Every node follows a well-defined lifecycle managed by the FlowRunner (Production Mode) or FlowEngine (Development Mode). The lifecycle consists of the following phases:

#### Lifecycle Methods

| Method | When Called | Purpose |
|--------|-------------|---------|
| `__init__(node_config)` | Workflow loading | Initialize node with static configuration |
| `init()` | Before first execution | Validate node readiness and call `setup()` |
| `setup()` | Called by `init()` | Initialize resources (DB connections, API clients) |
| `run(node_data)` | Each iteration | Entry point - populates form values, then calls `execute()` |
| `execute(node_data)` | Each iteration | Core business logic implementation |
| `cleanup()` | Shutdown | Release resources (connections, file handles) |

#### Execution Flow

```
Workflow Load:
  __init__(node_config) → form populated from config

Before Loop Starts:
  init() → is_ready() check → setup()

Each Iteration:
  run(node_data) → populate_form_values(node_data) → execute(node_data)

Shutdown:
  cleanup()
```

#### Form Value Population

The `run()` method handles Jinja template rendering before execution:

1. Receives `NodeOutput` from the previous node.
2. Calls `populate_form_values(node_data)` to render any Jinja templates in form fields.
3. Validates the form after template rendering.
4. Calls `execute(node_data)` with the processed input.

```python
async def run(self, node_data: NodeOutput) -> NodeOutput:
    self.populate_form_values(node_data)
    return await self.execute(node_data)
```

#### Validation with `is_ready()`

The `is_ready()` method validates the node before execution:

* For non-template fields: Performs full Django field validation.
* For Jinja template fields (containing `{{ }}`): Only checks that required fields are not empty.
* Full validation of template fields occurs after rendering in `populate_form_values()`.

### 2.6 Node Properties & Registration

#### BaseNodeProperty Interface

All nodes must implement the following properties defined in `BaseNodeProperty`:

| Property/Method | Type | Required | Purpose |
|-----------------|------|----------|---------|
| `execution_pool` | `PoolType` | Yes | Preferred execution environment (ASYNC, THREAD, PROCESS) |
| `identifier()` | `classmethod` | Yes | Unique string identifier for node type registration |
| `label` | `property` | No | Display name (defaults to class name) |
| `description` | `property` | No | Node description for documentation |
| `icon` | `property` | No | Icon identifier for UI display |

#### NodeRegistry Auto-Discovery

The `NodeRegistry` automatically discovers all node classes in the `Node.Nodes` package:

1. **Discovery:** Walks through all subpackages of `Node.Nodes` using `pkgutil`.
2. **Filtering:** Identifies classes that inherit from `ProducerNode`, `BlockingNode`, or `NonBlockingNode`.
3. **Registration:** Maps each node's `identifier()` to its class for instantiation.

```python
# Auto-discovery happens once, lazily
NodeRegistry._discover_node_classes()

# Node creation by type identifier
node = NodeRegistry.create_node(node_config)
```

**Node Identifier Convention:**
* Use kebab-case for identifiers (e.g., `"queue-reader"`, `"if-condition"`).
* The identifier in the workflow JSON `type` field must match exactly.

### 2.7 Form System

The Form System provides a Django-based configuration interface for nodes, supporting cascading field dependencies and Jinja template rendering.

#### Architecture Overview

The form system follows the Single Responsibility Principle with four specialized classes:

| Class | Responsibility |
|-------|---------------|
| `BaseForm` | Core form functionality (validation, field values, rebinding) |
| `DependencyHandler` | Manages field dependency cascading |
| `DependencyInjector` | Abstract interface for dependency configuration |
| `FormSerializer` | JSON serialization of forms for API/UI consumption |

#### BaseForm

`BaseForm` extends Django's `Form` with incremental update support:

```python
class BaseForm(DependencyInjector, forms.Form, metaclass=FormABCMeta):
    def update_field(self, field_name, value):
        """Update a single field and trigger dependency cascading."""
        
    def get_field_value(self, field_name):
        """Get current field value from any source."""
        
    def get_all_field_values(self):
        """Get all field values as a dictionary."""
```

**Key Features:**
* Incremental field updates without full form rebinding.
* Automatic dependency cascading when parent fields change.
* Django validation integration with error handling.

#### Cascading Field Dependencies

Forms can define parent-child field relationships where changing a parent field updates child field choices:

```python
class LocationForm(BaseForm):
    country = forms.ChoiceField(choices=[...])
    state = forms.ChoiceField(choices=[])  # Populated based on country
    city = forms.ChoiceField(choices=[])   # Populated based on state
    
    def get_field_dependencies(self):
        return {
            'country': ['state'],
            'state': ['city']
        }
    
    def populate_field(self, field_name, parent_value):
        if field_name == 'state':
            return get_states_for_country(parent_value)
        elif field_name == 'city':
            return get_cities_for_state(parent_value)
        return []
```

**DependencyHandler Behavior:**
1. When a parent field changes, clears all dependent fields recursively.
2. Calls `populate_field()` to get new choices for dependent fields.
3. Updates field choices in the form.

#### Jinja Template Support

Form fields can contain Jinja2 templates that are rendered at runtime with data from previous nodes:

```python
# In workflow JSON:
{
    "form": {
        "message": "Hello {{ data.user_name }}, your score is {{ data.score }}"
    }
}
```

**Template Rendering Flow:**
1. During `is_ready()`: Template fields are only checked for non-empty values.
2. During `populate_form_values()`: Templates are rendered using `NodeOutput.data`.
3. After rendering: Full Django validation is performed.

#### FormSerializer

Converts Django forms to JSON for API responses and UI rendering:

```python
serializer = FormSerializer(form)
json_output = serializer.to_json()

# Output structure:
{
    "fields": [
        {
            "tag": "select",
            "name": "country",
            "label": "Country",
            "options": [{"value": "us", "text": "United States"}],
            "value": "us",
            "errors": []
        }
    ],
    "non_field_errors": []
}
```

#### Node Form Integration

Nodes declare their form by implementing `get_form()`:

```python
class MyNode(BlockingNode):
    def get_form(self) -> Optional[BaseForm]:
        return MyNodeForm()
```

The form is automatically:
1. Populated with config data during `__init__()`.
2. Validated during `is_ready()`.
3. Template-rendered during `run()`.

---

## 3. Execution Model & Flow



The system's execution model differs significantly between its two operating modes.



### 3.1 Production Mode: The LoopManager Cycle



In Production Mode, the execution flow is **fully asynchronous** within each loop. The LoopManager executes the flow sequentially (awaiting each node) until it hits the Non-Blocking Node, at which point the iteration is complete.



1.  **Start:** LoopManager awaits the **Producer Node** (`await producer.execute(...)`).

2.  **Middle:** LoopManager sequentially awaits all **Blocking Nodes**. Each node's `execute()` must complete before continuing.

3.  **End:** LoopManager awaits the **Non-Blocking Node** (the async execution chain ends here). That node completes and the iteration ends.

4.  **Restart:** Immediately after the Non-Blocking Node completes, the LoopManager **jumps back to the Producer Node** to initiate the next iteration.



### 3.2 Execution Rules Summary (Production Mode)



| Node Type | Execution Model | LoopManager Behavior | Use Case |

|-----------|-----------------|---------------------|----------|

| **Producer** | Async (`async execute()`) | Awaited first, re-invoked after iteration completes | Starting loops, generating jobs, orchestrating flow |

| **Blocking** | Async (`async execute()`) | Awaits node and all downstream Blocking children to complete | Critical sequential operations, sequential async processing |

| **Non-Blocking** | Async (`async execute()`) | Awaits node execution, then iteration ends | Async branching, offloading long tasks, creating async boundaries |



### 3.3 Async Execution Model



* **LoopManager / Orchestrator:** fully async control flow using `async/await`; runs in asyncio event loops, thread pools, or process pools.

* **Nodes:** all nodes implement `async execute()` methods. Node authors must:

  * Implement `async def execute(node_data: NodeData) -> NodeData` for all nodes.

  * Use `async/await` for all I/O operations, queue access, and asynchronous work.

  * Ensure `execute()` completes (via await) only when the node has reached the state that should allow the orchestrator to continue the chain.

* **Reason:** outputs of a node directly become inputs of downstream nodes; async completion guarantees consistent handoff and deterministic loop timing while enabling optimal I/O performance and scalability.



*Loops run inside asyncio event loops (primary), ThreadPool, or ProcessPool execution contexts. The LoopManager core uses async/await throughout for orchestration control.*



### 3.4 Development Mode: The Orchestrator Cycle



In Development Mode, there is no `LoopManager`. The Orchestrator executes single nodes on-demand.



1.  **Request:** A developer requests the execution of a single node (e.g., Node B).

2.  **Dependency Check:** The Orchestrator inspects the workflow graph to find the upstream node (e.g., Node A). It checks a Redis cache for the last known output of Node A.

3.  **Input Resolution:** If a cached output for Node A is found, it is used as the input for Node B. If not, the execution may fail or await the execution of Node A.

4.  **Execution:** The Orchestrator runs `await node.execute(...)` for Node B in the specific `ExecutionPool` defined on Node B.

5.  **Store Output:** The output `NodeData` from Node B is saved to the Redis cache, overwriting any previous result for Node B and making it available for downstream nodes.

### 3.5 FlowNode & Graph Architecture

The workflow graph is represented internally using `FlowNode` objects connected in a directed graph structure.

#### FlowNode Data Structure

```python
@dataclass
class FlowNode:
    id: str                                    # Unique node identifier
    instance: BaseNode                         # The actual node implementation
    next: Dict[str, List["FlowNode"]]         # Branch key -> list of next nodes
```

#### Multiple Branch Support

The `next` field uses `Dict[str, List[FlowNode]]` instead of `Dict[str, FlowNode]` to support:

* **Multiple outgoing edges with the same key:** A single node can connect to multiple downstream nodes.
* **Logical branching:** LogicalNodes use `"yes"` and `"no"` keys to route execution.
* **Default connections:** Non-logical edges use `"default"` as the key.

**Example:**
```python
# Node "1" connects to both "node_10" and "node_14" via default branch
flow_node.next = {
    "default": [node_10, node_14]
}

# LogicalNode with yes/no branches
logical_node.next = {
    "yes": [success_node],
    "no": [failure_node]
}
```

#### Branch Key Normalization

The `BranchKeyNormalizer` utility handles conversion between workflow JSON and internal representation:

| JSON sourceHandle | Internal Key | Display Label |
|-------------------|--------------|---------------|
| `null` | `"default"` | None |
| `"Yes"` | `"yes"` | `"Yes"` |
| `"No"` | `"no"` | `"No"` |

#### FlowGraph Operations

The `FlowGraph` class manages the node collection:

```python
class FlowGraph:
    node_map: Dict[str, FlowNode]  # node_id -> FlowNode
    
    def add_node(self, flow_node: FlowNode)
    def connect_nodes(self, source_id: str, target_id: str, key: str)
    def get_node_instance(self, node_id: str) -> BaseNode
    def get_upstream_nodes(self, node_id: str) -> List[FlowNode]
```

| Method | Purpose |
|--------|---------|
| `add_node()` | Add a FlowNode to the graph |
| `add_node_at_end_of()` | Add a node and connect it as next of existing node |
| `connect_nodes()` | Connect two existing nodes with a branch key |
| `get_node()` | Get FlowNode by ID |
| `get_node_instance()` | Get the BaseNode instance by ID |
| `get_all_next()` | Get all next nodes for a given node |
| `get_upstream_nodes()` | Get all parent nodes that connect to a given node |

#### FlowBuilder

The `FlowBuilder` constructs the graph from workflow JSON:

1. **Add Nodes:** Parses node definitions and creates `FlowNode` instances via `NodeRegistry`.
2. **Connect Nodes:** Processes edges to establish `next` connections with normalized branch keys.

```python
flow_builder = FlowBuilder(flow_graph, NodeRegistry())
flow_builder.load_workflow(workflow_json)
```

#### FlowAnalyzer

The `FlowAnalyzer` provides graph traversal and analysis:

| Method | Purpose |
|--------|---------|
| `get_producer_nodes()` | Find all ProducerNode instances |
| `get_first_node_id()` | Find the entry point (node with no incoming edges) |
| `find_non_blocking_nodes()` | Find all NonBlockingNode instances |
| `find_loops()` | Find all (Producer, EndingNode) pairs |
| `build_chain_from_start_to_end()` | Build execution chain between two nodes |

---

## 4. Cross-Loop Communication — QueueManager (Redis-backed)

Cross-loop data flow is achieved through an abstracted `QueueManager` API, which manages Redis-backed queues stored in the Orchestrator.

### 4.1 Redis Queue Dictionary

* The **Workflow Orchestrator** maintains a dictionary of named queues, where each queue instance is inherently **multi-process safe** (backed by Redis).
* This approach guarantees predictable communication regardless of the sender/receiver pool types (Thread, Process).
* Queues are not owned by the LoopManager; they are managed at the orchestrator level.

### 4.2 QueueManager API Contract

Nodes access the queue system only through the high-level `QueueManager` API, which abstracts away Redis details (serialization, connection management, BPOP/BRPOP logic). All QueueManager methods are async.

| Node Type | Action | API Call Abstraction |
|-----------|--------|---------------------|
| **QueueNode** | Writes data to a queue | `await orchestrator.queue_manager.push(queue_name, data)` |
| **QueueReader** | Reads data from a queue | `await orchestrator.queue_manager.pop(queue_name, timeout)` |

The **QueueReader Node** in Loop B will use the `pop` method to await until data is available in the named queue.

### 4.3 Cross-Loop Data Flow

When a node pushes data to a queue:

* Workflow Orchestrator registers the event through the QueueManager.
* Orchestrator routes the message to all LoopManagers interested in that queue.
* Loop B receives data as NodeData for its QueueReader node.

This enables plug-and-play pipelines and decouples loops without requiring them to know each other's runtime details.

### 4.4 Post-Processing Pipeline

After the workflow graph is built from JSON, a series of post-processors validate and enhance the graph before execution.

#### PostProcessor Abstract Base

All post-processors inherit from `PostProcessor`:

```python
class PostProcessor(ABC):
    def __init__(self, graph: FlowGraph):
        self.graph = graph

    @abstractmethod
    def execute(self) -> None:
        """Execute the post-processing operation."""
        pass
```

#### Built-in Post-Processors

The `FlowEngine` applies post-processors in order:

```python
_post_processors: List[Type[PostProcessor]] = [QueueMapper, NodeValidator]
```

##### QueueMapper

Automatically assigns unique queue names to connected `QueueNode`-`QueueReader` pairs:

**Process:**
1. Iterates through all nodes in the graph.
2. For each `QueueNode`, finds connected `QueueReader` nodes.
3. Generates unique queue name: `queue_{source_id}_{target_id}`.
4. Assigns the queue name to both nodes' configs.

**Example:**
```
QueueNode "node_5" -> QueueReader "node_8"
Generated queue name: "queue_node_5_node_8"
```

##### NodeValidator

Validates all nodes are ready for execution:

**Process:**
1. Iterates through all nodes in the graph.
2. Calls `is_ready()` on each node.
3. Collects validation errors from node forms.
4. Raises `ValueError` with detailed error list if any node fails validation.

**Error Output:**
```
Workflow validation failed:
Node 'node_5': field_name: This field is required.
Node 'node_8': api_key: Invalid format.
```

#### Custom Post-Processors

Create custom post-processors by extending `PostProcessor`:

```python
class MyCustomProcessor(PostProcessor):
    def execute(self) -> None:
        for node_id, flow_node in self.graph.node_map.items():
            # Custom processing logic
            pass
```

Register in `FlowEngine`:
```python
FlowEngine._post_processors.append(MyCustomProcessor)
```

---

## 5. Workflow Orchestrator Responsibilities

The Workflow Orchestrator is the master controller, but its responsibilities shift depending on the operating mode.

### 5.1 Core Responsibilities (Both Modes)

*   **Workflow Loading:** Loads workflow definitions (e.g., React Flow JSON) and initializes `NodeConfig` for each node.
*   **Graph Management:** Builds the executable graph of nodes from the workflow definition.
*   **State & Observability:** Maintains and exposes system-wide state, health, logs, and metrics.
*   **Communication:** Manages the `QueueManager` for cross-loop communication and the Redis cache for `Development Mode`.

### 5.2 Production Mode Responsibilities

*   **Lifecycle Management:** Manages the lifecycle of `LoopManagers`, starting, stopping, and pausing entire loops.
*   **Execution Delegation:** Delegates the entire execution of a loop to the corresponding `LoopManager`.

### 5.3 Development Mode Responsibilities

*   **Direct Execution:** Directly handles requests from developers to execute single nodes. There is no `LoopManager`.
*   **Dependency & Input Resolution:** Before executing a node, it checks the workflow graph for upstream dependencies and queries the Redis cache for their outputs to use as input.
*   **Pool Management:** Executes the requested node in the specific `ExecutionPool` that the node has defined for itself.
*   **State Caching:** Stores the output of the executed node back into the Redis cache.

### 5.4 FlowEngine Implementation

The `FlowEngine` class is the concrete implementation of the Workflow Orchestrator:

```python
class FlowEngine:
    def __init__(self):
        self.data_store = DataStore()
        self.flow_runners: List[FlowRunner] = []
        self.flow_graph = FlowGraph()
        self.flow_analyzer = FlowAnalyzer(self.flow_graph)
        self.flow_builder = FlowBuilder(self.flow_graph, NodeRegistry())
```

#### Core Components

| Component | Purpose |
|-----------|---------|
| `DataStore` | Facade for Redis queue and cache operations |
| `FlowGraph` | Holds all FlowNode instances and connections |
| `FlowAnalyzer` | Graph traversal and analysis operations |
| `FlowBuilder` | Constructs graph from workflow JSON |
| `FlowRunner[]` | One runner per loop (Production Mode) |

#### Workflow Loading

```python
def load_workflow(self, workflow_json: Dict[str, Any]):
    # 1. Build graph from JSON
    self.flow_builder.load_workflow(workflow_json)
    
    # 2. Run post-processors
    for processor_class in self._post_processors:
        processor = processor_class(self.flow_graph)
        processor.execute()
    
    # 3. Create FlowRunner for each ProducerNode
    producer_nodes = self.flow_analyzer.get_producer_nodes()
    for producer_flow_node in producer_nodes:
        self.create_loop(producer_flow_node)
```

#### Execution Methods

| Method | Mode | Purpose |
|--------|------|---------|
| `run_production()` | Production | Starts all FlowRunners concurrently via `asyncio.gather()` |
| `run_development_node(node_id, input_data)` | Development | Executes a single node directly |

```python
async def run_production(self):
    tasks = [runner.start() for runner in self.flow_runners]
    await asyncio.gather(*tasks)

async def run_development_node(self, node_id: str, input_data: NodeOutput) -> NodeOutput:
    node = self.flow_graph.get_node_instance(node_id)
    return await node.run(input_data)
```

---

## 6. LoopManager Responsibilities (Production Mode Only)

LoopManager handles one loop at a time:

* Maintains reference to the ProducerNode.
* Determines the execution pool for the loop by calling a dedicated method (e.g., `select_pool()`). This method inspects the `ExecutionPool` preference of all nodes in the chain and selects the highest-priority pool (`PROCESS` > `THREAD` > `ASYNC`).
* Executes node chains in defined order; awaits each node's `execute()` to complete.
* Handles data transformation and passes NodeData to downstream nodes.
* Reports node-level exceptions and routes failed payloads to DLQ (all operations are async).

**LoopManager must NOT**:

* Own or manage queue storage internals — it uses the orchestrator-level `QueueManager` abstraction for cross-loop communication.
* Implicitly retry failed nodes.
* Communicate directly with other LoopManagers.

All cross-loop data flows go through orchestrator-level messaging.

### 6.1 FlowRunner Implementation

The `FlowRunner` class is the concrete implementation of the LoopManager concept:

```python
class FlowRunner:
    def __init__(self, producer_flow_node: FlowNode, executor: Optional[PoolExecutor] = None):
        self.producer_flow_node = producer_flow_node
        self.producer = producer_flow_node.instance
        self.executor = executor or PoolExecutor()
        self.running = False
        self.loop_count = 0
```

#### Initialization Phase

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

#### Loop Execution

```python
async def start(self):
    self.running = True
    await self._init_nodes()
    
    while self.running:
        self.loop_count += 1
        try:
            # Execute producer
            data = await self.executor.execute_in_pool(
                producer.execution_pool, producer, NodeOutput(data={})
            )
            
            # Traverse and execute nodes
            current = self.producer_flow_node
            while True:
                next_nodes = current.next
                if not next_nodes:
                    break
                
                # Select branch (default or logical output)
                branch_key = "default" if "default" in next_nodes else list(next_nodes.keys())[0]
                next_list = next_nodes.get(branch_key, [])
                
                next_flow_node = next_list[0]
                next_instance = next_flow_node.instance
                
                # Execute node in appropriate pool
                data = await self.executor.execute_in_pool(
                    next_instance.execution_pool, next_instance, data
                )
                
                # Stop at NonBlockingNode (loop end marker)
                if isinstance(next_instance, NonBlockingNode):
                    break
                
                current = next_flow_node
                
        except Exception as e:
            logger.exception("Error in loop", error=str(e))
            await asyncio.sleep(1)  # Brief pause before retry
```

#### Key Behaviors

| Behavior | Description |
|----------|-------------|
| **Node Initialization** | Recursively calls `init()` on all nodes before loop starts |
| **Branch Selection** | Currently uses `"default"` key for normal flow, falls back to first available key |
| **Loop Termination** | Iteration ends when `NonBlockingNode` is reached |
| **Error Recovery** | Logs exception, pauses briefly, then continues to next iteration |
| **Pool Delegation** | Uses `PoolExecutor` for all node execution |

> **Note:** LogicalNode branch selection based on `output` property (`"yes"`/`"no"`) is defined in the LogicalNode class but FlowRunner branch selection logic may need enhancement to fully utilize this for conditional routing.

---

## 7. Workflow Input Contract

* Input format: **React Flow JSON** with:
  * **Nodes**: List of node objects including `id`, `type` (e.g., 'producer', 'blocking', 'non-blocking'), and `data` (which maps to the `NodeConfig`).
  * **Edges**: List of connections defining the flow and used to prepare the node mapping (the execution chain).
* The orchestrator uses edges to determine immediate downstream nodes and whether paths contain Blocking semantics.

---

## 8. Error Handling (Immediate Failure Policy)

The system enforces an **Immediate Failure Policy** with **zero retries** to prioritize overall system throughput and stability.

### 8.1 Zero Retries

* **Zero automatic retries.** There will be **NO automatic retries** for any failing node.
* No automatic retry attempts by the orchestrator for failing nodes.

### 8.2 Action on Error

As soon as an unhandled exception occurs in **any node** (Producer, Blocking, or Non-Blocking):

* Capture exception and related `NodeData` payload.
* Send failed payload + exception details to a **Dead-Letter Queue (DLQ)** (mandatory). This is a mandatory terminal action for the failed payload to prevent data loss and allow for external investigation.
* The LoopManager must **immediately send control back to the Producer Node**. This terminates the failed iteration and restarts the loop process with the next unit of work.

### 8.3 Failure Isolation

* All node-level exceptions must be captured and reported by the LoopManager.
* Failure isolation is mandatory: The Orchestrator must support policies to prevent a single node or loop failure from crashing the entire system.
* Loops can continue or be paused based on policy, but the orchestrator may isolate failures to avoid system-wide crash.

### 8.4 Rationale

Fail-fast design to preserve throughput and isolate recurring bad payloads into the DLQ for offline inspection.

---

## 9. PoolExecutor

The `PoolExecutor` class handles the actual execution of nodes in different execution pools (ASYNC, THREAD, PROCESS).

### 9.1 Architecture

```python
class PoolExecutor:
    def __init__(self, max_workers_thread: int = 10, max_workers_process: int = 4):
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        self._process_pool: Optional[ProcessPoolExecutor] = None
```

The pools are lazily initialized on first use to conserve resources.

### 9.2 Execution Methods

| Pool Type | Method | Mechanism |
|-----------|--------|-----------|
| `ASYNC` | Direct await | `await node.run(node_output)` |
| `THREAD` | ThreadPoolExecutor | Runs in thread with new event loop |
| `PROCESS` | ProcessPoolExecutor | Serializes node/data via pickle |

#### Async Execution (Default)

```python
if pool == PoolType.ASYNC:
    return await node.run(node_output)
```

#### Thread Execution

For CPU-bound tasks that can't release the GIL:

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

#### Process Execution

For true parallelism with CPU-intensive tasks:

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

### 9.3 Pool Selection Guidelines

| Use Case | Recommended Pool | Reason |
|----------|------------------|--------|
| I/O-bound (HTTP, DB, file) | `ASYNC` | Best concurrency for I/O |
| CPU-bound with GIL release | `THREAD` | Parallel execution possible |
| CPU-bound Python code | `PROCESS` | True parallelism, bypasses GIL |
| External process calls | `PROCESS` | Isolation from main process |

### 9.4 Serialization Requirements

**Process Pool Constraints:**
* Node classes must be picklable (no lambdas, closures, or unpicklable attributes).
* `NodeOutput` and all nested data must be JSON-serializable or picklable.
* Resources (connections, file handles) cannot be serialized - use `setup()` to initialize in-process.

### 9.5 Cleanup

```python
def shutdown(self) -> None:
    if self._thread_pool:
        self._thread_pool.shutdown(wait=True)
    if self._process_pool:
        self._process_pool.shutdown(wait=True)
```

---

## 10. DataStore & Storage Architecture

The storage system follows the Single Responsibility Principle with specialized classes for different concerns.

### 10.1 Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    DataStore                        │
│                   (Facade)                          │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ QueueStore  │  │ CacheStore  │  │   Redis     │  │
│  │  (Lists)    │  │  (Strings)  │  │ Connection  │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
                   ┌───────────┐
                   │   Redis   │
                   └───────────┘
```

### 10.2 DataStore Facade

The `DataStore` provides a unified interface to storage services:

```python
class DataStore:
    def __init__(self, host="127.0.0.1", port=6379, db=0, password=None):
        self._redis_connection = RedisConnection(host, port, db, password)
        self._queue_store = QueueStore(self._redis_connection)
        self._cache_store = CacheStore(self._redis_connection)
    
    @property
    def queue(self) -> QueueStore:
        return self._queue_store
    
    @property
    def cache(self) -> CacheStore:
        return self._cache_store
```

**Usage:**
```python
data_store = DataStore()

# Queue operations
await data_store.queue.push("my_queue", {"key": "value"})
item = await data_store.queue.pop("my_queue", timeout=5)
length = await data_store.queue.length("my_queue")

# Cache operations
await data_store.cache.set("my_key", {"data": 123}, ttl=3600)
value = await data_store.cache.get("my_key")
await data_store.cache.delete("my_key")
exists = await data_store.cache.exists("my_key")
```

### 10.3 QueueStore

Handles queue operations using Redis Lists:

| Method | Redis Command | Purpose |
|--------|--------------|---------|
| `push(queue_name, data)` | `LPUSH` | Add item to queue (left push) |
| `pop(queue_name, timeout)` | `BRPOP` | Blocking right pop (FIFO order) |
| `length(queue_name)` | `LLEN` | Get queue length |

**Key Features:**
* **Multi-process safe:** Multiple processes can push/pop from the same queue.
* **Blocking pop:** `BRPOP` with configurable timeout for efficient waiting.
* **JSON serialization:** Data is JSON-serialized before storage.

```python
class QueueStore:
    async def push(self, queue_name: str, data: Dict):
        queue_key = f"{self._prefix}queue:{queue_name}"
        serialized_data = serialize(data)
        await conn.lpush(queue_key, [serialized_data])
    
    async def pop(self, queue_name: str, timeout: Optional[float] = None):
        result = await conn.brpop([queue_key], timeout=timeout)
        return deserialize(result.value) if result else None
```

### 10.4 CacheStore

Handles key-value cache operations using Redis Strings:

| Method | Redis Command | Purpose |
|--------|--------------|---------|
| `set(key, value, ttl)` | `SET` / `SETEX` | Store value with optional TTL |
| `get(key)` | `GET` | Retrieve value |
| `delete(key)` | `DEL` | Remove key |
| `exists(key)` | `EXISTS` | Check if key exists |

**Use Cases:**
* Development Mode: Cache node outputs for step-by-step execution.
* Session data: Store temporary workflow state.
* Configuration: Cache frequently accessed settings.

### 10.5 RedisConnection

Manages Redis connection lifecycle:

```python
class RedisConnection:
    async def ensure_connection(self):
        """Get or create async Redis connection."""
        if self._connection is None:
            self._connection = await coredis.Redis(
                host=self._host,
                port=self._port,
                db=self._db,
                password=self._password
            )
        return self._connection
    
    async def close(self):
        """Close the Redis connection."""
        if self._connection:
            await self._connection.close()
```

### 10.6 Serialization Utilities

```python
def serialize(data: Dict) -> str:
    """Convert dict to JSON string for Redis storage."""
    return json.dumps(data)

def deserialize(data: str) -> Dict:
    """Convert JSON string back to dict."""
    return json.loads(data)
```

---

## 11. Logging & Observability

The system uses **structlog** for structured logging with both human-readable console output and machine-readable JSON file output.

### 11.1 Logging Configuration

```python
from config.logging_config import setup_logging
setup_logging()  # Call once at application startup
```

**Features:**
* **Console Output:** Pretty-printed, colored logs for development
* **File Output:** JSON Lines format (`.jsonl`) for machine processing
* **Daily Rotation:** Log files rotate daily (UTC) with 30-day retention
* **Structured Context:** Includes timestamp, log level, filename, line number

**Log File Location:** `logs/workflow.jsonl` (rotates to `workflow_YYYY-MM-DD.jsonl`)

### 11.2 Using Logging in Nodes

```python
import structlog

logger = structlog.get_logger(__name__)

class MyNode(BlockingNode):
    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        logger.info("Processing data", node_id=self.node_config.id, data_size=len(node_data.data))
        # ... node logic ...
        logger.debug("Completed processing", result_count=10)
```

---

## 12. Developer Guidance & Expectations

### 12.1 Node Authors

Developers implementing nodes should:

* Implement `async def execute(node_data: NodeData) -> NodeData` for all nodes.
* Use `async/await` throughout for all I/O operations, queue access, and asynchronous work.
* Ensure `execute()` completes (via await) only when the node's obligations are met.
* When implementing QueueReader as a Producer, handle async pop semantics via `await QueueManager.pop(...)` inside their node code.
* Understand that nodes follow strict async timing semantics.
* Never manage their own concurrency; nodes simply "run" when invoked via async execution.
* Implement `get_form()` to return a `BaseForm` subclass if the node requires configuration.
* Use `setup()` for resource initialization (connections, clients) instead of `__init__()`.

### 12.2 System Implementers

Developers implementing the orchestrator should:

* Provide clear data contracts (schemas) for NodeData passed between nodes.
* Ensure Redis QueueManager is fault tolerant and monitored (connection health, queue lengths, DLQ).
* Provide observability (logs, metrics, health endpoints) per loop and node.
* Understand that loops are fully isolated execution tracks.
* Understand that queue nodes enable multi-loop coordination.
* Understand that the orchestrator controls lifecycle, messaging, and concurrency.

### 12.3 Key Developer Expectations

Developers should understand:

* Nodes follow strict timing semantics.
* Loops are fully isolated execution tracks.
* Queue nodes enable multi-loop coordination.
* Orchestrator controls lifecycle, messaging, and concurrency.
* Loops run using Asyncio Event Loop (primary), ThreadPool, or ProcessPool.
* All nodes use async/await throughout; LoopManager awaits all node executions.

---

## 13. Open Implementation Decisions

The following items are left to implementation and are not required to block the specification:

* Exact serialization format for NodeData over Redis (e.g., JSON, CBOR, protobuf).
* DLQ retention/eviction policy and tooling for reprocessing DLQ items.
* Concrete retry or backoff strategies for external repair tools (kept out of orchestrator; DLQ is used instead).
* Specific health endpoint formats and metric collection mechanisms.
* LogicalNode branch selection integration in FlowRunner (using `output` property for conditional routing).

---

## 14. Glossary

* **BaseForm:** Django-based form class with cascading field dependencies and Jinja template support. Used for node configuration.
* **BaseNode:** The base class from which all nodes inherit.
* **BlockingNode:** Must finish (and downstream blocking chain must finish) before continuing.
* **BranchKeyNormalizer:** Utility class for converting between workflow JSON source handles and internal branch keys.
* **CacheStore:** Redis String-based key-value cache for storing node outputs and temporary data.
* **DataStore:** Facade class providing unified access to QueueStore, CacheStore, and RedisConnection.
* **DependencyHandler:** Manages cascading field dependencies in forms, handling initialization, updates, and clearing.
* **DependencyInjector:** Abstract interface that forms implement to define field dependency relationships.
* **Development Mode:** An operating mode for the Orchestrator focused on iterative, single-node execution for testing and debugging. It does not use a `LoopManager`.
* **DLQ:** Dead-Letter Queue storing failed NodeData + error context.
* **ExecutionPool:** An enum (`ASYNC`, `THREAD`, `PROCESS`) on a node declaring its ideal execution environment. Used by the `LoopManager` in Production Mode to select a pool for the whole loop, and by the `Orchestrator` in Development Mode to run a single node.
* **FlowAnalyzer:** Component responsible for graph traversal and analysis operations (finding producers, loops, chains).
* **FlowBuilder:** Component that constructs the FlowGraph from workflow JSON definitions.
* **FlowEngine:** The concrete implementation of the Workflow Orchestrator. Manages workflow loading, post-processing, and execution.
* **FlowGraph:** Data structure holding all FlowNode instances and their connections.
* **FlowNode:** Data structure representing a node in the flow graph, containing the node instance and connections to next nodes.
* **FlowRunner:** The concrete implementation of LoopManager. Manages a single loop's execution in Production Mode.
* **FormSerializer:** Utility class that converts Django forms to JSON for API/UI consumption.
* **LogicalNode:** A BlockingNode subclass for conditional branching with yes/no output routing.
* **Loop:** A continuous execution track controlled by a single ProducerNode, running in an isolated pool. This concept primarily applies to **Production Mode**.
* **LoopManager:** The per-loop executor for **Production Mode**. It runs nodes in sequence and dynamically determines the execution pool for each loop cycle. Implemented as `FlowRunner`.
* **NodeConfig:** Static initialization/config data passed to nodes during initialization. Contains `id`, `type`, and `data` (with `form` and `config` sections).
* **NodeConfigData:** Pydantic model containing form data and config data for a node.
* **NodeOutput:** Runtime payload passed between nodes during execution. Contains `id`, `data`, and `metadata`.
* **NodeOutputMetaData:** Metadata about node output including source and destination node IDs.
* **NodeRegistry:** Auto-discovery system that finds and registers node classes based on their `identifier()` method.
* **Non-Blocking Node:** Marks iteration end in the execution model; executed asynchronously using await.
* **PoolExecutor:** Component that executes nodes in ASYNC, THREAD, or PROCESS pools based on their `execution_pool` property.
* **PoolType:** Enum with values `ASYNC`, `THREAD`, `PROCESS` indicating execution environment preference.
* **PostProcessor:** Abstract base class for workflow post-processing operations (validation, queue mapping).
* **ProducerNode:** Starts an iteration (QueueReader is treated as a Producer).
* **Production Mode:** The main operating mode for the Orchestrator, focused on autonomous, high-performance execution of entire workflows via `LoopManagers`.
* **QueueMapper:** Post-processor that automatically assigns unique queue names to connected QueueNode-QueueReader pairs.
* **QueueManager:** Redis-backed queue abstraction for cross-loop communication.
* **QueueNode:** A NonBlockingNode that writes data to a Redis queue.
* **QueueReader:** A ProducerNode that reads data from a Redis queue to start a loop iteration.
* **QueueStore:** Redis List-based queue implementation for cross-loop communication.
* **RedisConnection:** Connection lifecycle manager for async Redis operations.
* **NodeValidator:** Post-processor that validates all nodes are ready before workflow execution.
* **Workflow Orchestrator:** The central coordination system that can operate in either **Production Mode** or **Development Mode** to manage and execute workflows. Implemented as `FlowEngine`.

---

