"""Verify a private sources-only CamRig bundle without modifying it."""
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def verify(bundle):
    files=[p for p in bundle.rglob('*') if p.is_file()]
    forbidden={'.serena','.cursor','.git','__pycache__','.pytest_cache','tests'}
    for path in files:
        relative=path.relative_to(bundle)
        assert not forbidden.intersection(relative.parts),str(relative)
        assert path.suffix not in ('.log','.pyc','.c4d'),str(relative)
        assert not path.name.startswith('.env'),str(relative)
    expected=list((ROOT/'camrig').glob('*.py'))+[ROOT/'camrig/ud_template.json',ROOT/'camrig/legacy_140.txt',ROOT/'cam_rig_builder.pyp']
    for source in expected:
        target=bundle/source.relative_to(ROOT)
        assert target.is_file(),str(target)
        assert target.read_bytes()==source.read_bytes(),str(target)+' differs from source'
    broken=[]
    for path in bundle.rglob('*.md'):
        text=re.sub(r'```.*?```','',path.read_text(encoding='utf-8-sig'),flags=re.S)
        for target in re.findall(r'\]\(([^\n]+?)\)',text):
            target=unquote(target.strip().strip('<>')).split('#')[0]
            if not target or re.match(r'[a-z]+://|mailto:',target,re.I): continue
            if not (path.parent/target).exists(): broken.append(str(path.relative_to(bundle))+': '+target)
    assert not broken,'\n'.join(broken)
    archive=bundle.with_suffix('.zip')
    with zipfile.ZipFile(archive) as zf:
        assert zf.testzip() is None
        expected_names={str(p.relative_to(bundle.parent)).replace('\\','/') for p in files}
        assert set(zf.namelist())==expected_names
        for path in files:
            assert zf.read(str(path.relative_to(bundle.parent)).replace('\\','/'))==path.read_bytes()
    return {'status':'PASS','files':len(files),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'checks':['source identity','no caches/secrets/local configs','local Markdown links','ZIP integrity and content identity']}

if __name__=='__main__':
    print(json.dumps(verify(Path(sys.argv[1]).resolve()),indent=2))
