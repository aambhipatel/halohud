import unittest
from headless import Harness

class GearMotionTests(unittest.TestCase):
    def test_slide_and_continuous_reversal(self):
        h=Harness();h.lua.execute("""
          local G=require('gear_motion');local s=G.new()
          G.update(s,2,0,260);assert(s.position==2)
          local prev=2
          for i=1,15 do G.update(s,7,1/60,260);assert(s.position>=prev and s.position<=7);prev=s.position end
          local p,v=s.position,s.velocity
          G.update(s,1,0,260);assert(s.position==p and math.abs(s.velocity-v)<1e-10)
          for i=1,120 do G.update(s,1,1/60,260) end
          assert(s.position==1)
        """)

    def test_neutral_reverse_peak_scale_and_settle(self):
        h=Harness();h.lua.execute("""
          local G=require('gear_motion');local s=G.new();G.update(s,0,0,260)
          G.update(s,-1,0,260)
          for i=1,5 do G.update(s,-1,.025,260) end
          assert(s.letter=='N' and s.scale>1 and s.scale<1.3)
          for i=1,6 do G.update(s,-1,.025,260) end
          assert(s.letter=='R' and s.scale>1.29 and s.position==0)
          for i=1,11 do G.update(s,-1,.025,260) end
          assert(s.scale==1 and s.phase==nil)
          G.update(s,0,0,260)
          for i=1,11 do G.update(s,0,.025,260) end
          assert(s.letter=='N' and s.scale>1.29)
          G.update(s,-1,0,260)
          for i=1,40 do G.update(s,-1,.025,260) end
          assert(s.letter=='R' and s.scale==1)
        """)

    def test_layout_rebuild_preserves_motion(self):
        h=Harness();h.lua.execute("""
          local R=require('renderer');local new=R.new
          R.new=function(...) local r=new(...);local render=r.render
            r.render=function(t) observedPosition=t.gearPosition;observedLetter=t.slotLetter;render(t) end
            return r end
          uiState={windowSize=vec2(1920,1080)};ac.getUI=function() return uiState end
          ac.getSim=function() return {carsCount=1,currentSessionIndex=0} end
          car={gear=2,rpm=2000,speedKmh=30,physicsAvailable=true,racePosition=1,
            driverName=function() return 'Driver' end}
          ac.getCar=function() return car end
        """)
        # Use live telemetry so the desired gear is controlled directly.
        h.lua.execute("ui.checkbox=function(label) return label=='Force demo telemetry' end")
        h.frame(0);h.lua.globals().script.windowMain()
        h.frame(0)
        h.lua.execute('car.gear=6');h.frame(.02)
        before=h.lua.globals().observedPosition
        self.assertGreater(before,2);self.assertLess(before,6)
        h.lua.execute('uiState.windowSize=vec2(1280,720)');h.frame(.02)
        self.assertGreater(h.lua.globals().observedPosition,before)
        self.assertLess(h.lua.globals().observedPosition,6)

    def test_duration_control_auto_saves(self):
        h=Harness();h.frame(0)
        h.lua.execute("ui.slider=function(label,v) return label=='Gear animation' and 400 or v end;script.windowMain()")
        h.frame(.41)
        self.assertEqual(float(h.ini['HUD']['GEAR_ANIMATION_MS']),400)
