-- Rising-edge detection and session-scoped car classification.
local ZoneMath=require('drs_zone_math')
local M={}
local STARTUP_GRACE_SECONDS=5
function M.new()
  return {clock=0,lastPlayed=-math.huge,classes={},inside=false,outsideSeconds=0,availableTravel=0,resetAt=0,slowSeconds=0,frame=0}
end

function M.reset(s)
  s.resetAt=s.clock
  s.learnSeeded=false
  s.hasDriven=false
  s.slowSeconds=0
  s.slowReason=nil
  s.previous=nil
  s.previousActive=nil
  s.activeRise=false
  s.position=nil
  s.inPits=nil
  s.outsideSeconds=0
  s.availableTravel=0
  s.latchedZone=nil
  s.inside=false
end

-- Check for discontinuities before considering an availability edge. Compare
-- signed wrapped travel so a normal crossing of the timing line stays valid.
function M.sample(s,car,dt,trackLength)
  local pos=car.splinePosition
  if type(pos)~='number' or not (pos>=0 and pos<=1) then
    M.reset(s)
    return false,'invalid spline position'
  end
  local pits=car.isInPitlane==true or car.isInPit==true
  local delta=0
  if s.position then
    local rawDelta=pos-s.position
    delta=rawDelta
    if delta>.5 then delta=delta-1 elseif delta<-.5 then delta=delta+1 end
    local maxJump=.025
    if trackLength and trackLength>0 then
      maxJump=math.min(.1,math.max(25,math.abs(car.speedKmh or 0)/3.6*math.min(dt,.5)*3)/trackLength)
    end
    if math.abs(delta)>maxJump then
      M.reset(s);s.position=pos;s.inPits=pits
      return false,'teleport',delta,rawDelta,maxJump
    end
  end
  if pits or s.inPits then
    -- Reset on entering/leaving pits. Remaining in pits is one continuous
    -- observation, so sustained evidence can accumulate after the grace period.
    if s.inPits~=pits then M.reset(s) end
    s.position=pos;s.inPits=pits
    return false,'pit lane'
  end
  s.position=pos;s.inPits=pits
  return true,nil,math.max(0,delta)
end

function M.overrideList(value)
  local ids={}
  for id in value:gmatch('[^,%s;]+') do ids[id:lower()]=true end
  return ids
end

function M.session(s)
  M.reset(s)
  s.classes={}
  M.resetTrace(s)
end

local function classify(s,id,value,reason,debug,car)
  local previous=s.classes[id]
  if previous==value or previous=='free_use' then return end
  s.classes[id]=value
  if debug then
    debug(string.format('classification: %s %s -> %s (%s) | frame=%d | splinePosition=%s | speedKmh=%s | isInPitlane=%s | isInPit=%s | drsAvailable=%s',
      id,previous or 'unknown',value,reason,s.frame,tostring(car.splinePosition),tostring(car.speedKmh),
      tostring(car.isInPitlane),tostring(car.isInPit),tostring(car.drsAvailable)))
  end
end

function M.status(s,reason,debug,attempt)
  if reason==s.reason and not attempt then return end
  s.reason=reason
  if reason and debug then debug('suppression: '..reason) end
end

function M.triggerMode(cfg,override)
  if override=='on' or cfg.drsTriggerMode=='SPLINE' then return 'SPLINE' end
  return 'AUTO'
end

local function crossingZone(zones,from,to,travel,margin)
  if not from or travel<=0 then return nil end
  local first,distance
  for i,item in ipairs(zones) do
    local toStart=(item.start-from)%1
    if toStart>0 and toStart<=travel+1e-9 and (not distance or toStart<distance) then
      if ZoneMath.isInsideZone(to,item.start,item.finish) or ZoneMath.distance(to,item.finish)<=margin then
        first,distance=i,toStart
      end
    end
  end
  return first
end

