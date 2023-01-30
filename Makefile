black:
	python3 -m pipenv run black --skip-string-normalization app/ tests/

deploy:
	python3 -m pipenv run sls deploy

install:
	python3 -m pipenv install --dev

pycodestyle:
	python3 -m pipenv run pycodestyle --ignore=E501,W503 app/ tests/

sort:
	python3 -m pipenv run python -m isort --atomic app/ tests/
test:
	python3 -m pipenv run pytest --cache-clear --cov-report=term --cov=app/
