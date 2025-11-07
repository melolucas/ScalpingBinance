.PHONY: run dry stats rank test docker clean

run:
	python -m app.main run

dry:
	python -m app.main run --dry-run

stats:
	python -m app.main stats

rank:
	python -m app.main rank

test:
	pytest -q

docker:
	docker compose up --build -d

clean:
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov

