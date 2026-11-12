import unittest
from headless import Harness

class Version14Tests(unittest.TestCase):
    def test_inactive_label_boxes(self):
        h=Harness();h.lua.execute('''local R=require('renderer');local S=require('settings');local T=require('telemetry')
          local r=R.new(S.read(nil),1920,1080);local t=T.new();t.ers=true
          local rect=r.rect;local boxes
          r.rect=function(u,v,w,h,color,...)
            if u==-112 and w==224 and h==27 then boxes[v]=color end
            rect(u,v,w,h,color,...)
          end
          for _,deploy in ipairs({0.5,0.51}) do
            boxes={};t.deploy=deploy
            ui.beginTransparentWindow('test',vec2(),vec2(1920,1080),true,false)
            r.render(t);ui.endTransparentWindow()
            assert(math.abs(boxes[14].r-65/255)<1e-9)
            if deploy<=0.5 then assert(math.abs(boxes[-18].r-65/255)<1e-9)
            else assert(boxes[-18]==r.c.green) end
          end
        ''')

    def test_release_flushes_pending_changes(self):
        h=Harness();h.frame()
        h.lua.execute("ui.slider=function(label,v) if label=='HUD scale' then return 0.75 end return v end")
        h.lua.globals().script.windowMain()
        self.assertEqual(h.saves,0)
        h.lua.globals().releaseCallback()
        self.assertEqual(h.saves,1)
        self.assertEqual(float(h.ini['HUD']['SCALE']),0.75)

    def test_rpm_and_deploy_boundaries(self):
        h=Harness();h.lua.execute('''local R=require('renderer');local T=require('telemetry');local S=require('settings')
          local c=S.read(nil);c.revLimit=8000
          local r=R.new(c,1920,1080);local t=T.new();t.ers=true
          local draw=r.draw;local text=r.text
          local fill,labels
          r.draw=function(q,color,...)
            if q==r.rpm[1] then fill=color end
            draw(q,color,...)
          end
          r.text=function(s,u,v,size,color,...)
            labels[tostring(s)]=color
            text(s,u,v,size,color,...)
          end
          for _,rpm in ipairs({10000,10999,11000,11001,13000}) do
            for _,deploy in ipairs({0.49,0.5,0.51}) do
              for _,overtake in ipairs({false,true}) do
                t.rpm=rpm;t.deploy=deploy;t.overtake=overtake;labels={}
                ui.beginTransparentWindow('test',vec2(),vec2(1920,1080),true,false)
                r.render(t);ui.endTransparentWindow()
                assert((fill.r>0.9)==(rpm>11000))
                assert(labels.OVERTAKE==r.c.dim)
                assert(labels.BOOST==(deploy>0.5 and r.c.white or r.c.dim))
              end
            end
          end
        ''')

    def test_debounced_save_even_if_controls_closed_and_hud_disabled(self):
        h=Harness();h.frame()
        h.lua.execute("ui.slider=function(label,v) if label=='HUD scale' then return 0.8 end return v end")
        h.lua.globals().script.windowMain()
        h.frame(0.2);self.assertEqual(h.saves,0)
        # A later change restarts the debounce rather than writing every drag frame.
        h.lua.execute("ui.checkbox=function(label) return label=='Show HUD' end")
        h.lua.globals().script.windowMain()
        h.frame(0.2);self.assertEqual(h.saves,0)
        h.frame(0.21);self.assertEqual(h.saves,1)
        self.assertEqual(float(h.ini['HUD']['SCALE']),0.8)
        self.assertEqual(h.ini['HUD']['ENABLED'],'0')
        h.frame(1);self.assertEqual(h.saves,1)

    def test_demo_profile_and_arc_persist_and_reload(self):
        h=Harness(demo='AUTO');h.frame()
        h.lua.execute("ui.checkbox=function(label) return label=='Force demo telemetry' or label=='Outer arc' or label=='Measure Lua CPU time' end")
        h.lua.globals().script.windowMain();h.frame(0.41)
        self.assertEqual(h.ini['HUD']['DEMO'],'ON')
        self.assertEqual(h.ini['HUD']['PROFILE_CPU'],'1')
        self.assertEqual(h.ini['HUD']['OUTER_ARC'],'1')
        h.lua.execute("ui.checkbox=function() return false end;ui.button=function(label) return label=='Reload config.ini' end")
        h.lua.globals().script.windowMain()
        states={}
        h.lua.globals().remember=lambda label,value:states.update({label:value})
        h.lua.execute("ui.button=function() return false end;ui.checkbox=function(label,v) remember(label,v);return false end")
        h.lua.globals().script.windowMain()
        self.assertTrue(states['Force demo telemetry']);self.assertTrue(states['Outer arc'])
        self.assertTrue(states['Measure Lua CPU time'])

    def test_save_errors_are_visible_and_retried(self):
        h=Harness();h.frame()
        h.lua.execute("ui.slider=function(label,v) if label=='HUD scale' then return 0.9 end return v end; py_ini_save=function() error('write failure fixture') end")
        h.lua.globals().script.windowMain();h.frame(0.41)
        messages=[];h.lua.globals().ui.textWrapped=messages.append
        h.lua.globals().script.windowMain()
        self.assertTrue(any('write failure fixture' in m for m in messages))
        h.lua.globals().py_ini_save=h.ini_save
        h.frame(2.1);self.assertEqual(h.saves,1)

if __name__=='__main__':unittest.main()
