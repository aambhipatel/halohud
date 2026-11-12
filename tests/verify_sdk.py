"""Verify the runtime's CSP API and fields against an installed/generated SDK.

python tests/verify_sdk.py PATH/TO/extension/internal/lua-sdk/ac_apps/lib.lua
Only reads declarations; does not execute CSP. The generated SDK is not bundled.
"""
from pathlib import Path
import re, sys, hashlib
from headless import APP

def main():
    if len(sys.argv)!=2: raise SystemExit(__doc__)
    p=Path(sys.argv[1]); sdk=p.read_text(encoding='utf-8')
    runtime='\n'.join(x.read_text(encoding='utf-8') for x in APP.glob('*.lua') if x.name!='glyphs.lua')
    calls=set(re.findall(r'\b((?:ac|ui|os)\.[A-Za-z_]\w*)\s*\(',runtime))
    # INIConfig.load is nested, include explicitly rather than matching its prefix.
    calls.discard('ac.INIConfig')
    if 'ac.INIConfig.load(' in runtime: calls.add('ac.INIConfig.load')
    missing=[x for x in calls if not re.search(r'function\s+'+re.escape(x)+r'\s*\(',sdk)]
    assert not missing, 'Missing SDK calls: '+str(missing)
    for field in sorted(set(re.findall(r'\bcar\.([A-Za-z_]\w*)',runtime))):
        assert re.search(r'---@field '+re.escape(field)+r'\b',sdk),'Missing car field '+field
    for field in ('carsCount','currentSessionIndex','leaderboard','car','windowSize',
                  'raceSessionType','racePosition','isConnected','isActive',
                  'appsHidden','uiHidden'):
        assert re.search(r'---@field '+field+r'\b',sdk),'Missing state field '+field
    for method in ('driverName','get','set','save'):
        assert re.search(r'function [\w_]+:'+method+r'\(',sdk),'Missing method '+method
    print('Verified calls: '+', '.join(sorted(calls)))
    print('Verified car fields and state/INI methods')
    print('SDK SHA256: '+hashlib.sha256(p.read_bytes()).hexdigest())

if __name__=='__main__':main()
