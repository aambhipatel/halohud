import unittest
from headless import Harness

class ReverseSlotTests(unittest.TestCase):
    def test_reverse_neutral_forward_use_correct_first_slot(self):
        h=Harness();h.lua.execute('''local R=require('renderer');local S=require('settings');local T=require('telemetry')
          for _,count in ipairs({6,8,12}) do
            local cfg=S.read(nil);cfg.gearCount=count
            local r=R.new(cfg,1920,1080);local t=T.new()
            local text,draw=r.text,r.draw
            local labels,highlight
            r.text=function(label,u,v,size,color,...)
              if v==-12 and u>=430 and (label=='N' or label=='R') then labels[#labels+1]={label,u,v,size,color} end
              text(label,u,v,size,color,...)
            end
            r.draw=function(q,...)
              if q==r.gears[0] then highlight=true end
              draw(q,...)
            end
            for _,gear in ipairs({0,-1,1,-1,0}) do
              t.gear=gear;labels={};highlight=false
              ui.beginTransparentWindow('test',vec2(),vec2(1920,1080),true,false)
              r.render(t);ui.endTransparentWindow()
              assert(#labels==1 and labels[1][1]==(gear==-1 and 'R' or 'N'))
              assert(labels[1][2]==454 and labels[1][3]==-12)
              assert(highlight==(gear<=0))
              assert(labels[1][4]==(gear<=0 and 25 or 20))
            end
          end
        ''')

if __name__=='__main__':unittest.main()
