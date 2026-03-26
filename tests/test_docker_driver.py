from types import SimpleNamespace

import pytest

from sdk_test_agent.docker_driver.build_context import make_tar_context
from sdk_test_agent.docker_driver.docker_sdk_driver import DockerSdkDriver
from sdk_test_agent.docker_driver.docker_driver_errors import DockerImageError
from sdk_test_agent.docker_driver.docker_driver_models import BuildImageSpec, ContainerCreateSpec, ExecCreateSpec


class FakeExecResult:
    def __init__(self, exit_code=0, output=(b"ok", b"")):
        self.exit_code = exit_code
        self.output = output


class FakeContainer:
    def __init__(self, cid: str = "c1"):
        self.id = cid
        self.name = "fake"
        self.status = "running"
        self.attrs = {"Id": cid}

    def start(self):
        return None

    def exec_run(self, **kwargs):
        return FakeExecResult()

    def put_archive(self, dest, data):
        return True

    def get_archive(self, path):
        return [b"abc"], {"name": path}

    def logs(self, tail=200):
        return b"logs"

    def reload(self):
        return None

    def stop(self, timeout=10):
        return None

    def remove(self, force=False, v=False):
        return None


class FakeContainers:
    def __init__(self):
        self._c = FakeContainer()

    def create(self, **kwargs):
        return self._c

    def get(self, cid):
        return self._c


class FakeImages:
    def __init__(self):
        self.last_build_kwargs = None

    def get(self, image):
        return SimpleNamespace(id="img1")

    def pull(self, image):
        return SimpleNamespace(id="img1")

    def build(self, **kwargs):
        self.last_build_kwargs = kwargs
        image = SimpleNamespace(id="built-img", tags=[kwargs.get("tag")] if kwargs.get("tag") else [])
        logs = [{"stream": "ok"}]
        return image, logs


class FakeClient:
    def __init__(self):
        self.images = FakeImages()
        self.containers = FakeContainers()

    def ping(self):
        return True


def test_docker_sdk_driver_happy_path() -> None:
    driver = DockerSdkDriver(client_factory=FakeClient)
    assert driver.ping() is True
    assert driver.ensure_image("python:3.11-slim") == "img1"

    cref = driver.create_container(ContainerCreateSpec(image="python:3.11-slim", command=["sleep", "infinity"]))
    assert cref.container_id == "c1"

    driver.start_container(cref.container_id)
    out = driver.exec(ExecCreateSpec(container_id=cref.container_id, argv=["python", "-V"]))
    assert out.exit_code == 0
    assert out.stdout == b"ok"

    driver.put_archive(cref.container_id, "/", b"tar")
    data, stat = driver.get_archive(cref.container_id, "/workspace")
    assert data == b"abc"
    assert stat["name"] == "/workspace"

    assert driver.logs(cref.container_id) == b"logs"
    driver.stop_container(cref.container_id)
    driver.remove_container(cref.container_id)


def test_build_image_inline_dockerfile() -> None:
    driver = DockerSdkDriver(client_factory=FakeClient)
    result = driver.build_image(
        BuildImageSpec(
            tag="demo:inline",
            dockerfile_text="FROM python:3.11-slim\nRUN python -V\n",
        )
    )

    assert result.image_id == "built-img"
    assert result.tags == ["demo:inline"]


def test_build_image_with_context_files() -> None:
    driver = DockerSdkDriver(client_factory=FakeClient)
    result = driver.build_image(
        BuildImageSpec(
            tag="demo:files",
            dockerfile_text="FROM python:3.11-slim\nCOPY hello.py /app/hello.py\n",
            context_files={"hello.py": b"print('hello')\n"},
        )
    )

    assert result.image_id == "built-img"


def test_make_tar_context_empty_rejected() -> None:
    with pytest.raises(ValueError):
        make_tar_context(None)


def test_build_image_invalid_spec_rejected() -> None:
    driver = DockerSdkDriver(client_factory=FakeClient)
    with pytest.raises(DockerImageError):
        driver.build_image(BuildImageSpec())


class FailingImages(FakeImages):
    def build(self, **kwargs):
        image = SimpleNamespace(id="built-img", tags=[])
        logs = [{"errorDetail": {"message": "COPY failed: missing.txt"}}]
        return image, logs


class FailingClient(FakeClient):
    def __init__(self):
        self.images = FailingImages()
        self.containers = FakeContainers()


def test_build_image_error_from_logs() -> None:
    driver = DockerSdkDriver(client_factory=FailingClient)
    with pytest.raises(DockerImageError):
        driver.build_image(
            BuildImageSpec(
                dockerfile_text="FROM python:3.11-slim\nCOPY missing.txt /tmp/missing.txt\n",
            )
        )
