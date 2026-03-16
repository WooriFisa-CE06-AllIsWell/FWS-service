"""
vCenter 연동 서비스

- VM 생성/삭제: pyVmomi (SOAP API) — vSphere 7.0에서 REST clone 미지원
- 자원 현황:    REST API (/api/...)
"""

import ssl
import time
from datetime import datetime

import requests
import urllib3
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

from config import settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ── pyVmomi 헬퍼 ────────────────────────────────────────────────────────────

def _get_si():
    """vCenter SOAP 연결 반환"""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return SmartConnect(
        host=settings.VCENTER_HOST,
        user=settings.VCENTER_USER,
        pwd=settings.VCENTER_PASSWORD,
        sslContext=context,
    )


def _get_obj(content, vimtype, moref_id: str):
    """MoRef ID로 vSphere 오브젝트 반환"""
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True
    )
    for obj in container.view:
        if obj._moId == moref_id:
            container.Destroy()
            return obj
    container.Destroy()
    raise ValueError(f"{vimtype[0].__name__} '{moref_id}' not found")


def _get_obj_by_name(content, vimtype, name: str):
    """이름으로 vSphere 오브젝트 반환"""
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True
    )
    for obj in container.view:
        if obj.name == name:
            container.Destroy()
            return obj
    container.Destroy()
    raise ValueError(f"{vimtype[0].__name__} '{name}' not found")


