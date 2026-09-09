"""Render KiCad CLI copper SVGs as labeled, cropped six-layer contact sheets."""
import os, re, pathlib, sys
os.environ['QT_QPA_PLATFORM']='offscreen'
import pcbnew as p
from PyQt6.QtWidgets import QApplication
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QImage,QPainter,QColor,QFont
from PyQt6.QtCore import QRectF,QByteArray
app=QApplication([])
b=p.LoadBoard('kicad/haven_dev_board.kicad_pcb')
out=pathlib.Path('routing-evidence/images');out.mkdir(exist_ok=True)
for ref in (sys.argv[1:] or ['U15','U2','MDBT531','U10','CN1']):
 f=next(f for f in b.GetFootprints() if f.GetReference()==ref)
 pads=list(f.Pads()); xs=[p.ToMM(a.GetPosition().x) for a in pads];ys=[p.ToMM(a.GetPosition().y) for a in pads]
 x=min(xs)-2;y=min(ys)-2;w=max(xs)-x+2;h=max(ys)-y+2
 side=max(w,h);x-=(side-w)/2;y-=(side-h)/2
 im=QImage(1800,1260,QImage.Format.Format_ARGB32);im.fill(QColor('#181818'));q=QPainter(im)
 for k,layer in enumerate(['F_Cu','In1_Cu','In2_Cu','In3_Cu','In4_Cu','B_Cu']):
  svg=pathlib.Path('/tmp/haven-svg/haven_dev_board-'+layer+'.svg').read_text()
  svg=re.sub(r'viewBox="[^"]*"',f'viewBox="{x} {y} {side} {side}"',svg,count=1)
  r=QSvgRenderer(QByteArray(svg.encode()));ox=(k%3)*600;oy=(k//3)*630
  q.save();q.setClipRect(QRectF(ox,oy+30,600,600));r.render(q,QRectF(ox,oy+30,600,600));q.restore();q.setPen(QColor('white'));q.setFont(QFont('Sans',12));q.drawText(ox+8,oy+22,ref+' '+layer+' (top view)')
  for a in pads:
   if a.IsOnLayer(b.GetLayerID(layer.replace('_','.'))):
    px=ox+(p.ToMM(a.GetPosition().x)-x)/side*600;py=oy+30+(p.ToMM(a.GetPosition().y)-y)/side*600
    q.setFont(QFont('Sans',7));q.drawText(int(px+4),int(py-4),a.GetNumber())
 q.end();im.save(str(out/(ref+'.png')))
 print(ref, 'crop',x,y,side)
