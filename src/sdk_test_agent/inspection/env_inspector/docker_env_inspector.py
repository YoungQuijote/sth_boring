from __future__ import annotations

from sdk_test_agent.cmd_ctrl.policies import InspectPolicy
from sdk_test_agent.docker_driver.base import BaseDockerDriver
from sdk_test_agent.docker_driver.docker_driver_models import ExecCreateSpec
from sdk_test_agent.inspection.inspection_enums import FindingLevel, InspectionStatus, InspectionSubjectType
from sdk_test_agent.inspection.inspection_models import InspectionFinding

from .env_inspector_base import BaseEnvInspector
from .env_inspector_models import DockerEnvInspectionInput, EnvInspectionReport, ProbeRecord


class DockerEnvInspector(BaseEnvInspector):
    inspector_name = "docker_env_inspector"

    def __init__(self, driver: BaseDockerDriver) -> None:
        self.driver = driver
        self.inspect_policy = InspectPolicy(
            allowed_binaries={
                "pwd",
                "ls",
                "env",
                "which",
                "python",
                "pip",
                "java",
                "mvn",
                "gradle",
            }
        )

    def inspect_docker_env(self, data: DockerEnvInspectionInput) -> EnvInspectionReport:
        report = EnvInspectionReport(
            subject_type=InspectionSubjectType.ENVIRONMENT,
            subject_name=data.container_id,
            status=InspectionStatus.SUCCESS,
            runtime_type=data.runtime_name,
            engine_id=data.engine_id,
            image_id=data.image_id,
            container_id=data.container_id,
        )

        try:
            container = self.driver.inspect_container(data.container_id)
        except Exception as exc:  # noqa: BLE001
            report.status = InspectionStatus.FAILED
            report.readiness = "failed"
            report.findings.append(InspectionFinding(code="container.inspect.failed", level=FindingLevel.ERROR, summary="failed to inspect container", detail=str(exc)))
            return report

        report.container_status = container.status
        if container.status != "running":
            report.status = InspectionStatus.FAILED
            report.readiness = "failed"
            report.findings.append(InspectionFinding(code="container.not_running", level=FindingLevel.ERROR, summary=f"container status is {container.status}"))
            return report

        probes = [
            ("probe.pwd", ["pwd"]),
            ("probe.ls", ["ls"]),
            ("probe.env", ["env"]),
            ("tool.python.which", ["which", "python"]),
            ("tool.python.version", ["python", "-V"]),
            ("tool.pip.which", ["which", "pip"]),
            ("tool.pip.version", ["pip", "-V"]),
            ("tool.pip.list", ["pip", "list"]),
            ("tool.java.version", ["java", "-version"]),
            ("tool.maven.version", ["mvn", "-v"]),
            ("tool.gradle.version", ["gradle", "-v"]),
        ]

        critical_ok = 0
        for name, argv in probes:
            rec = self._run_probe(data.container_id, name, argv)
            report.probe_records.append(rec)
            if rec.ok:
                if name in {"probe.pwd", "probe.ls", "probe.env"}:
                    critical_ok += 1
                report.findings.append(InspectionFinding(code=f"{name}.ok", level=FindingLevel.INFO, summary=f"{name} succeeded"))
            else:
                report.warnings.append(f"{name} failed")
                report.findings.append(InspectionFinding(code=f"{name}.failed", level=FindingLevel.WARNING, summary=f"{name} failed"))

        if critical_ok >= 3:
            report.readiness = "ready"
            report.status = InspectionStatus.SUCCESS if not report.warnings else InspectionStatus.PARTIAL
        elif critical_ok > 0:
            report.readiness = "degraded"
            report.status = InspectionStatus.PARTIAL
        else:
            report.readiness = "failed"
            report.status = InspectionStatus.FAILED

        return report

    def _run_probe(self, container_id: str, probe_name: str, argv: list[str]) -> ProbeRecord:
        try:
            self.inspect_policy.validate_argv(argv)
            out = self.driver.exec(ExecCreateSpec(container_id=container_id, argv=argv), timeout_sec=10)
            return ProbeRecord(
                probe_name=probe_name,
                command=argv,
                ok=out.exit_code == 0,
                exit_code=out.exit_code,
                stdout=(out.stdout or out.combined or b"").decode("utf-8", errors="replace") if (out.stdout or out.combined) else None,
                stderr=(out.stderr or b"").decode("utf-8", errors="replace") if out.stderr else None,
            )
        except Exception as exc:  # noqa: BLE001
            return ProbeRecord(probe_name=probe_name, command=argv, ok=False, exit_code=None, stderr=str(exc))
