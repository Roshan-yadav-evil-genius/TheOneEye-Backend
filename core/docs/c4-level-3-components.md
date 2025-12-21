# C4 Model: Level 3 - Component Diagrams

This view zooms into the **API Service** container to show its internal components and how they interact in the two different operating modes.

## Production Mode

In Production Mode, the `Orchestrator` delegates loop execution to `LoopManagers`.

```mermaid
C4Component
  title Component diagram (Production Mode)

  Person(developer, "Developer")

  Container_Boundary(api_service, "API Service") {
    Component(api, "API Endpoint", "/prod/start", "Accepts requests to start/stop workflow loops.")
    Component(orchestrator, "Orchestrator", "Manages LoopManagers and high-level state.")
    Component(loop_manager, "Loop Manager", "Manages the execution cycle of a single workflow loop.")
    Component(node, "Node", "A single unit of work (e.g., Producer, Blocking).")
    Component(queue_manager, "Queue Manager", "Handles cross-loop communication via Redis queues.")

    Rel(developer, api, "Starts a workflow loop")
    Rel(api, orchestrator, "Forwards request")
    Rel(orchestrator, loop_manager, "Instantiates and manages")
    Rel(loop_manager, node, "Executes nodes in sequence")
    Rel(node, queue_manager, "Uses for cross-loop data transfer")
  }

  System_Ext(redis, "Redis")
  Rel(queue_manager, redis, "Pushes to / Pops from job queues")

```

## Development Mode

In Development Mode, the `Orchestrator` directly executes single nodes, using Redis as a state cache. The `LoopManager` is not used.

```mermaid
C4Component
  title Component diagram (Development Mode)

  Person(developer, "Developer")

  Container_Boundary(api_service, "API Service") {
    Component(api, "API Endpoint", "/dev/execute", "Accepts requests to execute a single node.")
    Component(orchestrator, "Orchestrator", "Handles single-node execution requests.")
    Component(graph_reader, "Workflow Graph Reader", "Provides node dependency information.")
    Component(state_cache, "State Cache", "Reads/writes node outputs to Redis.")
    Component(node, "Node", "A single unit of work.")

    Rel(developer, api, "Requests execution of a node")
    Rel(api, orchestrator, "Forwards request")
    Rel(orchestrator, graph_reader, "Gets upstream dependencies")
    Rel(orchestrator, state_cache, "Checks for/gets input from Redis")
    Rel(orchestrator, node, "Executes the single node in its specific pool")
    Rel(orchestrator, state_cache, "Saves node output to Redis")
  }

  System_Ext(redis, "Redis")
  Rel(state_cache, redis, "Reads/writes node outputs")

```