# Workflow Orchestrator Requirements

[![Node Types Diagram](./NewDesign/docs/Node%20Architecture.png)](https://embed.figma.com/board/ipiIPvsqG17Is2kzJJkv08/Node-Architecture?node-id=0-1&embed-host=share)

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

### 2.3 Exampel of Producer and NonBlockingNode 

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

## 9. Developer Guidance & Expectations

### 9.1 Node Authors

Developers implementing nodes should:

* Implement `async def execute(node_data: NodeData) -> NodeData` for all nodes.
* Use `async/await` throughout for all I/O operations, queue access, and asynchronous work.
* Ensure `execute()` completes (via await) only when the node's obligations are met.
* When implementing QueueReader as a Producer, handle async pop semantics via `await QueueManager.pop(...)` inside their node code.
* Understand that nodes follow strict async timing semantics.
* Never manage their own concurrency; nodes simply "run" when invoked via async execution.

### 9.2 System Implementers

Developers implementing the orchestrator should:

* Provide clear data contracts (schemas) for NodeData passed between nodes.
* Ensure Redis QueueManager is fault tolerant and monitored (connection health, queue lengths, DLQ).
* Provide observability (logs, metrics, health endpoints) per loop and node.
* Understand that loops are fully isolated execution tracks.
* Understand that queue nodes enable multi-loop coordination.
* Understand that the orchestrator controls lifecycle, messaging, and concurrency.

### 9.3 Key Developer Expectations

Developers should understand:

* Nodes follow strict timing semantics.
* Loops are fully isolated execution tracks.
* Queue nodes enable multi-loop coordination.
* Orchestrator controls lifecycle, messaging, and concurrency.
* Loops run using Asyncio Event Loop (primary), ThreadPool, or ProcessPool.
* All nodes use async/await throughout; LoopManager awaits all node executions.

---

## 10. Open Implementation Decisions

The following items are left to implementation and are not required to block the specification:

* Exact serialization format for NodeData over Redis (e.g., JSON, CBOR, protobuf).
* DLQ retention/eviction policy and tooling for reprocessing DLQ items.
* Concrete retry or backoff strategies for external repair tools (kept out of orchestrator; DLQ is used instead).
* Specific health endpoint formats and metric collection mechanisms.

---

## 11. Glossary

* **BaseNode:** The base class from which all nodes inherit.
* **BlockingNode:** Must finish (and downstream blocking chain must finish) before continuing.
* **Development Mode:** An operating mode for the Orchestrator focused on iterative, single-node execution for testing and debugging. It does not use a `LoopManager`.
* **DLQ:** Dead-Letter Queue storing failed NodeData + error context.
* **ExecutionPool:** An enum (`ASYNC`, `THREAD`, `PROCESS`) on a node declaring its ideal execution environment. Used by the `LoopManager` in Production Mode to select a pool for the whole loop, and by the `Orchestrator` in Development Mode to run a single node.
* **Loop:** A continuous execution track controlled by a single ProducerNode, running in an isolated pool. This concept primarily applies to **Production Mode**.
* **LoopManager:** The per-loop executor for **Production Mode**. It runs nodes in sequence and dynamically determines the execution pool for each loop cycle.
* **NodeConfig:** Static initialization/config data passed to nodes during initialization.
* **NodeData:** Runtime payload passed to nodes during execution.
* **Non-Blocking Node:** Marks iteration end in the execution model; executed asynchronously using await.
* **ProducerNode:** Starts an iteration (QueueReader is treated as a Producer).
* **Production Mode:** The main operating mode for the Orchestrator, focused on autonomous, high-performance execution of entire workflows via `LoopManagers`.
* **QueueManager:** Redis-backed queue abstraction for cross-loop communication.
* **QueueNode:** A NonBlockingNode that writes data to a Redis queue.
* **QueueReader:** A ProducerNode that reads data from a Redis queue to start a loop iteration.
* **Workflow Orchestrator:** The central coordination system that can operate in either **Production Mode** or **Development Mode** to manage and execute workflows.

---

