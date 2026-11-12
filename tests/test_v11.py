import unittest, itertools, json
from headless import Harness, ROOT

class EnergyTests(unittest.TestCase):
    def setUp(self):
        self.h=Harness(); self.l=self.h.lua
        self.l.execute("T=require('telemetry'); S=require('settings'); cfg=S.read(nil); o=T.new(); c={kersPresent=true,kersCharge=0.5,kersCharging=true,kersInput=1,brake=0.8}")
    def runlua(self,s):self.l.execute(s)
    def test_positive_rate_and_damping(self):
        self.runlua('''cfg.recoveryFallback='EMPTY'
          T.sample(o,c,0.1,0.07);T.energy(o,0.1,cfg)
          c.kersCharge=0.505;T.sample(o,c,0.1,0.07);T.energy(o,0.1,cfg)
          assert(math.abs(o.rawRecharge-0.5)<1e-9)
          assert(math.abs(o.deploy-(1-math.exp(-0.2/0.07)))<1e-9)
          c.kersCharging=false;T.sample(o,c,0.1,0.07);T.energy(o,0.1,cfg)
          assert(o.rawRecharge==0)
        ''')
    def test_unmeasurable_full_charge_and_negative(self):
        self.runlua('''T.sample(o,c,0.1,0.07);T.energy(o,0.1,cfg)
          assert(o.rawRecharge==0.8)
          c.kersCharge=0.49;T.sample(o,c,0.1,0.07);T.energy(o,0.1,cfg)
          assert(o.rawRecharge==0)
          c.kersCharge=1;T.sample(o,c,0.1,0.07);T.energy(o,0.1,cfg)
          assert(o.rawRecharge==0)
          c.kersCharge=nil;T.sample(o,c,0.1,0.07);T.energy(o,0.1,cfg)
          assert(o.rawRecharge==0.8)
          cfg.recoveryFallback='EMPTY';T.energy(o,0.1,cfg);assert(o.rawRecharge==0)
        ''')
    def test_quantized_charge_timeout_and_long_frame(self):
        self.runlua('''cfg.recoveryFallback='EMPTY'
          T.sample(o,c,0.05,0.07);T.energy(o,0.05,cfg)
          for i=1,3 do T.sample(o,c,0.05,0.07);T.energy(o,0.05,cfg) end
          c.kersCharge=0.51;T.sample(o,c,0.05,0.07);T.energy(o,0.05,cfg)
          assert(math.abs(o.rawRecharge-0.5)<1e-9)
          for i=1,6 do T.sample(o,c,0.05,0.07);T.energy(o,0.05,cfg) end
          assert(o.rawRecharge==0)
          c.kersCharge=0.6;T.sample(o,c,2,0.07);T.energy(o,2,cfg);assert(o.rawRecharge==0)
        ''')
    def test_no_ers_default_empty_opt_in_drs(self):
        self.runlua('''c.kersPresent=false;c.drsPresent=true;c.drsActive=true
          cfg.noKersDeploy='EMPTY'
          T.sample(o,c,0.1,0.07);T.energy(o,0.1,cfg)
          assert(o.deploy==0 and o.recharge==0)
          cfg.noKersDeploy='DRS';T.energy(o,0.1,cfg);assert(o.rawDeploy==1 and o.deploy>0)
          c.drsActive=false;c.p2pStatus=42;cfg.noKersDeploy='DRS_OR_P2P'
          T.sample(o,c,0.1,0.07);T.energy(o,0.1,cfg);assert(o.rawDeploy==0)
          cfg.p2pActiveStatus=42;T.energy(o,0.1,cfg);assert(o.rawDeploy==1)
          c.physicsAvailable=false;T.sample(o,c,0.1,0.07);T.energy(o,0.1,cfg)
          assert(o.deploy==0 and o.recharge==0)
        ''')

class LayoutTests(unittest.TestCase):
    def test_digit_ink_centered_equal_advances(self):
        g=json.loads((ROOT/'source/glyphs.json').read_text())['labels']['glyphs']
        widths=[]
        for c in '0123456789':
            d=g[str(ord(c))];widths.append(d['advance'])
            self.assertAlmostEqual(d['x']+d['w']/2,d['advance']/2,places=3)
        self.assertEqual(len(set(widths)),1)
    def test_live_sliders_save_reset_and_other_options(self):
        h=Harness(overrides={'UNITS':'MPH','THEME':'AMBER','ENABLED':1})
        old=h.frame()
        h.lua.execute("ui.slider=function(label,v) if label=='HUD scale' then return 0.7 elseif label=='Center dial scale' then return 1.3 end return v end")
        h.lua.globals().script.windowMain()
        self.assertNotEqual(old,h.frame())
        h.lua.execute("ui.button=function(label) return label=='Save config.ini' end")
        h.lua.globals().script.windowMain()
        self.assertEqual(h.saves,1)
        self.assertEqual(float(h.ini['HUD']['SCALE']),0.7)
        self.assertEqual(float(h.ini['HUD']['DIAL_SCALE']),1.3)
        self.assertEqual(h.ini['HUD']['UNITS'],'MPH')
        self.assertEqual(h.ini['HUD']['THEME'],'AMBER')
        h.lua.execute("ui.slider=function(_,v) return v end;ui.button=function(label) return label=='Reset to defaults' end")
        h.lua.globals().script.windowMain()
        self.assertEqual(h.saves,1) # Reset is a preview until Save
        h.lua.execute("ui.button=function(label) return label=='Save config.ini' end")
        h.lua.globals().script.windowMain()
        self.assertEqual(float(h.ini['HUD']['SCALE']),1)
        self.assertEqual(h.ini['HUD']['UNITS'],'KMH')
    def test_region_scale_extremes_fit_and_offsets(self):
        for curve in (0,1.6):
            for scales in itertools.product((0.5,1.5),repeat=4):
                opts=dict(zip(('LEFT_SCALE','DIAL_SCALE','MODULE_SCALE','RIGHT_SCALE'),scales))
                opts.update(CURVE=curve,SCALE=1.5,X_OFFSET=960,Y_OFFSET=-540,OUTER_ARC=1)
                commands=Harness(1280,720,overrides=opts).frame()
                self.assertTrue(commands)
                for _,pts,_,_ in commands:
                    self.assertTrue(all(0<=x<=1280 and 0<=y<=720 for x,y in pts),(opts,pts))
    def test_false_enabled_persists(self):
        self.assertEqual(Harness(overrides={'ENABLED':0}).frame(),[])

if __name__=='__main__':unittest.main()
