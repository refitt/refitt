# REFITT developer convenience targets. Mirrors what CI does, for local parity.
# Native deps (psycopg2->libpq, confluent-kafka->librdkafka) must be present to `sync`:
#   macOS:  brew install libpq librdkafka   (and see .env for the build-path exports)
#   Debian: apt-get install libpq-dev librdkafka-dev

.DEFAULT_GOAL := help
.PHONY: help sync test client-boundary metadata build docker apptainer docs clean

help:  ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

sync:  ## Install/refresh the workspace environment
	uv sync --all-packages

test:  ## Run the test suite (requires a seeded Postgres; see tests.yml)
	uv run pytest -v

client-boundary:  ## Assert refitt-client installs wheel-only with no data-science deps (invariant §2)
	rm -rf dist && uv build --all-packages --wheel --no-sources --out-dir dist
	uv venv .venv-client
	VIRTUAL_ENV=.venv-client uv pip install --only-binary=:all: --find-links dist refitt-client
	@VIRTUAL_ENV=.venv-client uv pip list --format=freeze | cut -d= -f1 | tr 'A-Z' 'a-z' | \
		grep -Eqx 'refitt-data|numpy|pandas|scipy|sqlalchemy|astropy' \
		&& { echo "FAIL: client boundary violated (invariant §2)"; exit 1; } \
		|| echo "OK: client is wheel-only with no data-science deps"

metadata:  ## Build all distributions and validate packaging metadata
	uv build --all-packages --no-sources
	uvx --from 'validate-pyproject[all]' validate-pyproject pyproject.toml py/libs/*/pyproject.toml py/apps/*/pyproject.toml
	uvx twine check --strict dist/*

build:  ## Build sdist + wheel for all distributions
	uv build --all-packages --no-sources

docker:  ## Build the container image locally
	docker build -t refitt:local .

apptainer:  ## Build the Apptainer image locally
	apptainer build refitt.sif Apptainer --build-arg VERSION=$(shell git describe --tags --always 2>/dev/null || echo dev)

docs:  ## Build the website docs
	uv sync --group docs && uv run sphinx-build -b html docs/website/source docs/website/build/html

clean:  ## Remove build artifacts
	rm -rf dist build .venv-client refitt.sif
