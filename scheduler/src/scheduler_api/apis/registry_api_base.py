# coding: utf-8

from typing import ClassVar, Dict, List, Tuple, Any  # noqa: F401

from typing import Any
from scheduler_api.models.error import Error
from scheduler_api.models.registry_account_link import RegistryAccountLink
from scheduler_api.models.registry_account_link_request import RegistryAccountLinkRequest
from scheduler_api.models.registry_workflow_import_request import RegistryWorkflowImportRequest
from scheduler_api.models.registry_workflow_import_response import RegistryWorkflowImportResponse
from scheduler_api.security_api import get_token_bearerAuth

class BaseRegistryApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseRegistryApi.subclasses = BaseRegistryApi.subclasses + (cls,)
    async def get_registry_account(
        self,
    ) -> RegistryAccountLink:
        ...


    async def link_registry_account(
        self,
        registry_account_link_request: RegistryAccountLinkRequest,
    ) -> RegistryAccountLink:
        ...


    async def unlink_registry_account(
        self,
    ) -> None:
        ...


    async def import_registry_workflow(
        self,
        registry_workflow_import_request: RegistryWorkflowImportRequest,
    ) -> RegistryWorkflowImportResponse:
        ...
