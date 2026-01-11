PROJECT_NAME := docker-healthcheck-exporter
IMAGE_NAME := ghcr.io/gladioluss/docker_healthcheck_exporter

VERSION ?= $(shell git describe --tags --dirty --always 2>/dev/null || echo dev)
COMMIT  := $(shell git rev-parse --short HEAD)
DATE    := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")

DEB_OUT  := $(PROJECT_NAME)_$(VERSION)_amd64.deb

PLATFORMS := linux/amd64,linux/arm64

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  make deb-build          Build local binary via PyInstaller"
	@echo "  make deb-run            Running local binary"
	@echo "  make build              Build local docker image"
	@echo "  make run                Run container locally"
	@echo "  make run-local          Run exporter locally (poetry)"
	@echo "  make tag                Create git tag VERSION=x.y.z"
	@echo "  make release            Tag + push + docker push"
	@echo "  make lint               Run Ruff lint"
	@echo "  make format             Run Ruff formatter"
	@echo "  make test               Run pytest"
	@echo "  make coverage           Run coverage info"

.PHONY: deb-build
deb-build:
	@echo ">>> Building standalone binary via PyInstaller"
	poetry run pyinstaller -F -n docker-healthcheck-exporter main.py --clean
	@ls -la dist/docker-healthcheck-exporter

.PHONY: deb-run
deb-run:
	@echo ">>> Running local binary"
	./dist/docker-healthcheck-exporter

.PHONY: build
build:
	docker build \
		--build-arg VERSION=$(VERSION) \
		--build-arg VCS_REF=$(COMMIT) \
		--build-arg BUILD_DATE=$(DATE) \
		-t $(PROJECT_NAME):$(VERSION) \
		.

.PHONY: run
run:
	mkdir -p ./examples/textfile
	docker run --rm -it \
		-p 9102:9102 \
		-v /var/run/docker.sock:/var/run/docker.sock:ro \
		-v "$(PWD)/examples/textfile:/examples/textfile" \
		-e METRICS_FILE="/examples/textfile/docker_healthcheck_exporter.prom" \
		$(PROJECT_NAME):$(VERSION) \

.PHONY: run-local
run-local:
	poetry run docker-healthcheck-exporter

.PHONY: lint
lint:
	poetry run ruff check .

.PHONY: format
format:
	poetry run ruff format .

.PHONY: test
test:
	poetry run pytest

.PHONY: coverage
coverage:
	poetry run pytest --cov=docker_healthcheck_exporter --cov-report=term-missing

.PHONY: tag
tag:
	@if [ -z "$(VERSION)" ]; then echo "VERSION is required"; exit 1; fi
	git tag -a v$(VERSION) -m "Release v$(VERSION)"

.PHONY: release
release: tag
	git push origin v$(VERSION)
	$(MAKE) push
