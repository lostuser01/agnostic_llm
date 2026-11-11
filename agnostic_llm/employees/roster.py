"""Employee Roster: Manages the roster of AI employees, attaches models, and cross-links delegation.
"""
from __future__ import annotations
import logging
from typing import Optional, Iterator
from .base import Employee
from .alex import create_alex
from .morgan import create_morgan
from .taylor import create_taylor
from .elena import create_elena
from .supervisor import create_supervisor
from ..registry import Models
from ..macos import MacOSStore

log = logging.getLogger("agnostic_llm.roster")


class EmployeeRoster:
    """Manages the full array of AI employees."""

    def __init__(self, models: Optional[Models] = None, store: Optional[MacOSStore] = None):
        self.models = models
        self.store = store or MacOSStore()
        self._employees: dict[str, Employee] = {}
        self._init_default_team()

    def _init_default_team(self):
        # Register core employees
        core = [
            create_alex(self.store),
            create_morgan(self.store),
            create_taylor(self.store),
            create_elena(self.store),
            create_supervisor(self.store),
        ]
        for emp in core:
            self.add(emp)

    def add(self, employee: Employee):
        """Add an employee to the roster and wire cross-references."""
        employee.set_roster(self)
        if self.models:
            # Wire assigned model route
            try:
                llm = self.models.get(employee.route)
                employee.set_llm(llm)
            except Exception as e:
                log.warning("Could not assign model route '%s' to '%s': %s", employee.route, employee.name, e)
                # Fallback to default route or first available
                try:
                    employee.set_llm(self.models.get("default"))
                except Exception:
                    pass

        self._employees[employee.name.lower()] = employee

    def get(self, name: str) -> Optional[Employee]:
        """Look up employee by name (case-insensitive)."""
        return self._employees.get(name.lower().strip())

    def list_all(self) -> list[Employee]:
        """Return list of all registered employees."""
        return list(self._employees.values())

    def __iter__(self) -> Iterator[Employee]:
        return iter(self._employees.values())

    def bind_models(self, models: Models):
        """Bind LLM instances from Models registry to all employees based on their routes."""
        self.models = models
        for emp in self._employees.values():
            try:
                emp.set_llm(models.get(emp.route))
            except Exception:
                try:
                    emp.set_llm(models.get("default"))
                except Exception as e:
                    log.warning("Failed to bind model to %s: %s", emp.name, e)

    @classmethod
    def from_config(cls, config_path: str = "config.yaml", store: Optional[MacOSStore] = None) -> EmployeeRoster:
        """Create a roster configured with models and custom employees from a config file."""
        models = Models.from_file(config_path)
        roster = cls(models=models, store=store)

        # Check for custom employees in config
        custom_emps = models.cfg.get("employees", {})
        for name, spec in custom_emps.items():
            emp = Employee(
                name=spec.get("name", name.capitalize()),
                title=spec.get("title", f"{name.capitalize()} Specialist"),
                role=spec.get("role", "Specialist Assistant"),
                route=spec.get("route", "default"),
                voice=spec.get("voice", "Samantha"),
                avatar=spec.get("avatar", "🤖"),
                system_prompt=spec.get("system_prompt", ""),
                store=roster.store,
            )
            roster.add(emp)

        return roster

