-- HaloHUD for Assetto Corsa 1.11.1, original screen-space artwork. CSP 0.2.0+ (build 2651).
-- Required UI/telemetry calls were checked against the shipped 0.2.0 SDK.
local Telemetry=require('telemetry')
local Settings=require('settings')
local Renderer=require('renderer')
local HUDDrag=require('hud_drag')
local diagnostics={}
local Aero=require('aero')
local aero=Aero.new()
local GearMotion=require('gear_motion')
local gearMotion=GearMotion.new()
local LeaderboardMotion=require('leaderboard_motion')
local leaderboardMotion=LeaderboardMotion.new()
local DRSChime=require('drs_chime')
local DRSAudio=require('drs_audio')
local drs=DRSChime.new()
-- Script-scope state holds a strong reference to the CSP audio event.
local drsAudio=DRSAudio.new(__dirname..'/sounds')
local DRSZones=require('drs_zones')
local zones,zonePath,zoneError
local forceOn,forceOff
local loggedZoneFailure,zoneDebugLogged
local cfg, activeCfg, renderer, oldWidth, oldHeight
local function drsLog(message)
  if ac.log then pcall(ac.log,'[HaloHUD DRS] '..message) end
end
local function diagnosticLog() return diagnostics.drsLog and drsLog or nil end
local function resetDRSSession()
  if diagnostics.drsLog then drsLog('state reset: session start or restart') end
  DRSChime.session(drs)
  DRSAudio.stop(drsAudio)
  drs.session=nil
  zones,zonePath,zoneError=nil,nil,nil
  zoneDebugLogged=false
end
local drsSessionHook
if ac.onSessionStart then
  local ok,hook=pcall(ac.onSessionStart,resetDRSSession)
  if ok then drsSessionHook=hook end
end
local state=Telemetry.new()
local demoTime, rowTimer, previousMode = 0, 0, nil
local enabled=false
local cpu={update=0,draw=0,maxDraw=0,frames=0}
local errorMessage=nil
local statusMessage=nil
local dirty,saveTimer=false,0
local drag={}
local function markDirty()
  dirty=true; saveTimer=0.4; statusMessage='Saving settings...'
end
local function finishDrag()
  if drag.changed then markDirty() end
  drag.startX,drag.changed=nil,false
end
local function saveConfig()
  local ok,err=pcall(Settings.save,__dirname..'/config.ini',cfg)
  dirty=not ok; saveTimer=ok and 0 or 2
  errorMessage=not ok and tostring(err) or nil
  statusMessage=ok and 'Saved config.ini.' or nil
end
ac.onRelease(function()
  finishDrag()
  if cfg and dirty then saveConfig() end
  DRSAudio.dispose(drsAudio)
  drsSessionHook=nil
end)

local function loadConfig()
  local migratedLock
  cfg,migratedLock=Settings.read(ac.INIConfig.load(__dirname..'/config.ini'))
  enabled=cfg.enabled
  Settings.diagnostics(cfg,diagnostics)
  dirty=false; saveTimer=0
  if migratedLock then markDirty() end
  renderer=nil; activeCfg=nil; rowTimer=0; errorMessage=nil
  drag.startX,drag.changed,drag.doubleClick=nil,false,false
  DRSChime.reset(drs)
  DRSChime.resetTrace(drs)
  if diagnostics.drsLog then drsLog('state reset: config loaded') end
  forceOn=DRSChime.overrideList(cfg.drsForceOn)
  forceOff=DRSChime.overrideList(cfg.drsForceOff)
  DRSAudio.scan(drsAudio)
  zoneDebugLogged=false
  DRSAudio.select(drsAudio,cfg.drsSound,diagnosticLog(),cfg.drsEnabled)
end

