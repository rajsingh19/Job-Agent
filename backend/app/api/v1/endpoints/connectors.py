from typing import List
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user_id
from app.schemas.connector import ConnectorInfo
from app.services.connectors.registry import get_connector_registry

router = APIRouter()
connector_registry = get_connector_registry()


@router.get(
    "",
    response_model=List[ConnectorInfo],
    summary="List registered platform connectors and capabilities",
)
async def list_connectors(
    user_id: str = Depends(get_current_user_id),
):
    """
    Returns registered platform connectors, supported application methods,
    and capability definitions.
    """
    return connector_registry.list_connector_infos()
