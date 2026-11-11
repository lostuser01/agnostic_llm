"""AI Employee Array Module: Multi-agent executive personas, tools, and orchestration."""
from .base import Employee, EmployeeExecutionResult
from .roster import EmployeeRoster
from .alex import create_alex
from .morgan import create_morgan
from .taylor import create_taylor
from .elena import create_elena
from .supervisor import create_supervisor
from .jack import create_jack

__all__ = [
    "Employee",
    "EmployeeExecutionResult",
    "EmployeeRoster",
    "create_alex",
    "create_morgan",
    "create_taylor",
    "create_elena",
    "create_supervisor",
    "create_jack",
]

