import unittest
from PIL import Image
from headless import Harness, APP

class Version12Tests(unittest.TestCase):
    def test_highlight_shares_panel_projection_strips(self):
        for curve in (0,1,1.6):
            h=Harness(overrides={'CURVE':curve,'LEFT_SCALE':0.5})
            cmds=h.snapshot()
            rim=[c for c in cmds if c[0]=='assets/left_rim.png']
            highlight=[c for c in cmds if c[0]=='assets/player_highlight.png']
            self.assertEqual(len(rim),len(highlight))
            for a,b in zip(rim,highlight):
                self.assertEqual(a[1],b[1]);self.assertEqual(a[3],b[3])

    def test_continuous_mask_and_crop(self):
        with Image.open(APP/'assets/tab_fill.png') as a:
            self.assertTrue(all(a.getpixel((32,y))[3]>245 for y in range(10,182)))
        h=Harness(overrides={'CURVE':0})
        h.lua.execute('''local R=require('renderer');local S=require('settings');local T=require('telemetry')
          local cfg=S.read(ac.INIConfig.load('config.ini'));cfg.curve=0
          local t=T.new(); t.deploy=0.5;t.recharge=0
          ui.beginTransparentWindow('test',vec2(),vec2(1920,1080),true,false)
          R.new(cfg,1920,1080).render(t);ui.endTransparentWindow()''')
        q=[c for c in h.commands if c[0]=='assets/tab_fill.png']
        self.assertEqual(len(q),2) # two curved columns, no eight-segment subdivision
        for _,p,_,uv in q:
            self.assertAlmostEqual(p[2][1]-p[1][1],91)
            self.assertEqual(uv[0][1],0.5);self.assertEqual(uv[2][1],1)

    def test_profile_exact_id_runtime_values_generic_fallback(self):
        h=Harness();h.lua.execute('''local S=require('settings');local c=S.read(nil)
          local p={physicsAvailable=true,rpmLimiter=12000,gearCount=6}
          local e=S.effective(c,'formula_ultra_26',p)
          assert(e.profileActive and e.rpmMax==12000 and e.revLimit==12000 and e.gearCount==6)
          assert(e.recoveryMax==c.recoveryMax and c.carProfile.capacity==-1)
          local g=S.effective(c,'other_car',p)
          assert(not g.profileActive and g.rpmMax==15000 and g.gearCount==8 and g.revLimit==0)
          p.physicsAvailable=false;e=S.effective(c,'formula_ultra_26',p)
          assert(e.rpmMax==15000 and e.gearCount==8)
          c.carProfile.rpmMax=11000;c.carProfile.gears=7
          e=S.effective(c,'formula_ultra_26',p);assert(e.rpmMax==11000 and e.gearCount==7)
        ''')

    def test_car_profile_preserved_when_saving(self):
        h=Harness();h.frame();h.ini['CAR_PROFILE_FORMULA_ULTRA_26']['extra_note']='keep'
        h.lua.execute("ui.button=function(label) return label=='Save config.ini' end")
        h.lua.globals().script.windowMain()
        p=h.ini['CAR_PROFILE_FORMULA_ULTRA_26']
        self.assertEqual(p['car_id'],'formula_ultra_26');self.assertEqual(p['name'],'Formula Ultra 2026')
        self.assertEqual(float(p['battery_capacity_kj']),-1);self.assertEqual(p['extra_note'],'keep')

    def test_no_tag_commands_and_default_non_kers_fallback(self):
        source=(APP/'renderer.lua').read_text(encoding='utf-8')
        self.assertNotIn('SPONSOR',source)
        h=Harness();h.lua.execute('''local S=require('settings');local T=require('telemetry')
          local c=S.read(nil);local o=T.new()
          T.sample(o,{kersPresent=false,drsPresent=true,drsActive=true},0.07,0.07)
          T.energy(o,0.07,c);assert(o.rawDeploy==1 and o.recharge==0 and not o.ers)
        ''')

if __name__=='__main__':unittest.main()
