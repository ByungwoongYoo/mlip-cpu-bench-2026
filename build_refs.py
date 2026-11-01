"""Build refs/solids.json: experimental reference values for the MLIP EOS benchmark.
Sources (both are corrected to static-lattice 0 K, i.e. thermal expansion AND zero-point vibration removed,
which is what a static MLIP/DFT energy minimum should be compared with):
 [TSB16] F. Tran, J. Stelzl, P. Blaha, J. Chem. Phys. 144, 204120 (2016), doi:10.1063/1.4948636.
         Machine-readable 'Expt.' column of lattice_constants.csv / bulk_moduli.csv hosted at the
         DTU Computational Materials Repository, https://cmr.fysik.dtu.dk/uafd/uafd.html
         (paper text: 'experimental results that were corrected for thermal and zero-point vibrational effects').
 [LEJ14] K. Lejaeghere, V. Van Speybroeck, G. Van Oost, S. Cottenier, Crit. Rev. Solid State Mater. Sci. 39, 1 (2014),
         doi:10.1080/10408436.2013.772503, arXiv:1204.2733v5. Supplementary Tab. 2.2 (V0,exp corrected = V0,exp0 - dV1 - dV2)
         and Tab. 2.3 (B0,exp corrected = B0,exp0 - dB1 - dB2); structures = ancillary CIFs (PBE-relaxed shape).
Priority: TSB16 for all its 44 strongly bound cubic solids; LEJ14 adds elemental crystals not in TSB16.
Exclusions (documented in refs/EXCLUDED.md): molecular / rare-gas / van-der-Waals-bound or non-ground-state entries.
"""
import csv, json, re, hashlib, os
from ase.io import read
R = os.path.dirname(os.path.abspath(__file__)) + "/refs"
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
CLS = {}
for e in "Li Na K Rb Cs Ca Sr Ba Al V Ni Cu Nb Mo Rh Pd Ag Ta W Ir Pt Au Be Mg Sc Ti Cr Fe Co Zn Y Zr Tc Ru Cd Lu Hf Re Os In Tl Pb Ga Po".split(): CLS[e] = "metal"
for e in "C Si Ge Sn SiC BN BP AlN AlP AlAs GaN GaP GaAs InP InAs InSb B".split(): CLS[e] = "semiconductor"
for e in "LiH LiF LiCl NaF NaCl MgO".split(): CLS[e] = "ionic"
for e in "As Sb Bi".split(): CLS[e] = "semimetal"
OXIDE = {"MgO"}
NAT_CONV = {"diamond": 8, "zincblende": 8, "rocksalt": 8, "fcc": 4, "bcc": 2}
out = []
a = {r["material"]: r for r in csv.DictReader(open(f"{R}/lattice_constants.csv"))}
b = {r["material"]: r for r in csv.DictReader(open(f"{R}/bulk_moduli.csv"))}
for m, r in a.items():
    st = r["structure"]; ae = float(r["Expt."]); be = float(b[m]["Expt."])
    assert b[m]["structure"] == st
    out.append(dict(name=m, cls=CLS[m], oxide=m in OXIDE, structure=st, build="ase.build.bulk", cubic=True,
        a_ref=ae, V_ref_per_atom=round(ae**3 / NAT_CONV[st], 4), B_ref=be,
        source="TSB16", source_detail="Tran, Stelzl, Blaha, JCP 144, 204120 (2016); CMR uafd lattice_constants.csv & bulk_moduli.csv column 'Expt.'",
        correction="as published: experimental values corrected for thermal expansion and zero-point vibrations (paper Sec. II, Refs. 43,75); no further correction applied here"))
# ---- LEJ14 supplementary tables (pdftotext of anc/SupplMat.pdf) ----
txt = open(f"{R}/lej2014/anc/supp.txt").read()
s22 = txt[txt.index("Tab. 2.2"):txt.index("Tab. 2.3")]; s23 = txt[txt.index("Tab. 2.3"):txt.index("Tab. 2.4")]
num = r"(-?[0-9.]+)"
def parse(sec, n):
    d = {}
    for line in sec.splitlines():
        m = re.match(r"^\s*([A-Z][a-z]?)\s+" + r"\s+".join([num]*3) + r"\s*\[[0-9,]+\]\s+" + r"\s+".join([num]*n), line)
        if m: d[m.group(1)] = [float(x) for x in m.groups()[1:]]
    return d
