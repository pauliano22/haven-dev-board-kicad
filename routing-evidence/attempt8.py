from escape_helpers import *
b=p.LoadBoard('kicad/haven_dev_board.kicad_pcb')
# Reviewed U15/C32 close-ups: leave G4 upward, bend right of G3 ground via.
escape(b,'U15','G4',[(58.4404,110.2738),(58.4404,110.15),(58.65,109.9404),(58.65,106.7123),(64.4103,100.952)],.09,via=False)
save(b)
