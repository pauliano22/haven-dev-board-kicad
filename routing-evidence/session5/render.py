import pathlib,json,re,sys,fitz,os
from PIL import Image,ImageDraw
root=pathlib.Path('C:/Work/haven-board/routing-evidence/session5')
pads=json.loads((root/'pads.json').read_text())
for ref in sys.argv[1:] or pads:
 ps=pads[ref];side=5.5;cx=sum(a['x'] for a in ps)/2;cy=sum(a['y'] for a in ps)/2;x=cx-side/2;y=cy-side/2
 im=Image.new('RGB',(1500,1060),'#202020');draw=ImageDraw.Draw(im)
 for k,l in enumerate(['F_Cu','In1_Cu','In2_Cu','In3_Cu','In4_Cu','B_Cu']):
  svg=pathlib.Path(os.environ.get('HAVEN_SVG_DIR','C:/Work/haven-svg-session5')+'/haven_dev_board-'+l+'.svg').read_text()
  svg=re.sub(r'viewBox="[^"]*"',f'viewBox="{x} {y} {side} {side}"',svg,count=1)
  svg=re.sub(r'width="[^"]*"', 'width="500"',svg,count=1);svg=re.sub(r'height="[^"]*"','height="500"',svg,count=1)
  suffix=os.environ.get('HAVEN_RENDER_SUFFIX','')
  (root/(ref+suffix+'-'+l+'.svg')).write_text(svg)
  doc=fitz.open(stream=svg.encode(),filetype='svg');pix=doc[0].get_pixmap(alpha=True)
  tile=Image.frombytes('RGBA',(pix.width,pix.height),pix.samples).resize((500,500))
  ox=(k%3)*500;oy=(k//3)*530;im.paste(tile,(ox,oy+30),tile)
  draw.text((ox+8,oy+8),f'{ref} {l} TOP VIEW',fill='white')
  for a in ps:
   px=ox+(a['x']-x)/side*500;py=oy+30+(a['y']-y)/side*500
   draw.ellipse((px-3,py-3,px+3,py+3),outline='white')
   draw.text((px+6,py-16),a['pin']+' '+a['net'],fill='white')
 im.save(root/(ref+suffix+'.png'))
 print(ref,'crop',x,y,side)