V = parse(s22, 2); B = parse(s23, 2)   # V: VASP, Vexp(corr), Vexp0(raw), dV1, dV2 ; B: VASP, Bexp(corr), Bexp0(raw), dB1, dB2
LEJ_INCLUDE = "Be B Mg Sc Ti Cr Fe Co Zn Ga As Y Zr Tc Ru Cd In Sb Lu Hf Re Os Tl Pb Bi Po".split()
tsb_el = {o["name"] for o in out}
for e in LEJ_INCLUDE:
    assert e not in tsb_el
    v = V[e]; bb = B[e]
    # sanity: corrected = raw - dV1 - dV2 (rounding 0.02)
    assert abs(v[2] - v[3] - v[4] - v[1]) < 0.03, (e, v)
    assert abs(bb[2] - bb[3] - bb[4] - bb[1]) < 0.3, (e, bb)
    at = read(f"{R}/lej2014/anc/{e}.cif")
    out.append(dict(name=e, cls=CLS[e], oxide=False, structure="LEJ14-CIF", build=f"refs/lej2014/anc/{e}.cif (cell scaled isotropically to V_ref)",
        cubic=None, a_ref=None, V_ref_per_atom=v[1], B_ref=bb[1], n_atoms_cif=len(at),
        source="LEJ14", source_detail="Lejaeghere et al., Crit. Rev. Solid State Mater. Sci. 39, 1 (2014), arXiv:1204.2733v5 SupplMat Tab. 2.2/2.3",
        correction=f"V0: raw exp {v[2]} A3/atom - thermal dV1 {v[3]} - zero-point dV2 {v[4]} = {v[1]}; B0: raw exp {bb[2]} GPa - dB1 ({bb[3]}) - dB2 ({bb[4]}) = {bb[1]} GPa"))
# cubic Lej CIFs -> a_ref
import numpy as np
for o in out:
    if o["source"] == "LEJ14":
        at = read(f"{R}/lej2014/anc/{o['name']}.cif"); c = at.cell.cellpar()
        cub = np.allclose(c[:3], c[0], rtol=1e-4) and np.allclose(c[3:], 90, atol=1e-3)
        o["cubic"] = bool(cub)
        if cub:
            o["a_ref"] = round((o["V_ref_per_atom"] * len(at)) ** (1/3), 4); o["structure"] = f"LEJ14-CIF cubic conv. cell ({len(at)} atoms)"
# cross-check overlapping elements (TSB16 vs LEJ14) -> reported, not used
xc = []
for o in out:
    if o["source"] == "TSB16" and o["name"] in V and o["name"] in B:
        xc.append(dict(name=o["name"], V_TSB16=o["V_ref_per_atom"], V_LEJ14=V[o["name"]][1], dV_pct=round(100*(V[o["name"]][1]/o["V_ref_per_atom"]-1),2),
                       B_TSB16=o["B_ref"], B_LEJ14=B[o["name"]][1], dB_pct=round(100*(B[o["name"]][1]/o["B_ref"]-1),1)))
meta = dict(files={f: sha(f"{R}/{f}") for f in ["lattice_constants.csv", "bulk_moduli.csv", "lej2014/anc/SupplMat.pdf"]},
            urls=["https://cmr.fysik.dtu.dk/uafd/uafd.html", "https://arxiv.org/e-print/1204.2733v5"], n=len(out))
json.dump(dict(meta=meta, solids=out, crosscheck_TSB16_vs_LEJ14=xc), open(f"{R}/solids.json", "w"), indent=1)
print(len(out), {c: sum(o["cls"] == c for o in out) for c in set(CLS.values())})
for x in xc: print(x)
