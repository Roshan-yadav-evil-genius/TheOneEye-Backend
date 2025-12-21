# 2. Use Redis for Caching and Queues

*   **Status:** Proposed
*   **Date:** 2025-12-01
*   **Deciders:** Annie

## Context and Problem Statement

The architecture requires two distinct but related persistence/messaging mechanisms:
1.  A multi-process safe queue for passing jobs between different loops (`Production Mode`).
2.  A fast, shared cache for storing the state of individual node executions (`Development Mode`).

We need a technology that can satisfy both requirements effectively without introducing unnecessary complexity.

## Decision Drivers

*   **Performance:** The system needs low-latency reads and writes for both queuing and caching.
*   **Process Safety:** The mechanism must work reliably when accessed from different processes, as nodes may run in a `ProcessPool`.
*   **Simplicity:** Using a single technology for both use cases reduces operational overhead and the number of system dependencies.
*   **Feature Set:** The technology should have robust support for both queue-like operations (lists with blocking pops) and key-value caching (with optional TTLs).

## Considered Options

1.  **RabbitMQ for Queues + Memcached for Cache:** A classic combination. RabbitMQ is a very robust message broker. This was rejected because it requires maintaining two separate services.
2.  **PostgreSQL for Queues and Cache:** Using a relational database. This was rejected as it's overkill for this use case and would likely have higher latency than in-memory solutions.
3.  **Redis:** An in-memory data store that natively supports both rich list operations (LPUSH, BRPOP) for queuing and first-class key-value caching.

## Decision Outcome

Chosen option: **"Redis"**.

Redis will be the single, unified data store for two purposes:
1.  **Queuing:** The `QueueManager` will use Redis Lists to implement robust, multi-process safe job queues for cross-loop communication in `Production Mode`.
2.  **Caching:** The `Orchestrator` will use Redis Hashes or simple Keys to store the outputs of node executions in `Development Mode`, providing a shared cache for the step-through execution feature.

### Consequences

*   The entire system has only one external data-store dependency, simplifying deployment and maintenance.
*   The system benefits from the high performance of an in-memory database.
*   We must ensure the Redis instance is provisioned with enough memory and appropriate eviction policies to handle both workloads.
