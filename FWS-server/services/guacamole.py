"""
Apache Guacamole REST API 연동 서비스

VM 생성 완료 후 Guacamole에 SSH 접속 정보를 자동 등록합니다.
Guacamole 0.9.14+ / 1.x 기준입니다.

클라이언트 직접 URL 형식:
  /guacamole/#/client/{base64("{conn_id}\0c\0{dataSource}")}
  → 이 URL로 이동하면 로그인 후 해당 VM SSH로 바로 연결됩니다.
"""

import base64

import requests

from config import settings


class GuacamoleClient:
    def __init__(self):
        self.base_url = settings.GUACAMOLE_URL.rstrip("/")
        self.token: str | None = None
        self.data_source: str = "mysql"  # 로그인 응답에서 실제 값으로 업데이트됨

    # ── 인증 ────────────────────────────────────────────────────────────────

    def login(self):
        """
        Guacamole 토큰 발급
        응답 예: {"authToken": "...", "username": "...", "dataSource": "mysql", ...}
        """
        resp = requests.post(
            f"{self.base_url}/guacamole/api/tokens",
            data={
                "username": settings.GUACAMOLE_USER,
                "password": settings.GUACAMOLE_PASSWORD,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self.token = data["authToken"]
        self.data_source = data.get("dataSource", "mysql")

    def _params(self) -> dict:
        return {"token": self.token}

    # ── SSH 연결 등록 ────────────────────────────────────────────────────────

    def create_ssh_connection(self, vm_name: str, ip: str, ssh_user: str) -> str:
        """
        Guacamole에 SSH 연결을 등록하고 connection ID를 반환합니다.

        Args:
            vm_name: 연결 이름 (VM 이름과 동일하게 설정)
            ip: VM IP 주소
            ssh_user: SSH 사용자 이름

        Returns:
            Guacamole connection identifier (문자열)
        """
        self.login()

        body = {
            "parentIdentifier": "ROOT",
            "name": vm_name,
            "protocol": "ssh",
            "parameters": {
                "hostname": ip,
                "port": "22",
                "username": ssh_user,
                "password": settings.VM_SSH_PASSWORD,
            },
            "attributes": {
                "max-connections": "1",
                "max-connections-per-user": "1",
            },
        }

        resp = requests.post(
            f"{self.base_url}/guacamole/api/session/data/{self.data_source}/connections",
            params=self._params(),
            json=body,
        )
        resp.raise_for_status()
        result = resp.json()
        conn_id = result.get("identifier", "")
        return conn_id

    def build_client_url(self, connection_id: str) -> str:
        """
        Guacamole 브라우저 직접 접속 URL을 생성합니다.

        Guacamole 클라이언트는 해시 파라미터로 연결을 식별합니다:
          #/client/{base64("{id}\\0c\\0{dataSource}")}
          - \\0 : NUL 구분자
          - c   : connection 타입 (connection group이면 g)

        사용자가 이 URL을 열면 로그인 후 해당 VM의 SSH 터미널로 바로 이동합니다.
        """
        token_raw = f"{connection_id}\0c\0{self.data_source}"
        token = base64.b64encode(token_raw.encode()).decode()
        return f"{self.base_url}/guacamole/#/client/{token}"

    def get_client_url_by_name(self, vm_name: str) -> str:
        """
        VM 이름으로 Guacamole 연결을 찾아 직접 접속 URL을 반환합니다.
        홈 화면의 "VM 접속" 기능에서 사용합니다.
        """
        self.login()

        resp = requests.get(
            f"{self.base_url}/guacamole/api/session/data/{self.data_source}/connections",
            params=self._params(),
        )
        resp.raise_for_status()
        connections: dict = resp.json()

        for conn_id, conn in connections.items():
            if conn.get("name") == vm_name:
                return self.build_client_url(conn_id)

        raise ValueError(f"Guacamole에서 '{vm_name}' 연결을 찾을 수 없습니다")

    # ── SSH 연결 삭제 ────────────────────────────────────────────────────────

    def delete_connection_by_name(self, vm_name: str):
        """
        vm_name과 일치하는 Guacamole 연결을 찾아 삭제합니다.
        연결이 없어도 에러를 발생시키지 않습니다.
        """
        self.login()

        # 전체 연결 목록 조회 (dict 형태: {id: connection_obj})
        resp = requests.get(
            f"{self.base_url}/guacamole/api/session/data/{self.data_source}/connections",
            params=self._params(),
        )
        resp.raise_for_status()
        connections: dict = resp.json()

        for conn_id, conn in connections.items():
            if conn.get("name") == vm_name:
                del_resp = requests.delete(
                    f"{self.base_url}/guacamole/api/session/data"
                    f"/{self.data_source}/connections/{conn_id}",
                    params=self._params(),
                )
                del_resp.raise_for_status()
                break
