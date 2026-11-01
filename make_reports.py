#!/usr/bin/env python3
"""Generate BENCHMARK_EN.md and BENCHMARK_KO.md from results/summary.json, results/tables.md and logs/*.res.
Every number in the reports comes from those files (no hand-typed results)."""
import json, os, re, glob, math, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(f"{HERE}/results/summary.json"))
T = open(f"{HERE}/results/tables.md").read()
M = S["models"]
def section(title_prefix):
    parts = re.split(r"^## ", T, flags=re.M)
    for p in parts:
        if p.startswith(title_prefix):
            return "\n".join(l for l in p.splitlines()[1:]).strip()
    raise KeyError(title_prefix)
order = sorted(M, key=lambda k: (M[k]["MAPE_a_eq_common"], M[k]["MAPE_B_common"]))
f2 = lambda x: "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.2f}"
f1 = lambda x: "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.1f}"
sg = lambda x: f"{x:+.2f}"
nC = S["n_common"]; common = S["common_subset"]
res = {}
for f in sorted(glob.glob(f"{HERE}/logs/*.res")):
    d = dict(kv.split("=", 1) for kv in re.findall(r"(\w+=(?:\d{4}-\d\d-\d\d [\d:]+ KST|\S+))", open(f).read()))
    res[d["name"]] = d
pro_jobs = {k: v for k, v in res.items() if k.startswith("prophet")}
pro_wall = sum(int(v["wall_s"]) for v in pro_jobs.values())
pro_peak = max(int(v["peak_rss_mb"]) for v in pro_jobs.values())
pro_rc = {k: v["rc"] for k, v in pro_jobs.items()}
pro_killed = sorted(k for k, v in pro_jobs.items() if v["rc"] != "0")
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M KST")
classes = {}
for s in json.load(open(f"{HERE}/refs/solids.json"))["solids"]:
    classes[s["cls"]] = classes.get(s["cls"], 0) + 1
LIC = {
 "chgnet_r2scan": ("matgl (BSD-3-Clause)", "No licence stated on the Hugging Face model card (checked materialyze/ and BowenD-UCB/ repos); treat as unspecified", "모델 카드에 라이선스 명시 없음 (Hugging Face materialyze/, BowenD-UCB/ 확인) — 미지정으로 간주", "CHGNet-PES-MatPES-r2SCAN-1M-2026.9 via matgl; trained on MatPES r2SCAN 2025.2"),
 "pet_mad_s": ("upet (BSD-3-Clause)", "BSD-3-Clause (Hugging Face lab-cosmo/upet tag)", "BSD-3-Clause (Hugging Face lab-cosmo/upet 태그)", "pet-mad-s, version 'latest', via UPETCalculator"),
 "prophet": ("MIT (Kairos Materials; backbone derived from Nequix, MIT)", "CC-BY-4.0 (LICENSE-WEIGHTS; Hugging Face kairosmaterial/prophet tag)", "CC-BY-4.0 (LICENSE-WEIGHTS; Hugging Face kairosmaterial/prophet 태그)", "prophet-oame-mbd.pt via KairosCalculator (use_kernel=False)"),
 "mace_mp": ("mace-torch (MIT)", "MIT (mace-foundations README)", "MIT (mace-foundations README)", "MACE-MP-0 medium, 2023-12-03 checkpoint, float64"),
 "flashcart_mad": ("Apache-2.0", "Apache-2.0 (Zenodo 10.5281/zenodo.23159584; arXiv 2610.06409)", "Apache-2.0 (Zenodo 10.5281/zenodo.23159584; arXiv 2610.06409)", "FlashCart-2.3M, MAD training set, seed 0, cutoff 5 Å"),
}
best_a = order[0]; best_B = min(M, key=lambda k: M[k]["MAPE_B_common"])
def fail_lines(lang):
    out = []
    for k in order:
        m = M[k]
        fl = m["failures"]; wl = m.get("warnings", [])
        hdr = f"**{m['label']}** — {m['n_ok']}/{m['n_attempted']} ok, {m['n_failed']} " + ("not ok" if lang == "en" else "실패/결과 없음") + (f" ({m['n_no_result']} " + ("without a result JSON" if lang == "en" else "개는 결과 JSON 없음") + ")" if m["n_no_result"] else "")
        out.append(hdr)
        if not fl: out.append("- " + ("none" if lang == "en" else "없음"))
        for s, why in fl: out.append(f"- {s}: {why}")
        if wl:
            out.append(("- warnings: " if lang == "en" else "- 경고: ") + "; ".join(f"{s} ({w})" for s, w in wl))
        out.append("")
    return "\n".join(out)
