"""Build every shipped PNG and glyph metadata. Python 3.10+, Pillow 11+.

All panel artwork is original layered vector geometry rasterized at 3x then
downsampled. Fonts are bundled under their SIL Open Font License. No game assets
or sponsor art are used. Run from any directory: python source/build_assets.py.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'apps/lua/HaloHUD'
OUT = APP / 'assets'
FONTS = Path(__file__).resolve().parent / 'fonts'
S = 3

def canvas(w, h):
    return Image.new('RGBA', (w*S, h*S))

def save(im, name):
    im.resize((im.width//S, im.height//S), Image.Resampling.LANCZOS).save(OUT / name)

def panel(name, w, h, points):
    """Separate glass and white rim masks permit arbitrary runtime accent tint."""
    mask = Image.new('L', (w*S, h*S))
    p = [(int(x*S), int(y*S)) for x,y in points]
    ImageDraw.Draw(mask).polygon(p, fill=255)
    glass = canvas(w,h)
    d = ImageDraw.Draw(glass)
    for y in range(h*S):
        f = y/(h*S)
        d.line([(0,y),(w*S,y)], fill=(6+int(3*(1-f)),24+int(9*(1-f)),43+int(12*(1-f)),int(178-28*f)))
    glass.putalpha(Image.composite(glass.getchannel('A'), Image.new('L',glass.size),mask))
    # Faint original scan-line texture, deliberately subordinate to the digits.
    lines = canvas(w,h)
    ld = ImageDraw.Draw(lines)
    for x in range(12,w-12,4):
        ld.line([(x*S,10*S),(x*S,(h-10)*S)],fill=(118,202,218,12),width=1)
    lines.putalpha(Image.composite(lines.getchannel('A'), Image.new('L',lines.size),mask))
    glass = Image.alpha_composite(glass,lines)
    save(glass,name+'_fill.png')
    line = canvas(w,h)
    ImageDraw.Draw(line).line(p+[p[0]],fill=(255,255,255,200),width=2*S,joint='curve')
    glow=line.filter(ImageFilter.GaussianBlur(3*S))
    glow.putalpha(glow.getchannel('A').point(lambda x:int(x*0.45)))
    save(Image.alpha_composite(glow,line),name+'_rim.png')

def dial():
    fill=canvas(360,360)
    d=ImageDraw.Draw(fill)
    d.ellipse((15*S,15*S,345*S,345*S),fill=(6,24,43,204))
    stripes=canvas(360,360); sd=ImageDraw.Draw(stripes)
    for x in range(30,331,4):
        sd.line((x*S,25*S,x*S,335*S),fill=(112,199,218,18),width=S)
    mask=Image.new('L',fill.size); ImageDraw.Draw(mask).ellipse((23*S,23*S,337*S,337*S),fill=255)
    stripes.putalpha(Image.composite(stripes.getchannel('A'),Image.new('L',fill.size),mask))
    save(Image.alpha_composite(fill,stripes),'dial_fill.png')
    rim=canvas(360,360); rd=ImageDraw.Draw(rim)
    rd.ellipse((15*S,15*S,345*S,345*S),outline=(255,255,255,230),width=2*S)
    rd.ellipse((21*S,21*S,339*S,339*S),outline=(255,255,255,95),width=S)
    rd.arc((11*S,11*S,349*S,349*S),190,350,fill=(255,255,255,95),width=3*S)
    glow=rim.filter(ImageFilter.GaussianBlur(4*S))
    glow.putalpha(glow.getchannel('A').point(lambda x:int(x*.5)))
    save(Image.alpha_composite(glow,rim),'dial_rim.png')

def misc():
    # White alpha masks; all runtime colors are supplied by renderer.lua.
    tab=canvas(64,192); d=ImageDraw.Draw(tab)
    d.rounded_rectangle((5*S,5*S,59*S,187*S),radius=10*S,fill=(255,255,255,225),outline=(255,255,255,255),width=2*S)
    save(tab,'tab.png')
    fill=canvas(64,192)
    ImageDraw.Draw(fill).rounded_rectangle((7*S,7*S,57*S,185*S),radius=8*S,fill='white')
    save(fill,'tab_fill.png')
    glow=canvas(256,64); d=ImageDraw.Draw(glow)
    d.rounded_rectangle((9*S,12*S,247*S,52*S),radius=4*S,fill=(255,255,255,90))
    save(glow.filter(ImageFilter.GaussianBlur(6*S)),'boost_glow.png')
    battery=canvas(128,48); d=ImageDraw.Draw(battery)
    d.rounded_rectangle((5*S,4*S,118*S,44*S),radius=5*S,fill='white')
    d.rectangle((118*S,17*S,123*S,31*S),fill='white')
    save(battery,'battery.png')
    bolt=canvas(32,48); ImageDraw.Draw(bolt).polygon([(19*S,2*S),(5*S,27*S),(15*S,27*S),(11*S,46*S),(28*S,19*S),(18*S,19*S)],fill='white')
    save(bolt,'bolt.png')
    Image.new('RGBA',(2,2),'white').save(OUT/'white.png')

def atlas(name, filename, bold=False):
    font=ImageFont.truetype(str(FONTS/filename),72)
    if bold:
        # Orbitron variable weight; Pillow's variation API is only needed at build time.
        font.set_variation_by_axes([700])
    im=Image.new('RGBA',(2048,1024)); d=ImageDraw.Draw(im)
    cap=-font.getbbox('H',anchor='ls')[1]
    digits=max(font.getlength(c) for c in '0123456789')
    data={'texture':f'assets/{name}.png','cap':cap,'glyphs':{}}
    for i,code in enumerate(range(32,127)):
        c=chr(code); x=(i%16)*128+8; baseline=(i//16)*128+96
        box=font.getbbox(c,anchor='ls')
        d.text((x,baseline),c,font=font,fill='white',anchor='ls')
        adv=digits if c.isdigit() else font.getlength(c)
        # bbox metadata in font pixels, UV padded by one pixel for filtering.
        x0,y0,x1,y1=box
        data['glyphs'][str(code)]={'advance':round(adv,4),'x':((adv-(x1-x0))/2-1 if c.isdigit() else x0-1),'y':y0-1,
          'w':x1-x0+2,'h':y1-y0+2,
          'uv':[(x+x0-1)/2048,(baseline+y0-1)/1024,(x+x1+1)/2048,(baseline+y1+1)/1024]}
    im.save(OUT/f'{name}.png')
    return data

def lua(v):
    if isinstance(v,dict): return '{'+','.join('['+json.dumps(str(k))+']='+lua(x) for k,x in v.items())+'}'
    if isinstance(v,list): return '{'+','.join(lua(x) for x in v)+'}'
    return json.dumps(v,separators=(',',':'))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    # The renderer applies the shared -10/172 skew to this canonical rectangle.
    panel('left',512,192,[(17,10),(497,10),(497,182),(17,182)])
    inset=12*(1+(10/172)**2)**0.5
    for name,top,bottom in [('player_highlight',106,170),('player_highlight_solo',64,128),('player_highlight_leader',22,86)]:
        highlight=canvas(512,192); hd=ImageDraw.Draw(highlight)
        box=((17+inset)*S,top*S,(497-inset)*S,bottom*S)
        hd.rectangle(box,fill=(255,255,255,25),outline=(255,255,255,240),width=2*S)
        save(highlight,name+'.png')
    panel('right',512,192,[(15,10),(495,10),(505,182),(25,182)])
    panel('module',96,192,[(10,7),(86,7),(86,185),(10,185)])
    dial(); misc()
    data={'labels':atlas('labels','Orbitron.ttf',True),
          'names':atlas('names','BarlowCondensed-BoldItalic.ttf')}
    (APP/'glyphs.lua').write_text('-- Generated by source/build_assets.py. Do not edit.\nreturn '+lua(data)+'\n',encoding='utf-8')
    (ROOT/'source/glyphs.json').write_text(json.dumps(data),encoding='utf-8')
    icon=Image.new('RGBA',(64,64)); d=ImageDraw.Draw(icon)
    d.ellipse((5,5,59,59),fill=(6,24,43,230),outline=(47,224,208),width=3)
    d.arc((13,16,51,51),190,350,fill=(58,184,232),width=5)
    icon.save(APP/'icon.png')
    manifest=[]
    for p in sorted(OUT.glob('*.png'))+[APP/'icon.png']:
        with Image.open(p) as a: manifest.append({'file':str(p.relative_to(APP)).replace('\\','/'),'width':a.width,'height':a.height})
    (ROOT/'source/asset-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'Built {len(manifest)} PNG assets and glyphs.lua')

if __name__=='__main__': main()
