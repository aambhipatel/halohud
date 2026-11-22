-- Normalized, inclusive spline intervals. This module runs in plain Lua.
local M={}
function M.isInsideZone(pos,start,finish)
  if start<=finish then return pos>=start and pos<=finish end
  return pos>=start or pos<=finish
end

function M.distance(a,b)
  local distance=math.abs(a-b)
  return math.min(distance,1-distance)
end

-- DETECTION is recorded for diagnostics, but only START/END describe where
-- DRS can be activated. A small margin around START tolerates telemetry lag.
function M.find(zones,pos,margin)
  local nearStart,nearBoundary
  for i,zone in ipairs(zones) do
    if M.isInsideZone(pos,zone.start,zone.finish) then return i,i,true end
    if M.distance(pos,zone.start)<=margin then nearStart=nearStart or i end
    if M.distance(pos,zone.finish)<=margin then nearBoundary=nearBoundary or i end
  end
  return nearStart,nearStart or nearBoundary,false
end
return M
