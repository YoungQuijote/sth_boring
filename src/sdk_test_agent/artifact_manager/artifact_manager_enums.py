from __future__ import annotations

ARTIFACT_DB_NAME = "artifact_manage.db"


class TaskType:
    SDK_DEPLOY = "sdk_deploy"
    SDK_TEST = "sdk_test"


class TaskStatus:
    CREATED = "created"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"


class ArtifactKind:
    INPUT_JAR = "input.jar"
    INPUT_POM = "input.pom"
    INPUT_SETTINGS_XML = "input.settings_xml"
    GENERATED_DOCKERFILE = "generated.dockerfile"
    EXEC_STDOUT = "exec.stdout"
    EXEC_STDERR = "exec.stderr"
    BUILD_LOG = "build.log"
    PROBE_RESULT = "probe.result"
    REPORT_JSON = "report.json"


class MimeType:
    TEXT_PLAIN = "text/plain"
    TEXT_MARKDOWN = "text/markdown"
    APPLICATION_JSON = "application/json"
    APPLICATION_XML = "application/xml"
    APPLICATION_JAR = "application/java-archive"
    APPLICATION_TAR = "application/x-tar"
