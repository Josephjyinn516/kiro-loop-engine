"""Base handler abstract class for the Kiro Loop Engine."""

from __future__ import annotations

from abc import ABC, abstractmethod

from kiro_loop_engine.models import InstructionBlock, ResultBlock


class BaseHandler(ABC):
    """Abstract base class for instruction type handlers.

    Subclass this to create custom handlers for new block types.

    Example:
        class MyCustomHandler(BaseHandler):
            def execute(self, block: InstructionBlock) -> ResultBlock:
                # Your custom logic here
                ...
    """

    @abstractmethod
    def execute(self, block: InstructionBlock) -> ResultBlock:
        """Execute the instruction block and return results.

        Args:
            block: The instruction block to execute.

        Returns:
            A ResultBlock containing execution outcome.
        """
        ...
