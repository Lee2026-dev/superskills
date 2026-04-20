# superskills

[English](README.md) | 简体中文

`superskills` 当前提供一个 Python CLI 工具，用于扫描本地 skill 目录并生成统一盘点文件。

## 功能说明

- 递归扫描固定目录：
  - `~/.codex/skills`
  - `~/.agents/skills`
  - `~/skills`
- 仅当目录包含 `SKILL.md` 时，判定为 skill
- 默认跟随符号链接（symlink）
- 默认忽略常见噪声目录：
  - `.git`
  - `node_modules`
  - `__pycache__`
  - `.venv`
- 同名 skill 全部保留，并标记冲突
- 在终端输出汇总信息，并将 JSON 写入：
  - `~/.agents/superskills.json`

## 安装

在仓库根目录执行：

```bash
pip3 install -e .
```

## 使用方式

### 安装后命令

```bash
skills-inventory scan
```

### 开发模式（不安装）

```bash
PYTHONPATH=src python3 -m skills_inventory.cli scan
```

## 输出内容

命令会写入 `~/.agents/superskills.json`，主要字段包括：

- `schema_version`
- `generated_at`
- `scan_roots`
- `settings`
- `summary`
- `skills`
- `conflicts`

终端汇总示例：

```text
total_skills=12 conflict_names=2 scanned_dirs=406 duration_ms=139
```

## 开发与测试

运行测试：

```bash
python3 -m pytest -v
```

## 目录结构

```text
src/skills_inventory/
  cli.py
  scanner.py
  models.py
  output.py
tests/
docs/
```

## 当前范围（MVP）

当前版本仅覆盖“发现与盘点”（偏只读行为）。  
安装/迁移/去重/版本管理等能力在后续迭代实现。

