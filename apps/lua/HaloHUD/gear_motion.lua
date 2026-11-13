-- Approved HTML gear animation, pure Lua. Persistent state survives layout rebuilds.
local M={}
function M.new() return {gear=nil,position=0,velocity=0,letter='N',scale=1,phase=nil} end
function M.update(s,gear,dt,duration)
  local target=math.max(0,gear)
  local desired=gear==-1 and 'R' or 'N'
  dt=type(dt)=='number' and dt==dt and math.max(0,math.min(.05,dt)) or 0
  duration=math.max(150,math.min(600,duration or 260))/1000
  if s.gear==nil then
    s.gear=gear;s.position=target;s.letter=desired
  elseif s.gear~=gear then
    if s.gear<=0 and gear<=0 then
      if s.phase==nil then s.phase=0 end
    else s.letter=desired;s.phase=nil;s.scale=1 end
    s.gear=gear
  end
  if s.phase~=nil then
    local previous=s.phase
    s.phase=math.min(1,s.phase+dt/(2*duration))
    s.scale=1+.30*math.sin(math.pi*s.phase)^2
    if previous<.5 and s.phase>=.5 then s.letter=desired end
    if s.phase>=1 then
      s.scale=1
      s.phase=s.letter~=desired and 0 or nil
    end
  else s.scale=1 end
  local w=7/duration;local offset=s.position-target
  local b=s.velocity+w*offset;local decay=math.exp(-w*dt)
  s.position=target+(offset+b*dt)*decay
  s.velocity=(s.velocity-w*b*dt)*decay
  if s.position<0 then s.position=0;s.velocity=0 end
  if math.abs(s.position-target)<.0001 and math.abs(s.velocity)<.002 then
    s.position=target;s.velocity=0
  end
  return s
end
return M
