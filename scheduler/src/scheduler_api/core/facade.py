"""Facade for the scheduler core subsystems."""

from __future__ import annotations

from dataclasses import dataclass

from .biz.facade import ControlPlaneBizFacade, biz_facade
from .biz.dispatch.orchestrator import RunOrchestrator, run_orchestrator
from .biz.services.run_state_service import RunStateService, run_state_service
from .biz.adapters.handlers import register_handlers
from .network.server import ControlPlaneServer
from .network.gateway import WorkerGateway, worker_gateway
from .network.manager import WorkerControlManager, worker_manager


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
