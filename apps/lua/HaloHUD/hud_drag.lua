-- Mouse and projected bounds are in UI pixels. Offsets are in design pixels.
local M={}

function M.contains(x,y,left,top,right,bottom)
  return x>=left and x<=right and y>=top and y<=bottom
end

function M.offset(bounds,x,y,dx,dy)
  return math.max(bounds.minX,math.min(bounds.maxX,x+dx/bounds.scale)),
    math.max(bounds.minY,math.min(bounds.maxY,y+dy/bounds.scale))
end

return M
