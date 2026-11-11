"""Tiny eval harness: same cases, every model, one table. Run it before you swap models."""
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Callable
from .base import LLM


@dataclass
class Case:
    prompt: str
    check: Callable[[str], bool]  # e.g. lambda out: "42" in out
    system: str | None = None


def run_evals(models: dict[str, LLM], cases: list[Case]) -> dict[str, dict]:
    results = {}
    for name, llm in models.items():
        passed, errors, t0 = 0, 0, time.time()
        for c in cases:
            try:
                passed += bool(c.check(llm.ask(c.prompt, system=c.system)))
            except Exception:
                errors += 1
        results[name] = {"passed": passed, "total": len(cases), "errors": errors,
                         "seconds": round(time.time() - t0, 2)}
    print(f"{'model':28} {'pass':>8} {'errors':>7} {'sec':>7}")
    for n, r in results.items():
        print(f"{n:28} {r['passed']:>3}/{r['total']:<4} {r['errors']:>7} {r['seconds']:>7}")
    return results
