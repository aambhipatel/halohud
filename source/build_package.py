"""Regenerate complete text listing, hashes and both distribution ZIPs.

Run after rebuilding assets, testing, and rendering previews:
    python source/build_package.py
No network, game directory access or destructive operations.
"""
from pathlib import Path
import hashlib, zipfile, json

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'apps/lua/HaloHUD'

EXCLUDED_DIRS={'.git','.venv','venv','__pycache__','.pytest_cache','.mypy_cache',
               '.vscode','.idea','htmlcov','dist'}
def publishable(p):
    rel=p.relative_to(ROOT)
    return not any(part in EXCLUDED_DIRS for part in rel.parts) and not (
        p.name in {'.env','.coverage','.DS_Store','Thumbs.db','Desktop.ini'}
        or (p.name.startswith('.env.') and p.name!='.env.example')
        or p.suffix.lower() in {'.pyc','.pyo','.log','.pem','.key','.zip'})

def files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and publishable(p)
                  and p.name not in ('FILES.sha256','SOURCE-CONTENTS.md'))

def main():
    # Preserve license notices when installing only the runtime ZIP.
    licenses=APP/'licenses'; licenses.mkdir(exist_ok=True)
    for src in [ROOT/'LICENSE.txt',*sorted((ROOT/'source/fonts').glob('*OFL.txt'))]:
        (licenses/src.name).write_bytes(src.read_bytes())
    source=[]
    extensions={'.lua': 'lua','.ini':'ini','.example':'ini','.py':'python',
                '.txt':'text','.json':'json','.html':'html','.cjs':'javascript'}
    for p in files():
        if p.suffix not in extensions: continue
        text=p.read_text(encoding='utf-8')
        source.append('## '+p.relative_to(ROOT).as_posix()+'\n\n````'+extensions[p.suffix]+'\n'+text+'\n````\n')
    (ROOT/'docs/SOURCE-CONTENTS.md').write_text('# Complete text file contents\n\n'
        'Runtime, generator, test, camera, license and offline-demo files are reproduced below. '
        'PNG/font binaries are supplied as actual files; regenerate PNGs with source/build_assets.py.\n\n'
        +'\n'.join(source),encoding='utf-8')
    allfiles=files()+[ROOT/'docs/SOURCE-CONTENTS.md']
    (ROOT/'FILES.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+
        p.relative_to(ROOT).as_posix()+'\n' for p in allfiles),encoding='utf-8')
    complete=ROOT.parent/(ROOT.name+'-complete.zip')
    install=ROOT.parent/(ROOT.name+'-install.zip')
    with zipfile.ZipFile(complete,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(allfiles+[ROOT/'FILES.sha256']): z.write(p,ROOT.name+'/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(install,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(APP.rglob('*')):
            if p.is_file() and publishable(p): z.write(p,p.relative_to(ROOT).as_posix())
    for path in (install,complete):
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            assert not any('__pycache__' in n for n in z.namelist())
            print(f'{path.name}: {len(z.namelist())} files, {path.stat().st_size:,} bytes, CRC passed')
    # Check manifest assets are present in the install, at exact dimensions.
    from PIL import Image
    with zipfile.ZipFile(install) as z:
        names=set(z.namelist())
        for entry in json.loads((ROOT/'source/asset-manifest.json').read_text()):
            asset=APP/entry['file']
            assert asset.relative_to(ROOT).as_posix() in names
            with Image.open(asset) as im: assert im.size==(entry['width'],entry['height'])
    print('Install structure and all '+str(len(json.loads((ROOT/'source/asset-manifest.json').read_text())))+' asset sizes verified')

if __name__=='__main__':main()
