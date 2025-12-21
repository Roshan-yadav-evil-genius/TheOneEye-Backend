# 1. Use Dual Operating Modes (Production and Development)

*   **Status:** Proposed
*   **Date:** 2025-12-01
*   **Deciders:** Annie

## Context and Problem Statement

The workflow execution system needs to serve two distinct use cases:
1.  High-performance, autonomous execution of complete, validated workflows.
2.  Flexible, iterative development and debugging of individual nodes by a developer.

A single execution model struggles to serve both needs efficiently. A full loop-based engine is too cumbersome for testing a single node, while a purely manual execution model lacks the performance and autonomy needed for production.

## Decision Drivers

*   **Developer Experience:** Developers need a fast way to test their node logic without running an entire workflow.
*   **Production Stability:** The production environment needs a robust, high-throughput engine that runs autonomously.
*   **Separation of Concerns:** The logic for development-time execution (e.g., checking a cache) is different from production execution (continuous loops).

## Considered Options

1.  **A Single, Unified Execution Mode:** A single mode that tries to handle both cases with feature flags. This was rejected due to high complexity and the risk of development-specific logic affecting production performance.
2.  **Separate Tools:** Building a separate CLI tool for testing nodes. This was rejected as it would not be able to reuse the orchestrator's core logic for node loading, configuration, and execution.
3.  **Two First-Class Operating Modes:** Building the `Orchestrator` to explicitly support a `Production Mode` and a `Development Mode`.

## Decision Outcome

Chosen option: **"Two First-Class Operating Modes"**.

The `Orchestrator` will be designed with two modes:
*   **Production Mode:** Uses `LoopManagers` to run entire workflows for high performance.
*   **Development Mode:** The `Orchestrator` directly executes single nodes, bypassing the `LoopManager` and using Redis for state caching between steps. This provides an interactive, step-through debugging experience.

### Consequences

*   The `Orchestrator`'s internal logic will be slightly more complex as it needs to switch behavior based on its mode.
*   The system as a whole becomes much more flexible and powerful for both operators and developers.
*   The responsibilities of the `Orchestrator` vs. the `LoopManager` are now extremely clear.
