"""Facade for the scheduler core subsystems."""

from __future__ import annotations

from dataclasses import dataclass

from scheduler_api.engine.facade import ControlPlaneBizFacade, biz_facade
from scheduler_api.engine.orchestrator import RunOrchestrator, run_orchestrator
from scheduler_api.service.run_state_service import RunStateService, run_state_service
from scheduler_api.infra.network.handlers import register_handlers
from scheduler_api.infra.network.server import ControlPlaneServer
from scheduler_api.infra.network.gateway import WorkerGateway, worker_gateway
from scheduler_api.infra.network.manager import WorkerControlManager, worker_manager


@dataclass(frozen=True)
class CoreFacade:
    biz: ControlPlaneBizFacade
    orchestrator: RunOrchestrator
    run_state: RunStateService
    worker_gateway: WorkerGateway
    worker_manager: WorkerControlManager

    def build_server(self) -> ControlPlaneServer:
        server = ControlPlaneServer()
        register_handlers(server)
        return server


core_facade = CoreFacade(
    biz=biz_facade,
    orchestrator=run_orchestrator,
    run_state=run_state_service,
    worker_gateway=worker_gateway,
    worker_manager=worker_manager,
)
