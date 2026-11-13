-- Approved vertical leaderboard spring. State persists independently of draw caches.
local M={}
function M.new() return {ready=false,p={x=30.5,v=0},o={x=-49,v=0},a={x=1,v=0},opponent={position='--',name='UNAVAILABLE'}} end
function M.update(s,t,dt,duration)
  local p=t.solo and -11.5 or t.leaderFirst and -53.5 or 30.5
  local o=t.leaderFirst and 30.5 or -49
  local a=t.solo and 0 or 1
  if not t.solo then s.opponent.position=t.ahead.position;s.opponent.name=t.ahead.name end
  dt=type(dt)=='number' and dt==dt and math.max(0,math.min(.05,dt)) or 0
  local w=7/(math.max(200,math.min(900,duration or 450))/1000)
  for key,target in pairs({p=p,o=o,a=a}) do
    local axis=s[key]
    if not s.ready then axis.x=target;axis.v=0 end
    local d=axis.x-target;local b=axis.v+w*d;local decay=math.exp(-w*dt)
    axis.x=target+(d+b*dt)*decay;axis.v=(axis.v-w*b*dt)*decay
    if math.abs(axis.x-target)<.0001 and math.abs(axis.v)<.002 then axis.x=target;axis.v=0 end
  end
  s.ready=true
  s.opponentAlpha=math.max(0,math.min(1,s.a.x))*math.min(1,math.abs(s.o.x-s.p.x)/55)
  return s
end
return M
