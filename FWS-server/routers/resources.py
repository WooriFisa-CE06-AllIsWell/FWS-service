from fastapi import APIRouter, HTTPException

from config import settings
from services.vcenter import VCenterClient, get_mock_resources

router = APIRouter()


@router.get("/resources")
def get_resources():
    """
    클러스터 가용 자원 현황 반환

    Response:
        cpu_total, cpu_used, cpu_available (vCPU)
        mem_total, mem_used, mem_available (GB)
        sto_total, sto_used, sto_available (GB)
    """
    if settings.MOCK_MODE:
        return get_mock_resources()

    try:
        client = VCenterClient()
        return client.get_resources()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"vCenter 연결 실패: {str(e)}")
