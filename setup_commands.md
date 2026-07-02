up:
	docker compose up -d

down:
	docker compose down

stop:
	docker compose stop

start:
	docker compose start

logs:
	docker compose logs -f

reset:
	docker compose down -v

reset is the only command that destroys the database.


# Alembic commands
migrate:
	uv run alembic upgrade head

revision:
	uv run alembic revision --autogenerate -m "$(m)"