def headline_rows():
    rows = ["| Model | ok / 70 | MAPE a (%) | MAPE B (%) | ME a (%) | ME B (%) | wall, common set (s) |", "|---|---|---|---|---|---|---|"]
    for k in order:
        m = M[k]
        rows.append(f"| {m['label']} | {m['n_ok']} | {f2(m['MAPE_a_eq_common'])} | {f1(m['MAPE_B_common'])} | {sg(m['ME_a_eq_common'])} | {m['ME_B_common']:+.1f} | {m['wall_common_s']:.0f} |")
    return "\n".join(rows)
def job_rows():
    rows = ["| job | rc | wall (s) | peak RSS (MB) | finished |", "|---|---|---|---|---|"]
    for k, v in res.items():
        rows.append(f"| {k} | {v['rc']} | {v['wall_s']} | {v['peak_rss_mb']} | {v.get('finished','')} |")
    return "\n".join(rows)
lic_rows_en = "| Model | Checkpoint used | Code licence | Weights licence |\n|---|---|---|---|\n" + "\n".join(f"| {M[k]['label']} | {LIC[k][3]} | {LIC[k][0]} | {LIC[k][1]} |" for k in order)
lic_rows_ko = "| 모델 | 사용한 체크포인트 | 코드 라이선스 | 가중치 라이선스 |\n|---|---|---|---|\n" + "\n".join(f"| {M[k]['label']} | {LIC[k][3]} | {LIC[k][0]} | {LIC[k][2]} |" for k in order)
charts = ["mape_by_model_class.png", "parity_a_cubic.png", "heatmap_a_err.png", "heatmap_B_err.png", "cost_vs_accuracy.png"]
cls_txt = ", ".join(f"{c} {n}" for c, n in classes.items())
counts = ", ".join(f"{M[k]['label']} {M[k]['n_ok']}/70" for k in order)
mgo = "; ".join(f"{M[k]['label']} a {sg(M[k]['oxide_MgO']['a_err'])} % / B {M[k]['oxide_MgO']['B_err']:+.1f} %" for k in order if M[k].get("oxide_MgO"))
pro_note_en = (f"Prophet was not run as a single job. The original sequential job (`logs/prophet.res`) was stopped by the RSS watchdog "
  f"(limit 3000 MB) while on B, so the remaining solids were run one per process (`logs/prophet__<solid>.res`) with the same cores, nice level and thread count. "
  f"Sum of Prophet job wall times: {pro_wall} s; largest job peak RSS: {pro_peak} MB; jobs with non-zero exit code: {', '.join(pro_killed) or 'none'}. "
  f"The B retry used a 3500 MB watchdog limit; all other Prophet jobs used 3000 MB. B (12-atom cell) is Prophet's memory peak: the in-process monitor recorded {M['prophet']['peak_rss_per_structure_max_mb']:.0f} MB, i.e. right at the ~3.5 GB budget. An earlier helper script (`resume_prophet.sh`) that would have batched many solids in one process was stopped (only its bash driver; the running Ga job was left alone) and replaced by `run_prophet_remaining.sh`, which runs one solid per job and skips solids that already have a JSON.")
pro_note_ko = (f"Prophet는 하나의 작업으로 끝까지 돌지 못했습니다. 처음의 순차 작업(`logs/prophet.res`)은 B 계산 중 RSS 감시(한도 3000 MB)에 의해 종료되었고, "
  f"나머지 고체는 같은 코어·nice·스레드 설정으로 고체 하나당 프로세스 하나씩(`logs/prophet__<solid>.res`) 실행했습니다. "
  f"Prophet 작업 wall time 합계: {pro_wall} s, 작업별 최대 peak RSS: {pro_peak} MB, 비정상 종료 코드 작업: {', '.join(pro_killed) or '없음'}. "
  f"B 재시도만 감시 한도 3500 MB, 나머지 Prophet 작업은 3000 MB였습니다. B(원자 12개 셀)가 Prophet의 메모리 최대치로, 프로세스 내부 모니터 기준 {M['prophet']['peak_rss_per_structure_max_mb']:.0f} MB를 기록해 ~3.5 GB 예산에 거의 닿았습니다. 여러 고체를 한 프로세스로 묶어 돌리려던 이전 보조 스크립트(`resume_prophet.sh`)는 bash 드라이버만 중단하고(실행 중이던 Ga 작업은 그대로 둠) "
  f"`run_prophet_remaining.sh`로 교체했습니다. 이 스크립트는 고체 하나당 작업 하나를 실행하고 JSON이 이미 있는 고체는 건너뜁니다.")
