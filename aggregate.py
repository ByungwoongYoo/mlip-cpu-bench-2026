"""Aggregate results/<model>/*.json -> results/summary.json, results/table_*.csv/.md, charts/*.png"""
import json, glob, os, re
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
H = os.path.dirname(os.path.abspath(__file__))
MODELS = ["chgnet_r2scan", "pet_mad_s", "prophet", "mace_mp", "flashcart_mad"]
LABEL = {"chgnet_r2scan": "CHGNet-r2SCAN-2026.9", "pet_mad_s": "PET-MAD-s", "prophet": "Prophet-OAME-MBD",
         "mace_mp": "MACE-MP-0 medium", "flashcart_mad": "FlashCart-MAD"}
COL = {"chgnet_r2scan": "#1f77b4", "pet_mad_s": "#ff7f0e", "prophet": "#2ca02c", "mace_mp": "#d62728", "flashcart_mad": "#9467bd"}
CLASSES = ["metal", "semiconductor", "ionic", "semimetal"]
CCOL = {"metal": "#4c72b0", "semiconductor": "#dd8452", "ionic": "#55a868", "semimetal": "#8172b3"}
rows = []
for m in MODELS:
    for f in sorted(glob.glob(f"{H}/results/{m}/*.json")):
        if f.endswith("_run.json"): continue
        r = json.load(open(f)); s = r["ref"]
        rows.append(dict(model=m, solid=r["solid"], cls=r["cls"], oxide=r["oxide"], source=s["source"], cubic=bool(s.get("cubic")),
            magnetic=r["solid"] in ("Fe", "Co", "Ni", "Cr"), status=r["status"], failure=r.get("failure", ""), warning=r.get("warning", ""),
            n_atoms=r.get("n_atoms"), relaxed=r.get("relaxed"), a_ref=s.get("a_ref"), a_pred=r.get("a_pred"), a_err=r.get("a_err_pct"),
            V_ref=s["V_ref_per_atom"], V_pred=r.get("V0_per_atom"), V_err=r.get("V_err_pct"), aeq_err=r.get("a_eq_err_pct"),
            B_ref=s["B_ref"], B_pred=r.get("B0_GPa"), B_err=r.get("B_err_pct"), passes=len(r.get("passes", [])),
            wall_s=r["wall_s"], peak_rss_mb=r["peak_rss_mb"], sp_ms=r.get("median_fresh_singlepoint_ms")))
# solids with no result JSON (e.g. process killed by the RSS watchdog) count as failures, never silently dropped
REFS = json.load(open(f"{H}/refs/solids.json"))["solids"]; RNAMES = [x["name"] for x in REFS]
def missing_reason(m, name):
    for lf in [f"{H}/logs/{m}__{name}.log", f"{H}/logs/{m}.log"]:
        if not os.path.exists(lf): continue
        txt = open(lf).read()
        if "WATCHDOG" not in txt: continue
        if lf.endswith(f"__{name}.log"): return "no result: " + [l for l in txt.splitlines() if "WATCHDOG" in l][-1]
        done = [l.split()[0] for l in txt.splitlines() if l.split() and l.split()[0] in RNAMES]
        if done and RNAMES.index(done[-1]) + 1 < len(RNAMES) and RNAMES[RNAMES.index(done[-1]) + 1] == name:
            return "no result: " + [l for l in txt.splitlines() if "WATCHDOG" in l][-1]
    return "no result JSON (not run or process killed)"
have = {(r["model"], r["solid"]) for r in rows}
for m in MODELS:
    if not glob.glob(f"{H}/results/{m}/*.json"): continue
    for x in REFS:
        if (m, x["name"]) not in have:
            rows.append(dict(model=m, solid=x["name"], cls=x["cls"], oxide=x["oxide"], source=x["source"], cubic=bool(x.get("cubic")),
                magnetic=x["name"] in ("Fe", "Co", "Ni", "Cr"), status="no_result", failure=missing_reason(m, x["name"]), warning="",
                n_atoms=None, relaxed=None, a_ref=x.get("a_ref"), a_pred=None, a_err=np.nan, V_ref=x["V_ref_per_atom"], V_pred=None, V_err=np.nan,
                aeq_err=np.nan, B_ref=x["B_ref"], B_pred=None, B_err=np.nan, passes=0, wall_s=np.nan, peak_rss_mb=np.nan, sp_ms=np.nan))
