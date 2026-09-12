import sys
sys.path.insert(0,'routing-evidence')
from escape_helpers import *
b=p.LoadBoard('kicad/haven_dev_board.kicad_pcb')
remove_tracks(b,['6c54e9ef-0ccb-42c0-ac17-00ad0c087df0','8d4ed71a-3c8b-42dc-b561-beeb5ef67c58','38ad71a8-b585-4950-a2fa-89d3c1d65372','d0c3f046-7fe9-4d9f-b49a-0bb2d819c77e','d1c1712f-8a47-46e5-bdf4-ef8c5df31785','e21bf12e-5ee9-4dc9-b0db-6e58f35634ad','f04c7792-d9d7-4a74-9e6a-e62dce774004'])
assert via_at(b,'C19','2',(62.5355,24.9776))
assert escape(b,'C19','1',[(63.0841,24.9776),(63.0841,25.2),(62.6227,25.6614),(62.2106,25.6614)],.15,via=False)
save(b)
