local Model=require('controls_model')
local Settings=require('settings')
local M={}

local function tooltip(text)
  if ui.itemHovered() then ui.setTooltip(text) end
end

local function header(text)
  ui.dummy(vec2(0,6))
  ui.header(text)
  ui.separator()
end

local function width(maximum)
  return math.max(1,math.min(maximum or 330,ui.availableSpaceX()))
end

local function toggle(view,key,label,help,value)
  if value==nil then value=view.cfg[key] end
  if ui.checkbox(label,value) then view.set(key,not value) end
  tooltip(help)
end

local function slider(view,key,id,label,help,format,factor,maxWidth)
  local schema=Settings.schema[key]
  factor=factor or 1
  ui.textWrapped(label)
  tooltip(help)
  ui.setNextItemWidth(width(maxWidth))
  local current=view.cfg[key]*factor
  local input=ui.slider(id,current,schema[3]*factor,schema[4]*factor,format)
  tooltip(help)
  if input~=current then
    view.set(key,math.max(schema[3],math.min(schema[4],input/factor)))
  end
end

local function choice(value,label) return {value=value,label=label} end
local speedChoices={choice('KMH','Kilometres per hour'),choice('MPH','Miles per hour')}
local nameChoices={choice('FULL','Surname'),choice('CODE','Three-letter code')}
local themeChoices={choice('TEAL','Teal'),choice('ICE','Ice blue'),choice('AMBER','Amber')}
local modeChoices={choice('AUTO','When the game enables DRS (auto)'),choice('SPLINE','When I cross a zone line')}
local modeHelp='Auto waits for the game to enable DRS. Zone entry cues at a track activation line even if the game denies DRS. Default: Auto. Force-on uses zone entry for that car, skipping the availability edge and free-use classification. Force-off wins.'

local function combo(view,key,id,label,help,items)
  local value=view.cfg[key]
  local preview=items[1].label
  for _,item in ipairs(items) do if item.value==value then preview=item.label;break end end
  ui.textWrapped(label)
  tooltip(help)
  ui.setNextItemWidth(width())
  view.choiceKey,view.choices=key,items
  ui.combo(id,preview,0,view.drawChoices)
  tooltip(help)
end

local resetLabels={
  visibility='Reset visibility?', layout='Reset HUD layout?', panels='Reset panel scales?', elements='Reset HUD elements?',
  appearance='Reset units and colors?', animations='Reset animations?', sound='Reset chime settings?',
  overrides='Clear both car override lists?', tuning='Reset DRS tuning?', diagnostics='Reset diagnostics?'
}
local function reset(view,section)
  ui.pushID(section)
  if view.pendingReset==section then
    ui.textWrapped(resetLabels[section])
    if ui.button('Confirm reset') then
      Model.reset(section,Settings.schema,view.set)
      view.pendingReset=nil
    end
    ui.sameLine()
    if ui.button('Cancel') then view.pendingReset=nil end
  elseif ui.button(section=='sound' and 'Reset section' or 'Reset to defaults') then
    view.pendingReset=section
  end
  ui.popID()
end

local function general(view)
  header('Visibility')
  toggle(view,'enabled','Show HUD','Shows the HaloHUD overlay while driving. Default: On.')
  reset(view,'visibility')
  header('Settings file')
  if ui.button('Save config.ini') then view.save() end
  tooltip('Writes the current settings to config.ini immediately.')
  ui.sameLine()
  if ui.button('Reload config.ini') then
    view.pendingReset=nil
    view.reload()
  end
  tooltip('Reads config.ini from disk and scans the sounds folder again. Unsaved edits are discarded.')

  header('HUD interaction')
  toggle(view,'lockHUD','Lock HUD position','Prevents mouse dragging and double-click reset. When unlocked, drag the HUD or double-click it to reset the offsets. Default: Off.')
  toggle(view,'debugMode','Debug Mode','Shows diagnostic tools and technical status.')
end