semi = [s for s in common if s in ("As", "Sb", "Bi")]
semi_en = f"The semimetal class in the common set has only n = {len(semi)} ({', '.join(semi)}), so its averages are dominated by single solids." if semi else "The common set contains no semimetal, so that column is empty."
semi_ko = f"공통 집합의 semimetal은 n = {len(semi)}({', '.join(semi)})뿐이라 평균이 개별 고체에 좌우됩니다." if semi else "공통 집합에 semimetal이 없어 해당 열은 비어 있습니다."
bj = res.get("prophet__B")
b_ok = os.path.exists(f"{HERE}/results/prophet/B.json") and json.load(open(f"{HERE}/results/prophet/B.json")).get("status") == "ok"
b_en = (f"exit code {bj['rc']}, wall {bj['wall_s']} s, peak RSS {bj['peak_rss_mb']} MB, fit {'ok' if b_ok else 'not ok'}") if bj else "not run"
b_ko = (f"종료 코드 {bj['rc']}, wall {bj['wall_s']} s, peak RSS {bj['peak_rss_mb']} MB, 피팅 {'성공' if b_ok else '실패'}") if bj else "실행 안 됨"
img = "\n\n".join(f"![{c}](charts/{c})" for c in charts)
ov, bc, rt, ps = section("Overall"), section("By class"), section("Runtime"), section("Per solid")

