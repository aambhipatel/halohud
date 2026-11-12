import unittest
from PIL import Image
from headless import Harness,APP

class CurvedGaugeTests(unittest.TestCase):
    def test_equal_segment_lengths_and_fitted_outline(self):
        with Image.open(APP/'assets/curved_pedal_segments.png') as im:
            for i in range(16):
                y=round(160+110-i*220/16-(220/16-2)/2)
                for left,right in [(0,320),(320,640)]:
                    xs=[x for x in range(left,right) if im.getpixel((x,y))[3]>128]
                    self.assertTrue(xs)
                    self.assertLessEqual(abs(len(xs)-50),2)

    def test_battery_distinct_colors_and_charge_crop(self):
        h=Harness();h.lua.execute("""
          local S=require('settings');local R=require('renderer');local T=require('telemetry')
          r=R.new(S.read(nil),1920,1080);t=T.new();t.ers=true;t.charge=.5
          ui.beginTransparentWindow('test',vec2(),vec2(1920,1080),true,false)
          r.render(t);ui.endTransparentWindow()
        """)
        battery=[c for c in h.commands if c[0]=='assets/battery.png']
        self.assertEqual(len(battery),2)
        self.assertLess(battery[0][2][2],.15)
        self.assertGreater(battery[1][2][1],.8)
        self.assertGreater(battery[0][2][3],.9)
        self.assertEqual(battery[1][3][1][0],.5)

    def test_continuous_energy_empty_partial_full_and_no_old_modules(self):
        h=Harness();h.lua.execute("""
          R=require('renderer');S=require('settings');T=require('telemetry')
          r=R.new(S.read(nil),1920,1080);t=T.new()
          function capture(v)
            t.recharge=v;t.deploy=v
            ui.beginTransparentWindow('test',vec2(),vec2(1920,1080),true,false)
            r.render(t);ui.endTransparentWindow()
          end
        """)
        for value,count in [(0,0),(.5,2),(1,2)]:
            h.commands=[];h.lua.globals().capture(value)
            fills=[c for c in h.commands if c[0]=='assets/curved_energy_fill.png' and c[2][1]>.6]
            self.assertEqual(len(fills),count)
            self.assertFalse(any(c[0] in ('assets/tab.png','assets/tab_fill.png','assets/module_fill.png','assets/module_rim.png') for c in h.commands))
            for c in fills:
                self.assertAlmostEqual(c[3][0][1],.5 if value==.5 else 0.13587,places=4)

    def test_energy_mask_has_no_internal_seams(self):
        import math
        with Image.open(APP/'assets/curved_energy_fill.png') as im:
            for side in (-1,1):
                for angle in range(-25,26):
                    for offset in range(-20,21):
                        a=math.radians(angle);r=206+offset
                        self.assertGreater(im.getpixel((round(320+side*r*math.cos(a)),round(160+r*math.sin(a))))[3],240)
