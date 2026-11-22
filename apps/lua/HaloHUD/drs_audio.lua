-- Cache file metadata on selection. Each cue gets its own 2D one-shot event.
local M={}
function M.new(folder)
  return {folder=folder, files={}, status='Not loaded', warned={}}
end

local function warn(s,key,message)
  if s.warned[key] then return end
  s.warned[key]=true
  if ac.log then pcall(ac.log,'[HaloHUD DRS] '..message) end
end

local function wavName(name)
  return type(name)=='string' and name:lower():match('%.wav$') and not name:find('[/:\\]')
end

function M.scan(s)
  s.files={}
  if not io.scanDir then s.scanStatus='Sound folder scan API unavailable';return end
  local ok,files=pcall(io.scanDir,s.folder,'*')
  if not ok or type(files)~='table' then s.scanStatus='Sound folder missing or unreadable';return end
  for _,name in ipairs(files) do
    if wavName(name) then
      local readable,exists=pcall(io.fileExists,s.folder..'/'..name)
      if readable and exists then s.files[#s.files+1]=name end
    end
  end
  table.sort(s.files)
  s.scanStatus=#s.files==0 and 'No WAV files found' or nil
end

local function call(log,label,fn,...)
  local ok,value=pcall(fn,...)
  if log then log(label..' pcall='..tostring(ok)..(ok and ' returned=' or ' error=')..tostring(value)) end
  return ok,value
end

local function absolutePath(folder,name,log)
  local path=folder..'/'..name
  if path:match('^%a:[/\\]') or path:match('^[/\\][/\\]') or path:sub(1,1)=='/' then return path end
  if ac.getFolder and ac.FolderID then
    local ok,root=call(log,'ac.getFolder(Root)',ac.getFolder,ac.FolderID.Root)
    if ok and type(root)=='string' and root~='' then return root..'/'..path end
  end
  if log then log('Could not confirm absolute app path') end
  return path
end

local function littleEndian(bytes,offset,count)
  local value=0
  for i=count-1,0,-1 do value=value*256+bytes:byte(offset+i) end
  return value
end

function M.wavHeader(bytes)
  if type(bytes)~='string' or bytes:sub(1,4)~='RIFF' or bytes:sub(9,12)~='WAVE' then
    return 'No RIFF/WAVE header'
  end
  local offset=13
  while offset+7<=#bytes do
    local chunk=bytes:sub(offset,offset+3)
    local size=littleEndian(bytes,offset+4,4)
    local data=offset+8
    if data+size-1>#bytes then return 'Truncated WAV chunk: '..chunk end
    if chunk=='fmt ' and size>=16 then
      local format=littleEndian(bytes,data,2)
      local channels=littleEndian(bytes,data+2,2)
      local rate=littleEndian(bytes,data+4,4)
      local bits=littleEndian(bytes,data+14,2)
      local extended=format==65534 and size>=40 and
        ' subformat='..string.format('0x%04X',littleEndian(bytes,data+24,2)) or ''
      return string.format('WAV header: format=0x%04X%s sampleRate=%d Hz bitDepth=%d channels=%d',
        format,extended,rate,bits,channels)
    end
    offset=data+size+size%2
  end
  return 'WAV header: fmt chunk missing or too short'
end

local function inspectHeader(s,file,size,log)
  if not io.load or type(size)~='number' or size<1 or size>4*1024*1024 then
    if log then log('WAV header unavailable (size unknown, empty file, or file exceeds 4 MiB diagnostic limit)') end
    return
  end
  local ok,bytes=pcall(io.load,file)
  if not ok then
    if log then log('WAV header read pcall=false error='..tostring(bytes)) end
    return
  end
  if log then log('WAV header read pcall=true bytes='..tostring(type(bytes)=='string' and #bytes or nil)) end
  local header=M.wavHeader(bytes)
  local key=file..'|'..header
  if log and not s.warned[key] then warn(s,key,header..' ('..file..')') end
end

-- CSP documents dispose() as both stopping and removing an event. Keep a
-- strong reference until replacement or cleanup, even after the cue finishes.
function M.dispose(s,log)
  local event=s.event
  s.event=nil
  s.testing=false
  if event then call(log,'AudioEvent:dispose',function() return event:dispose() end) end
end

function M.stop(s)
  if not s.testing and s.event then M.dispose(s) end
end

function M.select(s,name,log,reportMissing)
  M.dispose(s,log)
  s.name=name
  s.file=nil
  if not wavName(name) then
    s.status='Invalid WAV filename'
  elseif not io.fileExists then
    s.status='File audio API unavailable'
  else
    local file=absolutePath(s.folder,name,log)
    if log then log('Resolved WAV path: '..file) end
    local ok,exists=call(log,'io.fileExists',io.fileExists,file)
    local size
    if io.fileSize and (exists or log) then
      local _,value=call(log,'io.fileSize (bytes)',io.fileSize,file)
      size=value
    elseif log then log('io.fileSize unavailable') end
    if ok and exists then
      inspectHeader(s,file,size,log)
      s.file=file
      s.status='Ready'
      return true
    end
    s.status='WAV missing or unreadable'
  end
  if log then log(s.status) end
  if reportMissing then warn(s,s.status..'|'..name,s.status..' ('..name..')') end
  return false
end

local function playbackFailure(s,status,detail,log)
  s.status=status
  local message=status..(detail and ': '..tostring(detail) or '')
  warn(s,status..'|'..s.name,message..' ('..s.name..')')
  M.dispose(s,log)
  return message
end

function M.play(s,volume,log,testing)
  if volume<=0 then return false,'volume muted' end
  if not s.file then return false,s.status end
  if not (ac.AudioEvent and ac.AudioEvent.fromFile) then return false,'File audio API unavailable' end

  M.dispose(s,log)
  if log then log('ac.AudioEvent.fromFile options: filename='..s.file..', use3D=false, loop=false, reverbResponse=false') end
  local loaded,event=call(log,'ac.AudioEvent.fromFile',ac.AudioEvent.fromFile,
    {filename=s.file,use3D=false,loop=false},false)
  if not loaded or not event then
    return false,playbackFailure(s,'WAV could not be loaded',loaded and 'no event returned' or event,log),false,false
  end
  s.event=event
  local checked,valid=call(log,'Fresh AudioEvent:isValid',function() return event:isValid() end)
  if not checked then
    return false,playbackFailure(s,'AudioEvent validation failed',valid,log),nil,false
  end
  if not valid then
    return false,playbackFailure(s,'WAV could not be loaded','fresh event is invalid',log),false,false
  end
  -- Use the slider's linear gain once on the very handle that will start.
  local function setGain()
    event.cameraInteriorMultiplier=1
    event.cameraExteriorMultiplier=1
    event.cameraTrackMultiplier=1
    event.volume=volume
    return event.volume
  end
  if log then log('Requested AudioEvent.volume='..tostring(volume)) end
  local set,before=call(log,'AudioEvent.volume assignment/readback',setGain)
  if not set then
    return false,playbackFailure(s,'AudioEvent gain configuration failed',before,log),true,false
  end
  local started,result=call(log,'AudioEvent:start',function() return event:start() end)
  if not started then
    return false,playbackFailure(s,'AudioEvent:start failed',result,log),true,false
  end
  -- Some playback backends reinitialize channel properties on start. Read
  -- the started handle and restore the requested values if they changed.
  local gainOK,after,interior,exterior,track=pcall(function()
    return event.volume,event.cameraInteriorMultiplier,event.cameraExteriorMultiplier,event.cameraTrackMultiplier
  end)
  if log then
    if gainOK then
      log(string.format('AudioEvent gain | requested=%s | pre-start=%s | post-start=%s | camera multipliers=%s,%s,%s',
        tostring(volume),tostring(before),tostring(after),tostring(interior),tostring(exterior),tostring(track)))
    else log('AudioEvent post-start readback pcall=false error='..tostring(after)) end
  end
  if gainOK and (type(after)~='number' or math.abs(after-volume)>1e-6 or interior~=1 or exterior~=1 or track~=1) then
    call(log,'AudioEvent gain restore/readback',setGain)
  end
  s.testing=testing==true
  s.status='Ready'
  if log then call(log,'AudioEvent:isPlaying after start',function() return event:isPlaying() end) end
  return true,'start returned '..tostring(result),true,true
end

function M.test(s,volume,log)
  if volume<=0 then
    if log then log('Configured volume is 0. Using 0.65 for this test only') end
    volume=.65
  end
  return M.play(s,volume,log,true)
end

return M
