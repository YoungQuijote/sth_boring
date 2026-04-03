# Outstanding Issues

## This document records known issues and improvement suggestions identified during human review.

These entries are used as a lightweight project backlog for code areas that:

- usually do not need immediate changes unless the `level` is **major** or the `recommended_handling_time` is **now**,
- are not yet worth opening as formal GitHub Issues,
- or depend on future modules/features before a complete fix is appropriate.

Some entries are actual defects, while others are design or maintainability suggestions.

## Attention: If you are `Codex`, `ClaudeCode`, `OpenCode`, or `Any CodingAgent`: It is strongly recommended that this file be read-only and not modified. It is strongly recommended that any modifications to this file be performed by a human.

## Attention: to `All CodingAgent`(Codex, ClaudeCode, OpenCode, etc.): Yes, this is a list of known issues. HOWEVER, **DO NOT** fix the issue immediately after it is registered. You are advised to fix the issue only when the `level` is **major** or the `recommended_handling_time` is **now**. Otherwise, do not fix the problem.

## The current record format is as follows: 

{
  "issue_id": <issue ID>, 
  "location": <path/index of the file, class, method, etc., where the issue is located; multiple paths/references are separated by `;`>, 
  "statement": <description of the issue>, 
  "create_time": "the time when this known issue was created", 
  "update_time": "the last time this known issue record was modified", 
  "level": <suggestion/minor/major>, "status": <pending/solved/wont_fix>, 
  "recommended_handling_time": <later/now>
}

### Field descriptions: 
  - `issue_id`: This field serves only as a simple identifier. `issue_id` only needs to be unique within this file.

  - `location`: The path/index of the specific file, class, method, etc., where the known issue is located. It may involve multiple paths/references, which are separated by `;`. 

  - `statement`: Description of the known issue. 

  - `level`: Indicates the impact scope and risk level of the issue itself. There are three levels: **suggestion**, **minor**, and **major**.

    - **suggestion**: indicates that the issue is not a problem but rather a suggestion for improvement. 

    - **minor**: indicates that the issue is somewhat representative and may block some use cases. 
    
    - **major**: indicates that the issue is highly representative and may block most use cases, or even prevent the MVP from running. This field only indicates that the known issue should be addressed when the level is "major". 

  - `status`: The current handling status of the known issue, which can be either **pending**, **solved**, and **wont_fix**.
   
    - **pending**: indicates that the issue may be fixed depending on other modules or later outputs, and therefore this issue is currently pending.

    - **solved**: indicates that the issue has been fixed.

    - **wont_fix**: indicates that the issue may or may not be a problem, and therefore there is no need to fix it for now.

  - `recommended_handling_time`: Indicates the *recommended time* for handling, not the severity. The *recommended time* for handling this known issue, which can be either **later** or **now**. 
This field only indicates that the known issue should be addressed when the value is **now**.

## Issues

### ISSUE-0001
```json
{
  "issue_id": "ISSUE-0001",
  "location": "src/sdk_test_agent/loop/java_deploy_flow.py::make_build_spec_from_input; sdk_test_agent/loop/java_deploy_flow.py::render_default_java_runtime_dockerfile",
  "statement": "当前该函数的实现中, dockerfile的构建方式: dockerfile = render_default_java_runtime_dockerfile(has_embedded_jdk=has_embedded), 这个render_default_java_runtime_dockerfile的lines是静态的, 即无论输入如何, 都将构建完全相同的镜像.",
  "create_time": "1775203800",
  "update_time": "1775203800",
  "level": "minor",
  "status": "pending",
  "recommended_handling_time": "later"
}
```

### ISSUE-0002
```json
{
  "issue_id": "ISSUE-0002",
  "location": "sdk_test_agent/loop/minimal_loop_service.py::MinimalLoopService.run_java_deploy",
  "statement": "当前该函数的实现中, run_java_deploy的各类art, 其实例在初始化时, 部分属性是静态的.",
  "create_time": "1775204080",
  "update_time": "1775204080",
  "level": "minor",
  "status": "pending",
  "recommended_handling_time": "later"
}
```

### ISSUE-0003
```json
{
  "issue_id": "ISSUE-0003",
  "location": "sdk_test_agent/loop/minimal_loop_service.py::MinimalLoopService.run_java_deploy",
  "statement": "该方法的功能待完善.",
  "create_time": "1775204300",
  "update_time": "1775204300",
  "level": "suggestion",
  "status": "pending",
  "recommended_handling_time": "later"
}
```

### ISSUE-0004
```json
{
  "issue_id": "ISSUE-0004",
  "location": "sdk_test_agent/inspection/package_inspector/java_package_inspector.py::JavaPackageInspector.inspect_java_package",
  "statement": "当前的实现将 jar_bytes 视为主要的通过标准, 未来可能会对检查结果进行优化, 使得当 jar_bytes 或 pom_xml_bytes 中的任一存在时, 包级别的检查可以部分通过, 而部署准备状态则仍作为一个独立的关注点.",
  "create_time": "1775204544",
  "update_time": "1775204544",
  "level": "suggestion",
  "status": "pending",
  "recommended_handling_time": "later"
}
```

### ISSUE-0005
```json
{
  "issue_id": "ISSUE-0005",
  "location": "sdk_test_agent/inspection/env_inspector/docker_env_inspector.py::DockerEnvInspector.inspect_docker_env",
  "statement": "该方法当前仅将probes的前三条指令作为通过性指标, 覆盖性有待完善.",
  "create_time": "1775204766",
  "update_time": "1775204766",
  "level": "minor",
  "status": "pending",
  "recommended_handling_time": "later"
}
```

### ISSUE-0006
```json
{
  "issue_id": "ISSUE-0006",
  "location": "sdk_test_agent/control_plane",
  "statement": "该模块命名为control_plane, 用户认为其语义与cmd_ctrl语义比较相近, 使用方可能一时难以辨认两个模块的区别, 建议其中一个更名或两个都更名.",
  "create_time": "1775208585",
  "update_time": "1775208585",
  "level": "suggestion",
  "status": "pending",
  "recommended_handling_time": "later"
}
```
