-- HaloHUD for Assetto Corsa 1.7.0, original screen-space artwork. CSP 0.2.0+ (build 2651).
-- Required UI/telemetry calls were checked against the shipped 0.2.0 SDK.
local Telemetry=require('telemetry')
local Settings=require('settings')
local Renderer=require('renderer')
local Aero=require('aero')
local aero=Aero.new()
local cfg, activeCfg, renderer, oldWidth, oldHeight
local state=Telemetry.new()
local demoTime, rowTimer, previousMode = 0, 0, nil
local enabled, forceDemo, profile=false,false,false
local cpu={update=0,draw=0,maxDraw=0,frames=0}
local errorMessage=nil
local statusMessage=nil
local dirty,saveTimer=false,0
local dragMode,dragging=false,false
local function markDirty()
  dirty=true; saveTimer=0.4; statusMessage='Saving settings...'
end
local function saveConfig()
  cfg.enabled=enabled; cfg.profileCPU=profile
  local ok,err=pcall(Settings.save,__dirname..'/config.ini',cfg)
  dirty=not ok; saveTimer=ok and 0 or 2
  errorMessage=not ok and tostring(err) or nil
  statusMessage=ok and 'Saved config.ini.' or nil
end
ac.onRelease(function()
  if cfg and dirty then saveConfig() end
end)

local function loadConfig()
  cfg=Settings.read(ac.INIConfig.load(__dirname..'/config.ini'))
  enabled=cfg.enabled
  forceDemo=cfg.demo=='ON'
  profile=cfg.profileCPU
  dirty=false; saveTimer=0
  renderer=nil; activeCfg=nil; rowTimer=0; errorMessage=nil
  dragging=false
end

-- Only this adapter touches CSP; telemetry.lua can be tested with plain tables.
local function updateTelemetry(dt)
  demoTime=demoTime+math.max(0,dt)
  local sim=ac.getSim()
  local car=sim and sim.carsCount>0 and ac.getCar(0) or nil
  local effective=Settings.effective(cfg,car and ac.getCarID(0) or '',car)
  if not activeCfg or effective.rpmMax~=activeCfg.rpmMax or effective.revLimit~=activeCfg.revLimit
    or effective.gearCount~=activeCfg.gearCount then renderer=nil end
  activeCfg=effective
  local mode=(forceDemo or (not car and cfg.demo~='OFF')) and 'demo' or (car and 'live' or 'empty')
  if mode~=previousMode then
    state=Telemetry.new(); rowTimer=0; previousMode=mode
    aero=Aero.new()
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
  state.aeroPhase=Aero.update(aero,state.aeroActive,dt,cfg.aeroDuration)
end

function script.update(dt)
  if not cfg then
    local ok,err=pcall(loadConfig)
    if not ok then errorMessage=tostring(err); return end
  end
  -- Run persistence even when the HUD is disabled or controls are closed.
  if dirty then
    saveTimer=saveTimer-math.max(0,dt)
    if saveTimer<=0 then saveConfig() end
  end
  if not enabled then return end
  local start=profile and os.preciseClock() or 0
  updateTelemetry(dt)
  if profile then cpu.update=(os.preciseClock()-start)*1000 end
end

function script.drawHUD()
  if not cfg or not enabled or previousMode=='empty' then dragging=false; return end
  local uiState=ac.getUI()
  -- CSP's own visibility flags follow Ctrl+H and global UI hiding. Do not
  -- change ENABLED: showing the game's HUD again restores our previous state.
  if uiState.appsHidden or uiState.uiHidden then dragging=false; return end
  local screen=uiState.windowSize
  local start=profile and os.preciseClock() or 0
  if not renderer or oldWidth~=screen.x or oldHeight~=screen.y then
    renderer=Renderer.new(activeCfg or cfg,screen.x,screen.y)
    oldWidth,oldHeight=screen.x,screen.y
  end
  -- inputs=false gives a fixed, click-through HUD. Offsets are shared by sliders and the optional drag handle.
  ui.beginTransparentWindow('HaloHUD:overlay',vec2(0,0),screen,true,false)
  renderer.render(state)
  ui.endTransparentWindow()
  if dragMode then
    local info=renderer.drag
    local size=vec2(156,30)
    local pos=vec2(math.max(8,math.min(screen.x-size.x-8,info.anchor.x-size.x/2)),
      math.max(8,math.min(screen.y-size.y-8,info.anchor.y-size.y/2)))
    -- Only the small handle accepts input, never the fullscreen HUD surface.
    ui.beginTransparentWindow('HaloHUD:dragHandle',pos,size,true,true)
    ui.invisibleButton('##HaloHUDDrag',size)
    local held=ui.itemActive()
    if held then
      ui.captureMouse()
      if dragging then
        local delta=ui.mouseDelta()
        if (delta.x~=0 or delta.y~=0) and delta.x==delta.x and delta.y==delta.y
          and math.abs(delta.x)<1e6 and math.abs(delta.y)<1e6 then
          local x=Telemetry.clamp(info.x+delta.x/info.scale,info.minX,info.maxX)
          local y=Telemetry.clamp(info.y+delta.y/info.scale,info.minY,info.maxY)
          if x~=cfg.x or y~=cfg.y then
            cfg.x,cfg.y=x,y
            renderer=nil; markDirty()
          end
        end
      end
    end
    dragging=held
    ui.drawRectFilled(vec2(),size,rgbm(0.025,0.16,0.22,0.96),5)
    ui.setCursor(vec2(12,6));ui.text('Drag HUD')
    ui.endTransparentWindow()
  else dragging=false end
  if profile then
    cpu.draw=(os.preciseClock()-start)*1000
    cpu.maxDraw=math.max(cpu.maxDraw,cpu.draw); cpu.frames=cpu.frames+1
  end