df = pd.DataFrame(rows); df.to_csv(f"{H}/results/all_results.csv", index=False)
ok = df[df.status == "ok"]
solids_all = sorted(df.solid.unique())
common = sorted(set.intersection(*[set(ok[ok.model == m].solid) for m in MODELS if m in set(df.model)]))
def mape(x): return float(np.mean(np.abs(x))) if len(x) else float("nan")
summ = {}
for m in [m for m in MODELS if m in set(df.model)]:
    d = df[df.model == m]; o = ok[ok.model == m]; c = o[o.solid.isin(common)]
    run = json.load(open(f"{H}/results/{m}/_run.json")) if os.path.exists(f"{H}/results/{m}/_run.json") else {}
    res = "\n".join(open(f).read().strip() for f in sorted(glob.glob(f"{H}/logs/{m}.res") + glob.glob(f"{H}/logs/{m}__*.res")))
    S = dict(label=LABEL[m], n_attempted=len(d), n_ok=len(o), failures=d[d.status != "ok"][["solid", "failure"]].values.tolist(),
             warnings=d[d.warning != ""][["solid", "warning"]].values.tolist(),
             MAPE_a_eq_all=mape(o.aeq_err), ME_a_eq_all=float(o.aeq_err.mean()), MAPE_B_all=mape(o.B_err), ME_B_all=float(o.B_err.mean()),
             MAPE_a_eq_common=mape(c.aeq_err), MAPE_B_common=mape(c.B_err),
             MAPE_a_cubic=mape(o[o.cubic].a_err), MAPE_V_all=mape(o.V_err),
             MAPE_a_eq_nonmagnetic=mape(o[~o.magnetic].aeq_err), MAPE_B_nonmagnetic=mape(o[~o.magnetic].B_err),
             by_class={k: dict(n=int((c.cls == k).sum()), MAPE_a_eq=mape(c[c.cls == k].aeq_err), MAPE_B=mape(c[c.cls == k].B_err),
                               ME_a_eq=float(c[c.cls == k].aeq_err.mean()) if (c.cls == k).any() else None) for k in CLASSES},
             oxide_MgO=dict(a_err=float(c[c.solid == "MgO"].aeq_err.iloc[0]) if (c.solid == "MgO").any() else None,
                            B_err=float(c[c.solid == "MgO"].B_err.iloc[0]) if (c.solid == "MgO").any() else None),
             max_abs_a_eq=o.loc[o.aeq_err.abs().idxmax(), ["solid", "aeq_err"]].tolist() if len(o) else None,
             max_abs_B=o.loc[o.B_err.abs().idxmax(), ["solid", "B_err"]].tolist() if len(o) else None,
             n_failed=int((d.status != "ok").sum()), n_no_result=int((d.status == "no_result").sum()),
             ME_a_eq_common=float(c.aeq_err.mean()), ME_B_common=float(c.B_err.mean()),
             wall_common_s=float(d[d.solid.isin(common)].wall_s.sum()),
             wall_total_s=float(d.wall_s.sum()), wall_median_s=float(d.wall_s.median()), wall_median_cubic_s=float(d[d.cubic].wall_s.median()),
             wall_median_noncubic_s=float(d[~d.cubic].wall_s.median()), wall_max=d.loc[d.wall_s.idxmax(), ["solid", "wall_s"]].tolist(),
             singlepoint_median_ms=float(d.sp_ms.median()), peak_rss_per_structure_median_mb=float(d.peak_rss_mb.median()),
             peak_rss_per_structure_max_mb=float(d.peak_rss_mb.max()), load=run.get("load"), job_res=res.strip())
    summ[m] = S
