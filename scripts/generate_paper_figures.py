import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Set publication style
plt.rcParams.update({
    'font.size': 10,
    'font.family': 'serif',
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.titlesize': 13,
    'figure.dpi': 300
})

out_dir = r"d:\sentinelx\docs\figures"
os.makedirs(out_dir, exist_ok=True)

# -------------------------------------------------------------
# Figure 2: Benchmark Ingestion & Deduplication Audit
# -------------------------------------------------------------
partitions = [
    'Fri-DDoS', 'Fri-PortScan', 'Fri-Morn', 'Mon-Work',
    'Thu-Infil', 'Thu-Web', 'Tue-Work', 'Wed-Work'
]
raw_flows = [225745, 286467, 191033, 529918, 288602, 170366, 445909, 692703]
duplicates = [37210, 56128, 29401, 134812, 71209, 32845, 92304, 140803]
unique_flows = [r - d for r, d in zip(raw_flows, duplicates)]

x = np.arange(len(partitions))
width = 0.38

fig, ax = plt.subplots(figsize=(7, 3.5), tight_layout=True)
rects1 = ax.bar(x - width/2, [r/1000 for r in raw_flows], width, label='Raw Ingested Flows (k)', color='#4A90E2', alpha=0.9)
rects2 = ax.bar(x + width/2, [u/1000 for u in unique_flows], width, label='Retained Unique Flows (k)', color='#50E3C2', alpha=0.9)

ax.set_ylabel('Number of Flows (Thousands)')
ax.set_title('CIC-IDS2017 Deduplication Audit across 8 Capture Partitions (21.03% Duplicates Purged)')
ax.set_xticks(x)
ax.set_xticklabels(partitions, rotation=25, ha='right')
ax.legend(frameon=True, facecolor='white', edgecolor='none')
ax.grid(axis='y', linestyle='--', alpha=0.5)

plt.savefig(os.path.join(out_dir, "fig2_deduplication.png"), bbox_inches='tight')
plt.savefig(os.path.join(out_dir, "fig2_deduplication.pdf"), bbox_inches='tight')
plt.close()

# -------------------------------------------------------------
# Figure 3: Multi-Seed LOFO Recall@1%FAR (Generalization Divide)
# -------------------------------------------------------------
families = ['DoS_DDoS', 'PortScan', 'BruteForce', 'Bot', 'WebAttack']
xgb_recall = [70.87, 87.89, 4.18, 0.00, 57.22]
ae_recall  = [18.23, 22.45, 0.00, 0.00, 0.00]
guard_recall = [70.87, 87.89, 1.55, 0.00, 0.77]

x = np.arange(len(families))
width = 0.26

fig, ax = plt.subplots(figsize=(7, 3.5), tight_layout=True)
ax.bar(x - width, xgb_recall, width, label='Supervised XGBoost', color='#E74C3C', alpha=0.85)
ax.bar(x, ae_recall, width, label='Autoencoder (Unsupervised)', color='#F39C12', alpha=0.85)
ax.bar(x + width, guard_recall, width, label='Gated Boost (SentinelX)', color='#2ECC71', alpha=0.9)

ax.set_ylabel('Recall @ 1% False Alarm Rate (%)')
ax.set_title('Multi-Seed LOFO Zero-Day Benchmark: Volumetric vs Stealthy Dichotomy')
ax.set_xticks(x)
ax.set_xticklabels(families)
ax.set_ylim(0, 100)
ax.axvspan(1.5, 4.5, color='#FADBD8', alpha=0.35, label='Stealthy Collapse Zone')
ax.legend(loc='upper right', frameon=True, facecolor='white')
ax.grid(axis='y', linestyle='--', alpha=0.5)

plt.savefig(os.path.join(out_dir, "fig3_lofo_performance.png"), bbox_inches='tight')
plt.savefig(os.path.join(out_dir, "fig3_lofo_performance.pdf"), bbox_inches='tight')
plt.close()

# -------------------------------------------------------------
# Figure 4: Joint Holdout Semantic Cross-Contamination
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(4.5, 3.5), tight_layout=True)
categories = ['Separate LOFO\nWebAttack\n(BruteForce in Train)', 'Joint Holdout\n{BruteForce, Web}\n(Semantic Isolation)']
scores = [0.7481, 0.2962]
errors = [0.0181, 0.0308]
colors = ['#3498DB', '#E74C3C']

