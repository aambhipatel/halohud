"""Render and measure the actual projected timing panel bottom inset."""
from pathlib import Path
import sys,json,math
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from headless import Harness,ROOT
from render_preview import draw_commands
from PIL import Image,ImageDraw

def main():
    reports=[]
    for curve in (0,1,1.6):
        h=Harness(overrides={'CURVE':curve})
        h.lua.execute('''local S=require('settings');local R=require('renderer')
          local cfg=S.read(ac.INIConfig.load('config.ini'))
          layoutProbe=R.new(cfg,1920,1080)''')
        point=h.lua.globals().layoutProbe.point
        pairs=[];gaps=[]
        # Same longitudinal parameter, highlight bottom y=170 versus frame y=182.
        for i in range(17):
            u=-830+42+430*i/16
            a=point(u,78,False,'left');b=point(u,90,False,'left')
            p,q=(a.x,a.y),(b.x,b.y)
            gaps.append(math.dist(p,q));pairs.append((p,q))
        reports.append({'curve':curve,'design_normal_inset':12,
                        'projected_bottom_min':min(gaps),'projected_bottom_max':max(gaps),
                        'variation':max(gaps)-min(gaps)})
        if curve==1:
            commands=h.snapshot();im=draw_commands(commands)
            bg=Image.new('RGBA',im.size,(36,51,62,255));bg.alpha_composite(im)
            d=ImageDraw.Draw(bg)
            for p,q in pairs: d.line([p,q],fill=(255,220,80),width=2)
            panel=[c for c in commands if c[0]=='assets/left_rim.png']
            pts=[p for c in panel for p in c[1]]
            box=(int(min(p[0] for p in pts))-10,int(min(p[1] for p in pts))-10,
                 int(max(p[0] for p in pts))+10,int(max(p[1] for p in pts))+20)
            crop=bg.crop(box).resize(((box[2]-box[0])*2,(box[3]-box[1])*2))
            crop.save(ROOT/'previews/Highlight-inset-verification.png')
        assert max(gaps)-min(gaps)<0.01
    (ROOT/'reports/highlight-inset-measurements.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
    print(json.dumps(reports,indent=2))

if __name__=='__main__':main()
