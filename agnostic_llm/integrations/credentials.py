"""Credential lookup without putting secret values in configuration files."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod


class CredentialStore(ABC):
    """Small interface used by integrations to obtain credentials."""

    @abstractmethod
    def get(self, name: str, *, env_var: str | None = None) -> str | None:
        raise NotImplementedError

    def require(self, name: str, *, env_var: str | None = None) -> str:
        value = self.get(name, env_var=env_var)
        if not value:
            raise RuntimeError(f"credential not configured: {name}")
        return value


class KeychainCredentialStore(CredentialStore):
    """macOS Keychain adapter using the system ``security`` executable."""

    def __init__(self, service: str = "agnostic-llm"):
        self.service = service

    @property
    def available(self) -> bool:
        return sys.platform == "darwin" and shutil.which("security") is not None

    def get(self, name: str, *, env_var: str | None = None) -> str | None:
        del env_var
        if not self.available:
            return None
        result = subprocess.run(
            ["security", "find-generic-password", "-s", self.service, "-a", name, "-w"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    def set(self, name: str, value: str) -> None:
        if not self.available:
            raise RuntimeError("macOS Keychain is unavailable")
        subprocess.run(
            ["security", "add-generic-password", "-U", "-s", self.service, "-a", name, "-w", value],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )

    def delete(self, name: str) -> None:
        if not self.available:
            return
        subprocess.run(
            ["security", "delete-generic-password", "-s", self.service, "-a", name],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )


class EnvironmentCredentialStore(CredentialStore):
    """Environment-first lookup with optional Keychain fallback."""

    def __init__(self, fallback: CredentialStore | None = None):
        self.fallback = fallback if fallback is not None else KeychainCredentialStore()

    def get(self, name: str, *, env_var: str | None = None) -> str | None:
        value = os.getenv(env_var or name)
        if value:
            return value
        return self.fallback.get(name, env_var=env_var)
