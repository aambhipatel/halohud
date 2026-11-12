-- Approved HTML preview motion, in pure Lua. State lives outside the renderer
-- so layout/cache rebuilds do not restart an in-flight transition.
local M={}
function M.new() return {phase=0,velocity=0} end
function M.update(s,active,dt,durationMS)
  local target=active and 1 or 0
  dt=type(dt)=='number' and dt==dt and math.max(0,math.min(0.05,dt)) or 0
  local w=7/(math.max(150,math.min(1000,durationMS or 420))/1000)
  local offset=s.phase-target
  local b=s.velocity+w*offset
  local decay=math.exp(-w*dt)
  s.phase=target+(offset+b*dt)*decay
  s.velocity=(s.velocity-w*b*dt)*decay
  if s.phase<0 or s.phase>1 then s.phase=math.max(0,math.min(1,s.phase));s.velocity=0 end
  if math.abs(s.phase-target)<0.0001 and math.abs(s.velocity)<0.002 then
    s.phase=target;s.velocity=0
  end
  return s.phase
end
function M.poses(p)
  p=math.max(0,math.min(1,p))
  local angle=math.rad(-45+45*p)
  local thickness=2.2+1.8*p
  return {
    {x=-12+2.5*p,y=8-19*p,length=24+8*p,angle=angle,thickness=thickness},
    {x=12-12*p,y=8-6*p,length=24+27*p,angle=angle,thickness=thickness}}
end
function M.vertices(pose,originU,originV)
  local c,s=math.cos(pose.angle),math.sin(pose.angle)
  local l,h=pose.length/2,pose.thickness/2
  local points={}
  for i,v in ipairs({{-l,-h},{l,-h},{l,h},{-l,h}}) do
    points[i]={originU+pose.x+v[1]*c-v[2]*s,originV+pose.y+v[1]*s+v[2]*c}
  end
  return points
end
return M
