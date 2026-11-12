import unittest
from headless import Harness

class MouseDragTests(unittest.TestCase):
    def setup_drag(self, **kwargs):
        h=Harness(**kwargs)
        h.lua.execute('''
          windows={}; captures=0; held=false; dx=0; dy=0
          local begin=ui.beginTransparentWindow
          ui.beginTransparentWindow=function(id,p,s,pad,inputs)
            windows[#windows+1]={id=id,inputs=inputs}; begin(id,p,s,pad,inputs)
          end
          ui.itemActive=function() return held end
          ui.mouseDelta=function() return vec2(dx,dy) end
          ui.captureMouse=function() captures=captures+1 end
          local R=require('renderer'); local new=R.new
          R.new=function(...) local r=new(...); dragInfo=r.drag; return r end
        ''')
        h.frame(0)
        return h

    def toggle(self,h):
        h.lua.execute('''
          ui.checkbox=function(label) return label=='Drag HUD with mouse' end
          script.windowMain()
          ui.checkbox=function() return false end
        ''')

    def test_temporary_mode_only_handle_accepts_input(self):
        h=self.setup_drag(); self.assertEqual(len(h.lua.globals().windows),1)
        self.toggle(h); h.frame(0)
        self.assertEqual(h.lua.globals().windows[3].id,'HaloHUD:dragHandle')
        self.assertTrue(h.lua.globals().windows[3].inputs)
        self.toggle(h); h.lua.execute('windows={}')
        h.frame(0); self.assertEqual(len(h.lua.globals().windows),1)
        self.assertFalse(h.lua.globals().windows[1].inputs)
        self.assertEqual(h.saves,0)

    def test_fitted_scale_motion_and_autosave(self):
        for width,height,scale in ((1920,1080,1),(1280,720,.5),(2560,1440,1.5)):
            with self.subTest(width=width,scale=scale):
                h=self.setup_drag(width=width,height=height,overrides={'SCALE':scale})
                self.toggle(h); info=h.lua.globals().dragInfo
                x,y,s=info.x,info.y,info.scale
                h.lua.execute('held=true;dx=20;dy=12'); h.frame(0)
                self.assertEqual(h.saves,0) # initial click must not jump
                h.frame(0); h.frame(0) # rebuild, following stationary frame below
                # Two movement frames have now applied.
                h.lua.execute('dx=0;dy=0;held=false'); h.frame(.41)
                self.assertEqual(h.saves,1)
                expected_x=min(info.maxX,max(info.minX,x+40/s))
                expected_y=min(info.maxY,max(info.minY,y+24/s))
                self.assertAlmostEqual(float(h.ini['HUD']['X_OFFSET']),expected_x)
                self.assertAlmostEqual(float(h.ini['HUD']['Y_OFFSET']),expected_y)

    def test_edge_drag_reverses_without_dead_zone(self):
        h=self.setup_drag(overrides={'X_OFFSET':960,'Y_OFFSET':540})
        self.toggle(h); h.lua.execute('held=true'); h.frame(0)
        self.assertEqual(h.saves,0)
        h.lua.execute('dx=10000;dy=10000'); h.frame(0); h.frame(0)
        info=h.lua.globals().dragInfo
        self.assertAlmostEqual(info.x,info.maxX)
        self.assertAlmostEqual(info.y,info.maxY)
        h.lua.execute('dx=-12;dy=-8'); h.frame(0)
        h.lua.execute('dx=0;dy=0;held=false'); h.frame(.41)
        self.assertAlmostEqual(float(h.ini['HUD']['X_OFFSET']),info.maxX-12/info.scale)
        self.assertAlmostEqual(float(h.ini['HUD']['Y_OFFSET']),info.maxY-8/info.scale)

    def test_hidden_resets_drag_and_reset_exits_edit_mode(self):
        h=self.setup_drag(); self.toggle(h)
        h.lua.execute('hudUI=ac.getUI(); ac.getUI=function() return hudUI end;held=true')
        h.frame(0)
        h.lua.execute('hudUI.appsHidden=true;windows={};dx=40'); h.frame(0)
        self.assertEqual(len(h.lua.globals().windows),0)
        h.lua.execute('hudUI.appsHidden=false'); h.frame(0)
        self.assertEqual(h.saves,0)
        h.lua.execute('ui.button=function(label) return label=="Reset to defaults" end;script.windowMain();windows={}')
        h.frame(0); self.assertEqual(len(h.lua.globals().windows),1)

if __name__=='__main__': unittest.main()