local function hud(view)
  header('Layout')
  slider(view,'scale','##hudScale','HUD scale','Sets the overall HUD size. Default: 100%.','%.0f%%',100)
  slider(view,'x','##offsetX','Horizontal offset','Moves the HUD left or right in design pixels. Default: 0 px.','%.0f px')
  slider(view,'y','##offsetY','Vertical offset','Moves the HUD up or down in design pixels. Default: 0 px.','%.0f px')
  slider(view,'curve','##curvature','Halo curvature','Sets how strongly the HUD follows a curve. 0 is flat. Default: 1.00.','%.2f')
  reset(view,'layout')
  header('Panel scales')
  slider(view,'leftScale','##leftScale','Left timing panel scale','Resizes the leaderboard independently. Default: 100%.','%.0f%%',100)
  slider(view,'dialScale','##dialScale','Center speedometer scale','Resizes the circular dial independently. Default: 100%.','%.0f%%',100)
  slider(view,'moduleScale','##moduleScale','Pedal and energy module scale','Resizes the brake, throttle, recharge and deploy gauges. Default: 100%.','%.0f%%',100)
  slider(view,'rightScale','##rightScale','Right powertrain scale','Resizes the gear, RPM and active aero panel. Default: 100%.','%.0f%%',100)
  reset(view,'panels')
  header('Elements')
  toggle(view,'showLeft','Left zone · Leaderboard','Shows your position and the comparison driver. Default: On.')
  toggle(view,'showCenter','Center zone · Speedometer and gauges','Shows speed, brake, throttle, recharge, deploy and battery. Default: On.')
  toggle(view,'showRight','Right zone · Aero, gears and RPM','Shows active aero, gear selection and the RPM bar. Default: On.')
  toggle(view,'outerArc','Show outer arc','Adds a thin curve above the HUD. Default: Off.')
  reset(view,'elements')
  header('Units and colors')
  combo(view,'units','##speedUnits','Primary speed unit','Sets the main speed reading. Both units remain visible. Default: Kilometres per hour.',speedChoices)
  combo(view,'names','##driverNames','Driver name format','Sets how names appear in the leaderboard. Default: Surname.',nameChoices)
  combo(view,'theme','##theme','HUD color theme','Changes the HUD accent colors. Default: Teal.',themeChoices)
  slider(view,'opacity','##opacity','HUD opacity','Sets how opaque the HUD appears. Default: 95%.','%.0f%%',100)
  reset(view,'appearance')
  header('Animations')
  slider(view,'leaderboardDuration','##leaderboardDuration','Leaderboard animation','Sets how long the timing rows take to slide. Default: 0.45 s.','%.2f s',0.001)
  slider(view,'gearDuration','##gearDuration','Gear animation','Sets the gear highlight slide time. The N/R pulse lasts twice as long. Default: 0.26 s.','%.2f s',0.001)
  slider(view,'aeroDuration','##aeroDuration','Active aero animation','Sets how long the aero indicator takes to transition. Default: 0.42 s.','%.2f s',0.001)
  reset(view,'animations')
end

local toneColors={
  good={rgbm(.46,.94,.66,1),rgbm(.05,.31,.15,1)},
  warn={rgbm(1,.82,.44,1),rgbm(.39,.22,.02,1)},
  bad={rgbm(1,.65,.65,1),rgbm(.56,.10,.13,1)}
}
local function linear(channel)
  return channel<=.04045 and channel/12.92 or ((channel+.055)/1.055)^2.4
end
local function luminance(color)
  return .2126*linear(color.r)+.7152*linear(color.g)+.0722*linear(color.b)
end
local function statusColor(tone,background)
  if not background then return nil end
  local light=luminance(background)
  local choices=toneColors[tone]
  for _,candidate in ipairs(choices) do
    local other=luminance(candidate)
    if (math.max(light,other)+.05)/(math.min(light,other)+.05)>=4.5 then return candidate end
  end
end
local function statusLine(text,tone,background)
  local color=statusColor(tone,background)
  if color then ui.pushStyleColor(ui.StyleColor.Text,color) end
  ui.textWrapped(text)
  if color then ui.popStyleColor() end
end

