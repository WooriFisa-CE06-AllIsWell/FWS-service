from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from config import settings
from services.vcenter import VCenterClient, get_mock_vm
from services.guacamole import GuacamoleClient

router = APIRouter()


# ── 요청/응답 스키마 ─────────────────────────────────────────────────────────


class VMCreateRequest(BaseModel):
    os: str       # "ubuntu" | "rocky"
    cpu: int
    memory: int   # GB
    storage: int  # GB

    @field_validator("os")
    @classmethod
    def validate_os(cls, v: str) -> str:
        if v not in ("ubuntu", "rocky"):
            raise ValueError("os는 'ubuntu' 또는 'rocky' 여야 합니다")
        return v

    @field_validator("cpu")
    @classmethod
    def validate_cpu(cls, v: int) -> int:
        if v not in (1, 2, 4):
            raise ValueError("cpu는 1, 2, 4 중 하나여야 합니다")
        return v

    @field_validator("memory")
    @classmethod
    def validate_memory(cls, v: int) -> int:
        if v not in (1, 2, 4):
            raise ValueError("memory는 1, 2, 4 (GB) 중 하나여야 합니다")
        return v

    @field_validator("storage")
    @classmethod
    def validate_storage(cls, v: int) -> int:
        if v not in (20, 40, 80):
            raise ValueError("storage는 20, 40, 80 (GB) 중 하나여야 합니다")
        return v


class VMDeleteRequest(BaseModel):
    vm_name: str


# ── 엔드포인트 ───────────────────────────────────────────────────────────────


@router.post("/vm/create")
def create_vm(req: VMCreateRequest):
    """
    VM 생성 요청

    흐름: 템플릿 클론 → 스펙 변경 → 전원 ON → IP 반환 → Guacamole 등록

    ※ VM 전원 ON 후 IP 할당까지 최대 5분 소요됩니다.
    """
    if settings.MOCK_MODE:
        mock = get_mock_vm(req.os, req.cpu, req.memory, req.storage)
        # MOCK: Guacamole URL은 기본 홈으로 설정
        mock["guacamole_url"] = f"{settings.GUACAMOLE_URL.rstrip('/')}/guacamole/"
        return mock

    # vCenter에서 VM 생성
    try:
        vcenter = VCenterClient()
        vm_info = vcenter.create_vm(req.os, req.cpu, req.memory, req.storage)
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"VM 생성 실패: {str(e)}")

    # Guacamole에 SSH 연결 자동 등록 후 직접 접속 URL 생성
    guacamole_url = f"{settings.GUACAMOLE_URL.rstrip('/')}/guacamole/"  # 기본값
    try:
        guac = GuacamoleClient()
        conn_id = guac.create_ssh_connection(
            vm_name=vm_info["vm_name"],
            ip=vm_info["ip"],
            ssh_user=vm_info["ssh_user"],
        )
        if conn_id:
            # 해당 VM 연결로 바로 이동하는 URL 생성
            guacamole_url = guac.build_client_url(conn_id)
    except Exception as e:
        print(f"[WARN] Guacamole 연결 등록 실패 (수동으로 추가하세요): {e}")

    vm_info["guacamole_url"] = guacamole_url
    return vm_info


@router.get("/vm/connect")
def get_vm_connect_url(vm_name: str):
    """
    VM 이름으로 Guacamole 직접 접속 URL 반환

    홈 화면 "VM 접속" 모달에서 사용합니다.
    Guacamole에 등록된 연결 중 vm_name과 일치하는 것을 찾아 URL을 반환합니다.
    """
    if settings.MOCK_MODE:
        return {"guacamole_url": f"{settings.GUACAMOLE_URL.rstrip('/')}/guacamole/"}

    try:
        guac = GuacamoleClient()
        url = guac.get_client_url_by_name(vm_name)
        return {"guacamole_url": url}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Guacamole 연결 실패: {str(e)}")


@router.post("/vm/delete")
def delete_vm(req: VMDeleteRequest):
    """
    VM 반납 요청

    흐름: 전원 OFF → VM 삭제 → Guacamole 연결 제거
    """
    if not req.vm_name:
        raise HTTPException(status_code=400, detail="vm_name이 비어있습니다")

    if settings.MOCK_MODE:
        return {"success": True, "message": f"{req.vm_name} 반납 완료 (MOCK)"}

    # vCenter에서 VM 삭제
    try:
        vcenter = VCenterClient()
        vcenter.delete_vm(req.vm_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"VM 삭제 실패: {str(e)}")

    # Guacamole에서 연결 제거
    try:
        guac = GuacamoleClient()
        guac.delete_connection_by_name(req.vm_name)
    except Exception as e:
        print(f"[WARN] Guacamole 연결 삭제 실패: {e}")

    return {"success": True, "message": f"{req.vm_name} 반납 완료"}
