#!/usr/bin/env python
"""bench_mlip.py — CPU equation-of-state benchmark of machine-learned interatomic potentials (MLIPs)
against thermal- and zero-point-corrected experimental lattice constants / volumes and bulk moduli.

Usage (run inside the venv that provides the model):
    python bench_mlip.py --model mace_mp [--solids Si,Cu,Mg] [--threads 2]
Writes results/<model>/<solid>.json (one per solid) and results/<model>/_run.json (settings + timing summary).

Protocol (fixed for every model, recorded in every JSON under "settings"):
  * Structure at the experimental reference volume (cubic: ase.build.bulk primitive cell; others: Lejaeghere-2014
    CIF scaled isotropically). No k-points (MLIPs are k-point free); float64 where the model supports it.
  * 11 volumes uniformly in [0.94, 1.06] x V_centre (±6 % in volume ≈ ±2 % linear strain, as in the Delta test).
  * At each volume: if the cell has any free internal/shape degree of freedom, constant-volume relaxation of
    cell shape + atomic positions with symmetry constrained (ase FixSymmetry, symprec 1e-3,
    FrechetCellFilter(constant_volume=True), BFGS, fmax 0.005 eV/Å, max 300 steps). Cubic 1-/2-atom cells have no
    free coordinates and are evaluated as single points.
  * Birch–Murnaghan (3rd order) fit of E(V) -> V0, B0, B0'. If V0 is outside ±3 % of V_centre the grid is
    recentred on V0 (or on the lowest-energy grid point if the fit failed) and refitted, up to 3 passes. A fit whose V0 lies outside the sampled range, B0<=0, or any
    non-finite energy is a FAILURE and is reported, never silently dropped.
"""
import argparse, json, os, sys, time, threading, traceback, platform, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
# Directory holding the Prophet checkpoint (prophet-oame-mbd.pt) and the FlashCart MAD checkpoint tree
# (flashcart/models/mad/...). Set MLIP_MODEL_DIR to where you downloaded them.
SWEEP = os.environ.get("MLIP_MODEL_DIR", os.path.join(HERE, "models"))
SETTINGS = dict(n_volumes=11, vol_range=[0.94, 1.06], recentre_tol=0.03, max_passes=3, recentre_rule="if |V0/Vc-1|>3% (or fit failed) re-sample around V0 if the fit is sane (B0>0 and V0 within 10% of the sampled range), else around the lowest-energy grid point", eos="birchmurnaghan (ase.eos)",
                relax=dict(optimizer="BFGS", fmax_eV_per_A=0.005, max_steps=300, cell_filter="FrechetCellFilter(constant_volume=True)",
                           symmetry="FixSymmetry(symprec=1e-3)", applied_when="cell has free shape or internal DOF"),
                kpoints="none (MLIP)", spin="none (models are spin-unaware)", dtype="float64 where supported")

def load_model(key):
    import torch
    if key == "mace_mp":
        from mace.calculators import mace_mp
        return mace_mp(model="medium", device="cpu", default_dtype="float64"), "MACE-MP-0 medium (mace-torch, 2023-12-03 checkpoint)"
    if key == "chgnet_r2scan":
        import matgl
        from matgl.ext.ase import PESCalculator
        return PESCalculator(matgl.load_model("CHGNet-PES-MatPES-r2SCAN-1M-2026.9")), "matgl CHGNet-PES-MatPES-r2SCAN-1M-2026.9"
    if key == "pet_mad_s":
        from upet.ase import UPETCalculator
        return UPETCalculator(model="pet-mad-s", version="latest", device="cpu"), "UPET pet-mad-s (latest)"
    if key == "prophet":
        os.chdir(SWEEP)
        from prophet import KairosCalculator
        return KairosCalculator(model_path="prophet-oame-mbd.pt", use_kernel=False, device="cpu"), "Prophet OAME-MBD (KairosCalculator)"
    if key == "flashcart_mad":
        from flashcart.calculators import FlashCartCalculator
        return FlashCartCalculator(checkpoint=f"{SWEEP}/flashcart/models/mad/i3c3f96l2_lr2.5e-3_wd1.2e-2_fw0.1_r5.0_s0/best",
                                   device="cpu", add_atomic_offsets=True), "FlashCart MAD (seed 0)"
    raise SystemExit(f"unknown model {key}")