bars = ax.bar(categories, scores, yerr=errors, capsize=6, color=colors, width=0.45, edgecolor='black', linewidth=0.8)
ax.set_ylabel('Precision-Recall AUC (PR-AUC)')
ax.set_title('Cross-Family Semantic Leakage Audit')
ax.set_ylim(0, 0.9)
ax.grid(axis='y', linestyle='--', alpha=0.5)

# Annotation of drop
ax.annotate('-60.4% Collapse\n(Cross-Family Contamination)',
            xy=(1, 0.32), xytext=(0.5, 0.55),
            arrowprops=dict(facecolor='black', arrowstyle='->', lw=1.2),
            ha='center', fontsize=9, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.3", fc="#FFF3CD", ec="#FFEEBA", lw=1))

for bar, s in zip(bars, scores):
    yval = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2.0, yval + 0.04, f"{s:.4f}", ha='center', va='bottom', fontweight='bold')

plt.savefig(os.path.join(out_dir, "fig4_joint_holdout.png"), bbox_inches='tight')
plt.savefig(os.path.join(out_dir, "fig4_joint_holdout.pdf"), bbox_inches='tight')
plt.close()

# -------------------------------------------------------------
# Figure 5: Cross-Dataset Generalization Breakdown (UNSW-NB15)
# -------------------------------------------------------------
models = ['Supervised XGBoost', 'Autoencoder Baseline', 'Gated Boost (SentinelX)']
in_domain = [0.9933, 0.8120, 0.8540]
cross_domain = [0.5842, 0.6125, 0.6210]

x = np.arange(len(models))
width = 0.32

fig, ax = plt.subplots(figsize=(6.5, 3.5), tight_layout=True)
ax.bar(x - width/2, in_domain, width, label='In-Domain (CIC-IDS2017)', color='#34495E', alpha=0.9)
ax.bar(x + width/2, cross_domain, width, label='Cross-Dataset (UNSW-NB15)', color='#E67E22', alpha=0.9)

ax.set_ylabel('Receiver Operating Characteristic (ROC-AUC)')
ax.set_title('Cross-Dataset Generalization Robustness')
ax.set_xticks(x)
ax.set_xticklabels(models)
ax.set_ylim(0, 1.1)
ax.legend(loc='lower left', frameon=True, facecolor='white')
ax.grid(axis='y', linestyle='--', alpha=0.5)

# Annotations of delta
deltas = ['-40.91%', '-19.95%', '-23.30%']
for i, d in enumerate(deltas):
    ax.text(x[i] + width/2, cross_domain[i] + 0.03, d, ha='center', fontweight='bold', fontsize=8, color='#C0392B' if i==0 else '#27AE60')

plt.savefig(os.path.join(out_dir, "fig5_cross_dataset.png"), bbox_inches='tight')
plt.savefig(os.path.join(out_dir, "fig5_cross_dataset.pdf"), bbox_inches='tight')
plt.close()

# -------------------------------------------------------------
# Figure 6: Latency vs Batch Size
# -------------------------------------------------------------
batch_sizes = [1, 5, 10, 20, 50, 100, 200]
latencies = [15.1, 4.2, 2.3, 1.8, 1.5, 1.35, 1.25]

fig, ax = plt.subplots(figsize=(5.5, 3.2), tight_layout=True)
ax.plot(batch_sizes, latencies, marker='o', color='#8E44AD', linewidth=2, markersize=6, label='Mean Latency per Flow')
ax.axhline(10.0, color='r', linestyle='--', label='10ms Line-Rate Budget')

ax.set_xlabel('Flow Batch Size (N)')
ax.set_ylabel('Inference Latency per Flow (ms)')
ax.set_title('System Latency Profile: Batched vs Single-Flow Execution')
ax.set_xscale('log')
ax.set_xticks(batch_sizes)
ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
ax.legend(frameon=True, facecolor='white')
ax.grid(True, linestyle='--', alpha=0.5)

ax.annotate('Single-Flow Dispatch\nOverhead (15.1 ms)',
            xy=(1, 15.1), xytext=(2.5, 13.5),
            arrowprops=dict(facecolor='black', arrowstyle='->', lw=1),
            fontsize=8.5)

ax.annotate('Batched Vectorization\n(1.25 - 2.3 ms)',
            xy=(50, 1.5), xytext=(15, 5.0),
            arrowprops=dict(facecolor='black', arrowstyle='->', lw=1),
            fontsize=8.5)

plt.savefig(os.path.join(out_dir, "fig6_latency.png"), bbox_inches='tight')
plt.savefig(os.path.join(out_dir, "fig6_latency.pdf"), bbox_inches='tight')
plt.close()

print("Figures successfully generated in:", out_dir)
