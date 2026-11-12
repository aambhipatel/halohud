"""Original approved curved gauge masks; called by build_assets.py."""
from PIL import Image, ImageDraw
import math

def build(out, factor=3):
    S=factor
    def new(): return Image.new('RGBA',(640*S,320*S))
    def points(values,side): return [((320+side*x)*S,(160+y)*S) for x,y in values]
    def curve(y,r=241): return math.sqrt(r*r-y*y)
    fill,rim,bars,energy,energy_rim=[new() for _ in range(5)]
    for side in (-1,1):
        p=[(curve(-114+228*i/72)+54,-114+228*i/72) for i in range(73)]
        p += [(curve(114-228*i/72),114-228*i/72) for i in range(73)]
        # Round only the four corners, preserving the fitted curved side walls.
        rounded=[]
        for i,v in enumerate(p):
            before,after=p[(i-1)%len(p)],p[(i+1)%len(p)]
            def near(w):
                d=math.hypot(w[0]-v[0],w[1]-v[1]); f=min(3/d,.45)
                return (v[0]+(w[0]-v[0])*f,v[1]+(w[1]-v[1])*f)
            a,b=near(before),near(after)
            for j in range(5):
                t=j/4;rounded.append(((1-t)**2*a[0]+2*(1-t)*t*v[0]+t*t*b[0],(1-t)**2*a[1]+2*(1-t)*t*v[1]+t*t*b[1]))
        rp=points(rounded,side)
        ImageDraw.Draw(fill).polygon(rp,fill='white')
        ImageDraw.Draw(rim).line(rp+[rp[0]],fill='white',width=round(1.5*S),joint='curve')
        for i in range(16):
            bottom=110-i*220/16; top=bottom-220/16+2
            band=[(curve(top+(bottom-top)*j/8,243)+50,top+(bottom-top)*j/8) for j in range(9)]
            band += [(curve(bottom+(top-bottom)*j/8,243),bottom+(top-bottom)*j/8) for j in range(9)]
            ImageDraw.Draw(bars).polygon(points(band,side),fill='white')
        for im,width in ((energy,46),(energy_rim,50)):
            d=ImageDraw.Draw(im); path=[(206*math.cos(math.radians(-27+54*i/96)),206*math.sin(math.radians(-27+54*i/96))) for i in range(97)]
            pts=points(path,side)
            outline=[((206+width/2)*math.cos(math.radians(-27+54*i/96)),(206+width/2)*math.sin(math.radians(-27+54*i/96))) for i in range(97)]
            outline += [((206-width/2)*math.cos(math.radians(-27+54*i/96)),(206-width/2)*math.sin(math.radians(-27+54*i/96))) for i in range(96,-1,-1)]
            d.polygon(points(outline,side),fill='white')
            for x,y in (pts[0],pts[-1]): d.ellipse((x-width*S/2,y-width*S/2,x+width*S/2,y+width*S/2),fill='white')
    for name,im in zip(('curved_pedal_fill','curved_pedal_rim','curved_pedal_segments','curved_energy_fill','curved_energy_rim'),(fill,rim,bars,energy,energy_rim)):
        im.resize((640,320),Image.Resampling.LANCZOS).save(out/(name+'.png'))
