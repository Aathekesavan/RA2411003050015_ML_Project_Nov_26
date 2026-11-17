import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

def generate_sentinelx_deployment_diagram(output_path='docs/figures/sentinelx_deployment_ecosystem.png'):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 8), dpi=300)
    fig.patch.set_facecolor('#0A111F')
    ax.set_facecolor('#0A111F')
    
    # Title
    ax.text(0.5, 0.96, "SENTINELX-SHIFT OPERATIONAL DEPLOYMENT", 
            fontsize=13, fontweight='bold', color='#00C3EB', ha='center', va='center')
    ax.text(0.5, 0.925, "Dual-Engine Monitor-Only SOC Telemetry & Triage Architecture", 
            fontsize=9, color='#94A3B8', ha='center', va='center')

    # Box 1: Network Ingestion
    rect1 = patches.FancyBboxPatch((0.08, 0.70), 0.84, 0.18, boxstyle="round,pad=0.03", 
                                  edgecolor="#195FD7", facecolor="#162032", linewidth=2)
    ax.add_patch(rect1)
    ax.text(0.12, 0.84, "STEP 1: ENTERPRISE TELEMETRY INGESTION (DMZ & CORE TAP)", 
            fontsize=9.5, fontweight='bold', color='#38BDF8', va='center')
    ax.text(0.12, 0.79, "• Passive Network Mirror: Zero inline packet drops, 100% monitor-only posture", 
            fontsize=8.5, color='#F1F5F9', va='center')
    ax.text(0.12, 0.75, "• Flow Sanitizer: Strips IP/MAC/ports (eliminates 100% metadata shortcut learning)", 
            fontsize=8.5, color='#F1F5F9', va='center')
    ax.text(0.12, 0.71, "• Feature Extraction: Computes 76 transport dynamics & inter-arrival time (IAT) features", 
            fontsize=8.5, color='#CBD5E1', va='center')

    # Arrow 1 down
    ax.annotate('', xy=(0.5, 0.65), xytext=(0.5, 0.70),
                arrowprops=dict(arrowstyle="->", color="#00C3EB", lw=2.5))

    # Box 2: Dual Scoring Engine
    rect2 = patches.FancyBboxPatch((0.08, 0.40), 0.84, 0.24, boxstyle="round,pad=0.03", 
                                  edgecolor="#00C3EB", facecolor="#101D33", linewidth=2.5)
    ax.add_patch(rect2)
    ax.text(0.12, 0.60, "STEP 2: AUTOENCODER-ANCHORED GATED BOOST ENGINE", 
            fontsize=9.5, fontweight='bold', color='#00E5FF', va='center')
    ax.text(0.12, 0.55, "✔ Unsupervised Autoencoder Floor: [76-48-24-12-24-48-76] detects novel zero-day shifts", 
            fontsize=8.5, color='#F8FAFC', va='center')
    ax.text(0.12, 0.51, "✔ Empirical CDF Calibration: Uniform [0,1] normalization for statistical consistency", 
            fontsize=8.5, color='#F8FAFC', va='center')
    ax.text(0.12, 0.47, "✔ Gated Boost: s_guard = s_AE + 0.41 * I(s_XGB > 0.56) prevents catastrophic bleed", 
            fontsize=8.5, color='#F8FAFC', va='center')
    ax.text(0.12, 0.43, "✔ Multi-Tier Guardrails: Correlates NetFlow with Nginx & ModSecurity WAF audit logs", 
            fontsize=8.5, color='#38BDF8', va='center')

    # Arrow 2 down splits
    ax.annotate('', xy=(0.28, 0.33), xytext=(0.42, 0.40),
                arrowprops=dict(arrowstyle="->", color="#10B981", lw=2.5))
    ax.annotate('', xy=(0.72, 0.33), xytext=(0.58, 0.40),
                arrowprops=dict(arrowstyle="->", color="#F43F5E", lw=2.5))

    # Box 3A: Suppressed Bursts
    rect3a = patches.FancyBboxPatch((0.08, 0.12), 0.40, 0.20, boxstyle="round,pad=0.025", 
                                   edgecolor="#10B981", facecolor="#064E3B", linewidth=2)
    ax.add_patch(rect3a)
    ax.text(0.28, 0.29, "BENIGN TRAFFIC BURSTS", 
            fontsize=9, fontweight='bold', color='#34D399', ha='center', va='center')
    ax.text(0.28, 0.24, "AUTOMATED DE-ESCALATION", 
            fontsize=8, fontweight='bold', color='#A7F3D0', ha='center', va='center')
    ax.text(0.28, 0.19, "• Confirmed 200 OK host logs\n• Suppresses false alarm storms\n• Prevents analyst alert fatigue", 
            fontsize=7.8, color='#ECFDF5', ha='center', va='center')

    # Box 3B: Critical Triage
    rect3b = patches.FancyBboxPatch((0.52, 0.12), 0.40, 0.20, boxstyle="round,pad=0.025", 
                                   edgecolor="#F43F5E", facecolor="#4C0519", linewidth=2)
    ax.add_patch(rect3b)
    ax.text(0.72, 0.29, "STEALTHY / ZERO-DAY ATTACKS", 
            fontsize=9, fontweight='bold', color='#FDA4AF', ha='center', va='center')
    ax.text(0.72, 0.24, "PRIORITIZED SOC QUEUE", 
            fontsize=8, fontweight='bold', color='#FECDD3', ha='center', va='center')
    ax.text(0.72, 0.19, "• Correlated 401/WAF rule matches\n• Immediate human-in-the-loop triage\n• Immutable SQLite audit trail", 
            fontsize=7.8, color='#FFF1F2', ha='center', va='center')

    # Bottom summary pill
    rect_pill = patches.FancyBboxPatch((0.15, 0.02), 0.70, 0.065, boxstyle="round,pad=0.02", 
                                       edgecolor="#38BDF8", facecolor="#0F172A", linewidth=1.5)
    ax.add_patch(rect_pill)
    ax.text(0.5, 0.052, "SAFETY: Strict Monitor-Only posture guarantees 0% self-inflicted enterprise outages", 
            fontsize=8.5, fontweight='bold', color='#38BDF8', ha='center', va='center')

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Generated {output_path}")

if __name__ == '__main__':
    generate_sentinelx_deployment_diagram()
