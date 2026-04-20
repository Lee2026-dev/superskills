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
- 提供基于 Git 的 skill 版本状态：
  - `current_version`（当前 `HEAD` 命中的 SemVer tag，否则 `unknown`）
  - `latest_version`（抓取 tags 后计算出的最高 SemVer，否则 `unknown`）
- 支持查看已安装 skill 的可用版本（来自 Git tags）
- 支持升级已安装 skill 到指定 tag 或最新 SemVer
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
skills-inventory list-versions <name> [--path <绝对路径>]
skills-inventory upgrade <name> [--path <绝对路径>] (--to <tag> | --latest)
```

### 开发模式（不安装）

```bash
PYTHONPATH=src python3 -m skills_inventory.cli scan
PYTHONPATH=src python3 -m skills_inventory.cli list-versions <name> [--path <绝对路径>]
PYTHONPATH=src python3 -m skills_inventory.cli upgrade <name> [--path <绝对路径>] (--to <tag> | --latest)
```

### 命令说明

- `scan` 现在会在终端表格与 JSON 中默认输出 `current_version` 和 `latest_version`。
- `list-versions` 会抓取 tags，并按 SemVer 从高到低输出版本。
- `upgrade` 在目标仓库存在未提交改动时会拒绝执行。

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

## 当前范围（v1）

当前版本已覆盖“发现与盘点”以及基于 Git tag 的版本查看与升级能力。