local function syncLists(view)
  if view.onText==view.cfg.drsForceOn and view.offText==view.cfg.drsForceOff then return end
  view.onText,view.offText=view.cfg.drsForceOn,view.cfg.drsForceOff
  view.onItems,view.onLookup=Model.parseList(view.onText)
  view.offItems,view.offLookup=Model.parseList(view.offText)
  view.conflict=false
  for _,item in ipairs(view.onItems) do
    if view.offLookup[item.id] then view.conflict=true;break end
  end
end

local function editOverride(view,key,name,remove)
  local updated,errorText=Model.editList(view.cfg[key],name,remove)
  view.listError=errorText
  if updated then view.set(key,updated) end
end

local function drawList(view,key,title,items,opposite,addCurrent)
  ui.pushID(key)
  ui.text(title)
  if #items==0 then ui.textDisabled('No car overrides') end
  for _,item in ipairs(items) do
    ui.pushID(item.id)
    if ui.button('Remove') then editOverride(view,key,item.name,true) end
    ui.sameLine()
    ui.textWrapped(item.name)
    if opposite[item.id] then tooltip('This car is in both lists. Force-off wins.') end
    ui.popID()
  end
  if view.drsCar~='' then
    if ui.button(addCurrent) then editOverride(view,key,view.drsCar,false) end
  end
  ui.popID()
end

local function drsSettings(view)
  local background=ui.styleColor(ui.StyleColor.WindowBg)
  header('Chime settings')
  toggle(view,'drsEnabled','Enable DRS chime','Plays the selected sound when the chosen DRS trigger fires. Default: Off.')
  local buttonWidth=ui.measureText('Test chime').x+24
  slider(view,'drsVolume','##chimeVolume','Chime volume','Sets the cue volume from 0 to 100%. Default: 65%.','%.0f%%',100,ui.availableSpaceX()-buttonWidth-8)
  ui.sameLine()
  if ui.button('Test chime') then view.testChime() end
  tooltip('Plays the selected file now. At zero volume, this test uses 65%.')
  ui.textWrapped('Sound file')
  tooltip('Lists WAV files from HaloHUD/sounds/. Reload config.ini to scan again. Default: drs_chime.wav.')
  ui.setNextItemWidth(width())
  ui.combo('##drsSound',view.cfg.drsSound,0,view.drawSounds)
  tooltip('Select a WAV from the sounds folder. Default: drs_chime.wav.')
  if not view.cfg.debugMode then
    local warning=Model.soundWarning(view.drsStatus,view.drsSoundStatus,view.cfg.drsSound)
    if warning then statusLine(warning,'warn',background) end
  end
  combo(view,'drsTriggerMode','##triggerMode','Trigger mode',modeHelp,modeChoices)
  reset(view,'sound')
  if not view.cfg.debugMode then return end

  header('Car overrides')
  ui.textWrapped('Force-on uses the zone line. Force-off silences the car and wins conflicts.')
  if view.conflict then statusLine('Conflict: at least one car is in both lists. Force-off wins.','warn',background) end
  drawList(view,'drsForceOn','Force-on cars',view.onItems,view.offLookup,'Add current car to force-on')
  drawList(view,'drsForceOff','Force-off cars',view.offItems,view.onLookup,'Add current car to force-off')
  ui.textWrapped('Add by car folder ID')
  ui.setNextItemWidth(width())
  view.carInput=ui.inputText('##carFolderID',view.carInput)
  tooltip('Enter a folder name from content/cars to edit a car other than the one you are driving.')
  if ui.button('Add to force-on') then editOverride(view,'drsForceOn',view.carInput,false) end
  ui.sameLine()
  if ui.button('Add to force-off') then editOverride(view,'drsForceOff',view.carInput,false) end
  if view.listError then statusLine(view.listError,'warn',background) end
  reset(view,'overrides')
end

