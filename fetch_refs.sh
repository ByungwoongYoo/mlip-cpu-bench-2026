#!/usr/bin/env bash
# Downloads the raw experimental reference files that refs/solids.json was built from, and checks their sha256.
# They are not redistributed here; check their licences before republishing them.
#   TSB16: CMR "uafd" CSVs (Tran, Stelzl, Blaha, J. Chem. Phys. 144, 204120 (2016))
#   LEJ14: arXiv:1204.2733v5 source tarball, ancillary files (CIFs + SupplMat.pdf)
set -euo pipefail
cd "$(dirname "$0")/refs"
curl -fsSL -o lattice_constants.csv https://cmr.fysik.dtu.dk/_downloads/cabb79a118fe2e413470acdd2696c828/lattice_constants.csv
curl -fsSL -o bulk_moduli.csv       https://cmr.fysik.dtu.dk/_downloads/13a24458bde291e7cc8ca860d97d5b94/bulk_moduli.csv
mkdir -p lej2014
curl -fsSL -A "Mozilla/5.0" -o lej2014/src.tgz https://arxiv.org/e-print/1204.2733v5
tar -xzf lej2014/src.tgz -C lej2014
sha256sum -c <<SUMS
41111b812c366becae59e2a1dfa6437a19f1d645170fb5bc68755c73910f7de2  lattice_constants.csv
087b2be3caa46e7e9b15cfc03c338bd5f773d657b6d66ed373174befae583c28  bulk_moduli.csv
fd829316caa4940fcf6a8448381903777d331a3f0305b9a04781802d9a60c1f9  lej2014/anc/SupplMat.pdf
SUMS
# build_refs.py parses the supplementary tables from a text dump (poppler-utils)
pdftotext -layout lej2014/anc/SupplMat.pdf lej2014/anc/supp.txt
echo "refs ready. Optional: python3 ../build_refs.py to rebuild solids.json and compare."
