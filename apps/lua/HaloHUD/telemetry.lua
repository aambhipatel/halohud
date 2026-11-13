-- Pure Lua: intentionally independent of CSP so edge cases can be tested offline.
local M = {}
local function finite(x, fallback)
  return type(x) == 'number' and x == x and math.abs(x) < math.huge and x or (fallback or 0)
end
function M.clamp(x, lo, hi) return math.max(lo or 0, math.min(hi or 1, finite(x))) end

-- ASCII font atlas: normalize common Latin surnames, use ? for other code points.
local accents = {['ä']='A',['á']='A',['à']='A',['â']='A',['ã']='A',['å']='A',
  ['Ä']='A',['Á']='A',['À']='A',['Â']='A',['Ã']='A',['Å']='A',
  ['é']='E',['è']='E',['ê']='E',['ë']='E',['É']='E',['È']='E',['Ê']='E',['Ë']='E',
  ['í']='I',['ì']='I',['î']='I',['ï']='I',['Í']='I',['Ì']='I',['Î']='I',['Ï']='I',
  ['ö']='O',['ó']='O',['ò']='O',['ô']='O',['õ']='O',['Ö']='O',['Ó']='O',['Ò']='O',['Ô']='O',
  ['ü']='U',['ú']='U',['ù']='U',['û']='U',['Ü']='U',['Ú']='U',['Ù']='U',['Û']='U',
  ['ñ']='N',['Ñ']='N',['ç']='C',['Ç']='C',['ß']='SS',['ø']='O',['Ø']='O',['ł']='L',['Ł']='L'}
function M.name(raw, mode)
  local s = tostring(raw or '')
  for a, b in pairs(accents) do s = s:gsub(a, b) end
  s = s:gsub('[\194-\244][\128-\191]*', '?'):upper():gsub('[^ -~]', '')
  s = s:match('^%s*(.-)%s*$')
  s = s:match('([^%s]+)$') or 'DRIVER'
  if mode == 'CODE' then return s:sub(1, 3) end
  return #s > 19 and s:sub(1, 18)..'.' or s
end

function M.new()
  return {speed=0, rpm=0, gear=0, brake=0, throttle=0, rawBrake=0, rawThrottle=0,
    ers=false, charge=0, ersInput=0, charging=false, overtake=false,
    deploy=0, recharge=0, rawDeploy=0, rawRecharge=0, solo=false, leaderFirst=false,
    aeroPresent=false, aeroActive=false, aeroAvailable=false, physics=false, demo=false,
    ahead={position='--', name='CLEAR TRACK'}, player={position='--', name='DRIVER'}}
end

function M.sample(out, car, dt, tau)
  out.demo = false
  out.speed = math.max(0, finite(car.speedKmh))
  out.rpm = math.max(0, finite(car.rpm))
  out.gear = math.floor(finite(car.gear))
  out.physics = car.physicsAvailable ~= false
  out.rawBrake = out.physics and M.clamp(car.brake) or 0
  out.rawThrottle = out.physics and M.clamp(car.gas) or 0
  local a = 1 - math.exp(-math.max(0, finite(dt)) / math.max(0.001, tau))
  out.brake = out.brake + (out.rawBrake - out.brake) * a
  out.throttle = out.throttle + (out.rawThrottle - out.throttle) * a
  out.ers = out.physics and car.kersPresent == true
  out.charge = out.ers and M.clamp(car.kersCharge) or 0
  out.chargeValid = type(car.kersCharge)=='number' and car.kersCharge==car.kersCharge
    and car.kersCharge>=0 and car.kersCharge<=1
  -- This is CSP's normalized KERS input, not a claim of measured motor kW.
  out.ersInput = out.ers and M.clamp(car.kersInput) or 0
  out.charging = out.ers and car.kersCharging == true
  -- OVERTAKE means the explicit button is pressed, not guessed from throttle.
  out.overtake = out.ers and car.kersButtonPressed == true
  out.aeroPresent = out.physics and car.drsPresent == true
  out.aeroActive = out.aeroPresent and car.drsActive == true
  out.aeroAvailable = out.aeroPresent and car.drsAvailable == true
  -- SDK declares p2pStatus but not its enum values. Only a user-specified active
  -- value may enable this fallback; -1 in settings means unknown/disabled.
  out.p2pStatus = out.physics and finite(car.p2pStatus,-1) or -1
  return out
end

