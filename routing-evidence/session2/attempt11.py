import sys
sys.path.insert(0,'routing-evidence')
from escape_helpers import *
b=p.LoadBoard('kicad/haven_dev_board.kicad_pcb')
remove_tracks(b,['12b88f3f-e84b-4966-ac7f-86fdcfa5d7fd','74317d39-4346-4c3b-9ca9-661236c5a332','cdfee38c-8942-4e2c-8f67-896f749539be'])
assert escape(b,'C2','1',[(110.5341,84.4276),(110.5341,85.1149),(109.762,85.1149)],.15,via=False)
assert escape(b,'C2','2',[(109.9855,84.4276),(109.9855,83.6984),(110.5339,83.15),(110.5339,77.7983)],.15,via=False)
save(b)
