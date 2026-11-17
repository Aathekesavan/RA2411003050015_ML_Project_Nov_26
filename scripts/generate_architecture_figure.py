import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

out_dir = r"d:\sentinelx\docs\figures"
os.makedirs(out_dir, exist_ok=True)

fig, ax = plt.subplots(figsize=(10, 4.8), dpi=300)
ax.set_xlim(0, 100)
ax.set_ylim(0, 50)
ax.axis('off')

# Style helper
def draw_box(ax, x, y, w, h, title, subtitle, color, ec='#2C3E50', lw=1.5):
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5",
                                  facecolor=color, edgecolor=ec, linewidth=lw)
    ax.add_patch(rect)
    ax.text(x + w/2, y + h/2 + 1.2, title, ha='center', va='center', fontsize=9.5, fontweight='bold', color='#1A252F')
    if subtitle:
        ax.text(x + w/2, y + h/2 - 1.6, subtitle, ha='center', va='center', fontsize=8, color='#34495E')

def draw_arrow(ax, x1, y1, x2, y2, label=None):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(facecolor='#2C3E50', edgecolor='#2C3E50', width=1.5, headwidth=6, headlength=7))
    if label:
        ax.text((x1+x2)/2, (y1+y2)/2 + 1.2, label, ha='center', va='bottom', fontsize=7.5, color='#2C3E50')

# Layer 1: Ingestion
draw_box(ax, 2, 33, 20, 11, "NetFlow Telemetry", "76 Sanitized Transport Features\n(Stripped IPs, Ports, MACs)", "#D4E6F1")
draw_box(ax, 2, 6, 20, 11, "Host & WAF Logs", "Nginx Access/Error & ModSec\n(Stripped URI tokens/params)", "#FCF3CF")

# Layer 2: Correlation & Preprocessing
draw_box(ax, 27, 33, 18, 11, "Feature Scaling", "Quantile & Robust Scaling\nZero-Variance Pruning", "#E8F8F5")
draw_box(ax, 27, 6, 18, 11, "Temporal Matcher", "Window: Δt = ±30s\nClient IP Hash Matching", "#FEF9E7")

# Layer 3: SentinelGuard Engine
draw_box(ax, 50, 20, 24, 24, "SentinelGuard Hybrid Core", 
         "1. AE Reconstruction: s_AE\n2. XGBoost Risk: s_XGB\n3. Empirical CDF Percentiles\n4. Gated Boost: s_guard =\n   s_AE + 0.41 · I(s_XGB > 0.56)", 
         "#E8DAEF", ec='#6C3483', lw=2)

# Layer 4: Guardrail Engine
draw_box(ax, 78, 20, 20, 11, "Guardrail Policy", "• BruteForce (≥5 401s)\n• Benign Burst Suppress\n• Strict Protocol Check", "#D5F5E3", ec='#1E8449', lw=1.8)

# Layer 5: Operational Action
draw_box(ax, 78, 4, 20, 11, "Operational Triage", "CRITICAL / HIGH / MED / LOW\nStrict Monitor-Only Invariant\nSQLite Audit Log Badge", "#EDBB99", ec='#BA4A00', lw=1.8)

# Connectors
draw_arrow(ax, 22, 38.5, 27, 38.5)
draw_arrow(ax, 22, 11.5, 27, 11.5)
draw_arrow(ax, 45, 38.5, 50, 34)
draw_arrow(ax, 45, 11.5, 50, 24)
draw_arrow(ax, 74, 32, 78, 26, "Raw Tier")
draw_arrow(ax, 88, 20, 88, 15, "Verified Tier")

# Add title banner
ax.text(50, 48, "SentinelX-Shift: End-to-End Operational Pipeline Architecture", 
        ha='center', va='center', fontsize=12, fontweight='bold', color='#1A252F')

plt.tight_layout()
plt.savefig(os.path.join(out_dir, "fig1_architecture.png"), bbox_inches='tight')
plt.savefig(os.path.join(out_dir, "fig1_architecture.pdf"), bbox_inches='tight')
plt.close()
print("Architecture figure successfully generated.")
