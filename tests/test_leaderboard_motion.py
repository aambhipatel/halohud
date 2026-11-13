import unittest
from headless import Harness

class LeaderboardMotionTests(unittest.TestCase):
    def test_vertical_swap_reversal_and_solo_fade(self):
        h=Harness();h.lua.execute("""
          local M=require('leaderboard_motion');local s=M.new()
          local t={solo=false,leaderFirst=false,ahead={position='1',name='BEARMAN'}}
          M.update(s,t,0,450);assert(s.p.x==30.5 and s.o.x==-49)
          t.leaderFirst=true;M.update(s,t,.03,450);assert(s.p.x<30.5)
          local x,v=s.p.x,s.p.v;t.leaderFirst=false;M.update(s,t,0,450)
          assert(s.p.x==x and math.abs(s.p.v-v)<1e-10)
          for i=1,120 do M.update(s,t,1/60,450) end
          assert(s.p.x==30.5 and s.o.x==-49)
          t.solo=true;t.ahead={position='',name=''}
          M.update(s,t,.03,450);assert(s.opponent.name=='BEARMAN')
          for i=1,120 do M.update(s,t,1/60,450) end
          assert(s.p.x==-11.5 and s.opponentAlpha==0)
          t.solo=false;t.leaderFirst=true;t.ahead={position='2',name='RUSSELL'}
          for i=1,120 do M.update(s,t,1/60,450) end
          assert(s.p.x==-53.5 and s.o.x==30.5 and s.opponentAlpha==1)
        """)

    def test_crossover_fades_opponent_and_shared_highlight_projection(self):
        h=Harness();h.lua.execute("""
          local M=require('leaderboard_motion');local S=require('settings');local R=require('renderer');local T=require('telemetry')
          local t=T.new();t.solo=false;t.leaderFirst=false;t.ahead.name='BEARMAN'
          local m=M.new();M.update(m,t,0,450)
          m.p.x=0;m.o.x=0;M.update(m,t,0,450);assert(m.opponentAlpha==0)
          m.p.x=-15;t.leaderboardMotion=m
          local r=R.new(S.read(nil),1920,1080);local draw=r.draw;local count=0
          r.draw=function(q,...)
            if q[1]=='assets/player_highlight.png' then
              local p=r.point(-830+512*count/12,m.p.x-18.5)
              assert(math.abs(q[2].x-p.x)<1e-8 and math.abs(q[2].y-p.y)<1e-8)
              assert(q[6].y==104/192 and q[8].y==172/192);count=count+1
            end
            draw(q,...)
          end
          ui.beginTransparentWindow('test',vec2(),vec2(1920,1080),true,false)
          r.render(t);ui.endTransparentWindow();assert(count==12)
        """)

    def test_duration_control_auto_saves(self):
        h=Harness();h.frame(0)
        h.lua.execute("ui.slider=function(label,v) return label=='Leaderboard animation' and 650 or v end;script.windowMain()")
        h.frame(.41)
        self.assertEqual(float(h.ini['HUD']['LEADERBOARD_ANIMATION_MS']),650)

    def test_live_resize_preserves_transition(self):
        h=Harness(demo='OFF');h.lua.execute("""
          local R=require('renderer');local new=R.new
          R.new=function(...) local r=new(...);local render=r.render
            r.render=function(t) observed=t.leaderboardMotion.p.x;render(t) end;return r end
          uiState={windowSize=vec2(1920,1080)};ac.getUI=function() return uiState end
          ac.getSim=function() return {carsCount=2,currentSessionIndex=0,raceSessionType=3} end
          p={index=0,racePosition=2,gear=1,physicsAvailable=true,driverName=function() return 'Player' end}
          b={index=1,racePosition=1,driverName=function() return 'Bot' end}
          ac.getCar=function(i) return i==0 and p or b end
        """)
        h.frame(0);self.assertEqual(h.lua.globals().observed,30.5)
        h.lua.execute('p.racePosition=1;b.racePosition=2');h.frame(.25)
        x=h.lua.globals().observed
        self.assertLess(x,30.5);self.assertGreater(x,-53.5)
        h.lua.execute('uiState.windowSize=vec2(1280,720)');h.frame(.02)
        self.assertLess(h.lua.globals().observed,x)
        self.assertGreater(h.lua.globals().observed,-53.5)
