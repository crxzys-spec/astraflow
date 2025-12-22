import json
from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow
from scheduler_api.core.biz.domain.graph import build_edge_bindings_for_workflow
from scheduler_api.core.biz.domain.models import WorkflowScopeIndex

raw = """{\"id\":\"w\",\"schemaVersion\":\"2025-10\",\"metadata\":{\"name\":\"n\",\"namespace\":\"default\",\"originId\":\"w\"},\"nodes\":[{\"id\":\"n1\",\"type\":\"t1\",\"package\":{\"name\":\"p\",\"version\":\"1\"},\"status\":\"published\",\"category\":\"c\",\"label\":\"l\",\"position\":{\"x\":0,\"y\":0},\"ui\":{\"outputPorts\":[{\"key\":\"out\",\"label\":\"Out\",\"binding\":{\"path\":\"/results/x\",\"mode\":\"read\"}}]}},{\"id\":\"host\",\"type\":\"host\",\"package\":{\"name\":\"p\",\"version\":\"1\"},\"status\":\"published\",\"category\":\"c\",\"label\":\"Host\",\"position\":{\"x\":0,\"y\":0},\"ui\":{\"inputPorts\":[{\"key\":\"in\",\"label\":\"In\",\"binding\":{\"path\":\"/parameters/in\",\"mode\":\"write\"}}]},\"middlewares\":[{\"id\":\"mw1\",\"type\":\"mw\",\"package\":{\"name\":\"p\",\"version\":\"1\"},\"status\":\"published\",\"category\":\"c\",\"label\":\"MW\",\"ui\":{\"inputPorts\":[{\"key\":\"times\",\"label\":\"Times\",\"binding\":{\"path\":\"/parameters/times\",\"mode\":\"write\"}}]}}]}],\"edges\":[{\"id\":\"e1\",\"source\":{\"node\":\"n1\",\"port\":\"out\"},\"target\":{\"node\":\"host\",\"port\":\"mw:mw1:input:times\"}}]}"""
wf = StartRunRequestWorkflow.from_json(raw)
b = build_edge_bindings_for_workflow(wf, WorkflowScopeIndex(wf))
print(b)
