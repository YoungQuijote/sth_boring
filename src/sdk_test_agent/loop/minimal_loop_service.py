from __future__ import annotations

from sdk_test_agent.artifact_manager.artifact_manager_enums import ArtifactKind, MimeType, TaskType
from sdk_test_agent.artifact_manager.artifact_manager_service import ArtifactManagerService
from sdk_test_agent.control_plane.runtime_manager.runtime_manager_models import EnvFingerprintInput
from sdk_test_agent.control_plane.runtime_manager.runtime_manager_service import RuntimeManagerService
from sdk_test_agent.docker_driver.base import BaseDockerDriver

from .java_deploy_flow import make_build_spec_from_input, make_container_spec
from .minimal_loop_models import JavaDeployInput, MinimalLoopResult


class MinimalLoopService:
    def __init__(
        self,
        artifact_service: ArtifactManagerService,
        runtime_service: RuntimeManagerService,
        driver: BaseDockerDriver,
    ) -> None:
        self.artifact_service = artifact_service
        self.runtime_service = runtime_service
        self.driver = driver

    def run_java_deploy(self, payload: JavaDeployInput) -> MinimalLoopResult:
        task = self.artifact_service.create_task(TaskType.SDK_DEPLOY, input_summary=f"deploy {payload.sdk_name}")
        stage = self.artifact_service.create_stage(task.task_id, "ingest_input", status="done")

        jar_art = self.artifact_service.persist_artifact_bytes(
            task_id=task.task_id,
            stage_id=stage.stage_id,
            kind=ArtifactKind.INPUT_JAR,
            name="app.jar",
            content=payload.jar_bytes,
            subdir="inputs",
            mime_type=MimeType.APPLICATION_JAR,
            created_by_action="ingest_input",
        )
        pom_art = self.artifact_service.persist_artifact_bytes(
            task_id=task.task_id,
            stage_id=stage.stage_id,
            kind=ArtifactKind.INPUT_POM,
            name="pom.xml",
            content=payload.pom_xml_bytes,
            subdir="inputs",
            mime_type=MimeType.APPLICATION_XML,
            created_by_action="ingest_input",
        )

        dockerfile = make_build_spec_from_input(payload, tag=f"{payload.sdk_name}:latest")
        dockerfile_art = self.artifact_service.persist_artifact_bytes(
            task_id=task.task_id,
            stage_id=stage.stage_id,
            kind=ArtifactKind.GENERATED_DOCKERFILE,
            name="Dockerfile",
            content=(dockerfile.dockerfile_text or "").encode("utf-8"),
            subdir="generated",
            mime_type=MimeType.TEXT_PLAIN,
            created_by_action="render_dockerfile",
        )

        build = self.driver.build_image(dockerfile)
        self.runtime_service.register_image(build.image_id, build.tags, source_type="built", source_ref=task.task_id)

        cont = self.runtime_service.create_container(
            spec=make_container_spec(build.image_id),
            owner_task_id=task.task_id,
        )

        fp_payload = EnvFingerprintInput(
            runtime="docker",
            engine_id=self.runtime_service.engine_id,
            image_id=build.image_id,
            sdk_name=payload.sdk_name,
            sdk_version=payload.sdk_version,
            command=["sleep", "infinity"],
            env={},
            ports=[],
        )
        dep = self.runtime_service.create_deployment_record(
            task_id=task.task_id,
            sdk_name=payload.sdk_name,
            sdk_version=payload.sdk_version,
            image_id=build.image_id,
            container_id=cont.container_id,
            fingerprint_payload=fp_payload,
            reusable=1,
        )

        return MinimalLoopResult(
            task_id=task.task_id,
            image_id=build.image_id,
            container_id=cont.container_id,
            deployment_id=dep.deployment_id,
            artifact_ids=[jar_art.artifact_id, pom_art.artifact_id, dockerfile_art.artifact_id],
        )
