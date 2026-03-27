"""
logging.py
----------
Utility functions for logging Jules activities.
"""

from typing import Callable

from ..data_classes.models.activity import Activity
from ..data_classes.models.plan import Plan


"""
log_activity — TODO: describe purpose.

Args:
    activity: TODO: describe activity
    log: TODO: describe log
    None]: TODO: describe None]

Returns:
    TODO: describe return value
"""
def log_activity(activity: Activity, log: Callable[[str], None]) -> None:
    """
    Log a Jules activity in a human-readable format.

    Args:
        activity: The Activity to log
        log: Logging function (e.g., print, logger.info)

    Raises:
        RuntimeError: If the activity indicates session failure
    """
    atype = activity.activity_type

    if atype == "planGenerated":
        plan = Plan.from_dict(activity.payload.get("plan", {}))
        log(f"[Jules] Plan generated — {len(plan.steps)} step(s):")
        for step in plan.steps:
            log(f"         [{step.index + 1}] {step.title}")
    elif atype == "planApproved":
        log(f"[Jules] Plan approved (id={activity.payload.get('planId', '?')})")
    elif atype == "progressUpdated":
        title = activity.payload.get("title", "")
        desc = activity.payload.get("description", "")
        log(f"[Jules] Progress: {title}" + (f" — {desc}" if desc else ""))
    elif atype == "agentMessaged":
        log(f"[Jules] Agent: {activity.payload.get('agentMessage', '')}")
    elif atype == "sessionCompleted":
        log("[Jules] Session completed.")
    elif atype == "sessionFailed":
        raise RuntimeError(
            f"Jules session failed: {activity.payload.get('reason', 'unknown')}"
        )
