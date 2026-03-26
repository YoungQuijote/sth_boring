from __future__ import annotations

from sdk_test_agent.docker_driver.docker_driver_models import BuildImageSpec, ContainerCreateSpec

from .minimal_loop_models import JavaDeployInput


def render_default_java_runtime_dockerfile() -> str:
    return "\n".join(
        [
            "FROM eclipse-temurin:17-jre",
            "WORKDIR /app",
            "COPY app.jar /app/app.jar",
            'CMD ["java", "-jar", "/app/app.jar"]',
            "",
        ]
    )


def make_build_spec_from_input(data: JavaDeployInput, tag: str) -> BuildImageSpec:
    dockerfile = render_default_java_runtime_dockerfile()
    return BuildImageSpec(
        tag=tag,
        dockerfile_text=dockerfile,
        context_files={"app.jar": data.jar_bytes},
    )


def make_container_spec(image_ref: str) -> ContainerCreateSpec:
    return ContainerCreateSpec(image=image_ref, command=["sleep", "infinity"], working_dir="/app")
