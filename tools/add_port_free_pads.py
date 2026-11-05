"""Add the standalone pads the EasyEDA->KiCad port dropped.

The source board has 8 pads that belong to no component: battery (V_BAT,
GND), speaker (DAC_P, DAC_N) and four I2S test pads (BCLK, LRCLK, DIN,
DOUT), all on the bottom side. The port only converted pads inside
footprints, so the battery and speaker had nothing to solder to. Each pad
becomes a one-pad footprint, excluded from BOM and placement files (wires
or test probes go here, not parts). Run once. Usage:
  python3 tools/add_port_free_pads.py <board.kicad_pcb>
"""
import glob, json, os, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = glob.glob(os.path.join(HERE, "..", "extracted", "stock_openearable", "PCB", "*.epcb"))[0]
MM = 0.0254
NAMES = {"V_BAT": "TP_BAT+", "GND": "TP_BAT-", "DAC_P": "TP_SPK+", "DAC_N": "TP_SPK-",
         "BCLK": "TP_BCLK", "LRCLK": "TP_LRCLK", "DIN": "TP_DIN", "DOUT": "TP_DOUT"}

board = pcbnew.LoadBoard(sys.argv[1])
nets = board.GetNetsByName()
existing = {f.GetReference() for f in board.GetFootprints()}
added = 0
for line in open(SRC):
    if not line.startswith('["PAD"'):
        continue
    d = json.loads(line)
    net, layer, x, y, shape = d[3], d[4], d[6], d[7], d[10]
    ref = NAMES[net]
    if ref in existing:
        continue
    back = layer == 2
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(ref)
    fp.SetValue("pad")
    fp.SetFPID(pcbnew.LIB_ID("haven_footprints", "free_pad"))
    fp.SetAttributes(pcbnew.FP_SMD | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    pad = pcbnew.PAD(fp)
    pad.SetNumber("1")
    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    if shape[0] == "RECT":
        pad.SetShape(pcbnew.PAD_SHAPE_RECT)
        size = (shape[1], shape[2])
    else:
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        size = (shape[1], shape[1])
    pad.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(size[0] * MM), pcbnew.FromMM(size[1] * MM)))
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.F_Mask)
    pad.SetLayerSet(ls)
    fp.Add(pad)
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x * MM), pcbnew.FromMM(y * MM)))
    board.Add(fp)
    if back:
        fp.Flip(fp.GetPosition(), False)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x * MM), pcbnew.FromMM(y * MM)))
    for p in fp.Pads():
        p.SetNet(nets[net])
    added += 1
pcbnew.SaveBoard(sys.argv[1], board)
print(f"added {added} free pads")
