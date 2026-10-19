.PHONY: help install test process-data audit clean

PYTHON = ./.venv/Scripts/python.exe
PYTEST = $(PYTHON) -m pytest

help:
	@echo "SentinelX-Shift Build & Automation"
	@echo "  make install       - Install required packages in .venv"
	@echo "  make test          - Run pytest test suite"
	@echo "  make process-data  - Execute data cleaning and sampling pipeline"
	@echo "  make audit         - Run LOFO duplicate and leakage audit"
	@echo "  make clean         - Remove temporary and cache files"

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTEST) -v tests/

process-data:
	$(PYTHON) -m src.data.pipeline

audit:
	$(PYTHON) -m src.data.audit

lofo-split:
	$(PYTHON) -m src.eval.lofo

lofo-benchmark:
	$(PYTHON) -m src.eval.run_lofo_experiments

unsw-benchmark:
	$(PYTHON) -m src.eval.run_unsw_experiments

stability-benchmark:
	$(PYTHON) -m src.stability.run_stability_experiments

faithfulness:
	$(PYTHON) -m src.explain.faithfulness

clean:
	@powershell -Command "Get-ChildItem -Recurse -Filter '__pycache__' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Get-ChildItem -Recurse -Filter '.pytest_cache' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
