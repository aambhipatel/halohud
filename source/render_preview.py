"""Offline renderer and self-contained animated demo from actual Lua draw calls.

Run python source/render_preview.py, optionally --html. Pillow perspective
resampling differs slightly from CSP's two-triangle texture mapping.
"""
from pathlib import Path
import sys, math, json, base64, argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from headless import Harness, ROOT, APP
from PIL import Image, ImageChops, ImageDraw
import numpy as np

def draw_commands(commands,width=1920,height=1080):
    out=Image.new('RGBA',(width,height)); textures={}; tinted={}
    for texture,points,color,uv in commands:
        if texture not in textures: textures[texture]=Image.open(APP/texture).convert('RGBA')
        k=(texture,tuple(round(c,5) for c in color))
        if k not in tinted:
            tex=textures[texture]
            factors=[max(0,min(255,round(c*255))) for c in color]
            tinted[k]=ImageChops.multiply(tex,Image.new('RGBA',tex.size,tuple(factors)))
        tex=tinted[k]
        x0=math.floor(min(p[0] for p in points)); y0=math.floor(min(p[1] for p in points))
        x1=math.ceil(max(p[0] for p in points)); y1=math.ceil(max(p[1] for p in points))
        if x1<=x0 or y1<=y0: continue
        # Inverse projective map from local destination pixels into source UVs.
        A=[]; B=[]
        for p,t in zip(points,uv):
            x,y=p[0]-x0,p[1]-y0; u,v=t[0]*tex.width,t[1]*tex.height
            A.append([x,y,1,0,0,0,-u*x,-u*y]); B.append(u)
            A.append([0,0,0,x,y,1,-v*x,-v*y]); B.append(v)
        try: coeff=np.linalg.solve(np.asarray(A),np.asarray(B))
        except np.linalg.LinAlgError: continue
        patch=tex.transform((x1-x0,y1-y0),Image.Transform.PERSPECTIVE,coeff,
                            Image.Resampling.BICUBIC)
        # Projective mapping alone samples outside the destination quad. Clip it.
        mask=Image.new('L',patch.size)
        ImageDraw.Draw(mask).polygon([(p[0]-x0,p[1]-y0) for p in points],fill=255)
        patch.putalpha(ImageChops.multiply(patch.getchannel('A'),mask))
        out.alpha_composite(patch,(x0,y0))
    return out

def write_html():
    h=Harness(demo='ON'); frames=[]
    # Cache stable shapes in a command pool. This records the app itself; the web
    # demo contains no independently implemented telemetry or layout equations.
    pool=[]; index={}
    for i in range(192):
        # Step at graphics-like dt so animation timing matches the game, then
        # record only 12 snapshots/sec for the lightweight browser demo.
        for _ in range(5): commands=h.frame(1/60)
        frame=[]
        for c in commands:
            # Round only in the browser export, never the CSP app.
            c=[c[0],[[round(v,2) for v in p] for p in c[1]],
               [round(v,4) for v in c[2]],[[round(v,6) for v in p] for p in c[3]]]
            key=json.dumps(c,separators=(',',':'))
            if key not in index: index[key]=len(pool); pool.append(c)
            frame.append(index[key])
        frames.append(frame)
    images={p.relative_to(APP).as_posix():'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()
            for p in (APP/'assets').glob('*.png')}
    data=json.dumps({'pool':pool,'frames':frames,'images':images},separators=(',',':'))
    html='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>HaloHUD for Assetto Corsa — offline demo</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#101b23;color:#eaf6fa;font:15px system-ui,sans-serif}
