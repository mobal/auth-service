all:


black:
	python3 -m pipenv run python -m black --skip-string-normalization app/ tests/

deploy:
	python3 -m pipenv run sls deploy

flake:
	python3 -m pipenv run python -m autoflake --in-place --remove-unused-variables app/*.py tests/*.py

install:
	python3 -m pipenv install --dev
	npm i

pycodestyle:
	python3 -m pipenv run python -m pycodestyle --ignore=E501,W503 app/ tests/

sort:
	python3 -m pipenv run python -m isort --atomic app/ tests/

test:
	python3 -m pipenv run python -m pytest