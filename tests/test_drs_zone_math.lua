-- From the project root: lua tests/test_drs_zone_math.lua
package.path='apps/lua/HaloHUD/?.lua;'..package.path
local M=require('drs_zone_math')
local cases={
  {'normal inside',.4,.3,.6,true},
  {'normal before',.29,.3,.6,false},
  {'normal after',.61,.3,.6,false},
  {'normal START inclusive',.3,.3,.6,true},
  {'normal END inclusive',.6,.3,.6,true},
  {'wrap before finish line',.98,.9,.12,true},
  {'wrap after start line',.04,.9,.12,true},
  {'wrap excludes mid-lap',.5,.9,.12,false},
  {'wrap START inclusive',.9,.9,.12,true},
  {'wrap END inclusive',.12,.9,.12,true},
  {'wrap zero inclusive',0,.9,.12,true},
  {'wrap one inclusive',1,.9,.12,true}
}
for _,case in ipairs(cases) do
  assert(M.isInsideZone(case[2],case[3],case[4])==case[5],case[1])
  print('PASS: '..case[1])
end
local z={{start=.3,finish=.6}}
local activation,boundary=M.find(z,.293,40/5000)
assert(activation==1 and boundary==1)
activation,boundary=M.find(z,.607,40/5000)
assert(activation==nil and boundary==1)
assert(M.find(z,.293,40/10000)==nil)
print('PASS: meter-based activation margin and exit-boundary distinction')
print('13 DRS zone math cases passed')