main{max-width:1920px;margin:auto}canvas{width:100%;height:auto;display:block;background:#24333e}
footer{display:flex;flex-wrap:wrap;align-items:center;gap:16px;padding:16px 24px}
button{font:inherit;color:#fff;background:#164e67;border:1px solid #2fe0d0;border-radius:4px;padding:8px 16px;cursor:pointer}
button:focus-visible,input:focus-visible{outline:3px solid #fff;outline-offset:4px}
p{max-width:900px;margin:0;color:#aec3d0}input{accent-color:#2fe0d0}a{color:#2fe0d0}
</style><main><canvas id="hud" width="1920" height="1080" aria-label="Animated synthetic HaloHUD telemetry. No game connection."></canvas>
<footer><button id="play">Pause demo</button><label>Time <input id="seek" type="range" min="0" max="191" value="0"></label>
<label>Background <input id="bg" type="color" value="#24333e"></label>
<p>Synthetic telemetry · 16-second loop. Rendered from the packaged Lua app's draw commands at 12 snapshots/sec. The live app updates every game frame. This preview does not test CSP integration or performance.</p></footer></main>
<script>const DATA=__DATA__;
const cv=document.getElementById('hud'),ctx=cv.getContext('2d');
const seek=document.getElementById('seek'),play=document.getElementById('play');
const bg=document.getElementById('bg');let playing=true,frame=0,last=0;
const textures={},cache=new Map();
function tinted(name,c){
 const key=name+'|'+c.join(',');if(cache.has(key))return cache.get(key);
 const im=textures[name],can=document.createElement('canvas');can.width=im.width;can.height=im.height;
 const x=can.getContext('2d');x.drawImage(im,0,0);const d=x.getImageData(0,0,can.width,can.height);
 for(let i=0;i<d.data.length;i+=4){d.data[i]*=c[0];d.data[i+1]*=c[1];d.data[i+2]*=c[2];d.data[i+3]*=c[3];}
 x.putImageData(d,0,0);cache.set(key,can);return can;
}
function tri(im,p,t,ids){
 const [a,b,c]=ids.map(i=>p[i]),[u,v,w]=ids.map(i=>[t[i][0]*im.width,t[i][1]*im.height]);
 const det=u[0]*(v[1]-w[1])+v[0]*(w[1]-u[1])+w[0]*(u[1]-v[1]);if(Math.abs(det)<1e-9)return;
 function coeff(j){return [
 (a[j]*(v[1]-w[1])+b[j]*(w[1]-u[1])+c[j]*(u[1]-v[1]))/det,
 (a[j]*(w[0]-v[0])+b[j]*(u[0]-w[0])+c[j]*(v[0]-u[0]))/det,
 (a[j]*(v[0]*w[1]-w[0]*v[1])+b[j]*(w[0]*u[1]-u[0]*w[1])+c[j]*(u[0]*v[1]-v[0]*u[1]))/det];}
 const X=coeff(0),Y=coeff(1);ctx.save();ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.lineTo(...c);ctx.closePath();ctx.clip();
 ctx.transform(X[0],Y[0],X[1],Y[1],X[2],Y[2]);ctx.drawImage(im,0,0);ctx.restore();
}
function draw(){ctx.clearRect(0,0,1920,1080);ctx.fillStyle=bg.value;ctx.fillRect(0,0,1920,1080);
 for(const id of DATA.frames[frame]){const [name,p,c,t]=DATA.pool[id],im=tinted(name,c);tri(im,p,t,[0,1,2]);tri(im,p,t,[0,2,3]);}seek.value=frame;}
play.onclick=()=>{playing=!playing;play.textContent=playing?'Pause demo':'Play demo'};
seek.oninput=()=>{frame=+seek.value;draw()};bg.oninput=draw;
Promise.all(Object.entries(DATA.images).map(([name,url])=>new Promise(resolve=>{const im=new Image();im.onload=()=>{textures[name]=im;resolve()};im.src=url}))).then(()=>{
 draw();requestAnimationFrame(function tick(t){if(playing&&t-last>=1000/12){frame=(frame+1)%DATA.frames.length;draw();last=t}requestAnimationFrame(tick)});
});</script>'''.replace('__DATA__',data)
    (ROOT/'previews/Demo.html').write_text(html,encoding='utf-8')
    print(f'Demo.html: {len(pool)} pooled commands, {len(frames)} frames')

def main():
    p=argparse.ArgumentParser();p.add_argument('--html',action='store_true');args=p.parse_args()
    commands=Harness().snapshot()
    im=draw_commands(commands)
    im.save(ROOT/'previews/HaloHUD-transparent.png')
    back=Image.new('RGBA',im.size,(36,51,62,255)); back.alpha_composite(im)
    back.convert('RGB').save(ROOT/'previews/HaloHUD-preview.png')
    # Useful close-up without changing the runtime's proportions.
    back.crop((65,340,1870,940)).convert('RGB').save(ROOT/'previews/HaloHUD-detail.png')
    if args.html: write_html()
    print(f'Preview captured from {len(commands)} actual Lua textured quads')

if __name__=='__main__':main()
