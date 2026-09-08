"""Offline B10 pipeline: real routing, execution policy and budget gate."""
from types import SimpleNamespace

from agents.api_budget_gate import APIBudgetGate
from agents.assistant_executor import AssistantExecutor
from agents.cost_ledger import CostLedger
from agents.execution_policy import ExecutionPolicy
from agents.executor_registry import ExecutorRegistry
from agents.local_first_router import LocalFirstRouter


class RecordingExecutor:
    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def generate(self, question, level="L3", **kwargs):
        self.calls.append(question)
        return {"ok": True, "text": self.answer, "model": "synthetic",
                "level": level, "latency_ms": 0}


def pipeline(tmp_path, monkeypatch, *, cloud=False, limit=1, web_policy=None, router=None):
    ledger = CostLedger(daily_limit=limit, data_root=tmp_path)
    router = router or LocalFirstRouter(
        cost_ledger=ledger,
        data_root=tmp_path,
        vector_memory=SimpleNamespace(find_similar=lambda *a, **kw: []),
        web_research_policy=web_policy,
    )
    monkeypatch.setattr(router, "_get_retriever", lambda: SimpleNamespace(lookup=lambda question: {"found": False}))
    monkeypatch.setattr(router, "_get_cascade", lambda: SimpleNamespace(select=lambda question: {"level": "L3"}))
    local = RecordingExecutor("local answer")
    api = RecordingExecutor("cloud answer")
    executor = AssistantExecutor(
        router=router,
        execution_policy=ExecutionPolicy(cloud_api_enabled=cloud, cloud_levels={"L3"}),
        executor_registry=ExecutorRegistry(executors={"ollama": local, "api": api}),
        api_budget_gate=APIBudgetGate(ledger=ledger),
    )
    # Keep the decision/execution path real without user config or telemetry I/O.
    monkeypatch.setattr(executor, "_get_provider_selector", lambda: None)
    monkeypatch.setattr(executor, "_log_telemetry", lambda *args: None)
    return executor, ledger, local, api
