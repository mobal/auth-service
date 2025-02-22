all: black flake pycodestyle sort test

black:
	pipenv run black ./

flake:
	pipenv run autoflake --in-place --recursive --remove-all-unused-imports --remove-unused-variables app/*.py tests/*.py

install:
	pipenv install --dev --python 3.12

mypy:
	pipenv run python -m mypy app/ --explicit-package-base

pycodestyle:
	pipenv run python -m pycodestyle --ignore=E501,W503 app/ tests/

sort:
	pipenv run python -m isort --atomic app/ tests/

test:
	pipenv run python -m pytest
