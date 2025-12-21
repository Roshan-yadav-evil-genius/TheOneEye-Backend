"""
Workflow Events Module

Provides an event emitter system for workflow execution events.
This module is framework-agnostic and can be used with any backend.
"""

from .event_emitter import WorkflowEventEmitter
from .state_tracker import ExecutionStateTracker

__all__ = ["WorkflowEventEmitter", "ExecutionStateTracker"]

