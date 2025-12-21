# Sequence Diagrams

These diagrams illustrate the sequence of events during the execution of each operating mode.

## Production Mode

This shows a typical loop execution managed by a `LoopManager`.

```mermaid
sequenceDiagram
  participant LM as LoopManager
  participant PN as ProducerNode
  participant BN as BlockingNode
  participant NBN as NonBlockingNode

  loop Workflow Execution
    LM->>PN: await execute()
    PN-->>LM: Return NodeData
    LM->>BN: await execute(NodeData)
    BN-->>LM: Return new NodeData
    LM->>NBN: await execute(new NodeData)
    NBN-->>LM: Return final NodeData
  end
```

## Development Mode

This shows a developer executing a single node (`NodeB`) that depends on the output of a previous node (`NodeA`).

```mermaid
sequenceDiagram
  participant Dev as Developer
  participant API as API Endpoint
  participant Orch as Orchestrator
  participant Redis as Redis Cache
  participant NodeB as NodeB

  Dev->>API: POST /dev/execute (NodeB)
  API->>Orch: execute_node("NodeB")
  Orch->>Redis: get_state("NodeA_output")
  Redis-->>Orch: Return cached NodeA data
  Orch->>NodeB: await execute(cached_data)
  NodeB-->>Orch: Return new_data
  Orch->>Redis: set_state("NodeB_output", new_data)
  Redis-->>Orch: OK
  Orch-->>API: Execution successful
  API-->>Dev: 200 OK
```