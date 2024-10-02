unit-tests:
	@echo "========================"
	@echo "Run unit tests"
	@echo "========================"
	docker compose -f docker-compose-test.yaml run --rm tests \
	/bin/bash -c \
	"python -m pytest tests/unit \
	-s \
	-x \
	-vv \
	--color=yes \
	--cov=/app/src \
	--cov-report=html:/app/reports/coverage \
	--cov-report=xml:/app/reports/coverage/coverage.xml \
	--cov-report=term-missing"