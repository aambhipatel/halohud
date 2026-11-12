"""Read-only mesh-bound inspection. Does not open or unpack data.acd.

Binary layout checked against Content Manager's open-source Kn5Basic.Kn5Reader:
https://github.com/gro-ove/actools/blob/master/AcTools/Kn5File/Kn5Basic.cs
and ReadAheadBinaryReader.cs. No textures or geometry are exported.
Usage: python source/inspect_kn5.py path/to/fu26.kn5
"""
from pathlib import Path
import struct,json,sys
import numpy as np

def inspect(path):
    path=Path(path)
    if path.suffix.lower()!='.kn5': raise ValueError('Only a .kn5 model may be inspected')
    nodes=[]
    with path.open('rb') as f:
        def read(n):
            b=f.read(n)
            if len(b)!=n: raise ValueError('Truncated model')
            return b
        def u():return struct.unpack('<I',read(4))[0]
        def skip(n):f.seek(n,1)
        def string():
            n=u()
            if n>100000:raise ValueError('Unexpected string length')
            return read(n).decode('utf-8',errors='replace')
        assert read(6)==b'sc6969','Unsupported/encrypted model: no decryption attempted'
        version=u()
        if version>5:u()
        textures=u()
        for _ in range(textures):u();string();skip(u())
        materials=u()
        for _ in range(materials):
            string();string();skip(6)
            for _ in range(u()):string();skip(40)
            for _ in range(u()):string();u();string()
        def node(parent,path):
            kind=u(); name=string(); children=u();active=bool(read(1)[0])
            here=path+'/'+name; world=parent
            item={'path':here,'class':kind,'active':active}
            if kind==1:
                local=np.frombuffer(read(64),dtype='<f4').reshape((4,4)).astype(float)
                world=local@parent
                item['world_translation']=world[3,:3].tolist()
            elif kind in (2,3):
                skip(3)
                if kind==3:
                    for _ in range(u()):string();skip(64)
                count=u();stride=44 if kind==2 else 76
                raw=read(count*stride)
                vertices=np.ndarray((count,3),dtype='<f4',buffer=raw,strides=(stride,4)).astype(float)
                points=np.c_[vertices,np.ones(count)]@world
                item['vertices']=count
                item['world_min']=points[:,:3].min(axis=0).tolist()
                item['world_max']=points[:,:3].max(axis=0).tolist()
                skip(2*u());skip(33 if kind==2 else 16)
            else:raise ValueError('Unsupported node class '+str(kind))
            nodes.append(item)
            for _ in range(children):node(world,here)
        node(np.eye(4),'')
        consumed=f.tell()
        trailing=path.stat().st_size-consumed
    selected=[n for n in nodes if any(t in n['path'].lower() for t in ('halo','lcd','steer','driver','head','camera','cockpit'))]
    return {'model':path.name,'version':version,'node_count':len(nodes),
            'bytes_consumed':consumed,'trailing_bytes':trailing,
            'note':'Trailing bytes are not interpreted; bounds are from parsed nodes only.',
            'selected_nodes':selected}

if __name__=='__main__':
    data=inspect(sys.argv[1]);out=Path(__file__).resolve().parents[1]/'reports/model-inspection.json'
    out.write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps(data,indent=2))
