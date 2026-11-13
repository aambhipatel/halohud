-- Single drawing API: CSP 0.2.0 ui.drawImageQuad(). All static and dynamic
-- geometry uses the same projection, so moving CURVE never separates the labels.
local glyphs = require('glyphs')
local Aero = require('aero')
local M = {}
local whiteTexture = 'assets/white.png'
local PEDAL_SEGMENTS = 16 -- fit denser bars in the existing module envelope
local themes = {
  TEAL = {accent={47,224,208}, secondary={159,184,200}, blue={30,123,255}, green={43,227,122}},
  ICE = {accent={58,184,232}, secondary={169,198,219}, blue={30,123,255}, green={80,240,183}},
  AMBER = {accent={255,194,71}, secondary={215,192,153}, blue={30,123,255}, green={43,227,122}}
}
local function rgba(c,a) return rgbm(c[1]/255,c[2]/255,c[3]/255,a or 1) end

function M.new(cfg, width, height)
  local self={cfg=cfg, static={}, textCache={}, cacheCount=0, quads=0}
  local theme=themes[cfg.theme] or themes.TEAL
  local opacity=cfg.opacity
  self.c={accent=rgba(theme.accent,opacity), dim=rgba(theme.secondary,opacity),
    blue=rgba(theme.blue,opacity), green=rgba(theme.green,opacity),
    white=rgba({255,255,255},opacity), glass=rgba({255,255,255},opacity),
    inactive=rgba({52,79,91},opacity*.7), brake=rgba({255,64,56},opacity),
    black=rgba({6,24,43},opacity), glow=rgba({124,255,176},opacity*.3)}
  local ds,ms,ls,rs=cfg.dialScale or 1,cfg.moduleScale or 1,cfg.leftScale or 1,cfg.rightScale or 1
  local inner=175+180*(ds-1) -- preserve default shape, reflow as the dial changes
  local sideInner=inner+133*ms+10
  local radius=cfg.curve>0.0001 and 1650/cfg.curve or nil
  local function region(u,flat)
    if flat then return 'dial' end
    return math.abs(u)>=318 and (u<0 and 'left' or 'right') or 'module'
  end
  local function localPoint(u,v,flat,group)
    group=group or region(u,flat)
    if group=='curvedModule' then
      -- Keep gauge radii centered on the dial, independent of halo curvature.
      local r=math.sqrt(u*u+v*v)
      local k=(180*ds+(r-180)*ms)/r
      return u*k,v*k
    end
    if group=='dial' then u=u*ds; v=v*ds
    elseif group=='module' then
      u=(u<0 and -1 or 1)*(inner+(math.abs(u)-175)*ms); v=v*ms
    elseif group=='left' then u=-sideInner+(u+318-(v+82)*10/172)*ls; v=v*ls
    elseif group=='right' then u=sideInner+(u-318)*rs; v=v*rs end
    if flat or not radius then return u,v end
    local a=u/radius
    return (radius-v)*math.sin(a),radius-(radius-v)*math.cos(a)
  end
  local arcEnd=sideInner+522*math.max(ls,rs)
  local arcV=-math.max(196,180*ds+20,150*math.max(ls,rs,ms)+20)
  -- Conservative region envelopes include dynamic labels and battery.
  -- Fit the complete composition, then clamp offsets so controls cannot clip it.
  local minX,maxX,minY,maxY=0,0,0,0
  local function bounds(u,v,flat,g)
    local x,y=localPoint(u,v,flat,g)
    minX=math.min(minX,x);maxX=math.max(maxX,x)
    minY=math.min(minY,y);maxY=math.max(maxY,y)
  end
  for _,r in ipairs({{-840,-318,-145,130,'left'}, {318,840,-100,130,'right'},
      {-310,-160,-150,150,'curvedModule'}, {160,310,-150,150,'curvedModule'},
      {-184,184,-205,230,'dial'}}) do
    for i=0,64 do for _,v in ipairs({r[3],r[4]}) do
      bounds(r[1]+(r[2]-r[1])*i/64,v,r[5]=='dial',r[5])
    end end
  end
  if cfg.outerArc then for i=0,96 do bounds(-arcEnd+2*arcEnd*i/96,arcV,false,'arc') end end
  local s=math.min(math.min(width/1920,height/1080)*cfg.scale,
    (width-32)/(maxX-minX),(height-32)/(maxY-minY))
  local ox=math.max(16-minX*s,math.min(width-16-maxX*s,width/2+cfg.x*s))
  local oy=math.max(16-minY*s,math.min(height-16-maxY*s,height/2+(cfg.y-5)*s))
  function self.point(u,v,flat,group)
    local x,y=localPoint(u,v,flat,group)
    return vec2(ox+x*s,oy+y*s)
  end
  -- Mouse deltas use CSP UI pixels. Convert through the actual fitted scale,
  -- and start from the visible position (not a previously clamped request).
  self.drag={anchor=self.point(0,-214,true),scale=s,
    x=(ox-width/2)/s,y=(oy-height/2)/s+5,
    minX=math.max(-960,(16-minX*s-width/2)/s),
    maxX=math.min(960,(width-16-maxX*s-width/2)/s),
    minY=math.max(-540,(16-minY*s-height/2)/s+5),
    maxY=math.min(540,(height-16-maxY*s-height/2)/s+5)}
  function self.quad(u,v,w,h,texture,uv,flat,group)
    uv=uv or {0,0,1,1}; group=group or region(u+w/2,flat)
    return {texture or whiteTexture,
      self.point(u,v,flat,group),self.point(u+w,v,flat,group),self.point(u+w,v+h,flat,group),self.point(u,v+h,flat,group),
      vec2(uv[1],uv[2]),vec2(uv[3],uv[2]),vec2(uv[3],uv[4]),vec2(uv[1],uv[4])}
  end

  function self.draw(q,color,alpha)
    self.quads=self.quads+1
    if alpha then color=rgbm(color.r,color.g,color.b,color.mult*alpha) end
    ui.drawImageQuad(q[1],q[2],q[3],q[4],q[5],color,q[6],q[7],q[8],q[9])
  end

  function self.rect(u,v,w,h,color,flat)
    self.draw(self.quad(u,v,w,h,nil,nil,flat),color)
  end

  function self.image(texture,u,v,w,h,color,flat,strips)
    strips=strips or 1
    for i=0,strips-1 do
      self.draw(self.quad(u+w*i/strips,v,w/strips,h,texture,{i/strips,0,(i+1)/strips,1},flat),color)
    end
  end

  -- Text meshes are cached by complete string and location. The cache is bounded
  -- and reset in one small batch to avoid unbounded growth in long sessions.
  function self.text(str,u,v,size,color,style,align,maxWidth,flat,tracking,group)
    group=group or region(u,flat)
    str=tostring(str); style=style or 'labels'; tracking=tracking or 1
    local key=table.concat({str,u,v,size,style,align or '',maxWidth or 0,flat and 1 or 0,tracking,group},'|')
    local mesh=self.textCache[key]
    if not mesh then
      local font=glyphs[style]; local scale=size/font.cap; local width=0
      for i=1,#str do
        local g=font.glyphs[tostring(str:byte(i))] or font.glyphs['63']
        width=width+g.advance*scale+tracking
      end
      width=math.max(0,width-tracking)
      if maxWidth and width>maxWidth then
        local f=maxWidth/width; scale=scale*f; tracking=tracking*f; width=maxWidth
      end
      local x=u-(align=='center' and width/2 or align=='right' and width or 0)
      mesh={}
      for i=1,#str do
        local g=font.glyphs[tostring(str:byte(i))] or font.glyphs['63']
        if str:byte(i)~=32 then
          mesh[#mesh+1]=self.quad(x+g.x*scale,v+(g.y+font.cap)*scale,g.w*scale,g.h*scale,font.texture,g.uv,flat,group)
        end
        x=x+g.advance*scale+tracking
      end
      if self.cacheCount>=512 then self.textCache={}; self.cacheCount=0 end
      self.textCache[key]=mesh; self.cacheCount=self.cacheCount+1
    end
    for i=1,#mesh do self.draw(mesh[i],color) end
  end

  -- All gauge artwork shares a 640x320 design atlas centered at (0,0).
  -- Crop UVs instead of stretching a shorter fill; outlines retain their shape.
  local function gaugeQuad(side,top,bottom,texture)
    local u=side==1 and -310 or 160
    return self.quad(u,top,150,bottom-top,texture,
      {(u+320)/640,(top+160)/320,(u+470)/640,(bottom+160)/320},false,'curvedModule')
  end
  local function energyLabels()
    for side,label in ipairs({'RECHARGE','DEPLOY'}) do
      local sign=side==1 and -1 or 1
      local span=side==1 and 44 or 26
      for i=1,#label do
        local a=math.rad(-span/2+span*(i-1)/(#label-1))
        self.text(label:sub(i,i),sign*206*math.cos(a),206*math.sin(a)-4,
          10,self.c.white,nil,'center',nil,false,1,'curvedModule')
      end
    end
  end

  -- Capture static draw calls once: no extra canvas allocation, shader compilation,
  -- filesystem reads or per-frame rendering of glow layers.
  local originalDraw=self.draw
  self.draw=function(q,color,alpha) self.static[#self.static+1]={q,color,alpha} end
  local c=self.c; local n=cfg.strips
  self.image('assets/left_fill.png',-830,-92,512,192,c.glass,false,n)
  self.image('assets/left_rim.png',-830,-92,512,192,c.accent,false,n)
  self.image('assets/right_fill.png',318,-92,512,192,c.glass,false,n)
  self.image('assets/right_rim.png',318,-92,512,192,c.accent,false,n)
  for side=1,2 do
    self.draw(gaugeQuad(side,-150,150,'assets/curved_pedal_fill.png'),rgba({18,52,66},opacity))
    self.draw(gaugeQuad(side,-150,150,'assets/curved_pedal_rim.png'),c.accent)
    self.draw(gaugeQuad(side,-150,150,'assets/curved_energy_rim.png'),rgba({50,150,194},opacity))
    self.draw(gaugeQuad(side,-150,150,'assets/curved_energy_fill.png'),rgba({10,50,112},opacity))
  end
  self.text('BRAKE',-246,127,12,c.dim,nil,'center',nil,false,1,'curvedModule')
  self.text('THROTTLE',246,127,12,c.dim,nil,'center',nil,false,1,'curvedModule')
  self.image('assets/dial_fill.png',-180,-180,360,360,c.glass,true)
  self.image('assets/dial_rim.png',-180,-180,360,360,c.accent,true)
  self.text('ACTIVE',347,-62,12,c.white)
  self.text('AERO',347,-44,12,c.white)
  self.text('GEARS',620,-57,12,c.dim,nil,'center')
  self.text('RPM x1000',624,108,12,c.dim,nil,'center')
  for i=0,15 do
    local u=430+i*24
    self.rect(u,62,1.2,5,c.dim)
    if i%3==0 then self.text(string.format('%g',i*cfg.rpmMax/15000),u,72,9,c.dim,nil,'center') end
  end
  -- Exactly the same image rectangle, strip boundaries, projection and skew
  -- as the timing panel; the alpha mask contains the constant-inset row outline.
  -- The row highlight is selected dynamically below (lower row or solo center).
  if cfg.outerArc then
    for i=0,95 do
      local u=-arcEnd+2*arcEnd*i/96
      self.draw(self.quad(u,arcV,2*arcEnd/96+0.2,1.5,nil,nil,false,'arc'),c.accent,0.65)
    end
  end
  self.draw=originalDraw

  self.highlights={regular={},solo={},leader={}}
  for mode,texture in pairs({regular='assets/player_highlight.png',solo='assets/player_highlight_solo.png',leader='assets/player_highlight_leader.png'}) do
    for i=0,n-1 do
      self.highlights[mode][i+1]=self.quad(-830+512*i/n,-92,512/n,192,texture,{i/n,0,(i+1)/n,1})
    end
  end

  self.pedals={}; self.rpm={}; self.gears={}
  for side=1,2 do
    self.pedals[side]={}
    for i=1,PEDAL_SEGMENTS do
      local bottom=110-(i-1)*220/PEDAL_SEGMENTS
      self.pedals[side][i]=gaugeQuad(side,bottom-220/PEDAL_SEGMENTS+2,bottom,'assets/curved_pedal_segments.png')
    end
  end
  for i=1,48 do self.rpm[i]=self.quad(430+(i-1)*7.5,46,7.7,5) end
  local gearCount=math.max(1,math.min(12,cfg.gearCount or 8))
  local gearStep=344/gearCount
  local gearBox=math.min(36,gearStep-4)
  for gear=0,gearCount do self.gears[gear]=self.quad(454+gear*gearStep-gearBox/2,-24,gearBox,43) end
  self.chargeBg=self.quad(-64,178,128,48,'assets/battery.png',nil,true)

  function self.render(t)
    self.quads=0
    for i=1,#self.static do local q=self.static[i]; self.draw(q[1],q[2],q[3]) end
    local board=t.leaderboardMotion
    if board then
      -- Crop the existing approved mask to the row, and move all projected strips
      -- through the same skew/curve as the panel. Transparent atlas margins are excluded.
      for i=0,n-1 do
        self.draw(self.quad(-830+512*i/n,board.p.x-18.5,512/n,68,
          'assets/player_highlight.png',{i/n,104/192,(i+1)/n,172/192}),c.accent)
      end
    else
    local highlight=self.highlights[t.leaderFirst and 'leader' or t.solo and 'solo' or 'regular']
    for i=1,#highlight do self.draw(highlight[i],c.accent) end
    end
    for side,value in ipairs({t.brake,t.throttle}) do
      for i=1,PEDAL_SEGMENTS do
        self.draw(self.pedals[side][i],c.inactive)
        local f=math.max(0,math.min(1,value*PEDAL_SEGMENTS-(i-1)))
        if f>0 then self.draw(self.pedals[side][i],side==1 and c.brake or c.green,f) end
      end
    end
    -- Continuous bottom-up fill inside the rounded energy mask.
    local top=-206*math.sin(math.rad(27))-23
    local bottom=-top
    for side,value in ipairs({t.recharge or 0,t.deploy or 0}) do
      value=math.max(0,math.min(1,value))
      if value>0 then self.draw(gaugeQuad(side,bottom-(bottom-top)*value,bottom,
        'assets/curved_energy_fill.png'),rgba({70,180,255},opacity)) end
    end
    energyLabels()
    local kmh=math.floor(t.speed+0.5); local mph=math.floor(t.speed*0.6213711922+0.5)
    local mphFirst=cfg.units=='MPH'
    self.text(mphFirst and 'MPH' or 'KM/H',0,-127,13,c.white,nil,'center',nil,true)
    self.text(tostring(mphFirst and mph or kmh),0,-99,49,c.white,nil,'center',236,true,1)
    -- Highlight BOOST from the displayed deploy gauge, with the same damping.
    -- Exactly 50% remains plain; DRS/P2P fallback deploy is eligible too.
    local function inactiveBox(v)
      local border=rgba({125,139,148},opacity*0.8)
      self.rect(-112,v,224,27,rgba({65,75,83},opacity*0.55),true)
      self.rect(-112,v,224,1.5,border,true)
      self.rect(-112,v+25.5,224,1.5,border,true)
      self.rect(-112,v,1.5,27,border,true)
      self.rect(110.5,v,1.5,27,border,true)
    end
    if (t.deploy or 0)>0.5 then
      self.image('assets/boost_glow.png',-124,-27,248,48,c.glow,true)
      self.rect(-112,-18,224,27,c.green,true)
      self.rect(-112,-18,224,1.5,c.green,true)
      self.rect(-112,7.5,224,1.5,c.green,true)
      self.text('BOOST',0,-11,12,c.white,nil,'center',205,true,2)
    else
      inactiveBox(-18)
      self.text('BOOST',0,-11,12,c.dim,nil,'center',nil,true,2)
    end
    inactiveBox(14)
    self.text(t.ers and 'OVERTAKE' or 'NO ERS',0,21,12,c.dim,nil,'center',205,true,2)
    self.text(tostring(mphFirst and kmh or mph),0,57,38,c.white,nil,'center',205,true)
    self.text(mphFirst and 'KM/H' or 'MPH',0,110,12,c.dim,nil,'center',nil,true)
    self.draw(self.chargeBg,rgba({5,15,26},opacity)) -- empty battery silhouette remains visible without KERS
    if t.ers then
      if t.charge>0 then self.draw(self.quad(-64,178,128*t.charge,48,'assets/battery.png',{0,0,t.charge,1},true),rgba({46,212,255},opacity)) end
      self.image('assets/bolt.png',-10,186,16,30,c.white,true)
    else self.text('--',0,193,13,c.dim,nil,'center',nil,true) end
    if board then
      local alpha=board.opponentAlpha
      if alpha>0.001 then
        local dim=rgbm(c.dim.r,c.dim.g,c.dim.b,opacity*alpha)
        local white=rgbm(1,1,1,opacity*alpha)
        self.text(board.opponent.position,-779,board.o.x+2,23,dim,'names')
        self.text(board.opponent.name,-723,board.o.x,29,white,'names',nil,354)
      end
      self.text(t.player.position,-779,board.p.x+4,23,c.accent,'names')
      self.text(t.player.name,-723,board.p.x,31,c.accent,'names',nil,354)
    else
    if t.leaderFirst then
      self.text(t.player.position,-779,-49.5,23,c.accent,'names')
      self.text(t.player.name,-723,-53.5,31,c.white,'names',nil,354)
      self.text(t.ahead.position,-779,34.5,23,c.dim,'names')
      self.text(t.ahead.name,-723,30.5,29,c.white,'names',nil,354)
    else
    if not t.solo then
      self.text(t.ahead.position,-779,-47,23,c.dim,'names')
      self.text(t.ahead.name,-723,-49,29,c.white,'names',nil,300)
    end
    local rowOffset=t.solo and -42 or 0
    self.text(t.player.position,-779,34.5+rowOffset,23,c.accent,'names')
    self.text(t.player.name,-723,30.5+rowOffset,31,c.white,'names',nil,354)
    end
    end
    -- DRS is a proxy for the reference's active-aero icon, not universal active aero.
    local phase=t.aeroPhase
    if phase==nil then phase=t.aeroActive and 1 or 0 end -- static fixtures
    local idle=t.aeroAvailable and c.accent or c.dim
    local aeroColor=rgbm(idle.r+(c.green.r-idle.r)*phase,
      idle.g+(c.green.g-idle.g)*phase,idle.b+(c.green.b-idle.b)*phase,opacity)
    -- Both lines rotate clockwise / -> horizontal. Their ordering stays fixed:
    -- left becomes short/upper, right becomes long/lower, exactly as approved.
    for _,pose in ipairs(Aero.poses(phase)) do
      local v=Aero.vertices(pose,373.5,0)
      local q={whiteTexture}
      for i=1,4 do q[i+1]=self.point(v[i][1],v[i][2],false,'right') end
      q[6],q[7],q[8],q[9]=vec2(0,0),vec2(1,0),vec2(1,1),vec2(0,1)
      self.draw(q,aeroColor)
    end
    local position=t.gearPosition
    if position~=nil then
      position=math.max(0,math.min(gearCount,position))
      local u=454+position*gearStep
      -- Use the same projected quad as the existing gear row, moving continuously.
      local q=position==math.floor(position) and self.gears[position] or
        self.quad(u-gearBox/2,-24,gearBox,43)
      self.draw(q,c.accent,.32)
    end
    for gear=0,gearCount do
      local u=454+gear*gearStep
      local reverse=gear==0 and t.gear==-1
      local selected=t.gear==gear or reverse
      if position==nil and selected then self.draw(self.gears[gear],c.accent,.32) end
      local weight=position~=nil and math.max(0,1-math.abs(gear-position)) or (selected and 1 or 0)
      local size=20+5*weight
      local pulse=gear==0 and (t.slotScale or 1) or 1
      local label=gear==0 and (t.slotLetter or (reverse and 'R' or 'N')) or tostring(gear)
      local color=rgbm(c.dim.r+(c.white.r-c.dim.r)*weight,
        c.dim.g+(c.white.g-c.dim.g)*weight,c.dim.b+(c.white.b-c.dim.b)*weight,opacity)
      -- Expand about the glyph center instead of shifting its baseline down.
      self.text(label,u,-12-size*(pulse-1)/2,size*pulse,color,nil,'center',(gearStep-5)*pulse)
    end
    if t.gear>gearCount then self.text(t.gear,820,26,24,c.white,nil,'center') end
    local rpm=math.max(0,math.min(1,t.rpm/cfg.rpmMax))*48
    for i=1,48 do
      self.draw(self.rpm[i],c.inactive)
      local f=math.max(0,math.min(1,rpm-(i-1)))
      if f>0 then
        local z=(i-1)/47
        local atLimit=t.rpm>11000
        self.draw(self.rpm[i],atLimit and rgbm(1,0.25,0.22,opacity*f) or
          rgbm((47-4*z)/255,(224+3*z)/255,(208-86*z)/255,opacity*f))
      end
    end
    if t.demo then self.text('DEMO',0,-188,8,rgba({159,184,200},opacity*0.45),nil,'center',nil,true,2)
    elseif not t.physics then self.text('PHYSICS N/A',0,244,10,c.dim,nil,'center',nil,true) end
  end
  return self
end
return M
