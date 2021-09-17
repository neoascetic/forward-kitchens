.PHONY: build


cleanup:
	rm -rf .aws-sam/build


build: cleanup
	sam build --parallel --cached --use-container

deploy: build
	sam deploy --guided

test:
	pip3 -q install -r orders/requirements.txt
	pip3 -q install -r requirements.dev.txt
	python3 -m doctest -v orders/*.py
	python3 -m pytest -vvv tests

