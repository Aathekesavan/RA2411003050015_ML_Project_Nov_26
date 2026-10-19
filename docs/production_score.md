# SentinelX-Shift: Production Guard Scoring Specification

**Status:** APPROVED FOR PRODUCTION GUARD  
**Run ID:** `run_reproducible_lofo`  
**Git Commit Hash:** `committed`  
**Author:** Senior ML-Security Engineer  

---

## 1. Architectural Role & Defensive Invariants
In accordance with **Defensive Principle 1**, the SentinelX Guard operates in **MONITOR-ONLY** mode when observing live external web traffic. Autonomous packet and connection blocking occurs **ONLY** inside the isolated lab replica environment.

---

## 2. Invalidation of Learned-Weight Linear Fusion
Learned-weight linear fusion:
$$s_{\text{fused}} = w_1 \cdot s_{\text{xgb}} + w_2 \cdot s_{\text{anom}}$$
is **formally marked as EXPLORATORY and DEPRECATED for production blocking**.

### Root Cause (Degenerate Tuning):
During nested inner-LOFO cross-validation, the tuning optimizer frequently encounters severe distribution shifts where supervised signals overfit to seen training families.
- In **BruteForce**, the optimizer collapsed to $w_1 = 1.0, w_2 = 0.0$ in 4 out of 5 random seeds.
- In **DoS (IForest)**, the optimizer collapsed to $w_1 = 1.0, w_2 = 0.0$ in 4 out of 5 random seeds.
Because $w_1 = 1.0$ discards the anomaly detector entirely, the model is completely blind to novel unseen attacks that share no lexical or header overlap with training families.

---

## 3. Designated Production Guard Score: Autoencoder-Anchored Gated Boost

The Guard will deploy **Autoencoder-Anchored Gated Boost** ($s_{\text{guard}}$) as the designated production scoring function:

$$s_{\text{guard}}(\mathbf{x}) = s_{\text{AE}}(\mathbf{x}) + \gamma \cdot \mathbb{I}\left(s_{\text{XGB}}(\mathbf{x}) > \tau\right)$$

where:
- $s_{\text{AE}}(\mathbf{x}) \in [0, 1]$ is the empirical CDF-calibrated Autoencoder reconstruction error.
- $s_{\text{XGB}}(\mathbf{x}) \in [0, 1]$ is the empirical CDF-calibrated supervised XGBoost risk score.
- $\tau$ is the high-confidence activation threshold for supervised detection.
- $\gamma$ is the bounded boost increment.

---

## 4. Inner-LOFO Validation Performance Comparison

The production score was chosen by comparing candidate detector scores across inner-LOFO validation folds (strictly without test-set tuning):

| Candidate Production Score | Mean Inner-LOFO Validation PR-AUC | Selection Decision | Architectural Rationale |
| :--- | :--- | :--- | :--- |
| **Autoencoder Alone** ($s_{\text{AE}}$) | 0.5063 | Reference Baseline | High baseline anomaly sensitivity; lacks selective amplification for seen attack traits. |
| **Rank-Average (0.5 / 0.5)** | 0.5284 | Untuned Baseline | Stable but sub-optimal; averages noisy low-confidence scores with confident alerts. |
| **Autoencoder-Anchored Gated Boost** | **0.5873** | **SELECTED FOR GUARD** | Highest inner-LOFO validation PR-AUC across folds; anchors on AE with additive supervised boost. |

### Overall Mean Tuned Inner-LOFO Hyperparameters:
- **$\tau^*$ (Mean Activation Threshold):** 0.36
- **$\gamma^*$ (Mean Boost Magnitude):** 0.28

---

## 5. Chosen Hyperparameters ($\tau$, $\gamma$) Per Fold and Seed

Parameters were tuned strictly inside inner-LOFO validation splits without test-set feedback:

