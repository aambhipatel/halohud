"""Render three stages of the integrated Lua aero geometry for visual QA."""
from pathlib import Path
import sys,math
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from headless import Harness,ROOT
from render_preview import draw_commands
from PIL import Image,ImageDraw,ImageFont

def main():
    strip=Image.new('RGB',(900,390),(30,48,60));d=ImageDraw.Draw(strip)
    for i,phase in enumerate((0,0.5,1)):
        h=Harness();h.lua.globals().phaseFixture=phase
        h.lua.execute('''local R=require('renderer');local S=require('settings');local T=require('telemetry')
          probe=R.new(S.read(nil),1920,1080)
          local t=T.new();T.demo(t,0,'FULL');t.aeroPhase=phaseFixture
          ui.beginTransparentWindow('motion',vec2(),vec2(1920,1080),true,false)
          probe.render(t);ui.endTransparentWindow()
        ''')
        point=h.lua.globals().probe.point
        corners=[point(u,v,False,'right') for u in (330,418) for v in (-76,42)]
        box=(math.floor(min(p.x for p in corners))-8,math.floor(min(p.y for p in corners))-8,
             math.ceil(max(p.x for p in corners))+8,math.ceil(max(p.y for p in corners))+8)
        im=draw_commands(h.commands);bg=Image.new('RGBA',im.size,(36,51,62,255));bg.alpha_composite(im)
        crop=bg.crop(box).convert('RGB');crop.thumbnail((280,320))
        strip.paste(crop,(i*300+(300-crop.width)//2,45))
        d.text((i*300+20,15),('Inactive','Transition','Active')[i],font=ImageFont.load_default(size=18),fill='white')
    strip.save(ROOT/'previews/Aero-Lua-motion.png')
    print('Integrated Lua aero motion contact sheet rendered')

if __name__=='__main__':main()