local function drsStatus(view)
  syncLists(view)
  local on=view.onLookup[view.drsKey] or false
  local off=view.offLookup[view.drsKey] or false
  local mode=view.cfg.debugDRS and view.cfg.debugDRSActive and 'DIAGNOSTIC'
    or on and not off and 'SPLINE' or view.cfg.drsTriggerMode
  local status=Model.status(view.drsStatus,view.drsSoundStatus,view.drsFile,view.zoneCount,view.drsCar,
    view.drsClassification,on,off,mode,view.drsReason)
  local background=ui.styleColor(ui.StyleColor.WindowBg)
  header('Live status')
  statusLine(status.soundText,status.soundTone,background)
  statusLine(status.trackText,status.trackTone,background)
  ui.textWrapped(status.carText)
  statusLine(status.modeText,status.modeTone,background)
  ui.textWrapped(status.triggerText)
  ui.textWrapped(status.skipped)
end

local function drsTab(view)
  view.readDRS(view)
  if view.cfg.debugMode then drsStatus(view) end
  ui.childWindow('DRS chime options',vec2(0,0),false,0,view.drsSettingsBody)
end

local function tuning(view)
  slider(view,'drsCooldown','##cooldown','Minimum time between chimes','Prevents repeated cues close together. Default: 1.5 s.','%.2f s')
  slider(view,'drsMargin','##margin','Activation-line tolerance','Allows for telemetry timing near the zone boundary. Default: 40 m.','%.0f m')
  slider(view,'drsFreeSeconds','##freeUseSeconds','Free-use detection time','Sets how long availability outside the zones must persist before classification. Default: 2 s.','%.2f s')
  reset(view,'tuning')
end

local function diagnostics(view)
  if ui.checkbox('Force demo telemetry',view.cfg.demo=='ON') then view.set('demo',view.cfg.demo=='ON' and 'AUTO' or 'ON') end
  tooltip('Shows synthetic data for testing. Default: Auto, using live data when available.')
  toggle(view,'profileCPU','Measure Lua CPU time','Shows Lua update and draw submission times in Live telemetry. Default: Off.')
  toggle(view,'debugDRS','DRS debug logging','Writes chime state, trigger and suppression details to the CSP log. Default: Off.')
  if view.cfg.debugDRS then
    toggle(view,'debugDRSActive','Test cue when DRS opens','Uses the DRS activation edge instead of the normal trigger while debugging. Default: Off.')
  end
  reset(view,'diagnostics')
end

local function advanced(view)
  if view.cfg.debugMode then ui.treeNode('Diagnostics',0,view.diagnosticsBody) end
  ui.treeNode('DRS tuning',0,view.tuningBody)
  if view.cfg.debugMode then ui.treeNode('Live telemetry',0,view.telemetryBody) end
end

function M.new(view)
  view.carInput=''
  view.drsStatus={}
  view.drawChoices=function()
    for _,item in ipairs(view.choices) do
      if ui.selectable(item.label,item.value==view.cfg[view.choiceKey]) then view.set(view.choiceKey,item.value) end
    end
  end
  view.drawSounds=function()
    if #view.drsFiles==0 then ui.textDisabled('No WAV files found') end
    for _,name in ipairs(view.drsFiles) do
      if ui.selectable(name,name==view.cfg.drsSound) then view.set('drsSound',name) end
    end
  end
  view.general=function() general(view) end
  view.hud=function() hud(view) end
  view.drs=function() drsTab(view) end
  view.drsSettingsBody=function() drsSettings(view) end
  view.advanced=function() advanced(view) end
  view.diagnosticsBody=function() diagnostics(view) end
  view.tuningBody=function() tuning(view) end
  view.telemetryBody=function() view.readTelemetry(view) end
  view.drawTabs=function()
    ui.tabItem('General',0,view.general)
    ui.tabItem('HUD',0,view.hud)
    ui.tabItem('DRS Chime',0,view.drs)
    ui.tabItem('Advanced',0,view.advanced)
  end
  return view
end

function M.draw(view,cfg,errorText,statusText)
  view.cfg=cfg
  ui.textDisabled('Changes apply immediately and auto-save')
  tooltip('Changes are saved to config.ini after 0.4 seconds without edits. Save writes immediately. Reload reads the file and discards pending edits.')
  if errorText then
    ui.textWrapped(cfg.debugMode and errorText or 'Could not read or save config.ini.')
  elseif statusText then ui.textDisabled(statusText) end
  ui.tabBar('HaloHUD controls',0,view.drawTabs)
end

return M