class RSSMonitor:
    """Samples this process's resident set size every 10 ms; peak() returns max since last reset (MB)."""
    def __init__(self):
        self._peak = 0; self._stop = False
        threading.Thread(target=self._run, daemon=True).start()
    @staticmethod
    def rss():
        for l in open("/proc/self/status"):
            if l.startswith("VmRSS"): return int(l.split()[1]) / 1024
        return 0
    def _run(self):
        while not self._stop:
            self._peak = max(self._peak, self.rss()); time.sleep(0.01)
    def reset(self): self._peak = self.rss()
    def peak(self): return max(self._peak, self.rss())
    def hwm(self):
        for l in open("/proc/self/status"):
            if l.startswith("VmHWM"): return int(l.split()[1]) / 1024

NAT_CONV = {"diamond": 8, "zincblende": 8, "rocksalt": 8, "fcc": 4, "bcc": 2}

def build(s):
    from ase.build import bulk
    from ase.io import read
    if s["build"] == "ase.build.bulk":
        return bulk(s["name"], s["structure"], a=s["a_ref"])
    at = read(os.path.join(HERE, "refs/lej2014/anc", s["name"] + ".cif"))
    at.set_cell(at.cell * (s["V_ref_per_atom"] * len(at) / at.get_volume()) ** (1 / 3), scale_atoms=True)
    return at

def has_free_dof(at):
    from ase.spacegroup.symmetrize import check_symmetry
    ds = check_symmetry(at, 1e-3)
    cubic = 195 <= ds.number <= 230
    # all Wyckoff positions fixed? (cubic elemental/binary prototypes here have 1-2 atoms on special positions)
    return not (cubic and len(at) <= 2), ds.number

def energy_at(at0, vol, calc, relax, counters):
    from ase.constraints import FixSymmetry
    at = at0.copy()
    at.set_cell(at.cell * (vol / at.get_volume()) ** (1 / 3), scale_atoms=True)
    at.calc = calc
    nsteps = 0; conv = True
    if relax:
        from ase.filters import FrechetCellFilter
        from ase.optimize import BFGS
        at.set_constraint(FixSymmetry(at, symprec=1e-3))
        f = FrechetCellFilter(at, constant_volume=True)
        opt = BFGS(f, logfile=None)
        conv = bool(opt.run(fmax=SETTINGS["relax"]["fmax_eV_per_A"], steps=SETTINGS["relax"]["max_steps"]))
        nsteps = opt.nsteps
    t = time.perf_counter(); e = at.get_potential_energy(); counters["sp_times"].append(time.perf_counter() - t)
    return e, nsteps, conv, at.cell.cellpar().round(5).tolist()

