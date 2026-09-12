from escape_helpers import *
b=p.LoadBoard('kicad/haven_dev_board.kicad_pcb')
# U2 and L2 images inspected: outward A4 B.Cu escape, widen beyond BGA.
ok=escape(b,'U2','A4',[(67.3099,32.4772),(68.1,32.4772)],.15,via=False)
ok=segment(b,'SW',p.B_Cu,(68.1,32.4772),(71.0815,35.4587),.3) and ok
ok=segment(b,'SW',p.B_Cu,(71.0815,35.4587),(78.5903,35.4587),.3) and ok
if ok:save(b)
else:print('Not saved: complete path did not pass geometry checks')