function M.update(s,car,id,dt,length,zones,cfg,override,debug,sessionReady)
  dt=math.min(.25,math.max(0,dt))
  s.clock=s.clock+dt
  s.frame=s.frame+1
  local previous=s.previous
  local previousPosition=s.position
  local available=car.drsAvailable==true
  s.activeRise=false
  local classification=s.classes[id] or 'unknown'
  if not car.drsPresent then
    classify(s,id,'no_drs','DRS absent',debug,car)
    M.reset(s)
    s.classification=s.classes[id]
    M.status(s,'no DRS',debug)
    return false
  end
  if classification=='no_drs' then
    classify(s,id,'unknown','DRS now reported',debug,car)
    classification='unknown'
  end
  local speed=math.abs(car.speedKmh or 0)
  local pits=car.isInPitlane or car.isInPit
  local valid,reason,travel,rawDelta,jumpLimit=M.sample(s,car,dt,length)
  local zone,nearZone,inside
  local margin=length and length>0 and math.min(.5,cfg.drsMargin/length) or 0
  if (valid or reason=='pit lane') and #zones>0 and s.position then
    zone,nearZone,inside=ZoneMath.find(zones,s.position,margin)
  end
  s.inside=inside==true
  if sessionReady==false then
    s.learnSeeded=false;s.hasDriven=false;s.resetAt=s.clock
  elseif valid and speed>=5 and travel>0 and s.learnSeeded then
    s.hasDriven=true
  end
  -- First samples, placement on the grid and stationary cars inside a real
  -- activation zone are insufficient evidence. Begin a fresh dwell after grace.
  local slowReason=pits and 'available in pit lane' or speed<1 and s.hasDriven and 'available while stationary'
  if available and slowReason and not nearZone and (valid or reason=='pit lane')
    and s.learnSeeded and sessionReady~=false and s.clock-s.resetAt>=STARTUP_GRACE_SECONDS then
    if s.slowReason~=slowReason then s.slowSeconds=0;s.slowReason=slowReason end
    local elapsedAfterGrace=s.clock-s.resetAt-STARTUP_GRACE_SECONDS
    s.slowSeconds=s.slowSeconds+math.min(dt,elapsedAfterGrace)
    if s.slowSeconds>=cfg.drsFreeSeconds then classify(s,id,'free_use',slowReason,debug,car) end
  else
    s.slowSeconds=0;s.slowReason=nil
  end
  if valid or reason=='pit lane' then s.learnSeeded=sessionReady~=false end
  if valid and sessionReady~=false and available and not nearZone and speed>=1 then
    s.outsideSeconds=s.outsideSeconds+dt
    s.availableTravel=s.availableTravel+travel
    if (#zones>0 and s.outsideSeconds>=cfg.drsFreeSeconds)
      or (#zones==0 and (s.availableTravel>=.35 or s.outsideSeconds>=45)) then
      classify(s,id,'free_use','sustained availability away from known zones',debug,car)
    end
  else
    s.outsideSeconds=0;s.availableTravel=0
  end
  s.classification=s.classes[id] or 'unknown'
  if not valid then
    if reason=='teleport' and debug then
      debug(string.format('state reset: teleport | splinePosition=%.6f | spline delta=%+.6f | raw delta=%+.6f | limit=%.6f',
        s.position,travel,rawDelta,jumpLimit))
    end
    M.status(s,reason,debug,reason=='teleport')
    return false
  end
  local active=car.drsActive==true
  s.activeRise=s.previousActive==false and active
  s.previousActive=active
  s.previous=available
  if s.latchedZone and nearZone~=s.latchedZone then s.latchedZone=nil end
  if previous==nil then
    s.latchedZone=inside and zone or nil
    M.status(s,zone and 'started in zone' or available and 'already available on first sample' or 'initial sample',debug)
    return false
  end
  if M.triggerMode(cfg,override)=='SPLINE' then
    if #zones==0 then M.status(s,'no track zones for spline trigger',debug);return false end
    local crossed=crossingZone(zones,previousPosition,s.position,travel,margin)
    if not crossed then return false end
    if override=='off' then M.status(s,'override off',debug,true);return false end
    if s.latchedZone==crossed then M.status(s,'already cued in zone',debug,true);return false end
    if s.clock-s.lastPlayed<cfg.drsCooldown then M.status(s,'cooldown',debug,true);return false end
    return true,crossed
  end
  if not available or previous then
    if debug and s.inside and not available then M.status(s,'DRS unavailable in zone',debug) end
    return false
  end
  if override=='off' then M.status(s,'override off',debug,true);return false end
  if s.classification=='free_use' then M.status(s,'free-use car',debug,true);return false end
  if #zones>0 and not zone then M.status(s,'outside activation zone',debug,true);return false end
  if speed<5 then M.status(s,'speed below 5 km/h',debug,true);return false end
  if car.drsActive then M.status(s,'DRS already active at availability edge',debug,true);return false end
  if zone then classify(s,id,'zone_restricted','availability rose at activation',debug,car) end
  s.classification=s.classes[id] or 'unknown'
  if zone and s.latchedZone==zone then M.status(s,'already cued in zone',debug,true);return false end
  if s.clock-s.lastPlayed<cfg.drsCooldown then M.status(s,'cooldown',debug,true);return false end
  return true,zone
end

function M.played(s,zone,debug)
  s.lastPlayed=s.clock
  s.latchedZone=zone
  s.reason=nil
  if debug then debug('chime fired') end
end

function M.resetTrace(s)
  s.traceReady=false
  s.traceAvailable=nil
  s.traceActive=nil
  s.traceZone=nil
end

-- Diagnostics read raw telemetry, including frames rejected by eligibility.
-- Use wall time so the summary still advances while the simulation is paused.
function M.trace(s,car,id,sim,zones,cooldown,now,log)
  local pos=car and car.splinePosition
  local available=car and car.drsAvailable
  local active=car and car.drsActive
  local present=car and car.drsPresent
  local zone
  if zones and type(pos)=='number' and pos>=0 and pos<=1 then
    for i,item in ipairs(zones) do
      if ZoneMath.isInsideZone(pos,item.start,item.finish) then zone=item.index or i-1;break end
    end
  end
  local classification=s.classes[id] or 'unknown'
  if not s.traceReady or s.traceAvailable~=available or s.traceActive~=active or s.traceZone~=zone then
    local place=' | splinePosition='..tostring(pos)..' | in-zone='..tostring(zone or 'none')
      ..' | classification: '..classification
    if not s.traceReady or s.traceAvailable~=available then
      log('drsAvailable '..tostring(s.traceAvailable)..' -> '..tostring(available)..place)
    end
    if not s.traceReady or s.traceActive~=active then
      log('drsActive '..tostring(s.traceActive)..' -> '..tostring(active)..place)
    end
    if s.traceReady and s.traceZone~=zone then
      log('zone '..tostring(s.traceZone or 'none')..' -> '..tostring(zone or 'none')..place)
    end
    s.traceReady=true
    s.traceAvailable=available;s.traceActive=active;s.traceZone=zone
  end
  if not s.nextTrace or now>=s.nextTrace then
    s.nextTrace=now+1
    log(string.format('state | car=%s | drsPresent=%s | drsAvailable=%s | drsActive=%s | splinePosition=%s | in-zone=%s | classification=%s | cooldown=%.2fs | replay=%s | paused=%s | trigger mode=%s | last suppression=%s',
      id,tostring(present),tostring(available),tostring(active),tostring(pos),tostring(zone or 'none'),
      classification,math.max(0,cooldown-(s.clock-s.lastPlayed)),
      tostring(sim and (sim.isReplayActive==true or sim.isReplayOnlyMode==true) or false),
      tostring(sim and sim.isPaused==true or false),s.triggerLabel or 'DRS availability (auto)',s.reason or 'none'))
  end
end

return M
