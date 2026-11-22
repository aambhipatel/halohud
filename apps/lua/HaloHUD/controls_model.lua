-- Presentation helpers. The runtime remains responsible for DRS eligibility.
local M={}

M.sections={
  visibility={'enabled'},
  layout={'scale','x','y','curve'},
  panels={'leftScale','dialScale','moduleScale','rightScale'},
  elements={'showLeft','showCenter','showRight','outerArc'},
  appearance={'units','names','theme','opacity'},
  animations={'leaderboardDuration','gearDuration','aeroDuration'},
  sound={'drsEnabled','drsVolume','drsSound','drsTriggerMode'},
  overrides={'drsForceOn','drsForceOff'},
  tuning={'drsCooldown','drsMargin','drsFreeSeconds'},
  diagnostics={'demo','profileCPU','debugDRS','debugDRSActive'}
}

function M.reset(section,schema,set)
  for _,key in ipairs(M.sections[section]) do
    set(key,schema[key][2])
  end
end

function M.parseList(text)
  local items,lookup={},{}
  for name in text:gmatch('[^,%s;]+') do
    local id=name:lower()
    if not lookup[id] then
      items[#items+1]={name=name,id=id}
      lookup[id]=true
    end
  end
  return items,lookup
end

function M.editList(text,input,remove)
  local name=input:match('^%s*(.-)%s*$')
  if name=='' or name:find('[%s,;]') then return nil,'Enter one car folder ID.' end
  local id=name:lower()
  local names,found={},false
  -- Preserve the spelling and order of other entries, even when the saved list
  -- predates this UI and contains repeated names or mixed separators.
  for token in text:gmatch('[^,%s;]+') do
    if token:lower()==id then
      found=true
      if not remove then return text end
    else names[#names+1]=token end
  end
  if remove and not found then return text end
  if not remove then names[#names+1]=name end
  return table.concat(names,', ')
end

local reasons={
  ['no DRS']='this car does not report DRS support.',
  ['teleport']='the car jumped to a different position on the track.',
  ['invalid spline position']='the game did not report a valid track position.',
  ['pit lane']='the car was in or leaving the pit lane.',
  ['started in zone']='you started inside a zone.',
  ['initial sample']='HaloHUD was establishing the starting position.',
  ['already available on first sample']='DRS was already available when HaloHUD started checking.',
  ['no track zones for spline trigger']='this track has no readable zones for the selected trigger.',
  ['override off']='this car is on the force-off list.',
  ['already cued in zone']='the chime already played for this zone.',
  ['cooldown']='the minimum time between chimes had not passed.',
  ['DRS unavailable in zone']='the game had not enabled DRS in this zone.',
  ['free-use car']='this car was classified as allowing DRS outside zones.',
  ['outside activation zone']='the car was outside a DRS activation zone.',
  ['speed below 5 km/h']='the car was moving slower than 5 km/h.',
  ['DRS already active at availability edge']='DRS was already open when availability changed.',
  ['chime disabled']='the chime is turned off.',
  ['replay']='the game was in replay.',
  ['paused']='the game was paused.',
  ['spectating or AI control']='the player car was not under your control.',
  ['player physics unavailable']='live physics data was unavailable for the player car.',
  ['no live player telemetry']='no live player telemetry was available.',
  ['normal cue disabled by active-edge diagnostic']='the DRS activation diagnostic replaced the normal cue.',
  ['availability cue disabled by active-edge diagnostic']='the DRS activation diagnostic replaced the normal cue.',
  ['no clean activation edge']='the game did not report a clean availability change.',
  ['volume muted']='the chime volume was set to zero.',
  ['Not loaded']='the sound had not loaded.',
  ['WAV missing or unreadable']='the WAV file was missing or unreadable.',
  ['Invalid WAV filename']='the selected filename was invalid.',
  ['File audio API unavailable']='the CSP file audio interface was unavailable.',
  ['WAV could not be loaded']='CSP could not load the WAV file.',
  ['AudioEvent validation failed']='CSP could not validate the audio event.',
  ['AudioEvent gain configuration failed']='CSP could not set the chime volume.',
  ['AudioEvent:start failed']='CSP could not start playback.',
  ['AudioEvent.volume assignment/readback failed']='CSP could not set the chime volume.',
  ['AudioEvent camera configuration failed']='CSP could not set the camera audio levels.',
  ['AudioEvent playback state or stop failed']='CSP could not prepare the sound for playback.',
  ['Playback failed']='CSP could not play the sound.'
}
M.reasons=reasons
function M.skipped(reason)
  if not reason then return 'Last skipped chime: no reason recorded yet.' end
  local text=reasons[reason]
  if not text then
    -- Playback errors append native details after a colon and space.
    local prefix=reason:match('^(.-): ')
    text=reasons[prefix] or 'the cue was skipped. See DRS debug logging for details.'
  end
  return 'Last skipped chime: '..text
end

-- An actionable warning is useful even with all diagnostic UI hidden.
function M.soundWarning(cache,status,name)
  if cache.warningStatus~=status or cache.warningName~=name then
    cache.warningStatus,cache.warningName=status,name
    if status=='Ready' then cache.warning=nil
    elseif status=='WAV missing or unreadable' then
      cache.warning='Sound file not found or unreadable. Put '..name..' in HaloHUD/sounds/ and reload settings.'
    elseif status=='Not loaded' then
      cache.warning='Reload settings after adding a WAV to HaloHUD/sounds/.'
    else cache.warning='The selected sound could not play. Choose a readable WAV from the sounds folder.' end
  end
  return cache.warning
end

-- Rebuild display strings only when an input changes. Keep native errors in
-- logs rather than showing long engine messages in the control window.
function M.status(cache,sound,file,count,car,classification,on,off,mode,reason)
  local rebuild=cache.sound~=sound or cache.file~=file or cache.count~=count or cache.car~=car
    or cache.classification~=classification or cache.on~=on or cache.off~=off or cache.mode~=mode
  if rebuild then
    cache.sound,cache.file,cache.count,cache.car=sound,file,count,car
    cache.classification,cache.on,cache.off,cache.mode=classification,on,off,mode
    if sound=='Ready' and file then cache.soundText,cache.soundTone='Sound file: ready','good'
    elseif sound=='WAV missing or unreadable' then cache.soundText,cache.soundTone='Sound file: missing or unreadable','bad'
    elseif sound=='Not loaded' then cache.soundText,cache.soundTone='Sound file: not loaded yet','warn'
    else cache.soundText,cache.soundTone='Sound file: playback unavailable','bad' end
    if count==nil then cache.trackText,cache.trackTone='Track: no live track data','warn'
    elseif count==0 then
      if mode=='SPLINE' then cache.trackText='Track: no zones loaded. Spline cues need track zone data.'
      elseif mode=='DIAGNOSTIC' then cache.trackText='Track: no zones loaded. The activation diagnostic can still play.'
      else cache.trackText='Track: no zones loaded. Using game availability only.' end
      cache.trackTone='warn'
    else
      cache.trackText='Track: '..count..(count==1 and ' DRS zone loaded' or ' DRS zones loaded')
      cache.trackTone='good'
    end
    cache.triggerText=mode=='DIAGNOSTIC' and 'Current trigger: DRS activation diagnostic'
      or mode=='SPLINE' and 'Current trigger: zone entry' or 'Current trigger: game availability (auto)'
    cache.carText='Car ID: '..(car~='' and car or 'no player car')
    if car=='' then cache.modeText,cache.modeTone='This car: no player car','warn'
    elseif off then cache.modeText,cache.modeTone='This car: forced off','bad'
    elseif on then cache.modeText,cache.modeTone='This car: forced on (zone entry)','good'
    elseif classification=='free_use' then cache.modeText,cache.modeTone='This car: free-use DRS','warn'
    elseif classification=='no_drs' then cache.modeText,cache.modeTone='This car: no DRS support','warn'
    elseif classification=='zone_restricted' then cache.modeText,cache.modeTone='This car: follows DRS zones','good'
    else cache.modeText,cache.modeTone='This car: not classified yet','warn' end
  end
  if reason~=cache.reason or not cache.skipped then
    cache.skipped=M.skipped(reason)
    cache.reason=reason
  end
  return cache
end

return M