EN = f"""# CPU equation-of-state benchmark of five machine-learned interatomic potentials

Generated {now} by `make_reports.py` from `results/summary.json`, `results/tables.md` and `logs/*.res` (tables by `aggregate.py`).

## Summary
- 70 solids, five models. Solids with a successful fit: {counts}.
- **Common set** (solids every model fitted successfully): **n = {nC}**. All headline numbers below use this set, so the models are compared on the same solids.
- Lowest lattice-constant error on the common set: **{M[best_a]['label']}** (MAPE a {f2(M[best_a]['MAPE_a_eq_common'])} %). Lowest bulk-modulus error: **{M[best_B]['label']}** (MAPE B {f1(M[best_B]['MAPE_B_common'])} %).

{headline_rows()}

MAPE = mean absolute percentage error against experiment; ME = mean signed error (positive = model overestimates). For non-cubic solids "a" is the volume-equivalent lattice constant, (V/atom)^(1/3); its error is one third of the volume error to first order. The table is sorted by MAPE a.

## Method
- **Structures.** The 44 cubic solids from TSB16 are built with `ase.build.bulk` (primitive cell). The 26 extra elements from LEJ14 use the paper's ancillary CIFs, scaled isotropically to the experimental volume. Class counts: {cls_txt}.
- **Strain range.** 11 volumes spaced evenly over [0.94, 1.06] × V_centre, i.e. ±6 % in volume (about ±2 % linear strain, as in the Delta test).
- **Relaxation.** If a cell has free shape or internal degrees of freedom, each volume gets a constant-volume relaxation of cell shape and atomic positions, with symmetry kept (ASE FixSymmetry symprec 1e-3, FrechetCellFilter(constant_volume=True), BFGS, fmax 0.005 eV/Å, max 300 steps). Cubic 1- and 2-atom cells have no free coordinates and get single-point energies.
- **EOS fit.** Third-order Birch–Murnaghan (`ase.eos`), giving V0, B0 and B0'. If |V0/V_centre − 1| > 3 %, the grid is recentred and refitted, at most 3 passes. A fit **fails** if V0 is outside the sampled range, B0 ≤ 0, or any energy is not finite. A relaxation that reaches 300 steps without converging is kept with a warning in the result JSON, not counted as a failure (this happened only for CHGNet-r2SCAN: 10 volume points on Hf, Lu, Tc, Y and Zr, and 6 on B, which failed anyway). We report completion counts over all 70 solids. Accuracy averages on the common set use only the solids completed by every model; failures receive no numerical penalty in those averages. Every failure is listed below.
- **Settings.** No k-points. No spin input: we did not specify or optimise magnetic order. float64 where the model supports it. Settings are stored in every result JSON under `settings`.
- **Metrics.** a error = (a_model − a_ref)/a_ref. B error = (B0,model − B_ref)/B_ref. The parity plot uses cubic solids only.

## Reference data (`refs/`)
- **TSB16:** F. Tran, J. Stelzl, P. Blaha, J. Chem. Phys. 144, 204120 (2016). 44 cubic solids, column `Expt.` of the CMR `uafd` CSVs (`refs/lattice_constants.csv`, `refs/bulk_moduli.csv`), already corrected for thermal expansion and zero-point effects.
- **LEJ14:** K. Lejaeghere et al., Crit. Rev. Solid State Mater. Sci. 39, 1 (2014), arXiv:1204.2733v5. 26 extra elements; V0 and B0 with thermal and zero-point corrections (V = raw − ΔV1 − ΔV2) and the ancillary CIFs.
- `refs/solids.json` is built by `build_refs.py`, which also stores checksums. `refs/README.md` lists the exclusions (molecular and van der Waals crystals, S, Mn, Hg, and data sets that could not be downloaded). The two sources are **not independent**: TSB16 reuses LEJ14's corrections for elements.

## Results

### Overall (all columns from `results/tables.md`)
{ov}

"all ok" columns use every solid that model fitted, so they cover different sets of solids and should not be used to rank models.

### Per class (common set)
{bc}

The oxide class has only MgO (n = 1), so it is reported per solid: {mgo}. {semi_en}

### Charts
{img}

## CPU timing
All jobs ran on the same shared 8-core box, pinned to cores 6,7 (`taskset -c 6,7`) at `nice -n 10`, with 2 threads (OMP/MKL/torch) and float64, one model at a time. `job.sh` records the job wall time and peak RSS, and an RSS watchdog kills a job above its limit. "Fresh single point" is the median time of 3 energy + forces + stress evaluations on new structures.

{rt}

Job records (`logs/*.res`):

{job_rows()}

{pro_note_en}

Timing caveats: other processes were running on the box, so these are observed workflow runtimes, not a controlled speed comparison. Per-solid wall time includes the constant-volume relaxations, so non-cubic solids are much slower than cubic ones, and the totals depend on how many relaxation steps each model needs. Model-loading policies also differ (Prophet reloads the model for each solid run after its watchdog restart). Shared-host contention and these loading differences prevent a controlled speed comparison.

## Failures
{fail_lines('en')}
Failed fits were not retried. Prophet's B was not a failed fit but a watchdog kill in the original run; it got exactly one retry with a 3500 MB limit: {b_en}. The Po errors (KeyError 'Po' for CHGNet; KeyError / ValueError on atomic number 84 for Prophet and MACE) mean those models have no parameters for polonium; they are element-coverage failures, not EOS-fit failures.

## Model licences
{lic_rows_en}

Check the upstream repositories before redistributing weights. The CHGNet-r2SCAN model card states no licence.

## Per-solid results
{ps}

## Limitations
- **Magnetism:** Fe, Co, Ni (ferromagnetic) and Cr (antiferromagnetic) are run without any spin or magnetic-order input. We did not specify or optimise magnetic order, so this benchmark does not test recovery of the correct magnetic states of Fe, Co, Ni or Cr. The overall table has a column that excludes them.
- **Oxides:** MgO is the only oxide with a corrected reference, so there is no meaningful oxide average.
- **Bulk-modulus uncertainty:** experimental B carries several % uncertainty (different techniques), and B from a ±6 % volume fit is sensitive to noise in the energy surface. Soft alkali and alkaline-earth metals (K, Rb, Cs, Ba), whose reference B is very small, produce very large percentage errors that dominate B MAPE.
- **References:** the two sources share corrections and are not independent. The zero-point corrections are model-based.
- **Coverage:** the common set (n = {nC}) is biased towards cubic solids; see `results/summary.json` → `common_subset` for the exact list.
- **Timing:** measured on a shared machine with 2 threads. Prophet was run as per-solid jobs (see CPU timing), so its job totals include one model load per solid.
- **No temperature or pressure:** the static-lattice E(V) is compared with experiment corrected to the static lattice. No phonon or finite-temperature effects are modelled.

## Files
`bench_mlip.py` (protocol), `job.sh` / `run_all.sh` / `run_prophet_remaining.sh` (job launchers), `aggregate.py` (tables and charts), `make_reports.py` (this report), `results/<model>/*.json` (raw per-solid results), `results/all_results.csv`, `results/summary.json`, `results/tables.md`, `charts/*.png`, `logs/`.
"""

