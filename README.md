# sth_boring

基于你提供的设计文档，当前仓库实现了 `sdk_test_agent` 三层骨架，并新增 `docker_driver` 的镜像构建能力。

## 当前能力

- `sandbox`：环境抽象 + Docker Python 沙箱
- `docker_driver`：Docker SDK 驱动封装（含 `build_image`）
- `cmd_ctrl`：任务语义控制层

目录位于：`src/sdk_test_agent/`。

## docker_driver build_image（新增）

`DockerSdkDriver.build_image(spec)` 已支持：

1. `dockerfile_text`（仅 Dockerfile 文本）
2. `dockerfile_text + context_files`（内存文件上下文）
3. `context_dir + dockerfile_path_in_context`（目录上下文）
4. `context_tar_bytes`（直接传 tar 上下文）

相关模型：
- `BuildImageSpec`
- `BuildImageResult`

并新增 `make_tar_context()` 用于把 Dockerfile/文件集编码为 tar build context。

## 结构

```text
src/sdk_test_agent/
├── sandbox/
├── docker_driver/
│   ├── build_context.py
│   ├── base.py
│   ├── models.py
│   ├── errors.py
│   └── docker_sdk_driver.py
└── cmd_ctrl/
```

## 运行测试

```bash
PYTHONPATH=src python -m pytest -q
```