end

function script.windowMain()
  if not cfg then
    ui.textWrapped(errorMessage or 'HaloHUD is loading.'); return
  end
  ui.text('HaloHUD for Assetto Corsa 1.7.0')
  if ui.checkbox('Show HUD',enabled) then enabled=not enabled; markDirty() end
  if ui.checkbox('Force demo telemetry',forceDemo) then
    forceDemo=not forceDemo; cfg.demo=forceDemo and 'ON' or 'AUTO'; markDirty()
  end
  if ui.checkbox('Measure Lua CPU time',profile) then
    profile=not profile; cpu.maxDraw=0; cpu.frames=0
    markDirty()
  end
  local function slider(label,key,lo,hi,fmt)
    local v=ui.slider(label,cfg[key],lo,hi,fmt or '%.2f')
    v=Telemetry.clamp(v,lo,hi)
    if v~=cfg[key] then cfg[key]=v; renderer=nil; markDirty() end
  end
  ui.text('Live layout (automatically fits screen)')
  if ui.checkbox('Drag HUD with mouse',dragMode) then
    dragMode=not dragMode; dragging=false
  end
  if dragMode then
    ui.textWrapped('Hold the Drag HUD handle above the dial and move your mouse. Turn this option off when finished. Position saves automatically.')
  end
  slider('HUD scale','scale',0.5,1.5)
  slider('X offset','x',-960,960,'%.0f px')
  slider('Y offset','y',-540,540,'%.0f px')
  slider('Curvature','curve',0,1.6)
  slider('Aero animation','aeroDuration',150,1000,'%.0f ms')
  slider('Left timing scale','leftScale',0.5,1.5)
  slider('Center dial scale','dialScale',0.5,1.5)
  slider('Pedal / energy modules scale','moduleScale',0.5,1.5)
  slider('Right powertrain scale','rightScale',0.5,1.5)
  if ui.checkbox('Outer arc',cfg.outerArc) then cfg.outerArc=not cfg.outerArc; renderer=nil; markDirty() end
  if ui.button('Save config.ini') then
    saveConfig()
  end
  if ui.button('Reset to defaults') then
    dragMode=false; dragging=false
    cfg=Settings.read(nil); enabled=cfg.enabled; forceDemo=false; profile=false; renderer=nil
    state=Telemetry.new(); rowTimer=0
    markDirty()
  end
  ui.textWrapped('Changes apply immediately and save automatically after 0.4 seconds without edits. Save writes immediately. Reset restores and saves defaults. Reload reads external edits.')
  if ui.button('Reload config.ini') then
    local ok,err=pcall(loadConfig)
    if not ok then errorMessage=tostring(err) end
  end
  if errorMessage then ui.textWrapped('Config error: '..errorMessage) end
  if statusMessage then ui.textWrapped(statusMessage) end
  if activeCfg and activeCfg.profileActive then
    local p=cfg.carProfile
    ui.textWrapped(p.name..' | '..p.class..' | '..p.bhp..' | '..p.weight)
    ui.textWrapped('Powertrain: '..activeCfg.powertrainSource)
    ui.text(string.format('RPM scale %.0f | limiter %.0f | gears %d',
      activeCfg.rpmMax,activeCfg.revLimit,activeCfg.gearCount))
    ui.textWrapped('Packed car data not exported: battery capacity, recovery calibration and camera remain unverified.')
  end
  ui.text(string.format('Source: %s | physics: %s',previousMode or 'loading',tostring(state.physics)))
  ui.text('Position '..state.player.position..' | '..(state.leaderFirst and 'Behind ' or 'Ahead ')..state.ahead.position..' '..state.ahead.name)
  ui.text(string.format('Speed %.3f km/h | RPM %.0f | Gear %d',state.speed,state.rpm,state.gear))
  ui.text(string.format('Raw brake %.3f | throttle %.3f',state.rawBrake,state.rawThrottle))
  ui.text(string.format('ERS %s | charge %.3f | input %.3f',tostring(state.ers),state.charge,state.ersInput))
  ui.text(string.format('DRS present %s | active %s',tostring(state.aeroPresent),tostring(state.aeroActive)))
  if profile then
    ui.text(string.format('Lua update %.3f ms | draw %.3f ms',cpu.update,cpu.draw))
    ui.text(string.format('Peak draw %.3f ms / %d frames',cpu.maxDraw,cpu.frames))
    ui.textWrapped('CPU submission only. Use CSP profiling and an on/off GPU frame-time comparison for the 0.3 ms target. Exclude initial warm-up.')
  end
  if renderer then ui.text(string.format('Textured quads: %d',renderer.quads)) end
end