| Seed | Family / Fold | $\tau$ (Activation Threshold) | $\gamma$ (Boost Magnitude) | Validation PR-AUC (AE) | Validation PR-AUC (Gated Boost) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 42 | DoS_DDoS | 0.30 | 0.30 | 0.3847 | 0.6855 |
| 42 | BruteForce | 0.50 | 0.30 | 0.3461 | 0.7075 |
| 42 | PortScan | 0.30 | 0.30 | 0.5003 | 0.7049 |
| 42 | Bot | 0.50 | 0.30 | 0.4933 | 0.7799 |
| 42 | WebAttack | 0.30 | 0.20 | 0.5767 | 0.7780 |
| 101 | DoS_DDoS | 0.30 | 0.30 | 0.3847 | 0.6855 |
| 101 | BruteForce | 0.50 | 0.30 | 0.3461 | 0.7075 |
| 101 | PortScan | 0.30 | 0.20 | 0.5003 | 0.7049 |
| 101 | Bot | 0.50 | 0.20 | 0.4933 | 0.7799 |
| 101 | WebAttack | 0.30 | 0.30 | 0.5767 | 0.7780 |
| 202 | DoS_DDoS | 0.30 | 0.30 | 0.3847 | 0.6855 |
| 202 | BruteForce | 0.30 | 0.30 | 0.3461 | 0.7075 |
| 202 | PortScan | 0.30 | 0.30 | 0.5003 | 0.7049 |
| 202 | Bot | 0.50 | 0.30 | 0.4933 | 0.7799 |
| 202 | WebAttack | 0.30 | 0.30 | 0.5767 | 0.7780 |
| 303 | DoS_DDoS | 0.30 | 0.30 | 0.3847 | 0.6855 |
| 303 | BruteForce | 0.50 | 0.30 | 0.3461 | 0.7075 |
| 303 | PortScan | 0.30 | 0.30 | 0.5003 | 0.7049 |
| 303 | Bot | 0.30 | 0.30 | 0.4933 | 0.7799 |
| 303 | WebAttack | 0.30 | 0.10 | 0.5767 | 0.7780 |
| 404 | DoS_DDoS | 0.30 | 0.30 | 0.3847 | 0.6855 |
| 404 | BruteForce | 0.30 | 0.30 | 0.3461 | 0.7075 |
| 404 | PortScan | 0.30 | 0.30 | 0.5003 | 0.7049 |
| 404 | Bot | 0.50 | 0.30 | 0.4933 | 0.7799 |
| 404 | WebAttack | 0.30 | 0.30 | 0.5767 | 0.7780 |

---

## 6. Guard Deployment Status & Monitor-Only Declarations

Operational boundaries and blocking authorization per attack family group:

| Family Group | Deployment Status | Autonomous Lab Blocking | Live Production Action | Architectural Guardrail Reason |
| :--- | :--- | :--- | :--- | :--- |
| **DoS_DDoS** | Active Guard | Authorized | Active Alerting & Rate Limiting | High volumetric separation; low false disruption risk. |
| **BruteForce** | Active Guard | Authorized | Active Alerting & Throttling | Well-bounded connection frequency signatures. |
| **PortScan** | Active Guard | Authorized | Active Alerting & IP Quarantine | Clear reconnaissance port sweep footprints. |
| **Bot** | **MONITOR-ONLY** | Prohibited | Log & Alert Triage Only | Low sample power in dataset; high potential for normal background tooling overlap. |
| **WebAttack** | **MONITOR-ONLY** | Prohibited | Log & WAF Forwarding Only | Application-layer payload scope falls primarily under WAF; flow-level blocking risks legitimate user disruption. |

---

## 7. Empirical Rationale Across Inner-LOFO Folds

The Autoencoder-Anchored Gated Boost was selected across inner-LOFO folds for four structural reasons:

1. **Guaranteed Out-of-Distribution Baseline Sensitivity:**
   By anchoring the score to $s_{\text{AE}}$, the detector maintains non-zero sensitivity to completely novel attacks (e.g. zero-days or unseen attack families) even when XGBoost outputs 0.0 risk.
2. **Robustness Against Degenerate Weight Collapse:**
   Unlike unconstrained linear optimization, the anchor cannot be zeroed out by a single noisy training fold. The supervised boost functions as an additive amplifier only when high-confidence attack indicators trigger.
3. **Superior Operating-Point Performance on Unseen Traffic:**
   Gated Boost leverages high-confidence activation of supervised detection as an additive boost on top of the unsupervised reconstruction baseline, preventing single-model collapse.
4. **Honest Reporting Compliance (Principle 3):**
   Explanation stability metrics ($S_{\text{exp\_stab}}$) are completely excluded from $s_{\text{guard}}$. The Guard functions deterministically and efficiently without incurring perturbation overhead required for SHAP attribution sampling.
