"""
Delay config and jitter for browser automation.
Reusable across any site. Use with human_behavior (human_wait, human_typing) or custom flows.
"""
import random

from pydantic import BaseModel, Field, model_validator


class DelayConfig(BaseModel):
    """Config for delay bounds (min/max milliseconds)."""

    min_ms: int = Field(50, ge=0, le=2000, description="Minimum delay in ms")
    max_ms: int = Field(500, ge=0, le=5000, description="Maximum delay in ms")

    @model_validator(mode="after")
    def min_le_max(self) -> "DelayConfig":
        if self.min_ms > self.max_ms:
            raise ValueError("min_ms must be <= max_ms")
        return self

    model_config = {"frozen": True}


def jitter_ms(config: DelayConfig) -> int:
    """Return a random delay in milliseconds within config bounds."""
    return random.randint(config.min_ms, config.max_ms)
