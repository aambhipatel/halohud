import unittest
from headless import Harness

class Version13Tests(unittest.TestCase):
    def renderer(self):
        h=Harness()
        h.lua.execute('''R=require('renderer');S=require('settings');T=require('telemetry')
          cfg=S.read(nil);r=R.new(cfg,1920,1080);t=T.new()
          texts={};local original=r.text
          r.text=function(str,u,v,...)
            texts[#texts+1]={text=tostring(str),u=u,v=v}
            original(str,u,v,...)
          end
          function capture()
            texts={}
            ui.beginTransparentWindow('test',vec2(),vec2(1920,1080),true,false)
            r.render(t);ui.endTransparentWindow()
          end
        ''')
        return h

    def test_unpadded_speed_both_unit_orders(self):
        h=self.renderer();g=h.lua.globals()
        for units in ('KMH','MPH'):
            for kmh in (0,1,9,17,99,108,184,296):
                g.cfg.units=units;g.t.speed=kmh;g.capture()
                values={row.v:row.text for row in g.texts.values() if row.u==0 and row.v in (-99,57)}
                mph=int(kmh*0.6213711922+0.5)
                self.assertEqual(values[-99],str(kmh if units=='KMH' else mph))
                self.assertEqual(values[57],str(mph if units=='KMH' else kmh))

    def test_sixteen_bottom_up_pedal_segments(self):
        h=self.renderer();g=h.lua.globals()
        self.assertEqual(len(g.r.pedals[1]),16);self.assertEqual(len(g.r.pedals[2]),16)
        # All 16 are inside the unchanged module envelope and ordered bottom-up.
        for side in (1,2):
            centers=[]
            for i in range(1,17):
                q=g.r.pedals[side][i]
                centers.append(sum(q[j].y for j in range(2,6))/4)
            self.assertTrue(all(a>b for a,b in zip(centers,centers[1:])))

    def test_inactive_slashes_active_icon_unchanged(self):
        h=self.renderer();h.lua.execute('''local A=require('aero')
          local idle=A.poses(0);local active=A.poses(1)
          assert(idle[1].angle==idle[2].angle and idle[1].angle<0)
          assert(active[1].angle==0 and active[2].angle==0)
          assert(active[1].length==32 and active[2].length==51)
          assert(active[1].x+373.5==364 and active[2].x+373.5==373.5)
          assert(active[1].y==-11 and active[2].y==2)
        ''')

    def test_solo_centered_row_transition_and_partial_board(self):
        h=self.renderer();g=h.lua.globals()
        h.lua.execute('''local p={index=0,driverName=function() return 'Solo Driver' end}
          T.rows(t,p,0,function() return nil end,'FULL',1)
          assert(t.solo and t.ahead.name=='' and t.player.position=='1')
          capture()
        ''')
        names={row.text:row.v for row in g.texts.values()}
        self.assertEqual(names['DRIVER'],-11.5)
        self.assertNotIn('CLEAR TRACK',names)
        self.assertIn('assets/player_highlight_solo.png',[c[0] for c in h.commands])
        self.assertNotIn('assets/player_highlight.png',[c[0] for c in h.commands])
        # A one-entry board while other cars exist must not imply solo.
        h.commands=[]
        h.lua.execute('''local p={index=0,driverName=function() return 'Solo Driver' end}
          T.rows(t,p,1,function() return p end,'FULL',4)
          assert(not t.solo);capture()
        ''')
        self.assertIn('assets/player_highlight.png',[c[0] for c in h.commands])
        self.assertEqual({row.text:row.v for row in g.texts.values()}['DRIVER'],30.5)

if __name__=='__main__':unittest.main()