def _wait_task(task, timeout: int = 600):
    """vSphere Task 완료까지 대기"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = task.info.state
        if state == vim.TaskInfo.State.success:
            return task.info.result
        if state == vim.TaskInfo.State.error:
            raise RuntimeError(f"Task 실패: {task.info.error.msg}")
        time.sleep(5)
    raise TimeoutError("Task가 시간 내에 완료되지 않았습니다")


# ── REST API 클라이언트 (자원 현황용) ───────────────────────────────────────

class VCenterClient:
    def __init__(self):
        self.base_url = f"https://{settings.VCENTER_HOST}"
        self.session_token: str | None = None
        self.verify = settings.VCENTER_VERIFY_SSL

    def login(self):
        resp = requests.post(
            f"{self.base_url}/api/session",
            auth=(settings.VCENTER_USER, settings.VCENTER_PASSWORD),
            verify=self.verify,
        )
        resp.raise_for_status()
        self.session_token = resp.json()

    def _headers(self) -> dict:
        return {"vmware-api-session-id": self.session_token}

    def _get(self, path: str, params: dict = None):
        resp = requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            params=params,
            verify=self.verify,
        )
        resp.raise_for_status()
        return resp.json()

    # ── VM 생성 (pyVmomi) ────────────────────────────────────────────────────

    def create_vm(self, os: str, cpu: int, memory_gb: int, storage_gb: int) -> dict:
        """템플릿 클론 → 스펙 변경 → 전원 ON → IP 반환"""
        template_value = (
            settings.TEMPLATE_UBUNTU if os == "ubuntu" else settings.TEMPLATE_ROCKY
        )
        ssh_user = "bo" if os == "ubuntu" else "root"
        os_label = "Ubuntu 22.04 LTS" if os == "ubuntu" else "Rocky Linux 9"
        vm_name = f"fws-vm-{datetime.now().strftime('%m%d-%H%M%S')}"

        si = _get_si()
        try:
            content = si.RetrieveContent()

            # 소스 VM/템플릿
            if template_value.startswith("vm-"):
                source = _get_obj(content, [vim.VirtualMachine], template_value)
            else:
                source = _get_obj_by_name(content, [vim.VirtualMachine], template_value)

            # 배치 대상
            datastore = _get_obj(content, [vim.Datastore], settings.DATASTORE)
            folder = _get_obj(content, [vim.Folder], settings.VM_FOLDER)
            cluster = _get_obj(content, [vim.ClusterComputeResource], settings.CLUSTER)
            resource_pool = cluster.resourcePool

            # 클론 스펙
            relocate_spec = vim.vm.RelocateSpec(
                datastore=datastore,
                pool=resource_pool,
            )
            config_spec = vim.vm.ConfigSpec(
                numCPUs=cpu,
                memoryMB=memory_gb * 1024,
            )
            clone_spec = vim.vm.CloneSpec(
                location=relocate_spec,
                config=config_spec,
                powerOn=True,
                template=False,
            )

            # 클론 실행
            task = source.Clone(folder=folder, name=vm_name, spec=clone_spec)
            new_vm = _wait_task(task, timeout=600)

            # IP 대기 (VMware Tools 필요, 최대 5분)
            ip = self._wait_for_ip_vmomi(new_vm, timeout=300)
            vm_id = new_vm._moId

        finally:
            Disconnect(si)

        return {
            "vm_name": vm_name,
            "vm_id": vm_id,
            "ip": ip,
            "os": os_label,
            "cpu": cpu,
            "memory": memory_gb,
            "storage": storage_gb,
            "ssh_user": ssh_user,
        }

    def _wait_for_ip_vmomi(self, vm, timeout: int = 300) -> str:
        """VMware Tools로 IP 할당 대기 (10초 간격)"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if vm.guest and vm.guest.ipAddress:
                    ip = vm.guest.ipAddress
                    if not ip.startswith("127.") and ":" not in ip:
                        return ip
            except Exception:
                pass
            time.sleep(10)
        raise TimeoutError(f"VM {vm.name}: IP를 {timeout}초 내에 가져오지 못했습니다")

    # ── VM 삭제 (pyVmomi) ────────────────────────────────────────────────────

    def delete_vm(self, vm_name: str):
        """전원 OFF → VM 삭제"""
        si = _get_si()
        try:
            content = si.RetrieveContent()
            vm = _get_obj_by_name(content, [vim.VirtualMachine], vm_name)

            # 전원 OFF
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                task = vm.PowerOff()
                _wait_task(task, timeout=120)
                time.sleep(3)

            # VM 삭제
            task = vm.Destroy()
            _wait_task(task, timeout=120)
        finally:
            Disconnect(si)

    # ── 자원 현황 (REST API) ─────────────────────────────────────────────────

    def get_resources(self) -> dict:
        # 호스트 하드웨어 정보는 pyVmomi로 조회
        # (REST /api/vcenter/host 목록에 cpu_count/memory_size_MiB 미포함 — vSphere 7.0.3)
        si = _get_si()
        try:
            content = si.RetrieveContent()
            cluster = _get_obj(content, [vim.ClusterComputeResource], settings.CLUSTER)
            cpu_total = sum(h.summary.hardware.numCpuCores for h in cluster.host)
            mem_total_mib = sum(
                h.summary.hardware.memorySize // (1024 * 1024) for h in cluster.host
            )
        finally:
            Disconnect(si)

        # VM 사용량 및 스토리지는 REST API로 조회
        self.login()
        all_vms = self._get("/api/vcenter/vm")
        powered_on_vms = [v for v in all_vms if v.get("power_state") == "POWERED_ON"]
        cpu_used = sum(v.get("cpu_count", 0) for v in powered_on_vms)
        mem_used_mib = sum(v.get("memory_size_MiB", 0) for v in powered_on_vms)

        datastores = self._get("/api/vcenter/datastore")
        sto_total_gb = sum(d.get("capacity", 0) for d in datastores) // (1024**3)
        sto_free_gb = sum(d.get("free_space", 0) for d in datastores) // (1024**3)

        return {
            "cpu_total": cpu_total,
            "cpu_used": cpu_used,
            "cpu_available": max(0, cpu_total - cpu_used),
            "mem_total": mem_total_mib // 1024,
            "mem_used": mem_used_mib // 1024,
            "mem_available": max(0, (mem_total_mib - mem_used_mib) // 1024),
            "sto_total": sto_total_gb,
            "sto_used": sto_total_gb - sto_free_gb,
            "sto_available": sto_free_gb,
        }


# ── Mock 데이터 ─────────────────────────────────────────────────────────────

def get_mock_resources() -> dict:
    return {
        "cpu_total": 80,
        "cpu_used": 52,
        "cpu_available": 20,
        "mem_total": 64,
        "mem_used": 24,
        "mem_available": 40,
        "sto_total": 2000,
        "sto_used": 600,
        "sto_available": 1400,
    }


def get_mock_vm(os: str, cpu: int, memory_gb: int, storage_gb: int) -> dict:
    ts = datetime.now().strftime("%m%d-%H%M%S")
    ssh_user = "bo" if os == "ubuntu" else "root"
    os_label = "Ubuntu 22.04 LTS" if os == "ubuntu" else "Rocky Linux 9"

    return {
        "vm_name": f"fws-vm-{ts}",
        "vm_id": "vm-mock-001",
        "ip": "192.168.11.50",
        "os": os_label,
        "cpu": cpu,
        "memory": memory_gb,
        "storage": storage_gb,
        "ssh_user": ssh_user,
    }
