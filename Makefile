.PHONY: help install test verify demo process-data audit clean

PYTHON = ./.venv/Scripts/python.exe
PYTEST = $(PYTHON) -m pytest

help:
	@echo "SentinelX-Shift Build & Automation"
	@echo "  make install       - Install required packages in .venv"
	@echo "  make test          - Run pytest test suite"
	@echo "  make verify        - Run unified release & artifact verification suite"
	@echo "  make demo          - Run Phase 3 web log & WAF correlation demo"
	@echo "  make process-data  - Execute data cleaning and sampling pipeline"
	@echo "  make audit         - Run LOFO duplicate and leakage audit"
	@echo "  make clean         - Remove temporary and cache files"

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTEST) -v tests/

verify:
	$(PYTHON) scripts/verify_release.py

demo:
	$(PYTHON) scripts/demo_phase3.py

replay-shadow:
	$(PYTHON) -c "from src.observability.replay import run_shadow_replay; import pprint; pprint.pprint(run_shadow_replay(dataset_source='synthetic', max_flows=50))"


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

report:
	$(PYTHON) -m src.eval.generate_reports
	$(PYTHON) scripts/generate_cross_dataset.py

serve:
	$(PYTHON) -m uvicorn src.api.service:app --host 127.0.0.1 --port 8000

dashboard: serve

clean:
	@powershell -Command "Get-ChildItem -Recurse -Filter '__pycache__' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Get-ChildItem -Recurse -Filter '.pytest_cache' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"

