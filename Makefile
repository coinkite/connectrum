# This Makefile is only useful for maintainers of this package.

all:
	echo Targets: build, tag, upload

.PHONY: build
build:
	python3 setup.py sdist

.PHONY: upload
upload: FNAME := $(shell ls -1t dist/connectrum-*gz | head -1)
upload:
	gpg -u 5A2A5B10 --detach-sign -a $(FNAME)
	twine upload $(FNAME)*

.PHONY: tag
tag: VER := $(shell python -c 'import connectrum; print(connectrum.__version__)')
tag:
	git tag v$(VER) -am "New release"
	git push --tags