local drsModeNames={AUTO='DRS availability (auto)',SPLINE='Zone entry (spline)'}
local function updateDRS(dt,sim,car,carID,mode)
  local debug=diagnosticLog()
  local key=drs.key or ''
  local override=forceOff[key] and 'off' or forceOn[key] and 'on'
  if (cfg.drsEnabled or debug) and mode=='live' then
    local focused=sim.focusedCar
    if drs.session~=sim.currentSessionIndex then
      resetDRSSession()
      drs.session=sim.currentSessionIndex
    end
    if drs.focus~=focused or drs.carID~=carID then
      if debug then debug('state reset: car or focus changed') end
      DRSChime.reset(drs)
      DRSAudio.stop(drsAudio)
      drs.focus,drs.carID=focused,carID
      drs.key=carID:lower()
      DRSChime.resetTrace(drs)
    end
    override=forceOff[drs.key] and 'off' or forceOn[drs.key] and 'on'
    local suppression
    if not cfg.drsEnabled then suppression='chime disabled'
    elseif sim.isReplayActive or sim.isReplayOnlyMode then suppression='replay'
    elseif sim.isPaused then suppression='paused'
    elseif (focused and focused>=0 and focused~=0) or car.isAIControlled then suppression='spectating or AI control'
    elseif not car.physicsAvailable or carID=='' then suppression='player physics unavailable' end
    if debug or not suppression then
      if not zones then
        zones,zonePath,zoneError=DRSZones.load()
        if zoneError and not loggedZoneFailure then
          drsLog(zoneError..'; using edge-only detection')
          loggedZoneFailure=true
          zoneDebugLogged=true
        end
      end
      if debug and not zoneDebugLogged then
        debug(zonePath and string.format('Loaded %d zones from %s',#zones,zonePath) or zoneError)
        zoneDebugLogged=true
      end
    end
    if suppression then
      if debug and drs.position~=nil then debug('state reset: '..suppression) end
      DRSChime.reset(drs)
      DRSAudio.stop(drsAudio)
      DRSChime.status(drs,suppression,debug)
    else
      local sessionReady=sim.isSessionStarted~=false and not sim.isInMainMenu
      local fire,zone=DRSChime.update(drs,car,drs.key,dt,sim.trackLengthM,zones,cfg,override,debug,sessionReady)
      local activeTest=diagnostics.activeCue
      if activeTest and fire then DRSChime.status(drs,'normal cue disabled by active-edge diagnostic',debug,true) end
      if (activeTest and drs.activeRise) or (not activeTest and fire) then
        local played,result,valid,started=DRSAudio.play(drsAudio,cfg.drsVolume,debug)
        if debug then
          debug('chime fired | playback='..tostring(played)..' | fresh valid='..tostring(valid)
            ..' | start succeeded='..tostring(started)..' | trigger='..(activeTest and 'debug drsActive' or DRSChime.triggerMode(cfg,override)=='SPLINE' and 'spline START' or 'drsAvailable')..' | '..result)
        end
        if played then
          if not activeTest then DRSChime.played(drs,zone) end
        else DRSChime.status(drs,result,debug,true) end
      end
    end
  else
    DRSChime.reset(drs)
    DRSAudio.stop(drsAudio)
    DRSChime.status(drs,cfg.drsEnabled and 'no live player telemetry' or 'chime disabled',debug)
  end
  if debug then
    drs.triggerLabel=diagnostics.activeCue and 'Debug drsActive' or drsModeNames[DRSChime.triggerMode(cfg,override)]
    DRSChime.trace(drs,car,carID:lower(),sim,zones,cfg.drsCooldown,os.preciseClock(),debug)
  end
end

local function updateTelemetry(dt,sim,car,carID,mode)
  demoTime=demoTime+math.max(0,dt)
  local effective=Settings.effective(cfg,carID,car)
  if not activeCfg or effective.rpmMax~=activeCfg.rpmMax or effective.revLimit~=activeCfg.revLimit
    or effective.gearCount~=activeCfg.gearCount then renderer=nil end
  activeCfg=effective
  if mode~=previousMode then
    state=Telemetry.new(); rowTimer=0; previousMode=mode
    aero=Aero.new(); gearMotion=GearMotion.new(); leaderboardMotion=LeaderboardMotion.new()
  end
  if mode=='demo' then Telemetry.demo(state,demoTime,cfg.names)
  elseif mode=='live' then
    Telemetry.sample(state,car,dt,cfg.damping/1000)
    Telemetry.energy(state,dt,activeCfg)
    rowTimer=rowTimer-dt
    if rowTimer<=0 then
      rowTimer=0.25
      local session=ac.getSession(sim.currentSessionIndex)
      if sim.raceSessionType==ac.SessionType.Race or (session and session.type==ac.SessionType.Race) then
        Telemetry.raceRows(state,car,sim.carsCount,function(index)
          return ac.getCar(index)
        end,cfg.names)
      else
        local board=session and session.leaderboard
        Telemetry.rows(state,car,board and #board or 0,function(rank)
          local entry=board and board[rank]
          return entry and entry.car or nil
        end,cfg.names,sim.carsCount)
      end
    end
  end
  state.leaderboardMotion=LeaderboardMotion.update(leaderboardMotion,state,dt,cfg.leaderboardDuration)
  local motion=GearMotion.update(gearMotion,state.gear,dt,cfg.gearDuration)
  state.gearPosition=motion.position;state.slotLetter=motion.letter;state.slotScale=motion.scale
  state.aeroPhase=Aero.update(aero,state.aeroActive,dt,cfg.aeroDuration)
end

function script.update(dt)
  if not cfg then
    local ok,err=pcall(loadConfig)
    if not ok then errorMessage=tostring(err); return end
  end
  -- CSP may stop calling drawHUD when the game's UI is hidden mid-drag.
  if drag.startX then
    local uiState=ac.getUI()
    if uiState.appsHidden or uiState.uiHidden then
      finishDrag()
      drag.doubleClick=false
    end
  end
  -- Run persistence even when the HUD is disabled or controls are closed.
  -- A pending save from another control must not capture an intermediate offset.
  if dirty and not drag.startX then
    saveTimer=saveTimer-math.max(0,dt)
    if saveTimer<=0 then saveConfig() end
  end
  if not enabled and not cfg.drsEnabled and not diagnostics.drsLog then return end
  local start=diagnostics.profile and os.preciseClock() or 0
  local sim=ac.getSim()
  local car=sim and sim.carsCount>0 and ac.getCar(0) or nil
  local carID=car and ac.getCarID(0) or ''
  local mode=(diagnostics.forceDemo or (not car and cfg.demo~='OFF')) and 'demo' or (car and 'live' or 'empty')
  updateDRS(dt,sim,car,carID,mode)
  if enabled then updateTelemetry(dt,sim,car,carID,mode) end
  if diagnostics.profile then cpu.update=(os.preciseClock()-start)*1000 end
end

local function fitRenderer(screen)
  if not renderer or oldWidth~=screen.x or oldHeight~=screen.y then
    renderer=Renderer.new(activeCfg or cfg,screen.x,screen.y)
    oldWidth,oldHeight=screen.x,screen.y
  end
end

local function overOtherUI(uiState,x,y)
  if uiState.wantCaptureMouse or ui.windowHovered(ui.HoveredFlags.AnyWindow) then return true end
  -- Also respect registered original AC/Python apps that are outside ImGui.
  for _,window in ipairs(ac.getAppWindows()) do
    if window.visible and (window.layer==0 or window.layerDuplicate) then
      local p,s=window.position,window.size
      if HUDDrag.contains(x,y,p.x,p.y,p.x+s.x,p.y+s.y) then return true end
    end
  end
  return false
end

local function moveHUD(x,y)
  if x==cfg.x and y==cfg.y then return false end
  cfg.x,cfg.y=x,y
  -- The powertrain settings snapshot is refreshed in update(), before draw.
  -- Synchronize offsets so a renderer rebuilt in this frame moves immediately.
  if activeCfg then activeCfg.x,activeCfg.y=x,y end
  renderer=nil
  return true
end

local function overHUD(x,y,regions)
  for _,r in ipairs(regions) do
    if HUDDrag.contains(x,y,r.left,r.top,r.right,r.bottom) then return true end
  end
  return false
end

local function dragHUD(uiState)
  local mouse=ui.mousePos()
  local valid=mouse.x>=0 and mouse.y>=0
  local b=renderer.drag
  if drag.startX then
    ui.captureMouse()
    if valid then
      local dx,dy=mouse.x-drag.startX,mouse.y-drag.startY
      if drag.changed or dx~=0 or dy~=0 then
        drag.doubleClick=false
        local x,y=HUDDrag.offset(b,drag.x,drag.y,dx,dy)
        if moveHUD(x,y) then drag.changed=true end
      end
    end
    if not valid or ui.mouseReleased() or not ui.mouseDown() then
      finishDrag()
      return
    end
    ui.setMouseCursor(ui.MouseCursor.ResizeAll)
    return
  end

  local clicked,doubleClicked=ui.mouseClicked(),ui.mouseDoubleClicked()
  local over=valid and overHUD(mouse.x,mouse.y,b.regions)
    and not overOtherUI(uiState,mouse.x,mouse.y)
  if clicked then drag.doubleClick=over end
  if not over then
    if doubleClicked then drag.doubleClick=false end
    return
  end
  if doubleClicked and drag.doubleClick then
    ui.captureMouse()
    drag.doubleClick=false
    if moveHUD(Settings.schema.x[2],Settings.schema.y[2]) then markDirty() end
  elseif clicked then
    drag.startX,drag.startY=mouse.x,mouse.y
    drag.x,drag.y=b.x,b.y
    ui.captureMouse()
  end

  if drag.startX or not ui.mouseDown() then ui.setMouseCursor(ui.MouseCursor.ResizeAll) end
  if not ui.mouseDown() then ui.setTooltip('Drag to move. Double-click to reset the HUD position.') end
end

function script.drawHUD()
  if not cfg or not enabled or previousMode=='empty' then finishDrag();drag.doubleClick=false;return end
  local uiState=ac.getUI()
  -- CSP's own visibility flags follow Ctrl+H and global UI hiding.
  if uiState.appsHidden or uiState.uiHidden then finishDrag();drag.doubleClick=false;return end
  local screen=uiState.windowSize
  local start=diagnostics.profile and os.preciseClock() or 0
  fitRenderer(screen)
  if not renderer.visible then finishDrag();drag.doubleClick=false;return end
  -- The overlay never takes focus or covers other apps with an input window.
  ui.beginTransparentWindow('HaloHUD:overlay',vec2(0,0),screen,true,false)
  if not cfg.lockHUD and cfg.opacity>0 then
    dragHUD(uiState)
    fitRenderer(screen)
  else
    finishDrag()
    drag.doubleClick=false
  end
  renderer.render(state)
  ui.endTransparentWindow()
  if diagnostics.profile then
    cpu.draw=(os.preciseClock()-start)*1000
    cpu.maxDraw=math.max(cpu.maxDraw,cpu.draw); cpu.frames=cpu.frames+1
  end
end

-- Controls call the same runtime actions regardless of which tab is visible.
local Controls=require('controls')
local controls
local function setControl(key,value)
  if cfg[key]==value then return end
  cfg[key]=value
  if key=='showLeft' or key=='showCenter' or key=='showRight' then
    if activeCfg then activeCfg[key]=value end
    renderer=nil
  elseif key=='enabled' then
    enabled=value
    if not value then finishDrag();drag.doubleClick=false end
  elseif key=='lockHUD' then
    if value then finishDrag();drag.doubleClick=false end
  elseif key=='debugMode' or key=='debugDRS' or key=='debugDRSActive' or key=='demo' or key=='profileCPU' then
    local wasLogging,wasActiveCue,wasProfiling=diagnostics.drsLog,diagnostics.activeCue,diagnostics.profile
    Settings.diagnostics(cfg,diagnostics)
    if wasLogging~=diagnostics.drsLog then
      zoneDebugLogged=false
      DRSChime.resetTrace(drs)
    end
    if wasActiveCue~=diagnostics.activeCue then drs.previousActive=nil end
    if wasProfiling~=diagnostics.profile then cpu.maxDraw=0;cpu.frames=0 end
  elseif key=='drsEnabled' then
    DRSChime.reset(drs)
    if not value then DRSAudio.dispose(drsAudio) end
  elseif key=='drsTriggerMode' then DRSChime.reset(drs)
  elseif key=='drsSound' then DRSAudio.select(drsAudio,value,diagnosticLog(),cfg.drsEnabled)
  elseif key=='drsForceOn' then forceOn=DRSChime.overrideList(value)
  elseif key=='drsForceOff' then forceOff=DRSChime.overrideList(value)
  elseif key~='drsVolume' and key~='drsCooldown' and key~='drsMargin' and key~='drsFreeSeconds' then
    renderer=nil
    if key=='names' then rowTimer=0 end
  end
  markDirty()
end

local function reloadControls()
  local ok,err=pcall(loadConfig)
  if not ok then errorMessage=tostring(err) end
  controls.listError=nil
end

local function testChime()
  local debug=diagnosticLog()
  if debug then debug('Test chime | enabled='..tostring(cfg.drsEnabled)..' | configured volume='..tostring(cfg.drsVolume)) end
  local played,result=DRSAudio.test(drsAudio,cfg.drsVolume,debug)
  if debug then debug('Test chime | playback='..tostring(played)..' | '..result) end
end

local function readDRSControls(view)
  view.drsFiles=drsAudio.files
  view.drsSoundStatus=drsAudio.status
  if drsAudio.status=='Ready' and not (ac.AudioEvent and ac.AudioEvent.fromFile) then
    view.drsSoundStatus='File audio API unavailable'
  end
  if not cfg.debugMode then return end
  local sim=ac.getSim()
  local car=sim and sim.carsCount>0 and ac.getCar(0) or nil
  local id=car and ac.getCarID(0) or ''
  if id~=view.drsCar then view.drsKey=id:lower() end
  view.drsCar=id
  view.drsFile=drsAudio.file
  view.drsClassification=drs.classes[view.drsKey] or
    (car and car.physicsAvailable and car.drsPresent==false and 'no_drs' or 'unknown')
  view.drsReason=drs.reason
  if not sim then view.zoneCount=nil
  elseif zones then view.zoneCount=#zones
  else
    -- The controls can display track information with audio disabled. Use a
    -- separate read-only cache so opening this tab cannot seed the detector.
    if view.zoneLength~=sim.trackLengthM or view.zoneConfig~=cfg or view.zoneSession~=drs.classes then
      view.zoneLength,view.zoneConfig,view.zoneSession=sim.trackLengthM,cfg,drs.classes
      local ok,previewZones=pcall(DRSZones.load)
      view.previewZoneCount=ok and #previewZones or 0
    end
    view.zoneCount=view.previewZoneCount
  end
end

local telemetryRows={}
local function controlText(index,format,...)
  local row=telemetryRows[index]
  if not row then row={};telemetryRows[index]=row end
  local changed=row.text==nil
  for i=1,select('#',...) do
    local value=select(i,...)
    if row[i]~=value then changed=true;row[i]=value end
  end
  if changed then row.text=string.format(format,...) end
  ui.textWrapped(row.text)
end

local function drawControlTelemetry()
  if activeCfg and activeCfg.profileActive then
    local p=cfg.carProfile
    controlText(1,'%s | %s | %s | %s',p.name,p.class,p.bhp,p.weight)
    controlText(2,'Powertrain: %s',activeCfg.powertrainSource)
    controlText(3,'RPM scale %.0f | limiter %.0f | gears %d',activeCfg.rpmMax,activeCfg.revLimit,activeCfg.gearCount)
    ui.textWrapped('Packed car data not exported: battery capacity, recovery calibration and camera remain unverified.')
  end
  controlText(4,'Source: %s | physics: %s',previousMode or 'loading',tostring(state.physics))
  controlText(5,'Position %s | %s %s %s',state.player.position,state.leaderFirst and 'Behind' or 'Ahead',state.ahead.position,state.ahead.name)
  controlText(6,'Speed %.3f km/h | RPM %.0f | Gear %d',state.speed,state.rpm,state.gear)
  controlText(7,'Raw brake %.3f | throttle %.3f',state.rawBrake,state.rawThrottle)
  controlText(8,'ERS %s | charge %.3f | input %.3f',tostring(state.ers),state.charge,state.ersInput)
  controlText(9,'DRS present %s | active %s',tostring(state.aeroPresent),tostring(state.aeroActive))
  if diagnostics.profile then
    controlText(10,'Lua update %.3f ms | draw %.3f ms',cpu.update,cpu.draw)
    controlText(11,'Peak draw %.3f ms / %d frames',cpu.maxDraw,cpu.frames)
    ui.textWrapped('These are Lua CPU submission times. Measure GPU frame time in CSP after warm-up.')
  end
  if renderer then controlText(12,'Textured quads: %d',renderer.quads) end
end

controls=Controls.new{
  set=setControl,save=saveConfig,reload=reloadControls,testChime=testChime,
  readDRS=readDRSControls,readTelemetry=drawControlTelemetry
}

function script.windowMain()
  if not cfg then ui.textWrapped(errorMessage and 'Could not load config.ini.' or 'HaloHUD is loading.');return end
  Controls.draw(controls,cfg,errorMessage,statusMessage)
end
