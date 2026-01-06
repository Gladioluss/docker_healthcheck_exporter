# Contributing

Thanks for considering a contribution to Docker Healthcheck Exporter!

## Ways to Contribute

- Report bugs and request features via GitHub Issues
- Improve documentation
- Submit code changes and packaging improvements

## Development Setup

Prereqs:
- Python 3.10+
- Poetry
- Docker Engine (for live Docker API tests)

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

## Tests

There are currently no automated tests in this repository. If you add tests,
please document how to run them here.

## Coding Guidelines

- Keep changes focused and easy to review
- Prefer small, well-scoped commits
- Update documentation when behavior changes

## Security Issues

Please do not open public issues for security problems. Follow the process in
`SECURITY.md`.