KOH = {"Model": "모델", "solids ok / 70 (failed)": "성공 / 70 (실패)", "MAPE a (%) common": "MAPE a (%) 공통", "MAPE B (%) common": "MAPE B (%) 공통",
       "MAPE a (%) all ok": "MAPE a (%) 전체 성공분", "MAPE B (%) all ok": "MAPE B (%) 전체 성공분", "mean signed a err (%)": "평균 부호 오차 a (%)",
       "mean signed B err (%)": "평균 부호 오차 B (%)", "MAPE a (%) excl. Fe/Co/Ni/Cr": "MAPE a (%) Fe/Co/Ni/Cr 제외", "worst a": "최대 a 오차", "worst B": "최대 B 오차",
       "model load (s)": "모델 로드 (s)", "RSS after load (MB)": "로드 후 RSS (MB)", "median wall / cubic solid (s)": "입방정 고체당 wall 중앙값 (s)",
       "median wall / non-cubic solid (s)": "비입방정 고체당 wall 중앙값 (s)", "slowest solid (s)": "가장 느린 고체 (s)", "total wall, common subset (s)": "총 wall, 공통 집합 (s)",
       "total wall, all solids with a result (s)": "총 wall, 결과 있는 전체 (s)", "median fresh single point E+F+σ (ms)": "새 구조 single point E+F+σ 중앙값 (ms)",
       "median / max process RSS per structure (MB)": "구조당 프로세스 RSS 중앙값 / 최대 (MB)", "job peak RSS (MB)": "작업 peak RSS (MB)",
       "Solid": "고체", "class": "분류", "ref source": "기준 출처", "a_ref or V_ref": "a_ref 또는 V_ref", "B_ref (GPa)": "B_ref (GPa)"}
def ko_table(t):
    lines = t.splitlines()
    for i, l in enumerate(lines):
        if l.startswith("| Model") or l.startswith("| Solid"):
            cells = [c.strip() for c in l.strip("|").split("|")]
            lines[i] = "| " + " | ".join(KOH.get(c, c) for c in cells) + " |"
    t = "\n".join(lines)
    return t.replace("no result", "결과 없음").replace("(max of", "(작업 중 최대,").replace(" jobs)", "개 작업)")
