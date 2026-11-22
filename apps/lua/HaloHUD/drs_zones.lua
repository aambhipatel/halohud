local M={}
local function normalized(value)
  local n=tonumber(value)
  return n and n>=0 and n<=1 and n or nil
end

function M.parse(text)
  local zones,current={},nil
  for line in text:gmatch('[^\r\n]+') do
    line=line:gsub('^\239\187\191',''):gsub('[;#].*$','')
    local section=line:match('^%s*%[([^%]]+)%]%s*$')
    if section then
      current=nil
      local index=tonumber(section:upper():match('^ZONE_(%d+)$'))
      if index then current={index=index};zones[#zones+1]=current end
    elseif current then
      local key,value=line:match('^%s*(%a+)%s*=%s*(.-)%s*$')
      if key then
        key=key:upper()
        if key=='START' then current.start=normalized(value)
        elseif key=='END' then current.finish=normalized(value)
        elseif key=='DETECTION' then current.detection=normalized(value) end
      end
    end
  end
  for i=#zones,1,-1 do
    local z=zones[i]
    if not z.start or not z.finish or z.start==z.finish then table.remove(zones,i) end
  end
  return zones
end

function M.load()
  if not io.load then return {},nil,'File read API unavailable' end
  local candidates={}
  if ac.getTrackDataFilename then
    local ok,path=pcall(ac.getTrackDataFilename,'drs_zones.ini')
    if ok and type(path)=='string' and path~='' then candidates[1]=path end
  end
  if ac.getFolder and ac.getTrackID and ac.FolderID then
    local ok,base=pcall(function()
      return ac.getFolder(ac.FolderID.Root)..'/content/tracks/'..ac.getTrackID()..'/data/drs_zones.ini'
    end)
    if ok and base~=candidates[1] then candidates[#candidates+1]=base end
  end
  for _,path in ipairs(candidates) do
    local ok,contents=pcall(io.load,path)
    if ok and type(contents)=='string' then
      local zones=M.parse(contents)
      if #zones>0 then return zones,path end
    end
  end
  return {},nil,'No readable DRS zones in '..(#candidates>0 and table.concat(candidates,' or ') or 'track data paths')
end
return M
