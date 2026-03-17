import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # vCenter 연결 정보
    VCENTER_HOST: str = os.getenv("VCENTER_HOST", "172.18.0.10")
    VCENTER_USER: str = os.getenv("VCENTER_USER", "administrator@vsphere.local")
    VCENTER_PASSWORD: str = os.getenv("VCENTER_PASSWORD", "")
    VCENTER_VERIFY_SSL: bool = os.getenv("VCENTER_VERIFY_SSL", "false").lower() == "true"

    # VM 템플릿 이름 (vCenter에 등록된 템플릿 이름과 정확히 일치해야 함)
    TEMPLATE_UBUNTU: str = os.getenv("TEMPLATE_UBUNTU", "ubuntu-22.04-template")
    TEMPLATE_ROCKY: str = os.getenv("TEMPLATE_ROCKY", "rocky-linux-9-template")

    # vCenter 배치 정보 (MoRef ID — vCenter UI > Managed Object Browser에서 확인)
    # 예) cluster: "domain-c8", datastore: "datastore-10", folder: "group-v100"
    CLUSTER: str = os.getenv("CLUSTER", "")
    DATASTORE: str = os.getenv("DATASTORE", "")
    VM_FOLDER: str = os.getenv("VM_FOLDER", "")

    # Guacamole 연결 정보
    GUACAMOLE_URL: str = os.getenv("GUACAMOLE_URL", "http://192.168.11.100:8080")
    GUACAMOLE_USER: str = os.getenv("GUACAMOLE_USER", "guacadmin")
    GUACAMOLE_PASSWORD: str = os.getenv("GUACAMOLE_PASSWORD", "guacadmin")

    # VM SSH 기본 비밀번호 (Guacamole 자동 접속용)
    VM_SSH_PASSWORD: str = os.getenv("VM_SSH_PASSWORD", "")

    # MOCK_MODE=true 이면 vCenter 없이도 더미 데이터로 동작
    MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() == "true"

    # 로그 서버 URL (비어있으면 로컬 파일만 기록)
    LOG_SERVER_URL: str = os.getenv("LOG_SERVER_URL", "")

    # CORS 허용 출처 (콤마 구분, * 는 전체 허용)
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")


settings = Settings()
