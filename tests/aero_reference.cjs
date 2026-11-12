// Run the approved HTML's real JavaScript as the parity reference for Lua.
const fs=require('fs'),vm=require('vm');
const html=fs.readFileSync(require('path').join(__dirname,'../previews/Aero-animation-preview.html'),'utf8');
const elements={};
const context={document:{getElementById(id){return elements[id]||(elements[id]={value:id==='duration'?'420':'0',checked:false,setAttribute(){}})}},
 matchMedia:()=>({matches:false}),performance:{now:()=>now},requestAnimationFrame:f=>{tick=f}};
let now=0,tick;vm.createContext(context);vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
elements.loop.checked=false;
const go=vm.runInContext('go',context),frames=[];let previous=-1;
for(let i=0;i<240;i++){
 const active=i<50||(i>=65&&i<140),dt=[1/60,1/144,1/30,0.08][i%4];
 if(+active!==previous){go(+active,now);previous=+active}
 now+=dt*1000;tick(now);
 frames.push({active,dt,phase:vm.runInContext('phase',context),velocity:vm.runInContext('velocity',context)});
}
process.stdout.write(JSON.stringify(frames));
