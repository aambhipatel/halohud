"""CSP interface mock for Lua 5.1 execution and offline pixel previews.

This tests app logic and records the *actual* Lua draw calls. It does not emulate
the game engine, CSP FFI, texture batching, filtering or GPU timing.
"""
from pathlib import Path
import configparser
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'apps/lua/HaloHUD'
# Development environment can keep dependencies outside the deliverable.
DEV_DEPS = ROOT.parents[1] / 'work/python-deps'
if DEV_DEPS.exists(): sys.path.insert(0,str(DEV_DEPS))
from lupa.lua51 import LuaRuntime

class Harness:
    def __init__(self, width=1920, height=1080, demo='ON', overrides=None):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.commands=[]
        self.saves=0
        self.ini=configparser.ConfigParser(inline_comment_prefixes=(';',))
        self.ini.read(APP/'config.ini',encoding='utf-8')
        self.ini['HUD']['DEMO']=demo
        for k,v in (overrides or {}).items(): self.ini['HUD'][k]=str(v)
        self.width,self.height=width,height
        g=self.lua.globals()
        g['__dirname']=APP.as_posix()
        g.py_ini_get=self.ini_get
        g.py_ini_set=self.ini_set
        g.py_ini_save=self.ini_save
        g.py_record=self.record
        g.py_clock=time.perf_counter
        g.py_width=width; g.py_height=height
        self.lua.execute("package.path = "+repr(APP.as_posix()+'/?.lua;')+" .. package.path")
        self.lua.execute('''
          script={}
          function vec2(x,y) return {x=x or 0,y=y or 0} end
          function rgbm(r,g,b,a) return {r=r,g=g,b=b,mult=a or 1} end
          local inWindow=false
          controlWidth=520
          ui={
            StyleColor={WindowBg=2,Text=0}, HoveredFlags={AnyWindow=4}, MouseCursor={ResizeAll=2},
            childWindow=function(_,_,_,_,body) body() end,
            tabBar=function(_,_,body) body() end,
            tabItem=function(name,_,body) if not controlTab or name==controlTab then body() end end,
            treeNode=function(name,_,body) if not openControlSections or openControlSections[name] then body() end end,
            pushID=function(value) controlID=value end,popID=function() controlID=nil end,
            itemHovered=function() return false end,setTooltip=function() end,
            dummy=function() end,header=function() end,separator=function() end,sameLine=function() end,
            availableSpaceX=function() return controlWidth end,measureText=function(s) return vec2(#s*8,16) end,
            inputText=function(_,value) return value end,textDisabled=function() end,
            setNextItemWidth=function() end,combo=function() end,selectable=function() return false end,
            styleColor=function() return rgbm(.08,.1,.12,1) end,pushStyleColor=function() end,popStyleColor=function() end,
            beginTransparentWindow=function(id,pos,size,padding,inputs)
              assert(not inWindow, 'Unbalanced window')
              assert(inputs==false, 'The overlay must stay click-through')
              inWindow=true
            end,
            endTransparentWindow=function() assert(inWindow); inWindow=false end,
            drawImageQuad=function(...) assert(inWindow); py_record(...) end,
            text=function() end, textWrapped=function() end,
            windowHovered=function() return false end, mousePos=function() return vec2(-1,-1) end,
            mouseClicked=function() return false end, mouseDoubleClicked=function() return false end,
            mouseDown=function() return false end, mouseReleased=function() return false end,
            captureMouse=function() end, setMouseCursor=function() end,
            checkbox=function() return false end, button=function() return false end,
            slider=function(_,v) return v end
          }
          os.preciseClock=py_clock
          ac={
            SessionType={Race=3},
            onRelease=function(callback) releaseCallback=callback end,
            onSessionStart=function(callback) sessionStartCallback=callback end,
            INIConfig={load=function() return {
              get=function(_,s,k,d) return py_ini_get(s,k,d) end,
              set=function(_,s,k,v) py_ini_set(s,k,v) end,
              save=function(_,path) py_ini_save(path) end} end},
            getSim=function() return {carsCount=0,currentSessionIndex=0} end,
            getUI=function() return {windowSize=vec2(py_width,py_height)} end,
            getAppWindows=function() return {} end,
            getCar=function() return nil end,
            getCarID=function() return 'generic_test_car' end,
            getTrackFullID=function() return 'mock_track/layout' end,
            getSession=function() return nil end
          }
        ''')
        self.lua.execute((APP/'HaloHUD.lua').read_text(encoding='utf-8'))

    def ini_get(self,s,k,d):
        raw=self.ini.get(s,k,fallback=str(d))
        if isinstance(d,bool): return raw.strip().upper() in ('1','TRUE','YES','ON')
        if isinstance(d,(int,float)): return float(raw)
        return raw

    def ini_set(self,s,k,v):
        if not self.ini.has_section(s): self.ini.add_section(s)
        self.ini[s][k]=('1' if v else '0') if isinstance(v,bool) else str(v)

    def ini_save(self,path):
        self.saves+=1  # deliberately never writes the real config in a test

    def record(self,texture,p1,p2,p3,p4,color,u1,u2,u3,u4):
        points=[[round(p.x,5),round(p.y,5)] for p in (p1,p2,p3,p4)]
        uv=[[float(p.x),float(p.y)] for p in (u1,u2,u3,u4)]
        tint=[float(color.r),float(color.g),float(color.b),float(color.mult)]
        self.commands.append([texture,points,tint,uv])

    def frame(self,dt=1/60):
        self.commands=[]
        self.lua.globals().script.update(dt)
        self.lua.globals().script.drawHUD()
        return self.commands

    def snapshot(self):
        """Reference-number fixture using the real renderer, not a separate mockup."""
        self.frame(0)
        self.commands=[]
        self.lua.execute('''
          local T=require('telemetry'); local R=require('renderer')
          local t=T.new(); T.demo(t,0,'FULL')
          t.speed=296; t.rpm=13250; t.gear=7; t.brake=0.08; t.throttle=0.94
          t.charge=0.72; t.overtake=true; t.charging=true; t.ersInput=0.88
          t.deploy=0.88; t.recharge=0.64
          local cfg=require('settings').read(ac.INIConfig.load(__dirname..'/config.ini'))
          local r=R.new(cfg,py_width,py_height)
          ui.beginTransparentWindow('preview',vec2(),vec2(py_width,py_height),true,false)
          r.render(t); ui.endTransparentWindow()
        ''')
        return self.commands
