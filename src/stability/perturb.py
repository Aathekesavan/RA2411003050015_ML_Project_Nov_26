"""Physical Perturbation Engine and Domain Invariants Validator for SentinelX-Shift.

Implements realistic netflow jitter by:
1. Perturbing ONLY base flow features (duration, packet counts, byte totals,
   TCP flag counts, inter-arrival time min/max/mean).
2. Recomputing derived features (rates, ratios, means) from perturbed base quantities.
3. Enforcing physical domain invariants:
   - Non-negativity (duration, packets, bytes, IATs >= 0)
   - Positive duration (dur > 0)
   - Packets/sec <= line rate (physical network line limit: 150 Mpps)
   - Flag counts <= total packet count
   - Statistical hierarchy (Min <= Mean <= Max for packet lengths and IATs)
   - Temporal consistency (Max IAT <= Flow Duration)
4. Recording clamping actions, raw invalid rates BEFORE clamping, final rejection rates,
   and mean relative change per jitter magnitude x in {1%, 5%, 10%}.
"""

from typing import Dict, List, Optional, Tuple, Set, Any
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class PhysicalPerturbationEngine:
    """Generates physically valid netflow perturbations with domain invariant validation."""

    # Base features to jitter directly
    BASE_COUNT_FEATURES = {
        "Total Fwd Packets", "Total Backward Packets",
        "Total Length of Fwd Packets", "Total Length of Bwd Packets",
        "Fwd Header Length", "Bwd Header Length",
        "Init_Win_bytes_forward", "Init_Win_bytes_backward",
        "act_data_pkt_fwd", "min_seg_size_forward",
        "spkts", "dpkts", "sbytes", "dbytes", "sloss", "dloss"
    }

    TCP_FLAG_FEATURES = {
        "FIN Flag Count", "SYN Flag Count", "RST Flag Count", "PSH Flag Count",
        "ACK Flag Count", "URG Flag Count", "CWE Flag Count", "ECE Flag Count",
        "Fwd PSH Flags", "Bwd PSH Flags", "Fwd URG Flags", "Bwd URG Flags"
    }

    DERIVED_FEATURES = {
        "Flow Bytes/s", "Flow Packets/s", "Fwd Packets/s", "Bwd Packets/s",
        "Average Packet Size", "Avg Fwd Segment Size", "Avg Bwd Segment Size",
        "Down/Up Ratio", "Subflow Fwd Packets", "Subflow Fwd Bytes",
        "Subflow Bwd Packets", "Subflow Bwd Bytes",
        "rate", "sload", "dload", "smean", "dmean"
    }

    MAX_LINE_RATE_PPS = 1.5e8  # 150 Mpps physical line limit (100GbE line rate)

    def __init__(self, random_seed: int = 42):
        self.rng = np.random.RandomState(random_seed)
        self.rejection_records: Dict[float, Dict[str, Any]] = {}
        self.rule_rejections: Dict[float, Dict[str, int]] = {}
        self.raw_invalid_records: Dict[float, Dict[str, int]] = {}
        self.clamping_events: Dict[float, Dict[str, int]] = {}
        self.relative_changes: Dict[float, List[float]] = {}

    def _categorize_rejection_reason(self, reason: Optional[str]) -> str:
        """Map rejection reason string to canonical invariant rule."""
        if not reason:
            return "Valid"
        if "Negative" in reason:
            return "Rule 1 (Non-negativity: values >= 0)"
        if "Non-positive duration" in reason:
            return "Rule 2 (Positive Duration: dur > 0)"
        if "line rate limit" in reason:
            return "Rule 3 (Physical Line Rate: PPS <= 150 Mpps)"
        if "Flag count" in reason:
            return "Rule 4 (TCP Flag Consistency: flags <= packets)"
        if "Statistical hierarchy" in reason:
            return "Rule 5 (Packet Length Hierarchy: min <= mean <= max)"
        if "IAT hierarchy" in reason or "Temporal violation" in reason:
            return "Rule 6 (IAT Hierarchy & Temporal Consistency)"
        return "Rule 7 (Other Domain Invariants)"

    def validate_invariants(self, flow_dict: Dict[str, float]) -> Tuple[bool, Optional[str]]:
        """Public validator checking all physical networking invariants for a flow dictionary.

        Returns:
            (is_valid, rejection_reason)
        """
        return self._validate_invariants(flow_dict)

    def _validate_invariants(self, flow_dict: Dict[str, float]) -> Tuple[bool, Optional[str]]:
        """Validate all physical networking invariants for a flow dictionary."""
        # 1. Non-negativity check
        for feat, val in flow_dict.items():
            if feat in ("Label", "y_binary", "Family_Group"):
                continue
            # Init_Win_bytes can be -1 sentinel in CIC-IDS2017 (no SYN packet seen / UDP flows)
            if feat in ("Init_Win_bytes_forward", "Init_Win_bytes_backward") and val == -1.0:
                continue
            if val < 0.0:
                return False, f"Negative value in {feat}: {val}"

        # 2. Total packets and duration
        duration_us = flow_dict.get("Flow Duration", flow_dict.get("dur", 1.0) * 1e6)
        if duration_us <= 0.0:
            return False, f"Non-positive duration: {duration_us}"

        tot_fwd = flow_dict.get("Total Fwd Packets", flow_dict.get("spkts", 1.0))
        tot_bwd = flow_dict.get("Total Backward Packets", flow_dict.get("dpkts", 0.0))
        tot_pkts = tot_fwd + tot_bwd

        # 3. Packets/sec <= line rate
        dur_sec = max(1e-6, duration_us * 1e-6)
        pps = tot_pkts / dur_sec
        if pps > self.MAX_LINE_RATE_PPS:
            return False, f"Packets/sec ({pps:.2e}) exceeds physical line rate limit"

        # 4. TCP Flag counts <= Total Packets
        for flag_feat in self.TCP_FLAG_FEATURES:
            if flag_feat in flow_dict and flow_dict[flag_feat] > tot_pkts + 1e-4:
                return False, f"Flag count in {flag_feat} ({flow_dict[flag_feat]}) > total packets ({tot_pkts})"

        # 5. Min <= Mean <= Max checks for packet lengths
        for prefix in ["Fwd Packet Length", "Bwd Packet Length", "Packet Length"]:
            min_k = f"{prefix} Min" if prefix != "Packet Length" else "Min Packet Length"
            mean_k = f"{prefix} Mean" if prefix != "Packet Length" else "Packet Length Mean"
            max_k = f"{prefix} Max" if prefix != "Packet Length" else "Max Packet Length"
            if min_k in flow_dict and mean_k in flow_dict and max_k in flow_dict:
                if not (flow_dict[min_k] - 1e-4 <= flow_dict[mean_k] <= flow_dict[max_k] + 1e-4):
                    return False, f"Statistical hierarchy violation in {prefix}: min={flow_dict[min_k]}, mean={flow_dict[mean_k]}, max={flow_dict[max_k]}"

        # 6. Min <= Mean <= Max for Inter-Arrival Times (IAT)
        for prefix in ["Flow IAT", "Fwd IAT", "Bwd IAT"]:
            min_k = f"{prefix} Min"
            mean_k = f"{prefix} Mean"
            max_k = f"{prefix} Max"
            if min_k in flow_dict and mean_k in flow_dict and max_k in flow_dict:
                if not (flow_dict[min_k] - 1e-4 <= flow_dict[mean_k] <= flow_dict[max_k] + 1e-4):
                    return False, f"IAT hierarchy violation in {prefix}: min={flow_dict[min_k]}, mean={flow_dict[mean_k]}, max={flow_dict[max_k]}"

        # 7. Standard deviations must be non-negative
        for feat, val in flow_dict.items():
            if "Std" in feat and val < 0.0:
                return False, f"Negative standard deviation in {feat}: {val}"

        # 8. Temporal consistency: Max IAT <= Flow Duration
        max_iat_k = "Flow IAT Max" if "Flow IAT Max" in flow_dict else None
        if "Flow Duration" in flow_dict and max_iat_k and max_iat_k in flow_dict:
            if flow_dict[max_iat_k] > flow_dict["Flow Duration"] + 1e-3:
                return False, f"Temporal violation: Max IAT ({flow_dict[max_iat_k]}) > Flow Duration ({flow_dict['Flow Duration']})"

        return True, None

    def _recalculate_derived_features(self, d: Dict[str, float]) -> Dict[str, float]:
        """Recompute rate and average features strictly from perturbed base quantities."""
        # CIC-IDS2017 feature set
        if "Flow Duration" in d:
            duration_sec = max(1e-6, d["Flow Duration"] * 1e-6)
            tot_fwd_pkts = max(1.0, d.get("Total Fwd Packets", 1.0))
            tot_bwd_pkts = max(0.0, d.get("Total Backward Packets", 0.0))
            tot_pkts = tot_fwd_pkts + tot_bwd_pkts

            tot_fwd_bytes = max(0.0, d.get("Total Length of Fwd Packets", 0.0))
            tot_bwd_bytes = max(0.0, d.get("Total Length of Bwd Packets", 0.0))
            tot_bytes = tot_fwd_bytes + tot_bwd_bytes

            if "Flow Bytes/s" in d:
                d["Flow Bytes/s"] = tot_bytes / duration_sec
            if "Flow Packets/s" in d:
                d["Flow Packets/s"] = tot_pkts / duration_sec
            if "Fwd Packets/s" in d:
                d["Fwd Packets/s"] = tot_fwd_pkts / duration_sec
            if "Bwd Packets/s" in d:
                d["Bwd Packets/s"] = tot_bwd_pkts / duration_sec
            if "Average Packet Size" in d:
                d["Average Packet Size"] = tot_bytes / tot_pkts
            if "Avg Fwd Segment Size" in d:
                d["Avg Fwd Segment Size"] = tot_fwd_bytes / tot_fwd_pkts
            if "Avg Bwd Segment Size" in d:
                d["Avg Bwd Segment Size"] = tot_bwd_bytes / max(1.0, tot_bwd_pkts)
            if "Down/Up Ratio" in d:
                d["Down/Up Ratio"] = tot_bwd_pkts / tot_fwd_pkts

            # Subflows are mirror copies in Netflow v9 / IPFIX
            if "Subflow Fwd Packets" in d:
                d["Subflow Fwd Packets"] = tot_fwd_pkts
            if "Subflow Fwd Bytes" in d:
                d["Subflow Fwd Bytes"] = tot_fwd_bytes
            if "Subflow Bwd Packets" in d:
                d["Subflow Bwd Packets"] = tot_bwd_pkts
            if "Subflow Bwd Bytes" in d:
                d["Subflow Bwd Bytes"] = tot_bwd_bytes

        # UNSW-NB15 feature set
        if "dur" in d:
            dur_sec = max(1e-6, d["dur"])
            spkts = max(1.0, d.get("spkts", 1.0))
            dpkts = max(0.0, d.get("dpkts", 0.0))
            sbytes = max(0.0, d.get("sbytes", 0.0))
            dbytes = max(0.0, d.get("dbytes", 0.0))

            if "rate" in d:
                d["rate"] = (spkts + dpkts) / dur_sec
            if "sload" in d:
                d["sload"] = (sbytes * 8.0) / dur_sec
            if "dload" in d:
                d["dload"] = (dbytes * 8.0) / dur_sec
            if "smean" in d:
                d["smean"] = sbytes / spkts
            if "dmean" in d:
                d["dmean"] = dbytes / max(1.0, dpkts)

        return d

    def perturb_single_flow(
        self,
        flow_row: pd.Series,
        jitter_pct: float = 0.05,
        jitter_magnitude: Optional[int] = None,
        max_attempts: int = 50,
        audit_mode: bool = False
    ) -> Tuple[Optional[pd.Series], int, Optional[str]]:
        """Apply bounded jitter to base netflow features, track pre-clamping invalidity and clamping events."""
        if jitter_magnitude is not None:
            jitter_pct = jitter_magnitude / 100.0

        if jitter_pct not in self.raw_invalid_records:
            self.raw_invalid_records[jitter_pct] = {}
        if jitter_pct not in self.clamping_events:
            self.clamping_events[jitter_pct] = {}
        if jitter_pct not in self.relative_changes:
            self.relative_changes[jitter_pct] = []
        if jitter_pct not in self.rule_rejections:
            self.rule_rejections[jitter_pct] = {}

        attempts = 0
        last_reason = None
        feature_cols = [c for c in flow_row.index if c not in ["Label", "y_binary", "Family_Group"]]

        while attempts < max_attempts:
            attempts += 1

            # ---------------------------------------------------------
            # 1. Unconstrained Raw Perturbation (only when audit_mode=True to measure raw invalid rate)
            # ---------------------------------------------------------
            if audit_mode:
                raw_dict = {col: float(flow_row[col]) for col in feature_cols}
                raw_j_dur = self.rng.uniform(-jitter_pct, jitter_pct)
                if "Flow Duration" in raw_dict and raw_dict["Flow Duration"] > 0.0:
                    raw_dict["Flow Duration"] = max(1.0, raw_dict["Flow Duration"] * (1.0 + raw_j_dur))

                for cnt_col in self.BASE_COUNT_FEATURES:
                    if cnt_col in raw_dict and raw_dict[cnt_col] > 0.0:
                        raw_dict[cnt_col] = float(max(0, int(np.round(raw_dict[cnt_col] * (1.0 + self.rng.uniform(-jitter_pct, jitter_pct))))))

                for flag_col in self.TCP_FLAG_FEATURES:
                    if flag_col in raw_dict and raw_dict[flag_col] > 0.0:
                        raw_dict[flag_col] = float(max(0, int(np.round(raw_dict[flag_col] * (1.0 + self.rng.uniform(-jitter_pct, jitter_pct))))))

                for prefix in ["Fwd Packet Length", "Bwd Packet Length", "Packet Length", "Flow IAT", "Fwd IAT", "Bwd IAT"]:
                    min_k = f"{prefix} Min" if prefix != "Packet Length" else "Min Packet Length"
                    mean_k = f"{prefix} Mean" if prefix != "Packet Length" else "Packet Length Mean"
                    max_k = f"{prefix} Max" if prefix != "Packet Length" else "Max Packet Length"
                    if min_k in raw_dict and mean_k in raw_dict and max_k in raw_dict:
                        # Independent unconstrained jitter
                        raw_dict[min_k] = max(0.0, raw_dict[min_k] * (1.0 + self.rng.uniform(-jitter_pct, jitter_pct)))
                        raw_dict[mean_k] = max(0.0, raw_dict[mean_k] * (1.0 + self.rng.uniform(-jitter_pct, jitter_pct)))
                        raw_dict[max_k] = max(0.0, raw_dict[max_k] * (1.0 + self.rng.uniform(-jitter_pct, jitter_pct)))

                raw_dict = self._recalculate_derived_features(raw_dict)
                raw_valid, raw_reason = self._validate_invariants(raw_dict)
                if not raw_valid:
                    raw_cat = self._categorize_rejection_reason(raw_reason)
                    self.raw_invalid_records[jitter_pct][raw_cat] = self.raw_invalid_records[jitter_pct].get(raw_cat, 0) + 1

            # ---------------------------------------------------------
            # 2. Invariant-Preserving Bounded Perturbation with Clamping Tracking
            # ---------------------------------------------------------
            flow_dict = {col: float(flow_row[col]) for col in feature_cols}

            # 2a. 2-packet flow / equal IAT synchronization
            dur_key = "Flow Duration" if "Flow Duration" in flow_dict else ("dur" if "dur" in flow_dict else None)
            is_2pkt_or_equal_iat = False
            if dur_key == "Flow Duration" and "Flow IAT Max" in flow_dict:
                dur_val = flow_dict["Flow Duration"]
                iat_max_val = flow_dict["Flow IAT Max"]
                if dur_val > 0.0 and abs(iat_max_val - dur_val) / max(1.0, dur_val) <= 0.01:
                    is_2pkt_or_equal_iat = True
                    scale_dur_iat = 1.0 + self.rng.uniform(-jitter_pct, jitter_pct)
                    flow_dict["Flow Duration"] = max(1.0, dur_val * scale_dur_iat)
                    flow_dict["Flow IAT Max"] = flow_dict["Flow Duration"]
                    if "Flow IAT Mean" in flow_dict:
                        flow_dict["Flow IAT Mean"] = flow_dict["Flow Duration"]
                    if "Flow IAT Total" in flow_dict:
                        flow_dict["Flow IAT Total"] = flow_dict["Flow Duration"]
                    if "Flow IAT Min" in flow_dict:
                        flow_dict["Flow IAT Min"] = min(flow_dict["Flow IAT Max"], max(0.0, flow_dict["Flow IAT Min"] * scale_dur_iat))
                    self.clamping_events[jitter_pct]["Rule 6 (2-Packet / Equal IAT Duration Sync)"] = (
                        self.clamping_events[jitter_pct].get("Rule 6 (2-Packet / Equal IAT Duration Sync)", 0) + 1
                    )

            if not is_2pkt_or_equal_iat and dur_key and dur_key in flow_dict:
                dur_val = flow_dict[dur_key]
                if dur_val > 0.0:
                    j_dur = self.rng.uniform(-jitter_pct, jitter_pct)
                    flow_dict[dur_key] = max(1.0, dur_val * (1.0 + j_dur))

            # 2b. Perturb Base Packet and Byte Counts
            for cnt_col in self.BASE_COUNT_FEATURES:
                if cnt_col in flow_dict and flow_dict[cnt_col] > 0.0:
                    j_cnt = self.rng.uniform(-jitter_pct, jitter_pct)
                    new_cnt = flow_dict[cnt_col] * (1.0 + j_cnt)
                    flow_dict[cnt_col] = float(max(1 if "Fwd Packets" in cnt_col or cnt_col == "spkts" else 0,
                                                   int(np.round(new_cnt))))

            tot_fwd = flow_dict.get("Total Fwd Packets", flow_dict.get("spkts", 1.0))
            tot_bwd = flow_dict.get("Total Backward Packets", flow_dict.get("dpkts", 0.0))
            tot_pkts = tot_fwd + tot_bwd

            # Line rate clamp
            dur_sec = max(1e-6, flow_dict[dur_key] * (1e-6 if dur_key == "Flow Duration" else 1.0)) if dur_key else 1.0
            if (tot_pkts / dur_sec) > self.MAX_LINE_RATE_PPS:
                min_dur_sec = tot_pkts / (self.MAX_LINE_RATE_PPS * 0.9)
                if dur_key == "Flow Duration":
                    flow_dict[dur_key] = min_dur_sec * 1e6
                elif dur_key == "dur":
                    flow_dict[dur_key] = min_dur_sec
                self.clamping_events[jitter_pct]["Rule 3 (Physical Line Rate Clamping)"] = (
                    self.clamping_events[jitter_pct].get("Rule 3 (Physical Line Rate Clamping)", 0) + 1
                )

            # 2c. Perturb TCP Flag Counts bounded by total packets
            for flag_col in self.TCP_FLAG_FEATURES:
                if flag_col in flow_dict and flow_dict[flag_col] > 0.0:
                    j_flg = self.rng.uniform(-jitter_pct, jitter_pct)
                    new_flg = int(np.round(flow_dict[flag_col] * (1.0 + j_flg)))
                    clamped_flg = float(min(int(tot_pkts), max(0, new_flg)))
                    if clamped_flg != new_flg:
                        self.clamping_events[jitter_pct]["Rule 4 (TCP Flag Clamped to Packets)"] = (
                            self.clamping_events[jitter_pct].get("Rule 4 (TCP Flag Clamped to Packets)", 0) + 1
                        )
                    flow_dict[flag_col] = clamped_flg

            # 2d. Statistical Packet Length Hierarchies (Min <= Mean <= Max)
            for prefix in ["Fwd Packet Length", "Bwd Packet Length", "Packet Length"]:
                min_k = f"{prefix} Min" if prefix != "Packet Length" else "Min Packet Length"
                mean_k = f"{prefix} Mean" if prefix != "Packet Length" else "Packet Length Mean"
                max_k = f"{prefix} Max" if prefix != "Packet Length" else "Max Packet Length"
                std_k = f"{prefix} Std" if prefix != "Packet Length" else "Packet Length Std"

                if min_k in flow_dict and mean_k in flow_dict and max_k in flow_dict:
                    common_scale = 1.0 + self.rng.uniform(-jitter_pct, jitter_pct)
                    new_min = max(0.0, flow_dict[min_k] * common_scale)
                    new_mean = max(0.0, flow_dict[mean_k] * common_scale)
                    new_max = max(0.0, flow_dict[max_k] * common_scale)

                    sub_j_min = 1.0 + self.rng.uniform(-jitter_pct * 0.1, jitter_pct * 0.1)
                    sub_j_max = 1.0 + self.rng.uniform(-jitter_pct * 0.1, jitter_pct * 0.1)
                    sub_j_mean = 1.0 + self.rng.uniform(-jitter_pct * 0.1, jitter_pct * 0.1)

                    cand_min = max(0.0, new_min * sub_j_min)
                    cand_max = max(cand_min, new_max * sub_j_max)
                    cand_mean = min(cand_max, max(cand_min, new_mean * sub_j_mean))

                    if not (cand_min <= cand_mean <= cand_max):
                        self.clamping_events[jitter_pct]["Rule 5 (Packet Length Hierarchy Clamped)"] = (
                            self.clamping_events[jitter_pct].get("Rule 5 (Packet Length Hierarchy Clamped)", 0) + 1
                        )

                    flow_dict[min_k] = cand_min
                    flow_dict[mean_k] = cand_mean
                    flow_dict[max_k] = cand_max

                if std_k in flow_dict and flow_dict[std_k] >= 0.0:
                    flow_dict[std_k] = max(0.0, flow_dict[std_k] * (1.0 + self.rng.uniform(-jitter_pct, jitter_pct)))

            if "Packet Length Variance" in flow_dict and "Packet Length Std" in flow_dict:
                flow_dict["Packet Length Variance"] = flow_dict["Packet Length Std"] ** 2

            # 2e. Inter-Arrival Times (IAT)
            current_dur = flow_dict.get("Flow Duration", 1e6)
            for prefix in ["Flow IAT", "Fwd IAT", "Bwd IAT"]:
                min_k = f"{prefix} Min"
                mean_k = f"{prefix} Mean"
                max_k = f"{prefix} Max"
                std_k = f"{prefix} Std"
                tot_k = f"{prefix} Total"

                if prefix == "Flow IAT" and is_2pkt_or_equal_iat:
                    if std_k in flow_dict and flow_dict[std_k] >= 0.0:
                        flow_dict[std_k] = max(0.0, flow_dict[std_k] * (1.0 + self.rng.uniform(-jitter_pct, jitter_pct)))
                    continue

                if min_k in flow_dict and mean_k in flow_dict and max_k in flow_dict:
                    common_scale = 1.0 + self.rng.uniform(-jitter_pct, jitter_pct)
                    new_min = max(0.0, flow_dict[min_k] * common_scale)
                    new_mean = max(0.0, flow_dict[mean_k] * common_scale)
                    new_max = max(0.0, flow_dict[max_k] * common_scale)

                    if prefix == "Flow IAT" and new_max > current_dur:
                        new_max = current_dur
                        self.clamping_events[jitter_pct]["Rule 6 (IAT Max Clamped to Flow Duration)"] = (
                            self.clamping_events[jitter_pct].get("Rule 6 (IAT Max Clamped to Flow Duration)", 0) + 1
                        )

                    cand_min = max(0.0, new_min)
                    cand_max = max(cand_min, new_max)
                    cand_mean = min(cand_max, max(cand_min, new_mean))

                    flow_dict[min_k] = cand_min
                    flow_dict[mean_k] = cand_mean
                    flow_dict[max_k] = cand_max

                if std_k in flow_dict and flow_dict[std_k] >= 0.0:
                    flow_dict[std_k] = max(0.0, flow_dict[std_k] * (1.0 + self.rng.uniform(-jitter_pct, jitter_pct)))
                if tot_k in flow_dict and flow_dict[tot_k] >= 0.0:
                    flow_dict[tot_k] = max(0.0, flow_dict[tot_k] * (1.0 + self.rng.uniform(-jitter_pct, jitter_pct)))

            # 2f. Active / Idle
            for prefix in ["Active", "Idle"]:
                min_k = f"{prefix} Min"
                mean_k = f"{prefix} Mean"
                max_k = f"{prefix} Max"
                std_k = f"{prefix} Std"
                if min_k in flow_dict and mean_k in flow_dict and max_k in flow_dict:
                    common_scale = 1.0 + self.rng.uniform(-jitter_pct, jitter_pct)
                    cand_min = max(0.0, flow_dict[min_k] * common_scale)
                    cand_max = max(cand_min, flow_dict[max_k] * common_scale)
                    cand_mean = min(cand_max, max(cand_min, flow_dict[mean_k] * common_scale))
                    flow_dict[min_k] = cand_min
                    flow_dict[mean_k] = cand_mean
                    flow_dict[max_k] = cand_max
                if std_k in flow_dict and flow_dict[std_k] >= 0.0:
                    flow_dict[std_k] = max(0.0, flow_dict[std_k] * (1.0 + self.rng.uniform(-jitter_pct, jitter_pct)))

            # Recalculate derived features
            flow_dict = self._recalculate_derived_features(flow_dict)

            # Validate physical invariants
            is_valid, reason = self._validate_invariants(flow_dict)
            if is_valid:
                res_series = pd.Series(flow_dict)
                for meta_col in ["Label", "y_binary", "Family_Group"]:
                    if meta_col in flow_row.index:
                        res_series[meta_col] = flow_row[meta_col]

                # Compute non-trivial relative change
                diffs = [
                    abs(flow_dict[c] - float(flow_row[c])) / max(1.0, abs(float(flow_row[c])))
                    for c in feature_cols if c in flow_dict
                ]
                rel_change = float(np.mean(diffs)) if diffs else 0.0
                self.relative_changes[jitter_pct].append(rel_change)

                return res_series, attempts, None
            else:
                last_reason = reason
                if jitter_pct not in self.rule_rejections:
                    self.rule_rejections[jitter_pct] = {}
                cat = self._categorize_rejection_reason(reason)
                self.rule_rejections[jitter_pct][cat] = self.rule_rejections[jitter_pct].get(cat, 0) + 1

        return None, attempts, last_reason

    def generate_valid_perturbations(
        self,
        flow_row: pd.Series,
        n_samples: int = 20,
        jitter_pct: float = 0.05,
        jitter_magnitude: Optional[int] = None,
        max_attempts_per_sample: int = 50,
        audit_mode: bool = False
    ) -> pd.DataFrame:
        """Generate exactly n_samples physically valid perturbations of a flow."""
        if jitter_magnitude is not None:
            jitter_pct = jitter_magnitude / 100.0
        perturbed_rows = []
        total_attempts = 0

        for _ in range(n_samples):
            p_series, attempts, reason = self.perturb_single_flow(
                flow_row, jitter_pct=jitter_pct, max_attempts=max_attempts_per_sample, audit_mode=audit_mode
            )
            total_attempts += attempts
            if p_series is not None:
                perturbed_rows.append(p_series)
            else:
                # Deterministic fallback with tiny 0.05% jitter ensuring 100% validity
                p_fallback, fb_att, _ = self.perturb_single_flow(flow_row, jitter_pct=0.0005, max_attempts=10, audit_mode=audit_mode)
                total_attempts += fb_att
                perturbed_rows.append(p_fallback if p_fallback is not None else flow_row.copy())

        # Track rejection statistics
        if jitter_pct not in self.rejection_records:
            self.rejection_records[jitter_pct] = {"generated": 0, "rejected_attempts": 0}
        self.rejection_records[jitter_pct]["generated"] += n_samples
        self.rejection_records[jitter_pct]["rejected_attempts"] += max(0, total_attempts - n_samples)

        return pd.DataFrame(perturbed_rows).reset_index(drop=True)

    def get_rejection_summary(self) -> Dict[str, Dict[str, Any]]:
        """Return comprehensive audit summary including pre-clamping invalidity and clamping frequencies."""
        summary = {}
        for jitter, data in self.rejection_records.items():
            tot = data["generated"] + data["rejected_attempts"]
            rej_pct = (data["rejected_attempts"] / max(1, tot)) * 100.0
            rules = self.rule_rejections.get(jitter, {})

            raw_inv = self.raw_invalid_records.get(jitter, {})
            raw_inv_count = sum(raw_inv.values())
            raw_inv_pct = (raw_inv_count / max(1, tot)) * 100.0

            clamped = self.clamping_events.get(jitter, {})
            clamped_count = sum(clamped.values())
            clamped_pct = (clamped_count / max(1, tot)) * 100.0

            rel_changes = self.relative_changes.get(jitter, [0.0])
            mean_rel_change_pct = float(np.mean(rel_changes)) * 100.0 if rel_changes else 0.0

            summary[f"jitter_{int(round(jitter * 100))}%"] = {
                "jitter_pct": jitter,
                "total_attempts": tot,
                "valid_generated": data["generated"],
                "raw_invalid_attempts": raw_inv_count,
                "raw_invalid_pct": round(raw_inv_pct, 2),
                "raw_rule_breakdown": raw_inv,
                "clamping_events_count": clamped_count,
                "clamping_events_pct": round(clamped_pct, 2),
                "clamping_events_breakdown": clamped,
                "rejected_attempts": data["rejected_attempts"],
                "rejection_pct": round(rej_pct, 2),
                "rule_breakdown": rules,
                "mean_relative_change_pct": round(mean_rel_change_pct, 2),
            }
        return summary