-- Charge fraction/second, not power or lap-budget usage. Quantized telemetry is
-- accumulated across unchanged frames; a timeout activates the explicit fallback.
function M.energy(out,dt,cfg)
  dt=finite(dt)
  local target=0
  if dt>0 and dt<=0.5 and out.ers and out.charging and out.chargeValid then
    if out._lastCharge and out._wasCharging then
      out._elapsed=(out._elapsed or 0)+dt
      local delta=out.charge-out._lastCharge
      if delta~=0 then
        out._rate=math.max(0,delta)/math.max(dt,out._elapsed)
        out._elapsed=0; out._measured=true
      elseif out._elapsed >= cfg.recoveryWindow/1000 then
        out._measured=false; out._rate=0
      end
    else out._measured=false; out._rate=0; out._elapsed=0 end
    if out.charge>=1 then target=0
    elseif out._measured then target=M.clamp(out._rate/cfg.recoveryMax)
    elseif cfg.recoveryFallback=='BRAKE' then target=out.rawBrake end
  elseif out.ers and out.charging and not out.chargeValid and cfg.recoveryFallback=='BRAKE' then
    target=out.rawBrake
  else out._measured=false; out._rate=0; out._elapsed=0 end
  -- Ignore pause/seek/long-frame derivatives; baseline is always advanced.
  if dt<=0 or dt>0.5 then target=0; out._measured=false; out._elapsed=0 end
  out._lastCharge=out.chargeValid and out.charge or nil
  out._wasCharging=out.charging
  out.rawRecharge=target
  local fallback=cfg.noKersDeploy=='DRS' or cfg.noKersDeploy=='DRS_OR_P2P'
  local p2p=cfg.noKersDeploy=='DRS_OR_P2P' and (cfg.p2pActiveStatus or -1)>=0
    and out.p2pStatus==cfg.p2pActiveStatus
  out.rawDeploy=out.ers and out.ersInput or
    (out.physics and fallback and (out.aeroActive or p2p) and 1 or 0)
  local a=1-math.exp(-math.max(0,dt)/(cfg.energyDamping/1000))
  out.recharge=out.recharge+(target-out.recharge)*a
  out.deploy=out.deploy+(out.rawDeploy-out.deploy)*a
  if not out.ers then
    out.recharge=0
    if not fallback or not out.physics then out.deploy=0 end
  end
end

-- Called at 4 Hz, separate from graphics-rate telemetry. CSP's leaderboard order
-- handles race positions and practice/qualifying lap-time rankings consistently.
function M.rows(out, player, count, atRank, mode, carCount)
  out.leaderFirst=false
  -- The simulation count distinguishes a solo session from P1 or a partially
  -- populated leaderboard. Older callers can supply just the leaderboard count.
  out.solo = (carCount or count)==1
  out.ahead.position, out.ahead.name = '--', 'CLEAR TRACK'
  if out.solo then out.ahead.position, out.ahead.name = '', '' end
  out.player.position = out.solo and '1' or '--'
  out.player.name = M.name(player:driverName(), mode)
  local previous, previousRank = nil, nil
  for rank = 0, math.max(0, finite(count)) - 1 do
    local other = atRank(rank)
    if other then
      if other.index == player.index then
        out.player.position = tostring(rank + 1)
        if previous then
          out.ahead.position = tostring(previousRank + 1)
          out.ahead.name = M.name(previous:driverName(), mode)
        end
        return
      end
      previous, previousRank = other, rank
    end
  end
  -- No populated leaderboard yet: keep the real name, leave rank unavailable.
end

-- Race classification must use each car's live racePosition, never its index
-- in session.leaderboard (which can keep the player first in AI races).
-- The comparison row holds P2 when leading, otherwise the driver at P-1.
function M.raceRows(out, player, count, getCar, mode)
  out.solo=count==1
  out.leaderFirst=false
  out.player.name=M.name(player:driverName(),mode)
  local position=finite(player.racePosition)
  if position<1 or position~=math.floor(position) then position=out.solo and 1 or 0 end
  out.player.position=position>0 and tostring(position) or '--'
  out.ahead.position,out.ahead.name='--','UNAVAILABLE'
  if out.solo then out.ahead.position,out.ahead.name='','';return end
  if position<1 then return end
  out.leaderFirst=position==1
  local otherPosition=out.leaderFirst and 2 or position-1
  for i=0,count-1 do
    local other=getCar(i)
    if other and other.index~=player.index and other.isConnected~=false
      and other.isActive~=false and finite(other.racePosition)==otherPosition then
      out.ahead.position=tostring(otherPosition)
      out.ahead.name=M.name(other:driverName(),mode)
      return
    end
  end
end

function M.demo(out, t, mode)
  out.solo=false
  out.leaderFirst=false
  out.demo, out.physics, out.ers, out.aeroPresent = true, true, true, true
  out.speed = 180 + 116 * math.sin(t * 0.65)
  out.rpm = 7900 + 6900 * math.sin(t * 0.81)
  out.gear = math.min(8, math.floor((math.sin(t * 0.39) + 1) * 5) - 1) -- R,N,1..8
  out.brake = (math.sin(t * 1.7) + 1) / 2
  out.throttle = (math.sin(t * 1.7 + math.pi) + 1) / 2
  out.rawBrake, out.rawThrottle = out.brake, out.throttle
  out.charge = (math.sin(t * 0.4) + 1) / 2
  out.ersInput = out.throttle
  out.deploy = out.throttle
  out.recharge = out.brake>0.55 and out.brake or 0
  out.charging = out.brake > 0.55
  out.overtake = math.sin(t * 0.8) > 0.3
  out.aeroActive = math.sin(t * 0.6) > 0
  out.aeroAvailable = true
  out.ahead = {position='12', name=M.name('Oliver Bearman', mode)}
  out.player = {position='13', name=M.name('George Russell', mode)}
  -- Exercise every board transition in demo, not just the telemetry gauges.
  local phase=math.floor((t%24)/6)
  if phase==1 then out.player.position='12';out.ahead.position='11'
  elseif phase==2 then out.leaderFirst=true;out.player.position='1';out.ahead.position='2'
  elseif phase==3 then out.solo=true;out.player.position='1';out.ahead.position='';out.ahead.name='' end
  return out
end
return M
