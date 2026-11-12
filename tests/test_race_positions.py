import unittest
from headless import Harness

class RacePositionTests(unittest.TestCase):
    def test_rank_changes_look_up_ahead_by_live_position(self):
        h=Harness()
        h.lua.execute('''local T=require('telemetry');local o=T.new()
          local p={index=0,racePosition=3,driverName=function() return 'Player Test' end}
          local a={index=1,racePosition=1,driverName=function() return 'AI Leader' end}
          local b={index=2,racePosition=2,driverName=function() return 'AI Ahead' end}
          local cars={[0]=p,a,b};local lookup=function(i) return cars[i] end
          T.raceRows(o,p,3,lookup,'FULL')
          assert(o.player.position=='3' and o.ahead.position=='2' and o.ahead.name=='AHEAD')
          p.racePosition=2;b.racePosition=3
          T.raceRows(o,p,3,lookup,'FULL')
          assert(o.player.position=='2' and o.ahead.name=='LEADER')
          p.racePosition=1;a.racePosition=2
          T.raceRows(o,p,3,lookup,'FULL');assert(o.leaderFirst and o.ahead.name=='LEADER' and o.ahead.position=='2')
          p.racePosition=3;b.racePosition=1
          T.raceRows(o,p,3,lookup,'CODE')
          assert(o.player.position=='3' and o.ahead.name=='LEA')
        ''')

    def test_missing_rank_opponent_and_solo_clear_stale_values(self):
        h=Harness();h.lua.execute('''local T=require('telemetry');local o=T.new()
          local p={index=0,racePosition=1,driverName=function() return 'Player Test' end}
          T.raceRows(o,p,4,function() return nil end,'FULL');assert(o.leaderFirst and o.ahead.name=='UNAVAILABLE')
          p.racePosition=4;T.raceRows(o,p,4,function() return nil end,'FULL')
          assert(o.player.position=='4' and o.ahead.name=='UNAVAILABLE')
          p.racePosition=0;T.raceRows(o,p,4,function() return nil end,'FULL')
          assert(o.player.position=='--' and o.ahead.name=='UNAVAILABLE')
          T.raceRows(o,p,1,function() return nil end,'FULL')
          assert(o.solo and o.player.position=='1' and o.ahead.name=='')
        ''')

    def test_app_ignores_player_first_board_in_bot_race(self):
        h=Harness(demo='AUTO');messages=[]
        h.lua.globals().recordText=messages.append
        h.lua.execute('''
          player={index=0,racePosition=3,driverName=function() return 'Player Test' end}
          leader={index=1,racePosition=1,driverName=function() return 'AI Leader' end}
          ahead={index=2,racePosition=2,driverName=function() return 'AI Ahead' end}
          ac.getSim=function() return {carsCount=3,currentSessionIndex=0,raceSessionType=3} end
          ac.getSession=function() return {type=3,leaderboard={[0]={car=player}}} end
          ac.getCar=function(i) return ({[0]=player,[1]=leader,[2]=ahead})[i] end
          ui.text=recordText
        ''')
        h.frame(0.25);h.lua.globals().script.windowMain()
        self.assertIn('Position 3 | Ahead 2 AHEAD',messages)
        messages.clear()
        h.lua.execute('player.racePosition=2;ahead.racePosition=3')
        h.frame(0.25);h.lua.globals().script.windowMain()
        self.assertIn('Position 2 | Ahead 1 LEADER',messages)

if __name__=='__main__':unittest.main()
