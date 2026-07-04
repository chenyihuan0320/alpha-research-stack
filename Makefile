.PHONY: check status progress tree push-github

check:
	./scripts/dev_check.sh

push-github:
	./scripts/push_to_github.sh

status:
	git status --short
	git diff --stat

progress:
	@cat docs/progress.md

tree:
	@find . \
		-path '*/.git' -prune -o \
		-path './.venv' -prune -o \
		-path '*/__pycache__' -prune -o \
		-path './.pytest_cache' -prune -o \
		-path '*.egg-info' -prune -o \
		-path './outputs/dev_checks' -prune -o \
		-print | LC_ALL=C sort
