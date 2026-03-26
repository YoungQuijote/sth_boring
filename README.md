# sth_boring

当前仓库已扩展到 SdkTestAgent 下一阶段基础能力：

- `artifact_manager`：中间数据落盘 + SQLite 索引（`artifact_manage.db`）
- `control_plane.runtime_registry`：资源登记（`runtime_registry.db`）
- `control_plane.runtime_manager`：通过 `docker_driver` 做 Docker 资源动作并同步 registry
- `loop`：最小 Java jar 部署闭环（input -> artifact -> build image -> container -> deployment record）

## 重命名规范（已完成）

为避免全局 `models.py/errors.py` 重名，已统一为：

- `sandbox/sandbox_models.py`
- `sandbox/sandbox_errors.py`
- `docker_driver/docker_driver_models.py`
- `docker_driver/docker_driver_errors.py`
- `cmd_ctrl/cmd_ctrl_models.py`
- `cmd_ctrl/cmd_ctrl_errors.py`

## 数据库

- Artifact DB: `artifact_manage.db`
- Runtime Registry DB: `runtime_registry.db`

## 测试

```bash
PYTHONPATH=src python -m pytest -q
```
