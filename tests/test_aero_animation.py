import json,shutil,subprocess,unittest
from pathlib import Path
from headless import Harness

class AeroAnimationTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node required only for HTML/Lua parity test')
    def test_matches_approved_html_javascript(self):
        frames=json.loads(subprocess.check_output(['node',str(Path(__file__).with_name('aero_reference.cjs'))],text=True))
        h=Harness();h.lua.execute("A=require('aero');motion=A.new()")
        g=h.lua.globals()
        for f in frames:
            g.A.update(g.motion,f['active'],f['dt'],420)
            self.assertAlmostEqual(g.motion.phase,f['phase'],places=10)
            self.assertAlmostEqual(g.motion.velocity,f['velocity'],places=10)

    def test_parallel_separation_and_projected_quads(self):
        h=Harness();h.lua.execute('''local A=require('aero');local S=require('settings');local R=require('renderer')
          local function separated(a,b)
            for _,polygon in ipairs({a,b}) do
              for i=1,4 do
                local j=i%4+1;local nx=-(polygon[j].y-polygon[i].y);local ny=polygon[j].x-polygon[i].x
                local amin,amax,bmin,bmax=math.huge,-math.huge,math.huge,-math.huge
                for k=1,4 do
                  local x=a[k].x*nx+a[k].y*ny;amin=math.min(amin,x);amax=math.max(amax,x)
                  x=b[k].x*nx+b[k].y*ny;bmin=math.min(bmin,x);bmax=math.max(bmax,x)
                end
                if amax<bmin or bmax<amin then return true end
              end
            end
            return false
          end
          for _,curve in ipairs({0,1,1.6}) do for _,scale in ipairs({0.5,1.5}) do
            local cfg=S.read(nil);cfg.curve=curve;cfg.rightScale=scale
            local r=R.new(cfg,1920,1080)
            for i=0,100 do
              local poses=A.poses(i/100);assert(poses[1].angle==poses[2].angle)
              local quads={}
              for j=1,2 do
                local vertices=A.vertices(poses[j],373.5,0);quads[j]={}
                for k=1,4 do quads[j][k]=r.point(vertices[k][1],vertices[k][2],false,'right') end
              end
              assert(separated(quads[1],quads[2]),'Aero quads must never cross')
            end
          end end
        ''')

    def test_reversal_continuity_and_frame_rate(self):
        h=Harness();h.lua.execute('''local A=require('aero');local a=A.new();local b=A.new()
          for i=1,12 do A.update(a,true,1/60,420) end
          for i=1,24 do A.update(b,true,1/120,420) end
          assert(math.abs(a.phase-b.phase)<1e-12)
          local p,v=a.phase,a.velocity
          A.update(a,false,0,420);assert(math.abs(a.phase-p)<1e-12 and math.abs(a.velocity-v)<1e-12)
          for i=1,120 do A.update(a,false,1/60,420) end
          assert(a.phase==0 and a.velocity==0)
        ''')

    def test_app_state_survives_layout_rebuild(self):
        h=Harness(demo='AUTO');phases=[]
        h.lua.globals().recordPhase=phases.append
        h.lua.execute('''local R=require('renderer');local create=R.new
          R.new=function(...)
            local r=create(...);local render=r.render
            r.render=function(t) recordPhase(t.aeroPhase);render(t) end
            return r
          end
          local c={index=0,drsPresent=true,drsActive=true,driverName=function() return 'Player' end}
          ac.getCar=function() return c end
          ac.getSim=function() return {carsCount=1,currentSessionIndex=0} end
        ''')
        h.frame(1/60)
        h.lua.execute("ui.slider=function(label,v) return label=='HUD scale' and 0.7 or v end")
        h.lua.globals().script.windowMain();h.frame(1/60)
        self.assertTrue(0<phases[0]<phases[1]<1)

if __name__=='__main__':unittest.main()
