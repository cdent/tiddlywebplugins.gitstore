.PHONY: release dist readme test clean

release: clean test
	git diff --exit-code # ensure there are no uncommitted changes
	git tag -a \
			-m v`python -c 'from setup import META; print META.__version__'` \
			v`python -c 'from setup import META; print META.__version__'`
	git push origin master --tags
	# XXX: duplicates dist target
	rm -r dist || true
	python setup.py sdist upload

dist: clean test
	rm -r dist || true
	python setup.py sdist

test: clean
	py.test -x --tb=short test

clean:
	find . -name "*.pyc" | xargs rm || true
	rm -rf tiddlywebplugins.gitstore.egg-info
	rm -rf html .figleaf coverage.lst # figleaf
	rm -rf htmlcov .coverage # coverage
	rm -rf test/__pycache__ # pytest
