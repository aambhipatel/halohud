"""Extract one version's README changelog for a GitHub release."""
from pathlib import Path
import argparse
import re

def extract(readme, version):
    version=version.removeprefix('v')
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?',version):
        raise ValueError('Expected a semantic version such as v1.10.0')
    active=False; capture=False; sections=[]; body=[]; fence=None
    for line in readme.splitlines():
        stripped=line.lstrip()
        marker=re.match(r'^(`{3,}|~{3,})',stripped)
        if marker:
            token=marker.group(1)
            if fence is None: fence=token
            elif token[0]==fence[0] and len(token)>=len(fence): fence=None
            if capture: body.append(line)
            continue
        if fence is None:
            heading=re.match(r'^(#{1,3})[ \t]+(.+?)\s*$',line)
            if heading:
                level=len(heading.group(1)); title=heading.group(2)
                if capture:
                    sections.append('\n'.join(body).strip());body=[];capture=False
                if level<=2:
                    active=level==2 and title.casefold()=='changelog'
                elif active and re.match(r'^v?'+re.escape(version)+r'(?=\s|$)',title):
                    capture=True
                continue
        if capture: body.append(line)
    if capture: sections.append('\n'.join(body).strip())
    if len(sections)!=1 or not sections[0]:
        raise ValueError(f'Expected one nonempty changelog entry for {version}; found {len(sections)}')
    return sections[0]+'\n'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag');parser.add_argument('--readme',type=Path,default=Path('README.md'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    notes=extract(args.readme.read_text(encoding='utf-8-sig'),args.tag)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(notes,encoding='utf-8')
    print(f'Extracted {args.tag} changelog into {args.output}')

if __name__=='__main__': main()
