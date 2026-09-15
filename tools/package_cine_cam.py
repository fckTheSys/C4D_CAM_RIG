"""Build a private allowlisted Cine zip; optionally install to a new folder."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.5.3'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--plugins-dir',type=Path)
    parser.add_argument('--update-existing',action='store_true',help='Verify old manifest and back up before updating')
    args = parser.parse_args()
    output = args.output.resolve()
    destination = args.plugins_dir.resolve()/'Cine_CAM' if args.plugins_dir else None
    backup = None
    if output.exists():
        raise FileExistsError('Refusing to overwrite an existing zip')
    if destination is not None and destination.exists():
        if not args.update_existing:
            raise FileExistsError('Existing installation requires --update-existing')
        previous = json.loads((destination/'manifest.json').read_text(encoding='utf-8'))
        if previous.get('command_id') != 10699230:
            raise ValueError('Not a known Cine installation')
        for name,digest in previous['files'].items():
            target = (destination/name).resolve()
            if not target.is_relative_to(destination) or hashlib.sha256(target.read_bytes()).hexdigest()!=digest:
                raise ValueError('Installation has local changes; refusing update: '+name)
        backup = ROOT/'release'/'private'/('Cine_CAM-backup-'+uuid.uuid4().hex)
        shutil.copytree(destination,backup)

    files = {name:ROOT/'Cine_CAM'/name for name in ('Cine_CAM.pyp','menu.py','README.md')}
    files.update({'runtime/'+name:ROOT/'prototypes'/'cine_variants'/name
                  for name in ('builder.py','runtime.py','inertia.py','effects_math.py')})
    files.update({'ck_runtime/'+name:ROOT/'prototypes'/'simple_camera'/name
                  for name in ('builder.py','runtime.py','motion_math.py','path_math.py','curve_math.py','PARAMETERS_RU.md')})
    for runtime in ('runtime', 'ck_runtime'):
        files[runtime+'/path_source.py'] = ROOT/'prototypes'/'path_source.py'
    for name in ('CAMERA_RIGS_GUIDE_RU.md', 'CK_CAM_PORTABILITY.md'):
        files['docs/'+name] = ROOT/'docs'/name
    payload = {name:path.read_bytes() for name,path in files.items()}
    payload['README.md'] = payload['README.md'].replace(b'../docs/CAMERA_RIGS_GUIDE_RU.md', b'docs/CAMERA_RIGS_GUIDE_RU.md')
    for name,data in payload.items():
        if name.endswith(('.py','.pyp')):
            compile(data.decode('utf-8'),name,'exec')
    manifest = {'name':'Cine Camera','version':VERSION,'command_id':10699230,
                'private_development':True,'scene_requires_plugin':False,
                'files':{name:hashlib.sha256(data).hexdigest() for name,data in payload.items()}}
    encoded = json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as archive:
        for name,data in payload.items():
            archive.writestr('Cine_CAM/'+name,data)
        archive.writestr('Cine_CAM/manifest.json',encoded)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for name,digest in manifest['files'].items():
            assert hashlib.sha256(archive.read('Cine_CAM/'+name)).hexdigest() == digest
    if destination is not None:
        destination.mkdir(parents=True,exist_ok=True)
        for name,source in files.items():
            target = destination/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(payload[name])
            assert hashlib.sha256(target.read_bytes()).hexdigest() == manifest['files'][name]
        (destination/'manifest.json').write_bytes(encoded)
    print(json.dumps({'status':'PASS','zip':str(output),'installed':str(destination) if destination else None,
                      'backup':str(backup) if backup else None,'files':len(payload)+1,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()},indent=2))


if __name__ == '__main__':
    main()
