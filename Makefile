.PHONY: install probe preprocess alpha test-local run

install:
	bash scripts/00_install_deps_ubuntu24.sh

probe:
	bash scripts/02_probe_uploaded_media.sh

preprocess:
	bash scripts/03_preprocess_all.sh

alpha:
	bash scripts/04_validate_alpha.sh

test-local:
	bash scripts/05_run_stdin_local_test.sh

run:
	. .venv/bin/activate && python -m bili_songbot
