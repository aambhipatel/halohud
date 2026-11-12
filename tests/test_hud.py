"""Run: python -m unittest discover -s tests -v (requires lupa, Pillow)."""
import math
import unittest
from headless import Harness, APP

class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.h=Harness(); self.lua=self.h.lua
        self.lua.execute("T=require('telemetry'); out=T.new()")

    def runlua(self,code): self.lua.execute(code)

    def test_mapping_and_no_speed_rpm_lag(self):
        self.runlua('''T.sample(out,{speedKmh=296.25,rpm=13250,gear=7,brake=1,gas=0.25,
          physicsAvailable=true,kersPresent=true,kersCharge=0.72,kersInput=0.88,
          kersCharging=true,kersButtonPressed=true,drsPresent=true,drsActive=true,drsAvailable=true},0.07,0.07)
          assert(out.speed==296.25 and out.rpm==13250 and out.gear==7)
          assert(math.abs(out.brake-(1-math.exp(-1)))<1e-12)
          assert(out.charge==0.72 and out.ersInput==0.88 and out.overtake and out.charging)
          assert(out.aeroActive and out.aeroAvailable)
        ''')

    def test_no_kers_and_no_faked_overtake(self):
        self.runlua('''T.sample(out,{speedKmh=100,rpm=8000,gear=4,gas=1,brake=0,
          kersPresent=false,kersCharge=1,kersInput=1,kersButtonPressed=true,drsPresent=false},0.016,0.07)
          assert(not out.ers and out.charge==0 and not out.overtake and not out.aeroActive)
          T.sample(out,{kersPresent=true,kersCharge=0.6,kersInput=1,gas=1,
          kersButtonPressed=false},0.016,0.07)
          assert(not out.overtake and out.ersInput==1)
        ''')

    def test_unavailable_physics(self):
        self.runlua('''T.sample(out,{physicsAvailable=false,speedKmh=200,rpm=9000,gear=5,
          gas=1,brake=1,kersPresent=true,kersCharge=1,drsPresent=true},1,0.07)
          assert(out.speed==200 and out.gear==5 and out.rawBrake==0 and out.rawThrottle==0)
          assert(not out.ers and not out.aeroPresent and not out.physics)
        ''')

    def test_nan_and_out_of_range(self):
        self.runlua('''T.sample(out,{speedKmh=0/0,rpm=math.huge,gear=-1,
          gas=5,brake=-1,kersPresent=true,kersCharge=3,kersInput=-4},0.016,0.07)
          assert(out.speed==0 and out.rpm==0 and out.gear==-1)
          assert(out.rawThrottle==1 and out.rawBrake==0 and out.charge==1 and out.ersInput==0)
        ''')

    def test_rows_p1_solo_empty_sparse_and_rank_order(self):
        self.runlua('''
          local p={index=0,driverName=function() return 'George Russell' end}
          local a={index=2,driverName=function() return 'Oliver Bearman' end}
          T.rows(out,p,1,function(i) return p end,'FULL')
          assert(out.solo and out.ahead.name=='' and out.player.position=='1')
          T.rows(out,p,0,function() return nil end,'FULL')
          assert(out.player.position=='--')
          T.rows(out,p,3,function(i) return ({[0]=a,[2]=p})[i] end,'CODE')
          assert(out.player.position=='3' and out.ahead.position=='1')
          assert(out.ahead.name=='BEA' and out.player.name=='RUS')
        ''')

    def test_names(self):
        self.runlua("""assert(T.name('Nico Hülkenberg','FULL')=='HULKENBERG')
          assert(T.name('  ','FULL')=='DRIVER')
          assert(T.name('A ReallyVeryLongSurnameWithMoreLetters','FULL'):len()==19)
          assert(T.name('周冠宇','FULL')=='???')""")

    def test_demo_full_ranges(self):
        vals=[]
        for i in range(1000):
            self.lua.globals().T.demo(self.lua.globals().out,i*.1,'FULL')
            o=self.lua.globals().out
            self.assertTrue(0<=o.brake<=1 and 0<=o.throttle<=1 and 0<=o.charge<=1)
            self.assertTrue(-1<=o.gear<=8)
            vals.append(o.gear)
        self.assertEqual(set(vals),set(range(-1,9)))

class IntegrationTests(unittest.TestCase):
    def test_every_lua_file_parses_in_lua51(self):
        h=Harness()
        loader=h.lua.eval('function(s) local f,e=loadstring(s); assert(f,e); return true end')
        for p in APP.glob('*.lua'): self.assertTrue(loader(p.read_text(encoding='utf-8')))

    def test_auto_demo_without_car_and_off(self):
        self.assertGreater(len(Harness(demo='AUTO').frame()),200)
        self.assertEqual(Harness(demo='OFF').frame(),[])

    def test_actual_app_live_solo_no_kers(self):
        h=Harness(demo='AUTO')
        h.lua.execute('''
          local c={index=0,speedKmh=296,rpm=13200,gear=7,gas=1,brake=0,
            physicsAvailable=true,kersPresent=false,drsPresent=false,
            driverName=function() return 'Test Player' end}
          ac.getSim=function() return {carsCount=1,currentSessionIndex=0} end
          ac.getCar=function() return c end
          ac.getSession=function() return {leaderboard={}} end
        ''')
        self.assertGreater(len(h.frame()),200)
        h.lua.globals().script.windowMain()

    def test_resolution_curve_theme_opacity_and_asset_bounds(self):
        for w,h,curve,theme in [(1920,1080,0,'TEAL'),(1920,1080,1.6,'ICE'),
                               (2560,1440,1,'AMBER'),(1280,720,1,'TEAL'),(3440,1440,1,'TEAL')]:
            a=Harness(w,h,overrides={'CURVE':curve,'THEME':theme,'OPACITY':0.6})
            commands=a.frame()
            for texture,points,tint,uv in commands:
                self.assertTrue((APP/texture).is_file(),texture)
                self.assertTrue(all(math.isfinite(n) for p in points for n in p))
                self.assertTrue(all(0<=n<=1 for p in uv for n in p))
                self.assertTrue(0<=tint[3]<=0.6+1e-6)
                self.assertTrue(all(-1<=p[0]<=w+1 and -1<=p[1]<=h+1 for p in points))

    def test_live_to_demo_transition(self):
        h=Harness(demo='AUTO')
        h.lua.execute('''
          local c={index=0,speedKmh=90,rpm=5000,gear=3,gas=0.5,brake=0,
            driverName=function() return 'Solo Player' end}
          ac.getSim=function() return {carsCount=1,currentSessionIndex=0} end
          ac.getCar=function() return c end
        ''')
        self.assertGreater(len(h.frame()),200)
        h.lua.execute("ac.getSim=function() return {carsCount=0} end")
        for i in range(100): self.assertGreater(len(h.frame()),200)

if __name__=='__main__': unittest.main()