def run_solid(s, calc, mon):
    from ase.eos import EquationOfState
    from ase.units import GPa
    rec = dict(solid=s["name"], cls=s["cls"], oxide=s["oxide"], ref=s, settings=SETTINGS, status="ok", passes=[])
    mon.reset(); t0 = time.perf_counter(); counters = dict(sp_times=[])
    try:
        at0 = build(s); nat = len(at0)
        relax, sg = has_free_dof(at0); rec.update(n_atoms=nat, spacegroup_ref=sg, relaxed=relax)
        vc = s["V_ref_per_atom"] * nat
        for p in (1, 2, 3):
            vols = np.linspace(*SETTINGS["vol_range"], SETTINGS["n_volumes"]) * vc
            E, steps, convs, cells = [], [], [], []
            for v in vols:
                e, n, c, cp = energy_at(at0, v, calc, relax, counters)
                E.append(e); steps.append(n); convs.append(c); cells.append(cp)
            E = np.array(E)
            if not np.all(np.isfinite(E)): raise RuntimeError("non-finite energy")
            p_rec = dict(pass_=p, V_centre=vc, volumes=vols.tolist(), energies=E.tolist(), relax_steps=steps,
                         relax_converged=convs, cellpars=cells)
            rec["passes"].append(p_rec)   # raw E(V) kept even if the fit fails
            try:
                eos = EquationOfState(vols, E, eos="birchmurnaghan"); v0, e0, b = eos.fit()
                p_rec.update(V0=v0, E0=e0, B0_GPa=b / GPa, B0_prime=float(eos.eos_parameters[2]))
                fitE = eos.func(vols, *eos.eos_parameters)
                p_rec["fit_rms_meV_per_atom"] = float(np.sqrt(np.mean((fitE - E) ** 2)) / nat * 1000)
            except Exception as ex:
                p_rec["fit_error"] = f"{type(ex).__name__}: {ex}"; v0 = None
            if v0 is not None and abs(v0 / vc - 1) <= SETTINGS["recentre_tol"]: break
            # recentre: on the fitted V0 if it is plausible, otherwise on the lowest-energy grid point
            ok_fit = v0 is not None and p_rec["B0_GPa"] > 0 and vols[0] * 0.9 <= v0 <= vols[-1] * 1.1
            vc = v0 if ok_fit else float(vols[int(np.argmin(E))])
        if "fit_error" in rec["passes"][-1]: raise RuntimeError("BM fit failed on final pass: " + rec["passes"][-1]["fit_error"])
        last = rec["passes"][-1]; v0 = last["V0"]; b0 = last["B0_GPa"]
        problems = []
        if not (min(last["volumes"]) <= v0 <= max(last["volumes"])): problems.append("V0 outside sampled range")
        if not (b0 > 0 and np.isfinite(b0)): problems.append("B0 non-positive/non-finite")
        if not all(last["relax_converged"]): rec["warning"] = "some constant-volume relaxations hit max_steps"
        if problems: rec["status"] = "failed"; rec["failure"] = "; ".join(problems)
        vpa = v0 / nat
        rec.update(V0_per_atom=vpa, B0_GPa=b0, V_err_pct=100 * (vpa / s["V_ref_per_atom"] - 1),
                   a_eq_err_pct=100 * ((vpa / s["V_ref_per_atom"]) ** (1 / 3) - 1), B_err_pct=100 * (b0 / s["B_ref"] - 1))
        if s.get("cubic") and s.get("a_ref"):
            nconv = NAT_CONV.get(s["structure"], nat)   # LEJ cubic CIFs are conventional cells already
            rec["a_pred"] = (vpa * nconv) ** (1 / 3); rec["a_err_pct"] = 100 * (rec["a_pred"] / s["a_ref"] - 1)
    except Exception as ex:
        rec["status"] = "failed"; rec["failure"] = f"{type(ex).__name__}: {ex}"; rec["traceback"] = traceback.format_exc()[-3000:]
    rec["wall_s"] = time.perf_counter() - t0
    try:   # 3 fresh (uncached) single-point energy+forces+stress evaluations at the reference structure
        ts = []
        for _ in range(3):
            at = build(s); at.calc = calc; calc.reset() if hasattr(calc, "reset") else None
            t1 = time.perf_counter(); at.get_potential_energy(); at.get_forces(); at.get_stress(); ts.append(time.perf_counter() - t1)
        rec["median_fresh_singlepoint_ms"] = 1000 * float(np.median(ts))
    except Exception as ex:
        rec["median_fresh_singlepoint_ms"] = None; rec["singlepoint_error"] = str(ex)
    rec["peak_rss_mb"] = mon.peak()
    rec["n_volume_points"] = len(counters["sp_times"])
    return rec

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--model", required=True); ap.add_argument("--solids", default="all")
    ap.add_argument("--threads", type=int, default=2); a = ap.parse_args()
    import torch; torch.set_num_threads(a.threads)
    refs = json.load(open(os.path.join(HERE, "refs/solids.json")))["solids"]
    if a.solids != "all": refs = [r for r in refs if r["name"] in a.solids.split(",")]
    out = os.path.join(HERE, "results", a.model); os.makedirs(out, exist_ok=True)
    mon = RSSMonitor(); rss_before = mon.rss(); t = time.perf_counter()
    calc, label = load_model(a.model)
    load = dict(load_s=time.perf_counter() - t, rss_after_load_mb=mon.rss(), rss_before_load_mb=rss_before)
    torch.set_num_threads(a.threads)
    summ = []
    for s in refs:
        r = run_solid(s, calc, mon); r.update(model=a.model, model_label=label)
        json.dump(r, open(os.path.join(out, s["name"] + ".json"), "w"), indent=1, default=float)
        summ.append((s["name"], r["status"], round(r.get("a_eq_err_pct", float("nan")), 2), round(r.get("B_err_pct", float("nan")), 1), round(r["wall_s"], 1)))
        print(*summ[-1], r.get("failure", ""), flush=True)
    json.dump(dict(model=a.model, label=label, settings=SETTINGS, threads=a.threads, load=load, process_peak_rss_mb=mon.hwm(),
                   host=dict(platform=platform.platform(), cpu=platform.processor(), nproc=os.cpu_count(), affinity=sorted(os.sched_getaffinity(0))),
                   versions=dict(python=sys.version.split()[0], torch=torch.__version__, ase=__import__("ase").__version__),
                   finished=time.strftime("%Y-%m-%d %H:%M:%S %Z"), solids=summ), open(os.path.join(out, "_run.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
