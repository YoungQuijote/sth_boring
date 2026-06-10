from pathlib import Path

from sdk_test_agent.artifact_manager import ARTIFACT_DB_NAME, ArtifactKind, ArtifactManagerRepo, ArtifactManagerService, TaskType


def test_artifact_manager_create_and_persist(tmp_path: Path) -> None:
    db = tmp_path / ARTIFACT_DB_NAME
    root = tmp_path / "artifacts"

    repo = ArtifactManagerRepo(str(db))
    repo.init_schema()
    svc = ArtifactManagerService(repo, str(root))

    task = svc.create_task(TaskType.SDK_DEPLOY, "demo")
    stage = svc.create_stage(task.task_id, "ingest", "done")
    artifact = svc.persist_artifact_bytes(
        task_id=task.task_id,
        stage_id=stage.stage_id,
        kind=ArtifactKind.INPUT_JAR,
        name="app.jar",
        content=b"jarbin",
        subdir="inputs",
    )

    assert artifact.storage_path.endswith("app.jar")
    assert Path(artifact.storage_path).exists()
