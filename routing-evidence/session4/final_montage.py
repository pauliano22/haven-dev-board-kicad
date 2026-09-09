from PIL import Image,ImageDraw
from pathlib import Path
root=Path(__file__).parent
im=Image.new('RGB',(1500,1590),'#202020')
for k,ref in enumerate(['C6','C8','C9','C13','C22','C34','C38','C44','C46']):
 tile=Image.open(root/(ref+'-final.png')).crop((1000,530,1500,1060))
 im.paste(tile,((k%3)*500,(k//3)*530))
im.save(root/'final-bottom-montage.png')