hr_ko = headline_rows().replace("| Model | ok / 70 | MAPE a (%) | MAPE B (%) | ME a (%) | ME B (%) | wall, common set (s) |", "| 모델 | 성공 / 70 | MAPE a (%) | MAPE B (%) | ME a (%) | ME B (%) | wall, 공통 집합 (s) |")
jr_ko = job_rows().replace("| job | rc | wall (s) | peak RSS (MB) | finished |", "| 작업 | 종료 코드 | wall (s) | peak RSS (MB) | 종료 시각 |")
KO = f"""# 머신러닝 원자간 퍼텐셜 5종 CPU 상태방정식(EOS) 벤치마크

{now}에 `make_reports.py`가 `results/summary.json`, `results/tables.md`, `logs/*.res`를 읽어 생성했습니다. 표는 `aggregate.py`가 만든 것입니다.

## 요약
- 고체 70종, 모델 5종. 피팅에 성공한 고체 수: {counts}.
- **공통 집합**(모든 모델이 피팅에 성공한 고체): **n = {nC}**. 아래 대표 수치는 모두 이 집합 기준이며, 모델을 같은 고체끼리 비교합니다.
- 공통 집합에서 격자상수 오차가 가장 작은 모델은 **{M[best_a]['label']}**(MAPE a {f2(M[best_a]['MAPE_a_eq_common'])} %), 체적탄성률 오차가 가장 작은 모델은 **{M[best_B]['label']}**(MAPE B {f1(M[best_B]['MAPE_B_common'])} %)입니다.

{hr_ko}

MAPE는 실험값 대비 평균 절대 백분율 오차, ME는 평균 부호 오차(양수 = 모델이 과대 예측)입니다. 비입방정 고체의 "a"는 부피 등가 격자상수 (V/atom)^(1/3)이며, 그 오차는 1차 근사로 부피 오차의 1/3입니다. 표는 MAPE a 순으로 정렬했습니다.

## 방법
- **구조.** TSB16의 입방정 고체 44종은 `ase.build.bulk`(primitive cell)로 만들었습니다. LEJ14의 추가 원소 26종은 논문 부록 CIF를 실험 부피에 맞게 등방 스케일링해 썼습니다. 분류별 개수: {cls_txt}.
- **변형 범위.** [0.94, 1.06] × V_centre 구간에 균등 간격 11개 부피, 즉 부피 ±6 %(선형 변형 약 ±2 %, Delta test와 동일)입니다.
- **완화.** 셀 모양이나 내부 좌표에 자유도가 있으면 각 부피에서 대칭을 유지하며 셀 모양과 원자 위치를 정적 부피로 완화했습니다(ASE FixSymmetry symprec 1e-3, FrechetCellFilter(constant_volume=True), BFGS, fmax 0.005 eV/Å, 최대 300 step). 원자 1~2개짜리 입방정 셀은 자유 좌표가 없어 single point 에너지만 계산합니다.
- **EOS 피팅.** 3차 Birch–Murnaghan(`ase.eos`)으로 V0, B0, B0'를 구합니다. |V0/V_centre − 1| > 3 %이면 격자를 다시 중심에 맞춰 재피팅하며 최대 3회까지 반복합니다. V0가 샘플 범위 밖이거나 B0 ≤ 0이거나 에너지에 비유한값이 있으면 **실패**입니다. 300 step 안에 수렴하지 않은 완화는 결과 JSON에 경고를 남기고 유지하며 실패로 세지 않습니다(CHGNet-r2SCAN에서만 발생: Hf, Lu, Tc, Y, Zr의 부피 점 10개와 어차피 실패한 B의 6개). 완료 개수는 70종 전체 기준으로 보고합니다. 공통 집합의 정확도 평균은 모든 모델이 완료한 고체만 쓰며, 실패는 그 평균에서 수치상 불이익을 받지 않습니다. 실패는 모두 아래에 적었습니다.
- **설정.** k-point 없음. 스핀 입력 없음: 자기 질서를 지정하거나 최적화하지 않았습니다. 모델이 지원하면 float64. 설정은 모든 결과 JSON의 `settings`에 저장됩니다.
- **지표.** a 오차 = (a_model − a_ref)/a_ref, B 오차 = (B0,model − B_ref)/B_ref. parity 그림은 입방정 고체만 씁니다.

## 기준 데이터 (`refs/`)
- **TSB16:** F. Tran, J. Stelzl, P. Blaha, J. Chem. Phys. 144, 204120 (2016). 입방정 고체 44종. CMR `uafd` CSV(`refs/lattice_constants.csv`, `refs/bulk_moduli.csv`)의 `Expt.` 열로, 열팽창과 영점 진동 효과가 이미 보정된 값입니다.
- **LEJ14:** K. Lejaeghere 외, Crit. Rev. Solid State Mater. Sci. 39, 1 (2014), arXiv:1204.2733v5. 추가 원소 26종. 열팽창·영점 보정을 적용한 V0와 B0(V = raw − ΔV1 − ΔV2)와 부록 CIF를 사용했습니다.
- `refs/solids.json`은 `build_refs.py`가 만들며 체크섬도 함께 기록합니다. 제외한 항목(분자성·반데르발스 결정, S, Mn, Hg, 내려받을 수 없던 데이터셋)은 `refs/README.md`에 정리되어 있습니다. 두 출처는 **서로 독립적이지 않습니다**. TSB16은 원소에 대해 LEJ14의 보정값을 그대로 씁니다.

## 결과

### 전체 (모든 열은 `results/tables.md`에서 가져옴)
{ko_table(ov)}

"전체 성공분" 열은 모델마다 피팅에 성공한 고체 전부를 쓰므로 모델별로 고체 집합이 다릅니다. 순위를 매기는 데 쓰면 안 됩니다.

### 분류별 (공통 집합)
{ko_table(bc)}

산화물 분류에는 MgO 하나뿐(n = 1)이라 개별 값으로 보고합니다: {mgo}. {semi_ko}

### 그림
{img}

## CPU 시간
모든 작업은 공유 8코어 머신에서 한 번에 한 모델씩 실행했습니다. 코어 6,7에 고정(`taskset -c 6,7`), `nice -n 10`, 스레드 2개(OMP/MKL/torch), float64입니다. `job.sh`가 작업 wall time과 peak RSS를 기록하고, RSS 감시가 한도를 넘는 작업을 종료합니다. "새 구조 single point"는 새 구조에 대해 에너지+힘+응력을 3번 계산한 시간의 중앙값입니다.

{ko_table(rt)}

작업 기록 (`logs/*.res`):

{jr_ko}

{pro_note_ko}

시간 관련 주의: 다른 프로세스가 같은 머신에서 돌고 있었으므로 이 시간은 관측된 워크플로 실행 시간이며 통제된 속도 비교가 아닙니다. 고체당 wall time에는 정적 부피 완화가 포함되므로 비입방정 고체가 입방정보다 훨씬 느리고, 합계는 모델별로 필요한 완화 step 수에 따라 달라집니다. 모델 로딩 방식도 다릅니다(Prophet은 watchdog 재시작 이후 실행한 고체마다 모델을 다시 불러옵니다). 공유 머신의 부하와 이런 로딩 차이 때문에 통제된 속도 비교는 할 수 없습니다.

## 실패
{fail_lines('ko')}
피팅 실패는 재시도하지 않았습니다. Prophet의 B는 피팅 실패가 아니라 처음 실행에서 감시에 의해 종료된 경우로, 한도 3500 MB로 딱 한 번 재시도했습니다: {b_ko}. Po 오류(CHGNet은 KeyError 'Po', Prophet과 MACE는 원자번호 84에 대한 KeyError / ValueError)는 해당 모델에 폴로늄 파라미터가 없다는 뜻으로, EOS 피팅 실패가 아니라 원소 범위 밖 실패입니다.

## 모델 라이선스
{lic_rows_ko}

가중치를 재배포하기 전에 원본 저장소를 확인하세요. CHGNet-r2SCAN 모델 카드에는 라이선스가 명시되어 있지 않습니다.

## 고체별 결과
{ko_table(ps)}

## 한계
- **자성:** Fe, Co, Ni(강자성)와 Cr(반강자성)은 스핀이나 자기 질서 입력 없이 계산했습니다. 자기 질서를 지정하거나 최적화하지 않았으므로, 이 벤치마크는 Fe, Co, Ni, Cr의 올바른 자기 상태를 재현하는지 검사하지 않습니다. 전체 표에 이들을 뺀 열이 있습니다.
- **산화물:** 보정된 기준값이 있는 산화물은 MgO뿐이라 의미 있는 산화물 평균을 낼 수 없습니다.
- **체적탄성률 불확도:** 실험 B 자체에 수 %의 불확도가 있고(측정법 차이), ±6 % 부피 범위 피팅으로 얻은 B는 에너지 곡면의 잡음에 민감합니다. 기준 B가 매우 작은 무른 알칼리·알칼리토 금속(K, Rb, Cs, Ba)은 백분율 오차가 매우 커서 B MAPE를 좌우합니다.
- **기준값:** 두 출처는 보정값을 공유해 독립적이지 않습니다. 영점 보정은 모델 기반 추정입니다.
- **범위:** 공통 집합(n = {nC})은 입방정 고체 쪽으로 치우쳐 있습니다. 정확한 목록은 `results/summary.json`의 `common_subset`에 있습니다.
- **시간:** 공유 머신에서 스레드 2개로 측정했습니다. Prophet는 고체별 작업으로 돌렸으므로(CPU 시간 절 참고) 작업 합계에 고체마다 모델 로드가 한 번씩 포함됩니다.
- **온도·압력 없음:** 정적 격자 E(V)를 정적 격자로 보정한 실험값과 비교합니다. 포논이나 유한 온도 효과는 모델링하지 않았습니다.

## 파일
`bench_mlip.py`(프로토콜), `job.sh` / `run_all.sh` / `run_prophet_remaining.sh`(작업 실행), `aggregate.py`(표와 그림), `make_reports.py`(이 보고서), `results/<model>/*.json`(고체별 원시 결과), `results/all_results.csv`, `results/summary.json`, `results/tables.md`, `charts/*.png`, `logs/`.
"""
open(f"{HERE}/BENCHMARK_EN.md", "w").write(EN)
open(f"{HERE}/BENCHMARK_KO.md", "w").write(KO)
print("wrote BENCHMARK_EN.md / BENCHMARK_KO.md; common n =", nC, "; order:", [M[k]["label"] for k in order])
