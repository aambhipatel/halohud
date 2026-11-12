import unittest
from PIL import Image,ImageChops
from headless import Harness,APP,ROOT

class ApprovedReviewTests(unittest.TestCase):
    def test_race_leader_second_follower_and_solo_transitions(self):
        h=Harness();h.lua.execute('''local T=require('telemetry');local R=require('renderer');local S=require('settings')
          local t=T.new();local r=R.new(S.read(nil),1920,1080)
          local p={index=0,racePosition=1,driverName=function() return 'George Russell' end}
          local b={index=1,racePosition=2,driverName=function() return 'Oliver Bearman' end}
          local cars={[0]=p,b};local get=function(i) return cars[i] end
          local texts,mask;local text,draw=r.text,r.draw
          r.text=function(label,u,v,...) texts[tostring(label)]=v;text(label,u,v,...) end
          r.draw=function(q,...)
            if q[1]:find('player_highlight',1,true) then mask=q[1] end
            draw(q,...)
          end
          local function render()
            texts={};ui.beginTransparentWindow('test',vec2(),vec2(1920,1080),true,false)
            r.render(t);ui.endTransparentWindow()
            assert(not texts['CLEAR TRACK'])
          end
          T.raceRows(t,p,2,get,'FULL');render()
          assert(t.leaderFirst and t.ahead.position=='2' and t.ahead.name=='BEARMAN')
          assert(texts.RUSSELL==-53.5 and texts.BEARMAN==30.5)
          assert(mask=='assets/player_highlight_leader.png')
          p.racePosition=2;b.racePosition=1
          T.raceRows(t,p,2,get,'FULL');render()
          assert(not t.leaderFirst and texts.RUSSELL==30.5 and texts.BEARMAN==-49)
          assert(mask=='assets/player_highlight.png')
          p.racePosition=1;T.raceRows(t,p,1,get,'FULL');render()
          assert(t.solo and not t.leaderFirst and texts.RUSSELL==-11.5 and not texts.BEARMAN)
          assert(mask=='assets/player_highlight_solo.png')
          T.raceRows(t,p,2,function() return nil end,'FULL');render()
          assert(t.leaderFirst and texts.UNAVAILABLE and not texts['CLEAR TRACK'])
        ''')

    def test_assets_match_approved_html_preview(self):
        for actual,approved in [('battery.png','battery_fill.png'),('player_highlight_leader.png','player_highlight_leader.png')]:
            with Image.open(APP/'assets'/actual) as a,Image.open(ROOT/'previews/approved-html/assets'/approved) as b:
                self.assertIsNone(ImageChops.difference(a.convert('RGBA'),b.convert('RGBA')).getbbox())

    def test_red_brakes_and_borderless_charge_masks(self):
        h=Harness();h.lua.execute('''local R=require('renderer');local S=require('settings');local T=require('telemetry')
          local r=R.new(S.read(nil),1920,1080);local t=T.new();t.ers=true;t.charge=0.5
          assert(r.c.brake.r==1 and r.c.brake.g<0.3 and r.c.brake.b<0.3)
          assert(r.chargeBg[1]=='assets/battery.png')
          local draw=r.draw;local count,fill
          r.draw=function(q,color,...)
            if q[1]=='assets/battery.png' then
              count=count+1
              if q~=r.chargeBg then fill=q end
            end
            draw(q,color,...)
          end
          count=0;ui.beginTransparentWindow('test',vec2(),vec2(1920,1080),true,false)
          r.render(t);ui.endTransparentWindow()
          assert(count==2 and fill[7].x==0.5 and fill[8].x==0.5)
          t.ers=false;count=0;ui.beginTransparentWindow('test',vec2(),vec2(1920,1080),true,false)
          r.render(t);ui.endTransparentWindow();assert(count==1)
        ''')

if __name__=='__main__':unittest.main()
