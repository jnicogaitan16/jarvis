"""Benchmarks — framework de evaluación de calidad para agentes y herramientas."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class BenchmarkCase:
    """Un caso de evaluación individual."""
    id: str
    name: str
    category: str  # "intent_detection", "security_detection", "memory_retrieval", etc.
    input_data: dict
    expected: dict  # Valores esperados para comparar
    evaluator: str = "exact"  # "exact", "contains", "gte", "callable"


@dataclass
class BenchmarkResult:
    case_id: str
    passed: bool
    expected: str = ""
    actual: str = ""
    duration_ms: int = 0
    error: str = ""


@dataclass
class BenchmarkSuiteResult:
    name: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    duration_ms: int = 0
    results: list[BenchmarkResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total else 0.0


class BenchmarkRunner:
    """Ejecuta suites de benchmarks."""

    def __init__(self):
        self._evaluators: dict[str, Callable] = {
            "exact": self._eval_exact,
            "contains": self._eval_contains,
            "gte": self._eval_gte,
        }

    def run_suite(self, name: str, cases: list[BenchmarkCase], run_fn: Callable) -> BenchmarkSuiteResult:
        """Ejecutar una suite de benchmarks.

        run_fn: función que recibe input_data y retorna un dict con resultados.
        """
        suite = BenchmarkSuiteResult(name=name, total=len(cases))
        suite_start = time.monotonic()

        for case in cases:
            start = time.monotonic()
            try:
                actual = run_fn(case.input_data)
                elapsed = int((time.monotonic() - start) * 1000)

                passed = self._evaluate(case, actual)
                result = BenchmarkResult(
                    case_id=case.id,
                    passed=passed,
                    expected=str(case.expected),
                    actual=str(actual)[:200],
                    duration_ms=elapsed,
                )

                if passed:
                    suite.passed += 1
                else:
                    suite.failed += 1

            except Exception as e:
                elapsed = int((time.monotonic() - start) * 1000)
                result = BenchmarkResult(
                    case_id=case.id,
                    passed=False,
                    error=str(e),
                    duration_ms=elapsed,
                )
                suite.errors += 1

            suite.results.append(result)

        suite.duration_ms = int((time.monotonic() - suite_start) * 1000)
        return suite

    def _evaluate(self, case: BenchmarkCase, actual: dict) -> bool:
        evaluator = self._evaluators.get(case.evaluator, self._eval_exact)
        return evaluator(case.expected, actual)

    def _eval_exact(self, expected: dict, actual: dict) -> bool:
        for key, val in expected.items():
            if actual.get(key) != val:
                return False
        return True

    def _eval_contains(self, expected: dict, actual: dict) -> bool:
        for key, val in expected.items():
            actual_val = str(actual.get(key, ""))
            if str(val) not in actual_val:
                return False
        return True

    def _eval_gte(self, expected: dict, actual: dict) -> bool:
        for key, val in expected.items():
            if actual.get(key, 0) < val:
                return False
        return True


# ---------------------------------------------------------------------------
# Built-in benchmark suites
# ---------------------------------------------------------------------------

INTENT_DETECTION_CASES = [
    BenchmarkCase("INT-001", "Detect PR analysis", "intent_detection",
                  {"text": "analiza el PR 1234"}, {"intent": "analyze_pr"}),
    BenchmarkCase("INT-002", "Detect QA request", "intent_detection",
                  {"text": "genera casos de prueba"}, {"intent": "qa"}),
    BenchmarkCase("INT-003", "Detect code request", "intent_detection",
                  {"text": "hay un bug en la función"}, {"intent": "code"}),
    BenchmarkCase("INT-004", "Detect memory query", "intent_detection",
                  {"text": "qué sabes de IntegratePIE"}, {"intent": "memory"}),
    BenchmarkCase("INT-005", "Detect help request", "intent_detection",
                  {"text": "qué puedes hacer"}, {"intent": "help"}),
    BenchmarkCase("INT-006", "General fallback", "intent_detection",
                  {"text": "buen día"}, {"intent": "general"}),
    BenchmarkCase("INT-007", "Detect review", "intent_detection",
                  {"text": "revisa el merge request"}, {"intent": "analyze_pr"}),
    BenchmarkCase("INT-008", "Detect gherkin", "intent_detection",
                  {"text": "escenarios gherkin para login"}, {"intent": "qa"}),
    BenchmarkCase("INT-009", "Detect status", "intent_detection",
                  {"text": "cómo va el sistema"}, {"intent": "status"}),
    BenchmarkCase("INT-010", "Detect refactor", "intent_detection",
                  {"text": "refactoriza la class UserService"}, {"intent": "code"}),
]

SECURITY_DETECTION_CASES = [
    BenchmarkCase("SEC-001", "Detect hardcoded password", "security",
                  {"diff": '+password = "secret123"'}, {"has_findings": True}),
    BenchmarkCase("SEC-002", "Detect API key", "security",
                  {"diff": '+API_KEY = "sk_live_abc123456789012345678"'}, {"has_findings": True}),
    BenchmarkCase("SEC-003", "Clean code no findings", "security",
                  {"diff": "+def hello(): return 'world'"}, {"has_findings": False}),
    BenchmarkCase("SEC-004", "Detect JWT token", "security",
                  {"diff": '+token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"'},
                  {"has_findings": True}),
    BenchmarkCase("SEC-005", "Detect private key", "security",
                  {"diff": "+-----BEGIN RSA PRIVATE KEY-----"}, {"has_findings": True}),
]

MEMORY_ISOLATION_CASES = [
    BenchmarkCase("MEM-001", "PIE data isolated from KameCol", "memory",
                  {"query": "FUR rollout", "search_project": "kamecol", "data_project": "integratepie"},
                  {"results_count": 0}),
    BenchmarkCase("MEM-002", "PIE data found in PIE", "memory",
                  {"query": "FUR rollout", "search_project": "integratepie", "data_project": "integratepie"},
                  {"results_found": True}, "contains"),
    BenchmarkCase("MEM-003", "KameCol data isolated from PIE", "memory",
                  {"query": "Django", "search_project": "integratepie", "data_project": "kamecol"},
                  {"results_count": 0}),
]
