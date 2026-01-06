PROJECT_NAME := docker-healthcheck-exporter
IMAGE_NAME := ghcr.io/gladioluss/docker_healthcheck_exporter

VERSION ?= $(shell git describe --tags --dirty --always 2>/dev/null || echo dev)
COMMIT  := $(shell git rev-parse --short HEAD)
DATE    := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")

PLATFORMS := linux/amd64,linux/arm64

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  make build              Build local docker image"
	@echo "  make run                Run container locally"
	@echo "  make push               Build & push multi-arch image"
	@echo "  make tag                Create git tag VERSION=x.y.z"
	@echo "  make release             Tag + push + docker push"

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
	docker run --rm -it \
		-p 9102:9102 \
		-v /var/run/docker.sock:/var/run/docker.sock:ro \
		$(PROJECT_NAME):$(VERSION)

.PHONY: push
push:
	docker buildx build \
		--platform $(PLATFORMS) \
		--build-arg VERSION=$(VERSION) \
		--build-arg VCS_REF=$(COMMIT) \
		--build-arg BUILD_DATE=$(DATE) \
		-t $(IMAGE_NAME):$(VERSION) \
		-t $(IMAGE_NAME):latest \
		--push \
		.

.PHONY: tag
tag:
	@if [ -z "$(VERSION)" ]; then echo "VERSION is required"; exit 1; fi
	git tag -a v$(VERSION) -m "Release v$(VERSION)"

.PHONY: release
release: tag
	git push origin v$(VERSION)
	$(MAKE) push
