"""Export JLCPCB fab files for Rev A into fab/rev_a/.

Gerbers + drill come from kicad-cli. BOM and CPL are built here because the
port's footprints all sit at orientation 0 with rotation baked into pad
geometry, so KiCad's own placement export would report 0 degrees for every
part. Rotation comes from the source placement instead. MPN/LCSC numbers
come from OpenEarable's own BOM (designed for JLCPCB assembly), with
HAVEN_BOM.csv as fallback.
Usage: python3 tools/export_rev_a_fab.py
"""
import collections, csv, json, os, re, subprocess, zipfile
import openpyxl, pcbnew

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PCB = os.path.join(ROOT, "kicad", "haven_dev_board.kicad_pcb")
OUT = os.path.join(ROOT, "fab", "rev_a")
OE_BOM = os.path.join(ROOT, "..", "hardware", "openearable_base_pcb", "OpenEarable-PCB-main-2.0",
                      "OpenEarable-PCB-main-2.0-BOM.xlsx")
os.makedirs(OUT, exist_ok=True)

# Gerbers, drill and CPL must share one origin, or JLCPCB sees the parts
# offset from the board: put the drill/place (aux) origin at the board's
# bottom-left and export everything relative to it.
board = pcbnew.LoadBoard(PCB)
bb = board.GetBoardEdgesBoundingBox()
origin = pcbnew.VECTOR2I(bb.GetLeft(), bb.GetBottom())
ds = board.GetDesignSettings()
if ds.GetAuxOrigin() != origin:
    ds.SetAuxOrigin(origin)
    board.Save(PCB)

# gerbers + drill
gdir = os.path.join(OUT, "gerbers")
os.makedirs(gdir, exist_ok=True)
layers = "F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "--layers", layers, "--use-drill-file-origin",
                "--subtract-soldermask", "-o", gdir + "/", PCB], check=True, capture_output=True)
subprocess.run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--drill-origin", "plot",
                "--excellon-separate-th",
                "--generate-map", "--map-format", "gerberx2", "-o", gdir + "/", PCB], check=True, capture_output=True)
with zipfile.ZipFile(os.path.join(OUT, "haven_rev_a_gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(gdir)):
        z.write(os.path.join(gdir, f), f)

# part data
oe = {}
oe_fp = {}
ws = openpyxl.load_workbook(OE_BOM, read_only=True).active
for row in list(ws.iter_rows(values_only=True))[1:]:
    _, _, comment, des, fpn, _, mpn, mfr, lcsc, supplier = row
    for d in str(des).split(","):
        oe[d.strip()] = (comment, mpn, lcsc if supplier == "LCSC" else "")
        oe_fp[d.strip()] = fpn
haven = {}
with open(os.path.join(ROOT, "HAVEN_BOM.csv")) as f:
    for r in csv.DictReader(f):
        for d in r["Reference"].split(","):
            haven[d.strip()] = r["MPN"]
placement = json.load(open(os.path.join(ROOT, "extracted", "pcb_placement.json")))


def clean(v):
    v = re.sub(r"\.1$", "", str(v or "")).replace("&gt;", ">")
    return v.replace("mΩ", "mohm").replace("kΩ", "k").replace("MΩ", "M").replace("Ω", "R").replace(" >", " min ").replace(">", "min ")


groups = collections.OrderedDict()
cpl = []
for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
    ref = fp.GetReference()
    if fp.IsExcludedFromBOM() or fp.IsDNP():
        continue
    comment, mpn, lcsc = oe.get(ref, (fp.GetValue(), haven.get(ref, ""), ""))
    if ref == "R21":
        comment, mpn, lcsc = "0R", "0402WGF0000TCE", "C17168"
    comment = clean(comment or fp.GetValue())
    footprint = str(fp.GetFPID().GetLibItemName())
    if re.fullmatch(r"[0-9a-f]{32}", footprint):
        footprint = oe_fp.get(ref) or footprint
    key = (comment, footprint, mpn or "", lcsc or "")
    groups.setdefault(key, []).append(ref)
    back = fp.GetLayer() == pcbnew.B_Cu
    p = fp.GetPosition()
    rot = placement.get(ref, {}).get("rot") or 0
    cpl.append([ref, f"{pcbnew.ToMM(p.x - origin.x):.4f}mm", f"{pcbnew.ToMM(origin.y - p.y):.4f}mm",
                "Bottom" if back else "Top", f"{rot % 360:g}"])

with open(os.path.join(OUT, "haven_rev_a_bom.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "Manufacturer Part", "LCSC Part #"])
    for (comment, footprint, mpn, lcsc), refs in groups.items():
        w.writerow([comment, ",".join(refs), footprint, mpn, lcsc])
with open(os.path.join(OUT, "haven_rev_a_cpl.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    w.writerows(cpl)
missing = [r for (c, fpn, m, l), refs in groups.items() if not l for r in refs]
print(f"BOM lines {len(groups)}, parts {len(cpl)}, without LCSC #: {missing}")
