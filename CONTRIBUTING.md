# Contributing

Thanks for taking the time to contribute. This project aims to be stable,
secure, and easy to operate in production.

## Ways to Contribute

- Bug reports and feature requests via GitHub Issues
- Documentation improvements
- Code changes, packaging, and CI improvements

## Development Setup

Prereqs:
- Python 3.10+
- Poetry
- Docker Engine (for integration tests)

Install dependencies:

```bash
poetry install
```

Run locally:

```bash
poetry run docker-healthcheck-exporter
```

If you want to test against a real Docker host, ensure you have access to
`/var/run/docker.sock` and that your user is in the `docker` group.

## Lint and Format

```bash
make lint
make format
```

## Tests and Coverage

```bash
make test
```

Coverage is enforced in CI (see `ci.yml`). Locally:

```bash
poetry run pytest --cov=docker_healthcheck_exporter --cov-report=term-missing
```

Docker integration tests require access to the local Docker Engine and will be
skipped if Docker is not available or no suitable local image exists.

## Pull Request Guidelines

- Keep changes focused and easy to review
- Prefer small, well-scoped commits
- Update documentation when behavior changes
- Add tests for new behavior or bug fixes

## Security Issues

Please do not open public issues for security problems. Follow the process in
`SECURITY.md`.
