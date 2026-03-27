"""
plan.py
-------
Defines the Plan and PlanStep data classes for Jules session plans.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
"""
PlanStep — TODO: describe purpose.
"""
class PlanStep:
    """
    Represents a single step in a Jules execution plan.

    Attributes:
        id: Unique identifier for the step
        title: Title/summary of the step
        description: Detailed description of what the step does
        index: Zero-based position of the step in the plan
    """

    id: str
    title: str
    description: str
    index: int

    @classmethod
    """
    from_dict — TODO: describe purpose.
    
    Args:
        cls: TODO: describe cls
        d: TODO: describe d
    
    Returns:
        TODO: describe return value
    """
    def from_dict(cls, d: Dict) -> "PlanStep":
        """
        Create a PlanStep instance from a dictionary.

        Args:
            d: Dictionary containing plan step data from Jules API

        Returns:
            PlanStep instance
        """
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
            index=d.get("index", 0),
        )


@dataclass
"""
Plan — TODO: describe purpose.
"""
class Plan:
    """
    Represents a complete execution plan for a Jules session.

    Attributes:
        id: Unique identifier for the plan
        steps: List of PlanStep instances in execution order
        create_time: ISO 8601 timestamp when the plan was created
    """

    id: str
    steps: List[PlanStep] = field(default_factory=list)
    create_time: str = ""

    @classmethod
    """
    from_dict — TODO: describe purpose.
    
    Args:
        cls: TODO: describe cls
        d: TODO: describe d
    
    Returns:
        TODO: describe return value
    """
    def from_dict(cls, d: Dict) -> "Plan":
        """
        Create a Plan instance from a dictionary.

        Args:
            d: Dictionary containing plan data from Jules API

        Returns:
            Plan instance
        """
        return cls(
            id=d.get("id", ""),
            steps=[PlanStep.from_dict(s) for s in d.get("steps", [])],
            create_time=d.get("createTime", ""),
        )
