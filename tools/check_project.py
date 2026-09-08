"""Deterministic static/host-Python checks; this is not a Cinema 4D runtime test."""
import ast
import json
import math
from pathlib import Path
import re
import sys
import types
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

def main():
    files=list((ROOT/'camrig').glob('*.py'))+list((ROOT/'tools').glob('*.py'))+list((ROOT/'tests').glob('*.py'))+[ROOT/'cam_rig_builder.pyp']
    for path in files:
        compile(path.read_text(encoding='utf-8-sig'),str(path),'exec')
    config={}
    # config's only runtime dependency is its display-color Vector. No simulation of C4D behavior.
    stub=types.ModuleType('c4d')
    stub.Vector=lambda *args:args
    previous=sys.modules.get('c4d')
    sys.modules['c4d']=stub
    try:
        exec(compile((ROOT/'camrig/config.py').read_text(encoding='utf-8'),'config.py','exec'),config)
    finally:
        if previous is None: del sys.modules['c4d']
        else: sys.modules['c4d']=previous
    template=json.loads((ROOT/'camrig/ud_template.json').read_text(encoding='utf-8'))
    params=[p for group in template['groups'] for p in group['params']]
    assert len({p['key'] for p in params})==len(params), 'duplicate stable keys'
    defaults={p['name']:p['default'] for p in params if p['type'] in ('real','bool','enum')}
    assert defaults==config['UD_DEFAULTS'], 'template/config defaults mismatch'
    src=(ROOT/'camrig/tag_embedded.py').read_text(encoding='utf-8')
    tree=ast.parse(src)
    values={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name):
            try: values[node.targets[0].id]=ast.literal_eval(node.value)
            except (ValueError,TypeError): pass
    assert values['EMBEDDED_RUNTIME_VERSION']==config['PLUGIN_VERSION']=='1.5.0'
    assert values['SCHEMA_VERSION']==config['SCHEMA_VERSION']
    for key,value in values.items():
        if key.startswith(('UD_','DEFAULT_')) and key in config:
            assert value==config[key],key
    for key,value in values['NEW_UD_DEFAULTS'].items():
        assert defaults[key]==value,key
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or '']
            assert all(not name.startswith(('camrig','pathlib','os','subprocess')) for name in names)
        if isinstance(node,ast.Call):
            assert not (isinstance(node.func,ast.Name) and node.func.id in ('open','__import__'))
            assert not (isinstance(node.func,ast.Attribute) and node.func.attr in ('Remove','InsertUnder','InsertTag','InsertObject'))
    ns={'math':math,'Any':object}
    pure=ast.Module(body=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('_safe_float','orbit_phase')],type_ignores=[])
    exec(compile(pure,'orbit_math','exec'),ns)
    for angle in [-1080,-720,-10,0,350,370,1080]:
        assert math.isclose(ns['orbit_phase'](angle),(angle%360)/360)
    assert ns['orbit_phase'](float('nan'))==0
    assert ns['orbit_phase'](float('inf'))==0
    broken=[]
    markdown=list(ROOT.glob('*.md'))+list((ROOT/'docs').rglob('*.md'))+list((ROOT/'tools').glob('*.md'))
    for path in markdown:
        text=path.read_text(encoding='utf-8-sig')
        text=re.sub(r'```.*?```','',text,flags=re.S)
        for target in re.findall(r'\]\(([^\n]+?)\)',text):
            target=unquote(target.strip().strip('<>')).split('#')[0]
            if not target or re.match(r'[a-z]+://|mailto:',target,re.I): continue
            if not (path.parent/target).exists(): broken.append(str(path.relative_to(ROOT))+': '+target)
    assert not broken,'Broken local Markdown links:\n'+'\n'.join(broken)
    print(json.dumps({'status':'PASS','python':sys.version.split()[0],'compiled_files':len(files),'parameters':len(params),'markdown_files':len(markdown),'checks':['explicit .py and .pyp compile','schema/default parity','portable runtime boundary','signed orbit math','local markdown links']},indent=2))

if __name__=='__main__': main()
