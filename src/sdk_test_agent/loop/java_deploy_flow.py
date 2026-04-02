from __future__ import annotations

from sdk_test_agent.docker_driver.docker_driver_models import BuildImageSpec, ContainerCreateSpec

from .minimal_loop_models import JavaDeployInput


def render_default_java_runtime_dockerfile(has_embedded_jdk: bool = False) -> str:
    lines = [
        "FROM eclipse-temurin:17-jre",
        "WORKDIR /app",
    ]
    if has_embedded_jdk:
        lines.extend(
            [
                "ADD jdk.tar.gz /opt/jdk/",
                "ENV JAVA_HOME=/opt/jdk",
                "ENV PATH=/opt/jdk/bin:$PATH",
            ]
        )
    lines.extend(
        [
            "COPY app.jar /app/app.jar",
            'CMD ["java", "-jar", "/app/app.jar"]',
            "",
        ]
    )
    return "\n".join(lines)


def make_build_spec_from_input(data: JavaDeployInput, tag: str) -> BuildImageSpec:
    has_embedded = data.jdk_bytes is not None
    dockerfile = render_default_java_runtime_dockerfile(has_embedded_jdk=has_embedded)
    context_files: dict[str, bytes] = {"app.jar": data.jar_bytes}
    if data.jdk_bytes is not None:
        context_files["jdk.tar.gz"] = data.jdk_bytes

    return BuildImageSpec(
        tag=tag,
        dockerfile_text=dockerfile,
        context_files=context_files,
    )


def make_container_spec(image_ref: str) -> ContainerCreateSpec:
    return ContainerCreateSpec(image=image_ref, command=["sleep", "infinity"], working_dir="/app")
