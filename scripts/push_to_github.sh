#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

DRY_RUN=0
NO_PUSH=0
MESSAGE=""

usage() {
  cat <<'EOF'
用法: scripts/push_to_github.sh [选项]

自动暂存当前变更、提交并推送到 GitHub origin。

选项:
  -m, --message TEXT   自定义 commit message（默认根据变更自动生成）
  -n, --dry-run        只显示将要执行的操作，不实际提交或推送
      --no-push        只提交，不 push
  -h, --help           显示帮助

示例:
  scripts/push_to_github.sh
  scripts/push_to_github.sh -m "add candidate validation linkage"
  scripts/push_to_github.sh -n
EOF
}

log() {
  printf '%s\n' "$*"
}

run() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] $*"
  else
    "$@"
  fi
}

require_git_repo() {
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    log "错误: 当前目录不是 git 仓库。"
    exit 1
  fi
}

require_clean_secrets() {
  local file
  while IFS= read -r file; do
    [[ -z "${file}" ]] && continue
    case "${file}" in
      .env|.env.*)
        if [[ "${file}" != ".env.example" ]]; then
          log "错误: 拒绝提交敏感文件 ${file}。请确认 .gitignore 已生效。"
          exit 1
        fi
        ;;
      *credentials*.json|*secret*.json|*.pem|*.key|id_rsa|id_ed25519)
        log "错误: 拒绝提交疑似凭证文件 ${file}。"
        exit 1
        ;;
    esac
  done
}

collect_changed_files() {
  {
    git diff --name-only
    git diff --cached --name-only
    git ls-files --others --exclude-standard
  } | awk 'NF && !seen[$0]++'
}

summarize_areas() {
  local files="$1"

  if [[ -z "${files}" ]]; then
    printf '%s' "workspace updates"
    return
  fi

  printf '%s\n' "${files}" | awk -F/ '
    {
      if (index($0, "/") == 0) {
        print $0
      } else {
        print $1
      }
    }
  ' | awk '!seen[$0]++' | paste -sd, - | sed 's/,/, /g'
}

generate_commit_message() {
  local files
  files="$(collect_changed_files)"
  local count
  count="$(printf '%s\n' "${files}" | awk 'NF { c++ } END { print c + 0 }')"
  local areas
  areas="$(summarize_areas "${files}")"

  if [[ -f "docs/progress.md" ]]; then
    local headline
    headline="$(
      awk '
        /^## / { in_section=1; next }
        in_section && /^- 完成 / { sub(/^- 完成 /, ""); print; exit }
        in_section && /^- / && !/^- 完成 / { sub(/^- /, ""); print; exit }
      ' docs/progress.md
    )"
    if [[ -n "${headline}" ]]; then
      printf '%s\n\nAuto-sync %s file(s): %s.' "${headline}" "${count}" "${areas}"
      return
    fi
  fi

  printf 'sync: update %s (%s file(s)).\n' "${areas}" "${count}"
}

has_local_changes() {
  [[ -n "$(git status --porcelain)" ]]
}

has_unpushed_commits() {
  local branch upstream
  branch="$(git rev-parse --abbrev-ref HEAD)"
  upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
  if [[ -z "${upstream}" ]]; then
    return 1
  fi
  git fetch origin "${branch}" >/dev/null 2>&1 || true
  [[ -n "$(git log "${upstream}..HEAD" --oneline 2>/dev/null || true)" ]]
}

ensure_remote() {
  if ! git remote get-url origin >/dev/null 2>&1; then
    log "错误: 未配置 origin 远程。请先执行 gh repo create 或 git remote add origin <url>。"
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--message)
      MESSAGE="${2:-}"
      shift 2
      ;;
    -n|--dry-run)
      DRY_RUN=1
      shift
      ;;
    --no-push)
      NO_PUSH=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      log "未知参数: $1"
      usage
      exit 1
      ;;
  esac
done

require_git_repo

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
REMOTE_URL="$(git remote get-url origin 2>/dev/null || echo '未配置')"

log "仓库: ${ROOT}"
log "分支: ${BRANCH}"
log "远程: ${REMOTE_URL}"
log

if ! has_local_changes; then
  if has_unpushed_commits; then
    log "没有新的本地变更，但存在未推送 commit。"
  else
    log "没有可提交的变更，也没有未推送 commit。"
    exit 0
  fi
else
  log "检测到以下变更:"
  git status --short
  log

  if [[ -z "${MESSAGE}" ]]; then
    MESSAGE="$(generate_commit_message)"
  fi

  log "Commit message:"
  printf '%s\n' "${MESSAGE}"
  log

  require_clean_secrets < <(collect_changed_files)

  run git add -A
  require_clean_secrets < <(git diff --cached --name-only)

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] git commit"
    log "[dry-run] 将提交的文件统计:"
    {
      git diff --name-only
      git diff --cached --name-only
      git ls-files --others --exclude-standard
    } | awk 'NF && !seen[$0]++' | wc -l | xargs -I{} log "  {} file(s)"
    git diff --stat 2>/dev/null || true
  else
    git commit -m "$(cat <<EOF
${MESSAGE}
EOF
)"
    log "已创建 commit: $(git log -1 --oneline)"
    log
  fi
fi

if [[ "${NO_PUSH}" -eq 1 ]]; then
  log "已跳过 push（--no-push）。"
  exit 0
fi

ensure_remote

log "推送到 origin/${BRANCH} ..."
run git push -u origin "HEAD:${BRANCH}"
log "完成。"
