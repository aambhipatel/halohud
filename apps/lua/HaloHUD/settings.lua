-- One schema for defaults, compatibility reads, range clamps and saving.
local M={}
M.schema={
  drsEnabled={'DRS_CHIME_ENABLED',false}, drsTriggerMode={'DRS_TRIGGER_MODE','AUTO'}, drsVolume={'DRS_CHIME_VOLUME',0.65,0,1},
  drsCooldown={'DRS_COOLDOWN_SECONDS',1.5,1.5,10},
  drsMargin={'DRS_ACTIVATION_MARGIN_M',40,0,200},
  drsFreeSeconds={'DRS_FREE_USE_SECONDS',2,0.5,10},
  drsForceOn={'DRS_FORCE_ON',''}, drsForceOff={'DRS_FORCE_OFF',''},
  debugMode={'DEBUG_MODE',false}, lockHUD={'LOCK_HUD_POSITION',false},
  debugDRS={'DEBUG_DRS',false}, debugDRSActive={'DEBUG_DRS_ACTIVE_CHIME',false},
  drsSound={'DRS_SOUND','drs_chime.wav',preserveCase=true},
  enabled={'ENABLED',true}, scale={'SCALE',1,0.5,1.5}, x={'X_OFFSET',0,-960,960},
  y={'Y_OFFSET',0,-540,540}, curve={'CURVE',1,0,1.6}, opacity={'OPACITY',0.95,0,1},
  leftScale={'LEFT_SCALE',1,0.5,1.5}, dialScale={'DIAL_SCALE',1,0.5,1.5},
  moduleScale={'MODULE_SCALE',1,0.5,1.5}, rightScale={'RIGHT_SCALE',1,0.5,1.5},
  showLeft={'SHOW_LEFT_ZONE',true}, showCenter={'SHOW_CENTER_ZONE',true}, showRight={'SHOW_RIGHT_ZONE',true},
  outerArc={'OUTER_ARC',false}, aeroDuration={'AERO_ANIMATION_MS',420,150,1000},
  leaderboardDuration={'LEADERBOARD_ANIMATION_MS',450,200,900},
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
  return type(v)=='string' and not d.preserveCase and v:upper() or v
end
-- The old release kept dragMode in memory only. Honor an explicit legacy
-- config key if an older or customized install did write one.
local function legacyLock(ini)
  if not ini or ini:get('HUD','LOCK_HUD_POSITION','')~='' then return nil end
  for _,key in ipairs({'DRAG_HUD_WITH_MOUSE','DRAG_MODE'}) do
    local raw=ini:get('HUD',key,''):match('^%s*(.-)%s*$'):upper()
    if raw=='0' or raw=='FALSE' or raw=='OFF' or raw=='NO' then return true end
    if raw=='1' or raw=='TRUE' or raw=='ON' or raw=='YES' then return false end
  end
end

function M.diagnostics(c,result)
  local debug=c.debugMode
  result.drsLog=debug and c.debugDRS
  result.activeCue=result.drsLog and c.debugDRSActive
  result.forceDemo=debug and c.demo=='ON'
  result.profile=debug and c.profileCPU
end

function M.read(ini)
  local c={}
  for k,d in pairs(M.schema) do
    local v=d[2]
    if ini then v=ini:get('HUD',d[1],d[2]) end
    c[k]=clean(v,d)
  end
  local migratedLock=legacyLock(ini)
  if migratedLock~=nil then c.lockHUD=migratedLock end
  if c.drsTriggerMode~='SPLINE' then c.drsTriggerMode='AUTO' end
  c.strips=math.floor(c.strips)
  c.p2pActiveStatus=math.floor(c.p2pActiveStatus)
  c.carProfile={}
  for k,d in pairs(M.profileSchema) do
    local v=d[2]
    if ini then v=ini:get(M.profileSection,d[1],d[2]) end
    -- Metadata/path casing is significant: do not uppercase profile strings.
    c.carProfile[k]=type(d[2])=='string' and v or clean(v,d)
  end
  return c,migratedLock~=nil
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
