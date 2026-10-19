# SentinelX-Shift

> **Explanation-Aware Intrusion Detection and Protection Layer for Web Services Evaluated on Genuinely Unseen Attack Families**

---

## 1. Principles (Strict & Non-Negotiable)

1. **Defensive Only**: Automated traffic mitigation/blocking occurs **only** on isolated lab replicas. Production and real endpoints operate strictly in monitor-and-alert mode.
2. **Leakage-Free Protocol**: Evaluation enforces Leave-One-Attack-Family-Out (LOFO). The test set contains strictly benign flows and the single held-out attack family; the training set never observes that family. Deduplication is performed prior to splitting; encoders and scalers are fitted exclusively on training splits.
3. **Honest Reporting**: Explanation stability is tracked and reported as an empirical research signal regardless of whether it aids discrimination. Mitigation logic operates on the fused score without depending on explanation stability.
4. **Flow-Level Behavioral Scope**: SentinelX inspects netflow metrics (packet timings, lengths, inter-arrival times, flags). Application-layer payload inspection (SQLi, XSS) remains within the WAF domain.
5. **Reproducibility**: Deterministic random seeds, centralized configuration (`configs/config.yaml`), automated test suites, and strict execution logging.

---

## 2. Repository Layout

```text
sentinelx/
├── configs/          # Experiment configuration (config.yaml)
├── data/
│   ├── raw/          # Original CIC-IDS2017 & benchmark files
│   └── processed/    # Sanitized, deduplicated, sampled datasets
├── src/
│   ├── data/         # Loader, cleaner, leakage auditor, pipeline
│   ├── features/     # Feature engineering, scaling, transformations
│   ├── models/       # Supervised & anomaly models
│   ├── explain/      # Local explanations (SHAP / TreeSHAP)
│   ├── stability/    # Explanation stability calculations
│   ├── fusion/       # Score fusion & calibration
│   ├── alerts/       # Alert generation & triage
│   ├── guard/        # Lab replica mitigation policies
│   ├── api/          # FastAPI service
│   └── eval/         # LOFO evaluation matrix & metrics
├── dashboard/        # Dashboard (HTML + Chart.js)
├── lab/              # Docker Compose lab replica & traffic injection
├── notebooks/        # Analysis and exploration
├── tests/            # Unit and integration tests
├── results/          # Experiment output metrics and charts
└── docs/             # Data cards, threat models, architecture docs
```

---

## 3. Environment & Python Specification

- **Host Python Version**: `Python 3.12.10` (Verified in active `.venv`)
- **Key Pinned Dependencies**:
  - `numpy==2.3.4`, `pandas==2.3.3`, `scipy==1.17.1`, `scikit-learn==1.8.0`
  - `xgboost==3.4.1`, `shap==0.53.0`, `pydantic==2.12.5`, `fastapi==0.135.1`
  - `pytest==9.1.1`, `matplotlib==3.10.7`, `joblib==1.5.3`

---

## 4. Quick Start

### Setup Environment
```bash
# Using the pre-configured virtual environment
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Run Tests
```bash
make test
# or
.\.venv\Scripts\python.exe -m pytest -v tests/
```

### Process Data & Run Leakage Audit
```bash
make process-data
make audit
```

### Primary Datasets & Artifacts
- **Cleaned 60k Sample**: [`data/processed/cicids2017_sample60k.parquet`](file:///d:/sentinelx/data/processed/cicids2017_sample60k.parquet)
- **Data Card**: [`docs/data_card.md`](file:///d:/sentinelx/docs/data_card.md)
- **Leakage Audit Contrast**: [`results/leakage_audit.csv`](file:///d:/sentinelx/results/leakage_audit.csv)
- **LOFO Split Manifests**: [`results/manifests/`](file:///d:/sentinelx/results/manifests/)

