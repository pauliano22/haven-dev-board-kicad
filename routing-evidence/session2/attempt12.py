import sys
sys.path.insert(0,'routing-evidence')
from escape_helpers import *
b=p.LoadBoard('kicad/haven_dev_board.kicad_pcb')
remove_tracks(b,['adf42fb7-c276-451a-852c-8ba2d7d5ee39','e3e7f2c9-f5ba-4a16-a17a-39e485c18236','84f3ca19-2cde-4829-88b3-1a3f20117e56'])
assert via_at(b,'C14','1',(110.5341,62.9776))
assert escape(b,'C14','2',[(109.9855,62.9776),(109.2,62.9776),(109.2,64.5617),(110.5339,65.8956)],.15,via=False)
save(b)