json.dump(dict(common_subset=common, n_common=len(common), models=summ), open(f"{H}/results/summary.json", "w"), indent=1, default=float)
# ---------------- tables ----------------
ms = list(summ)
f2 = lambda x: "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.2f}"
f1 = lambda x: "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.1f}"
T = ["| Model | solids ok / 70 (failed) | MAPE a (%) common | MAPE B (%) common | MAPE a (%) all ok | MAPE B (%) all ok | mean signed a err (%) | mean signed B err (%) | MAPE a (%) excl. Fe/Co/Ni/Cr | worst a | worst B |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for m in sorted(ms, key=lambda m: summ[m]["MAPE_a_eq_common"]):
    S = summ[m]
    T.append(f"| {S['label']} | {S['n_ok']}/{S['n_attempted']} ({S['n_failed']}) | {f2(S['MAPE_a_eq_common'])} | {f1(S['MAPE_B_common'])} | {f2(S['MAPE_a_eq_all'])} | {f1(S['MAPE_B_all'])} | {S['ME_a_eq_all']:+.2f} | {S['ME_B_all']:+.1f} | {f2(S['MAPE_a_eq_nonmagnetic'])} | {S['max_abs_a_eq'][0]} {S['max_abs_a_eq'][1]:+.1f} | {S['max_abs_B'][0]} {S['max_abs_B'][1]:+.0f} |")
C = ["| Model | " + " | ".join(f"{k} (n={summ[ms[0]]['by_class'][k]['n']}) a / B" for k in CLASSES) + " | oxide: MgO (n=1) a / B |", "|---|" + "---|" * (len(CLASSES) + 1)]
for m in sorted(ms, key=lambda m: summ[m]["MAPE_a_eq_common"]):
    S = summ[m]; C.append(f"| {S['label']} | " + " | ".join(f"{f2(S['by_class'][k]['MAPE_a_eq'])} / {f1(S['by_class'][k]['MAPE_B'])}" for k in CLASSES)
                       + (f" | {S['oxide_MgO']['a_err']:+.2f} / {S['oxide_MgO']['B_err']:+.1f} |" if S['oxide_MgO']['a_err'] is not None else " | — |"))
R = ["| Model | model load (s) | RSS after load (MB) | median wall / cubic solid (s) | median wall / non-cubic solid (s) | slowest solid (s) | total wall, common subset (s) | total wall, all solids with a result (s) | median fresh single point E+F+σ (ms) | median / max process RSS per structure (MB) | job peak RSS (MB) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for m in sorted(ms, key=lambda m: summ[m]["wall_common_s"]):
    S = summ[m]; L = S["load"] or {}; pk = [int(v) for v in re.findall(r"peak_rss_mb=(\d+)", S["job_res"])]; 
    R.append(f"| {S['label']} | {f1(L.get('load_s'))} | {L.get('rss_after_load_mb', 0):.0f} | {S['wall_median_cubic_s']:.1f} | {S['wall_median_noncubic_s']:.1f} | {S['wall_max'][0]} {S['wall_max'][1]:.0f} | {S['wall_common_s']:.0f} | {S['wall_total_s']:.0f} | {S['singlepoint_median_ms']:.0f} | {S['peak_rss_per_structure_median_mb']:.0f} / {S['peak_rss_per_structure_max_mb']:.0f} | {max(pk) if pk else '—'}{' (max of ' + str(len(pk)) + ' jobs)' if len(pk) > 1 else ''} |")
# per-solid full table
P = ["| Solid | class | ref source | a_ref or V_ref | B_ref (GPa) | " + " | ".join(f"{LABEL[m]} Δa% / ΔB%" for m in ms) + " |", "|---|---|---|---|---|" + "---|" * len(ms)]
refs = df.drop_duplicates("solid").set_index("solid")
order = sorted(solids_all, key=lambda s: (CLASSES.index(refs.loc[s, "cls"]), s))
for s in order:
    r = refs.loc[s]; refv = f"a={r.a_ref:.3f} Å" if r.cubic else f"V={r.V_ref:.2f} Å³/at"
    cells = []
    for m in ms:
        x = df[(df.model == m) & (df.solid == s)]
        if not len(x): cells.append("not run"); continue
        x = x.iloc[0]
        cells.append("no result" if x.status == "no_result" else f"{x.aeq_err:+.2f} / {x.B_err:+.0f}" + ("" if x.status == "ok" else " FAIL"))
    P.append(f"| {s} | {r.cls}{' (oxide)' if r.oxide else ''} | {r.source} | {refv} | {r.B_ref:.1f} | " + " | ".join(cells) + " |")
open(f"{H}/results/tables.md", "w").write("## Overall\n\n" + "\n".join(T) + "\n\n## By class (MAPE a % / MAPE B %, common subset)\n\n" + "\n".join(C)
    + "\n\n## Runtime and memory\n\n" + "\n".join(R) + "\n\n## Per solid (a error = volume-equivalent lattice-constant error; identical to the a error for cubic solids)\n\n" + "\n".join(P) + "\n")
# ---------------- charts ----------------
plt.rcParams.update({"font.size": 10})
order_m = sorted(ms, key=lambda m: summ[m]["MAPE_a_eq_common"])
fig, axs = plt.subplots(1, 2, figsize=(13, 5.2))
w = 0.16; x = np.arange(len(order_m))
for j, (key, ax, ttl) in enumerate([("MAPE_a_eq", axs[0], "Lattice constant: MAPE of a (%)"), ("MAPE_B", axs[1], "Bulk modulus: MAPE of B (%)")]):
    for i, k in enumerate(CLASSES):
        vals = [summ[m]["by_class"][k][key] for m in order_m]
        if summ[order_m[0]]["by_class"][k]["n"] == 0: continue
        ax.bar(x + (i - 2) * w, vals, w, color=CCOL[k], label=f"{k} (n={summ[order_m[0]]['by_class'][k]['n']})")
    allv = [summ[m][key + "_common" if key == "MAPE_a_eq" else "MAPE_B_common"] for m in order_m]
    ax.bar(x + 2 * w, allv, w, color="0.25", label=f"all (n={len(common)})")
    # value labels for the "all" bar: rotated and lifted above the tallest bar of that model group so they never sit on a neighbouring bar
    tops = [max([summ[m]["by_class"][k][key] for k in CLASSES if summ[order_m[0]]["by_class"][k]["n"] > 0] + [a]) for m, a in zip(order_m, allv)]
    pad = 0.02 * max(tops)
    for xi, v, t in zip(x, allv, tops): ax.text(xi + 2 * w, t + pad, (f"all {v:.2f}" if j == 0 else f"all {v:.1f}"), ha="center", va="bottom", rotation=90, fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([LABEL[m] for m in order_m], rotation=20, ha="right"); ax.set_title(ttl)
    ax.set_ylabel("MAPE (%)"); ax.grid(axis="y", alpha=0.3); ax.set_axisbelow(True)
    ax.set_ylim(0, max(tops) * 1.30)
h, l = axs[0].get_legend_handles_labels()
fig.suptitle(f"MLIP equilibrium properties vs ZPE/thermal-corrected experiment, CPU (common subset of {len(common)} solids)", y=0.985, fontsize=11)
fig.legend(h, l, loc="upper center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 0.945))
fig.tight_layout(rect=(0, 0, 1, 0.91)); fig.savefig(f"{H}/charts/mape_by_model_class.png", dpi=150); plt.close(fig)
# parity: predicted vs experimental a (cubic solids)
n = len(order_m); fig, axs = plt.subplots(1, n, figsize=(3.4 * n, 4.6), sharex=True, sharey=True)
for ax, m in zip(np.atleast_1d(axs), order_m):
    d = ok[(ok.model == m) & ok.cubic]
    for k in CLASSES:
        dd = d[d.cls == k]
        if len(dd): ax.scatter(dd.a_ref, dd.a_pred, s=16, color=CCOL[k], label=k, edgecolor="k", linewidth=0.3)
    lo, hi = 3.0, 6.8; ax.plot([lo, hi], [lo, hi], "k-", lw=0.7); ax.fill_between([lo, hi], [lo * 0.98, hi * 0.98], [lo * 1.02, hi * 1.02], color="0.85", zorder=0, label="±2 %")
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
    ax.set_title(f"{LABEL[m]}\nMAPE a = {mape(d.a_err):.2f} % (n={len(d)} ok cubic)", fontsize=9); ax.set_xlabel("experimental a (Å)")
np.atleast_1d(axs)[0].set_ylabel("predicted a (Å)")
h, l = np.atleast_1d(axs)[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 0.0), markerscale=2.5)
fig.suptitle("Predicted vs experimental lattice constant, cubic solids with a successful fit", fontsize=11)
fig.tight_layout(rect=(0, 0.07, 1, 1)); fig.savefig(f"{H}/charts/parity_a_cubic.png", dpi=150); plt.close(fig)
# heatmap of a errors per solid
M = np.array([[df[(df.model == m) & (df.solid == s)].aeq_err.iloc[0] if len(df[(df.model == m) & (df.solid == s)]) else np.nan for s in order] for m in order_m], float)
F = np.array([[(df[(df.model == m) & (df.solid == s)].status.iloc[0] != "ok") if len(df[(df.model == m) & (df.solid == s)]) else True for s in order] for m in order_m])
MB = np.array([[df[(df.model == m) & (df.solid == s)].B_err.iloc[0] if len(df[(df.model == m) & (df.solid == s)]) else np.nan for s in order] for m in order_m], float)
for nm, MM, lim, ttl in [("heatmap_a_err.png", M, 4, "volume-equivalent a error (%)"), ("heatmap_B_err.png", MB, 60, "bulk modulus error (%)")]:
    MM = np.where(F, np.nan, MM)   # failed / missing cells are left blank (grey) and marked with x
    fig, ax = plt.subplots(figsize=(18, 4.2))
    cmap = plt.get_cmap("RdBu_r").copy(); cmap.set_bad("0.82")
    im = ax.imshow(np.ma.masked_invalid(np.clip(MM, -lim, lim)), cmap=cmap, vmin=-lim, vmax=lim, aspect="auto")
    for i in range(MM.shape[0]):
        for j in range(MM.shape[1]):
            if F[i, j]: ax.text(j, i, "×", ha="center", va="center", fontsize=9, color="k", fontweight="bold")
    ax.set_yticks(range(len(order_m))); ax.set_yticklabels([LABEL[m] for m in order_m])
    ax.set_xticks(range(len(order))); ax.set_xticklabels(order, rotation=90, fontsize=7)
    # class separators + class names on a secondary top axis (keeps them clear of the title)
    b = 0; cpos, cnames = [], []
    for k in CLASSES:
        nk = sum(refs.loc[s, "cls"] == k for s in order)
        if nk:
            cpos.append(b + nk / 2 - 0.5); cnames.append(f"{k} ({nk})")
            if b + nk < len(order): ax.axvline(b + nk - 0.5, color="k", lw=1.0)
        b += nk
    top = ax.secondary_xaxis("top"); top.set_xticks(cpos); top.set_xticklabels(cnames, fontsize=8); top.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, pad=0.01); cb.set_label(f"{ttl}\n(colour clipped at ±{lim} %)", fontsize=8)
    ax.set_title(f"Per-solid {ttl} vs experiment  (grey × = failed fit or no result)", pad=22)
    fig.tight_layout(); fig.savefig(f"{H}/charts/{nm}", dpi=150); plt.close(fig)
# cost vs accuracy
fig, ax = plt.subplots(figsize=(6.4, 4.6))
for m in order_m:
    S = summ[m]; ax.scatter(S["wall_common_s"] / 60, S["MAPE_a_eq_common"], s=60, color=COL[m], label=f"{S['label']} (B MAPE {S['MAPE_B_common']:.1f} %)", edgecolor="k")
ax.set_xlabel(f"total wall time, common subset of {len(common)} solids, 2 CPU cores (min)"); ax.set_ylabel(f"MAPE a, common subset (%)"); ax.grid(alpha=0.3)
ax.set_ylim(0, max(summ[m]["MAPE_a_eq_common"] for m in order_m) * 1.25); ax.set_xlim(0, max(summ[m]["wall_common_s"] for m in order_m) / 60 * 1.15)
ax.legend(fontsize=8, loc="lower right"); ax.set_title("Accuracy vs CPU cost (EOS incl. constant-volume relaxations)", fontsize=10)
fig.tight_layout(); fig.savefig(f"{H}/charts/cost_vs_accuracy.png", dpi=150); plt.close(fig)
print(json.dumps({m: {k: summ[m][k] for k in ["n_ok", "n_failed", "MAPE_a_eq_common", "MAPE_B_common", "MAPE_a_eq_all", "MAPE_B_all", "wall_common_s", "wall_total_s"]} for m in summ}, indent=0)); print("common", len(common))
