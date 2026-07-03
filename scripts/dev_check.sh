#!/usr/bin/env bash
set -euo pipefail

REPORT_DIR="outputs/dev_checks"
REPORT_FILE="${REPORT_DIR}/latest.md"
PYTEST_STATUS=0

mkdir -p "${REPORT_DIR}"
exec > >(tee "${REPORT_FILE}") 2>&1

project_tree() {
  find . \
    -path '*/.git' -prune -o \
    -path './.venv' -prune -o \
    -path '*/__pycache__' -prune -o \
    -path './.pytest_cache' -prune -o \
    -path './outputs/dev_checks' -prune -o \
    -print | LC_ALL=C sort
}

file_status() {
  local path="$1"
  if [[ -e "${path}" ]]; then
    echo "- ${path}: exists"
  else
    echo "- ${path}: missing"
  fi
}

run_pytest_if_available() {
  if [[ -f "pyproject.toml" || -d "tests" ]]; then
    if command -v pytest >/dev/null 2>&1; then
      echo '```text'
      if pytest -q; then
        echo '```'
        echo
        echo "pytest result: passed"
      else
        PYTEST_STATUS=$?
        echo '```'
        echo
        echo "pytest result: failed"
      fi
    else
      echo "未检测到测试或测试环境：存在 pyproject.toml 或 tests/，但当前环境没有 pytest。"
    fi
  else
    echo "未检测到测试或测试环境：未发现 pyproject.toml 或 tests/。"
  fi
}

echo "# Alpha Research Stack Dev Check"
echo
echo "## Snapshot"
echo
echo "- 当前时间: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "- 当前目录: $(pwd)"
echo "- git branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unavailable')"
echo
echo "## Git Status"
echo
echo '```text'
git status --short 2>/dev/null || echo "git status unavailable"
echo '```'
echo
echo "## Git Diff Stat"
echo
echo '```text'
git diff --stat 2>/dev/null || echo "git diff unavailable"
echo '```'
echo
echo "## Latest Commit"
echo
echo '```text'
git log -1 --oneline 2>/dev/null || echo "no commits"
echo '```'
echo
echo "## Project Tree"
echo
echo '```text'
project_tree
echo '```'
echo
echo "## Required Files"
echo
file_status "README.md"
file_status "AGENTS.md"
file_status "docs/progress.md"
file_status "docs/architecture.md"
file_status "docs/open_source_stack_audit.md"
echo
echo "## Tests"
echo
run_pytest_if_available
echo
echo "## ChatGPT Handoff"
echo
cat <<'HANDOFF'
请审查这个 Alpha Research Stack 开发 Goal：

- 仓库/PR 链接：
- Goal 编号：
- 本次目标：
- 主要改动：
- 验收命令：
  - make check
- 当前风险或未完成事项：
- 希望重点审查：
  - 是否符合 README.md 与 AGENTS.md 的项目边界
  - 是否更新了 docs/progress.md
  - 是否避免了业务代码、密钥和不必要依赖
  - 是否需要补充测试、CI 或文档
HANDOFF

exit "${PYTEST_STATUS}"
