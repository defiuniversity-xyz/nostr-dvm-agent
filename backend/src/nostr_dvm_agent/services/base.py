from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseDVMService(ABC):
    """Abstract base class for NIP-90 DVM service implementations."""

    kind: int
    name: str
    description: str
    default_cost_msats: int

    @abstractmethod
    async def validate_input(self, job_data: dict[str, Any]) -> bool:
        """Check that the job request has valid inputs for this service."""
        ...

    @abstractmethod
    async def estimate_cost(self, job_data: dict[str, Any]) -> int:
        """Return cost in millisatoshis based on input complexity."""
        ...

    @abstractmethod
    async def execute(self, job_data: dict[str, Any]) -> str:
        """Process the job and return the result content."""
        ...
