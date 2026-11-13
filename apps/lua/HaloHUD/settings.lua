-- One schema for defaults, compatibility reads, range clamps and saving.
local M={}
M.schema={
  enabled={'ENABLED',true}, scale={'SCALE',1,0.5,1.5}, x={'X_OFFSET',0,-960,960},
  y={'Y_OFFSET',0,-540,540}, curve={'CURVE',1,0,1.6}, opacity={'OPACITY',0.95,0,1},
  leftScale={'LEFT_SCALE',1,0.5,1.5}, dialScale={'DIAL_SCALE',1,0.5,1.5},
  moduleScale={'MODULE_SCALE',1,0.5,1.5}, rightScale={'RIGHT_SCALE',1,0.5,1.5},
  outerArc={'OUTER_ARC',false}, aeroDuration={'AERO_ANIMATION_MS',420,150,1000},
  gearDuration={'GEAR_ANIMATION_MS',260,150,600},
  profileCPU={'PROFILE_CPU',false}, units={'UNITS','KMH'}, names={'DRIVER_NAMES','FULL'},
  theme={'THEME','TEAL'}, demo={'DEMO','AUTO'}, damping={'PEDAL_DAMPING_MS',70,1,500},
  energyDamping={'ENERGY_DAMPING_MS',70,60,80}, recoveryMax={'RECOVERY_MAX_RATE',0.10,0.001,10},
  recoveryWindow={'RECOVERY_WINDOW_MS',250,50,2000},
  recoveryFallback={'RECOVERY_FALLBACK','BRAKE'}, noKersDeploy={'NO_KERS_DEPLOY','DRS_OR_P2P'},
  p2pActiveStatus={'P2P_ACTIVE_STATUS',-1,-1,255},
  gearCount={'GEAR_COUNT',8,1,12}, revLimit={'REV_LIMIT_RPM',0,0,30000},
  rpmMax={'RPM_MAX',15000,1000,30000}, strips={'CURVE_STRIPS',12,8,32}}
M.profileSection='CAR_PROFILE_FORMULA_ULTRA_26'
-- Confirmed readable metadata. -1 means NOT FOUND, not a car specification.
M.profileSchema={enabled={'ENABLED',true}, carId={'CAR_ID','formula_ultra_26'},
  name={'NAME','Formula Ultra 2026'}, class={'CLASS','race'}, bhp={'UI_BHP','950 bhp'},
  torque={'UI_TORQUE','575Nm'}, weight={'UI_WEIGHT','768kg*'},
  speed={'UI_TOP_SPEED','350+km/h'}, acceleration={'UI_ACCELERATION','2s 0-100'},
  ratio={'UI_POWER_WEIGHT','0.81 kg/hp'}, lcd={'DISPLAY_MESH','LCD'},
  script={'DISPLAY_SCRIPT','SF24_Display_script.lua'},
  live={'USE_LIVE_POWERTRAIN',true}, rpmMax={'RPM_MAX',-1,-1,30000},
  revLimit={'REV_LIMIT_RPM',-1,-1,30000}, gears={'GEARS',-1,-1,12},
  recoveryMax={'RECOVERY_MAX_RATE',-1,-1,10}, capacity={'BATTERY_CAPACITY_KJ',-1,-1,1000000}}
local function clean(v,d)
  if type(d[2])=='number' then
    if type(v)~='number' or v~=v or math.abs(v)==math.huge then v=d[2] end
    return math.max(d[3],math.min(d[4],v))
  end
  return type(v)=='string' and v:upper() or v
end
function M.read(ini)
  local c={}
  for k,d in pairs(M.schema) do
    local v=d[2]
    if ini then v=ini:get('HUD',d[1],d[2]) end
    c[k]=clean(v,d)
  end
  c.strips=math.floor(c.strips)
  c.p2pActiveStatus=math.floor(c.p2pActiveStatus)
  c.carProfile={}
  for k,d in pairs(M.profileSchema) do
    local v=d[2]
    if ini then v=ini:get(M.profileSection,d[1],d[2]) end
    -- Metadata/path casing is significant: do not uppercase profile strings.
    c.carProfile[k]=type(d[2])=='string' and v or clean(v,d)
  end
  return c
end
function M.effective(c,id,car)
  local e={}; for k,v in pairs(c) do e[k]=v end
  local p=c.carProfile
  e.profileActive=p and p.enabled and id==p.carId or false
  e.powertrainSource='generic configuration'
  if e.profileActive then
    local live=p.live and car and car.physicsAvailable~=false
    local limiter=live and car.rpmLimiter or 0
    local gears=live and car.gearCount or 0
    if p.rpmMax>0 then e.rpmMax=p.rpmMax
    elseif type(limiter)=='number' and limiter>0 then e.rpmMax=limiter end
    if p.revLimit>0 then e.revLimit=p.revLimit
    elseif type(limiter)=='number' and limiter>0 then e.revLimit=limiter end
    if p.gears>0 then e.gearCount=math.floor(p.gears)
    elseif type(gears)=='number' and gears>0 then e.gearCount=math.floor(gears) end
    e.gearCount=math.max(1,math.min(12,e.gearCount))
    if p.recoveryMax>0 then e.recoveryMax=p.recoveryMax end
    e.powertrainSource=live and 'live CSP / explicit profile overrides' or 'generic fallback / explicit profile overrides'
  end
  return e
end
function M.save(path,c)
  -- Preserve unknown keys/other sections; never replace the file with a subset.
  local ini=ac.INIConfig.load(path)
  for k,d in pairs(M.schema) do ini:set('HUD',d[1],clean(c[k],d)) end
  for k,d in pairs(M.profileSchema) do
    local v=c.carProfile[k]
    ini:set(M.profileSection,d[1],type(d[2])=='string' and v or clean(v,d))
  end
  ini:save(path)
end
return M
