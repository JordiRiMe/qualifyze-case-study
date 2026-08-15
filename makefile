# Access database
access-db:
	sudo docker compose exec db psql -U qualifyze -d qualifyze

# Scripts: Notice these commands are created in the pyproject.toml
## Init DB
init-db:
	uv run init-db
## Ingest FDA data
ingest-fda:
	uv run ingest-fda
## Ingest Warning Letters
ingest-warning-letters:
	uv run ingest-warning-letters
## Build model features
build-features:
	uv run build-features