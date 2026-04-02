# sth_boring

当前仓库已扩展到 SdkTestAgent inspection 阶段基础能力：

- `artifact_manager`：中间数据落盘 + SQLite 索引（`artifact_manage.db`）
- `control_plane.runtime_registry`：资源登记（`runtime_registry.db`）
- `control_plane.runtime_manager`：通过 `docker_driver` 做 Docker 资源动作并同步 registry
- `inspection.package_inspector`：输入件检查（Java jar/pom/manifest）
- `inspection.env_inspector`：运行环境只读探测（Docker 容器 probes）
- `loop`：最小 Java jar 部署闭环（支持可选注入 inspectors）

## 重命名规范（已完成）

- `sandbox/sandbox_models.py`
- `sandbox/sandbox_errors.py`
- `docker_driver/docker_driver_models.py`
- `docker_driver/docker_driver_errors.py`
- `cmd_ctrl/cmd_ctrl_models.py`
- `cmd_ctrl/cmd_ctrl_errors.py`

## Inspection MVP

- 顶层共用：`inspection_enums.py`、`inspection_models.py`
- package inspector：`JavaPackageInspector`
- env inspector：`DockerEnvInspector`
- 最小 loop 集成：build 前 package inspect，容器启动后 env inspect（可选依赖注入）

## 测试

```bash
PYTHONPATH=src python -m pytest -q
```
