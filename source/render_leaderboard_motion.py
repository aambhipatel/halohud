"""Render the real Lua leaderboard motion at selected transition points."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from headless import Harness,ROOT
from render_preview import draw_commands
from PIL import Image
h=Harness();h.lua.execute("""
  local S=require('settings');local T=require('telemetry');local R=require('renderer');local M=require('leaderboard_motion')
  r=R.new(S.read(nil),1920,1080);t=T.new();T.demo(t,0,'FULL');t.solo=false;t.leaderFirst=false
  m=M.new();t.leaderboardMotion=M.update(m,t,0,450)
  function capture(dt,leading,solo)
    t.leaderFirst=leading;t.solo=solo;t.leaderboardMotion=M.update(m,t,dt,450)
    ui.beginTransparentWindow('test',vec2(),vec2(1920,1080),true,false);r.render(t);ui.endTransparentWindow()
  end
""")
frames=[]
for count,leading,solo in [(0,False,False),(4,True,False),(90,True,False),(90,False,True)]:
    for _ in range(count):
        h.commands=[];h.lua.globals().capture(1/60,leading,solo)
    h.commands=[];h.lua.globals().capture(0,leading,solo)
    frame=Image.new('RGBA',(1920,1080),(36,51,62,255));frame.alpha_composite(draw_commands(h.commands))
    frames.append(frame.crop((50,400,900,850)).resize((680,360)))
strip=Image.new('RGB',(680*4,360))
for i,im in enumerate(frames):strip.paste(im,(i*680,0))
strip.save(ROOT/'previews/Leaderboard-Lua-motion.png')
print('Rendered Lua leaderboard: following, transition, leading, solo.')
