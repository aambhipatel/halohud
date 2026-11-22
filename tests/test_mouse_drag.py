import unittest
from headless import Harness


class MouseDragTests(unittest.TestCase):
    def setup_drag(self, **kwargs):
        h=Harness(**kwargs)
        h.lua.execute('''
          windows={}; captures=0; hoverCues=0
          px,py=-1,-1
          local begin=ui.beginTransparentWindow
          ui.beginTransparentWindow=function(id,p,s,pad,inputs)
            windows[#windows+1]={id=id,inputs=inputs};begin(id,p,s,pad,inputs)
          end
          ui.mousePos=function() return vec2(px,py) end
          ui.mouseClicked=function() return clicked==true end
          ui.mouseDoubleClicked=function() return doubleClicked==true end
          ui.mouseDown=function() return down==true end
          ui.mouseReleased=function() return released==true end
          ui.captureMouse=function() captures=captures+1 end
          ui.setMouseCursor=function(cursor)
            assert(cursor==ui.MouseCursor.ResizeAll);hoverCues=hoverCues+1
          end
          ui.windowHovered=function(flags)
            assert(flags==ui.HoveredFlags.AnyWindow);return otherWindow==true
          end
          local R=require('renderer');local new=R.new
          R.new=function(...) local r=new(...);dragInfo=r.drag;return r end
          hudUI=ac.getUI();ac.getUI=function() return hudUI end
        ''')
        h.frame(0)
        return h

    def pointer(self,h,dx=0,dy=0,*,down=False,click=False,double=False,release=False):
        g=h.lua.globals()
        g.px,g.py=g.originX+dx,g.originY+dy
        g.down,g.clicked,g.doubleClicked,g.released=down,click,double,release
        h.frame(0)

    def set_origin(self,h,side=.5,height=.5):
        g=h.lua.globals();b=g.dragInfo
        g.originX,g.originY=b.left+(b.right-b.left)*side,b.top+(b.bottom-b.top)*height

    def test_pure_drag_math_converts_delta_and_clamps(self):
        Harness().lua.execute('''
          local D=require('hud_drag')
          local b={minX=-20,maxX=80,minY=-50,maxY=25,scale=.5}
          assert(D.contains(15,24,15,16,45,40))
          assert(not D.contains(14,24,15,16,45,40))
          local x,y=D.offset(b,5,-10,8,-4);assert(x==21 and y==-18)
          x,y=D.offset(b,5,-10,500,-500);assert(x==80 and y==-50)
          x,y=D.offset(b,5,-10,-500,500);assert(x==-20 and y==25)
        ''')

    def test_migrates_only_explicit_legacy_key_and_persists_once(self):
        for legacy,locked in (('0','1'),('False','1'),('ON','0'),('',None),('typo',None)):
            with self.subTest(legacy=legacy):
                h=Harness(overrides={'DRAG_HUD_WITH_MOUSE':legacy,'X_OFFSET':23})
                del h.ini['HUD']['LOCK_HUD_POSITION']
                h.frame(.41)
                self.assertEqual(h.ini['HUD'].get('LOCK_HUD_POSITION'),locked)
                self.assertEqual(h.saves,int(locked is not None))
                h.lua.execute("ui.button=function(label) return label=='Reload config.ini' end;script.windowMain()")
                h.frame(.41)
                self.assertEqual(h.saves,int(locked is not None))
                self.assertEqual(float(h.ini['HUD']['X_OFFSET']),23)
                self.assertEqual(h.ini['HUD']['DRAG_HUD_WITH_MOUSE'],legacy)
        h=Harness(overrides={'DRAG_MODE':'false','LOCK_HUD_POSITION':'0'})
        h.frame(.41)
        self.assertEqual(h.saves,0)  # Explicit new setting takes precedence.

    def test_body_drag_at_multiple_scales_only_saves_after_release(self):
        for width,height,scale,curve,side in ((1920,1080,1,1,.25),(1280,720,.5,0,.5),(2560,1440,1.5,1.6,.75)):
            with self.subTest(width=width,scale=scale):
                h=self.setup_drag(width=width,height=height,overrides={'SCALE':scale,'CURVE':curve})
                self.set_origin(h,side)
                g=h.lua.globals();b=g.dragInfo
                self.pointer(h)
                self.assertEqual(g.hoverCues,1)
                self.pointer(h,down=True,click=True)
                self.assertEqual((g.dragInfo.x,g.dragInfo.y),(b.x,b.y))
                self.pointer(h,20,12,down=True)
                self.assertGreater(g.captures,1)
                self.assertTrue(all(not w.inputs and w.id=='HaloHUD:overlay' for w in g.windows.values()))
                h.frame(.41)
                self.assertEqual(h.saves,0)
                self.pointer(h,20,12,release=True)
                h.frame(.3)
                self.assertEqual(h.saves,0)
                h.frame(.12)
                self.assertEqual(h.saves,1)
                self.assertAlmostEqual(float(h.ini['HUD']['X_OFFSET']),min(b.maxX,max(b.minX,b.x+20/b.scale)))
                self.assertAlmostEqual(float(h.ini['HUD']['Y_OFFSET']),min(b.maxY,max(b.minY,b.y+12/b.scale)))
                h.frame(1)
                self.assertEqual(h.saves,1)

    def test_outside_or_other_window_press_never_steals_a_drag(self):
        for blocker in ('outside','imgui','capture','legacy app'):
            with self.subTest(blocker=blocker):
                h=self.setup_drag();g=h.lua.globals()
                self.set_origin(h)
                if blocker=='imgui': g.otherWindow=True
                elif blocker=='capture': g.hudUI.wantCaptureMouse=True
                elif blocker=='legacy app':
                    h.lua.execute('ac.getAppWindows=function() return {{visible=true,layer=0,position=vec2(originX-10,originY-10),size=vec2(20,20)}} end')
                self.pointer(h,0 if blocker!='outside' else -g.originX,down=True,click=True)
                g.otherWindow=False
                g.hudUI.wantCaptureMouse=False
                h.lua.execute('ac.getAppWindows=function() return {} end')
                self.pointer(h,15,15,down=True)
                self.pointer(h,15,15,release=True)
                h.frame(.41)
                self.assertEqual(g.captures,0)
                self.assertEqual(h.saves,0)

    def test_drag_clamps_and_follows_pointer_back_to_start(self):
        h=self.setup_drag();g=h.lua.globals();b=g.dragInfo
        self.set_origin(h)
        self.pointer(h,down=True,click=True)
        self.pointer(h,10000,10000,down=True)
        self.assertAlmostEqual(g.dragInfo.x,b.maxX)
        self.assertAlmostEqual(g.dragInfo.y,b.maxY)
        self.assertGreaterEqual(g.dragInfo.left,16-1e-8)
        self.assertLessEqual(g.dragInfo.right,h.width-16+1e-8)
        self.pointer(h,0,0,down=True)
        self.assertAlmostEqual(g.dragInfo.x,b.x)
        self.assertAlmostEqual(g.dragInfo.y,b.y)

    def test_lock_disables_drag_and_double_click_reset(self):
        h=self.setup_drag(overrides={'LOCK_HUD_POSITION':1,'X_OFFSET':30,'Y_OFFSET':25})
        g=h.lua.globals()
        self.set_origin(h)
        self.pointer(h,down=True,click=True)
        self.pointer(h,10,12,down=True)
        self.pointer(h,release=True)
        self.pointer(h,down=True,double=True)
        self.pointer(h,release=True)
        h.frame(.41)
        self.assertEqual((h.saves,g.captures,g.hoverCues),(0,0,0))
        h.lua.execute("controlTab='General';ui.checkbox=function(label) return label=='Lock HUD position' end;script.windowMain()")
        self.pointer(h,down=True,click=True)
        self.pointer(h,release=True)
        self.pointer(h,down=True,double=True)
        self.pointer(h,release=True)
        h.frame(.41)
        saved=h.ini['HUD']
        self.assertEqual(float(saved['X_OFFSET']),0)
        self.assertEqual(float(saved['Y_OFFSET']),0)
        self.assertEqual(saved['LOCK_HUD_POSITION'],'0')

    def test_hiding_during_drag_commits_position_and_releases_capture(self):
        h=self.setup_drag();g=h.lua.globals()
        self.set_origin(h)
        self.pointer(h,down=True,click=True)
        self.pointer(h,16,4,down=True)
        g.hudUI.appsHidden=True
        g.script.update(.41)
        self.assertEqual(h.saves,1)
        self.assertEqual(float(h.ini['HUD']['X_OFFSET']),16)
        captures=g.captures
        self.assertFalse(h.frame(0))
        g.hudUI.appsHidden=False
        self.pointer(h,30,40,down=True)
        self.assertEqual(g.captures,captures)


if __name__=='__main__': unittest.main()
