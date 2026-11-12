"""Render the solo-session state using the actual Lua renderer and telemetry rows."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from headless import Harness,ROOT
from render_preview import draw_commands
from PIL import Image

def main():
    h=Harness()
    h.lua.execute('''local T=require('telemetry');local R=require('renderer');local S=require('settings')
      local cfg=S.read(ac.INIConfig.load('config.ini'))
      local t=T.new();T.demo(t,0,'FULL')
      local p={index=0,driverName=function() return 'George Russell' end}
      T.rows(t,p,0,function() return nil end,'FULL',1)
      t.speed=17;t.rpm=2300;t.gear=1;t.throttle=0.47;t.brake=0.63;t.aeroActive=false
      t.deploy=0.3;t.recharge=0.4
      ui.beginTransparentWindow('soloPreview',vec2(),vec2(1920,1080),true,false)
      R.new(cfg,1920,1080).render(t);ui.endTransparentWindow()
    ''')
    im=draw_commands(h.commands)
    bg=Image.new('RGBA',im.size,(36,51,62,255));bg.alpha_composite(im)
    bg.crop((65,340,1870,940)).convert('RGB').save(ROOT/'previews/HaloHUD-solo-preview.png')
    # Integrated race-leader classification and upper player-row layout.
    h=Harness()
    h.lua.execute('''local T=require('telemetry');local R=require('renderer');local S=require('settings')
      local t=T.new();T.demo(t,0,'FULL')
      local p={index=0,racePosition=1,driverName=function() return 'George Russell' end}
      local b={index=1,racePosition=2,driverName=function() return 'Oliver Bearman' end}
      T.raceRows(t,p,2,function(i) return i==0 and p or b end,'FULL')
      t.speed=296;t.rpm=9500;t.gear=7;t.brake=0.65;t.throttle=0.8;t.charge=0.62;t.deploy=0.3;t.recharge=0.4
      ui.beginTransparentWindow('leader',vec2(),vec2(1920,1080),true,false)
      R.new(S.read(nil),1920,1080).render(t);ui.endTransparentWindow()
    ''')
    im=draw_commands(h.commands);bg=Image.new('RGBA',im.size,(36,51,62,255));bg.alpha_composite(im)
    bg.crop((65,340,1870,940)).convert('RGB').save(ROOT/'previews/HaloHUD-race-leader.png')
    # Keep the existing independent-scale/outer-arc example current as well.
    h=Harness(overrides={'LEFT_SCALE':0.7,'RIGHT_SCALE':0.7,'MODULE_SCALE':0.9,'DIAL_SCALE':1,'OUTER_ARC':1})
    im=draw_commands(h.snapshot());bg=Image.new('RGBA',im.size,(36,51,62,255));bg.alpha_composite(im)
    bg.convert('RGB').save(ROOT/'previews/HaloHUD-live-layout-example.png')
    print('Solo state and scaled-layout previews regenerated')

if __name__=='__main__':main()
