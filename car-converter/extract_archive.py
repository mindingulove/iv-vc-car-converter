"""Complete lossless RSC5 resource extraction with collision-free model pairing."""
from pathlib import Path
import json,re,hashlib,shutil,zlib,struct
from resource_input import scan,resource

def extract_archive(source,dest,cache):
 source=Path(source).resolve();dest=Path(dest).resolve();dest.mkdir(parents=True,exist_ok=True);resources=dest/'resources';resources.mkdir(exist_ok=True);entries,blob,sha=scan(source,cache);records=[];names={};pending=None;shared_num=0
 for e in entries:
  recovered=resource(blob[e['offset']:e['offset']+e['length']]);i=e['index'];kind=e['typ'];embedded=e['names'][0] if e['names'] else 'unnamed'
  if kind==112:
   base=f"{i:06d}_"+re.sub('[^a-z0-9_-]','_',embedded.lower())[:80];filename=base+'.wft';pending=base
  elif kind==8:
   if pending:filename=pending+'.wtd';pending=None
   else:
    hints=' '.join(e['names']).lower()
    base='vehshare_truck' if 'vehicle_generic_truck_interior' in hints and len(e['names'])<10 else 'vehshare' if shared_num==0 else 'vehshare2' if shared_num==1 and len(e['names'])>10 else 'vehshare_extra'
    if base in names:base+='_'+str(i)
    names[base]=True;shared_num+=1;filename=base+'.wtd'
  else:filename=f'{i:06d}_type{kind}.rsc';pending=None
  path=resources/filename
  if path.exists() and path.read_bytes()!=recovered['data']:raise ValueError('Existing extraction differs: '+str(path))
  path.write_bytes(recovered['data']);assert zlib.decompress(path.read_bytes()[12:])
  records.append(dict(index=i,name=filename,type=kind,sourceOffset=e['offset'],bytes=e['length'],sourceSha256=hashlib.sha256(blob[e['offset']:e['offset']+e['length']]).hexdigest(),sha256=hashlib.sha256(recovered['data']).hexdigest(),checksumRepaired=recovered['checksumRepaired'],embeddedNames=e['names']))
 models=sum(r['type']==112 for r in records);textures=sum(r['type']==8 for r in records)
 for r in records:
  if r['type']==112:
   partner=resources/(Path(r['name']).stem+'.wtd')
   if partner.exists():r['pairedTexture']=partner.name
 manifest=dict(sourceArchive=str(source),sourceArchiveSha256=sha,naming='Index-prefixed embedded donor labels. Original encrypted directory filenames are not authenticated. Immediately following WTD paired with the model; shared dictionaries separately named.',resources=records,modelCount=models,textureDictionaryCount=textures,totalResources=len(records),compressedResourceBytes=sum(r['bytes'] for r in records),checksumRepairs=sum(r['checksumRepaired'] for r in records))
 # Sidecar data stays with the extraction, separate from native VC data.
 game=source.parents[3]
 if (game/'common/data').exists():shutil.copytree(game/'common/data',dest/'source-data',dirs_exist_ok=True)
 for parent in [game,*list(game.parents)[:2]]:
  for pattern in ['*CREDIT*.txt','*READ ME*.txt','readme.txt']:
   for p in parent.glob(pattern):shutil.copy2(p,dest/('SOURCE_'+p.name))
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 (dest/'README.md').write_text(f'''# Extracted vehicle resources\n\nSource: {source}\n\n{models} WFT models and {textures} WTD texture dictionaries; {len(records)} resources total. Original archives were not changed. The loose resources remain in their native RSC5 formats, preserving geometry, textures and mipmaps. {manifest['checksumRepairs']} existing resource checksum errors were corrected in extracted copies and recorded in manifest.json.\n\nFile names use the resource index and embedded donor label; these are not authenticated original IMG directory names. Each adjacent model/texture pair has a common basename. Shared dictionaries are named vehshare*.wtd. Select a WFT in the car converter; keep its matching WTD and the shared dictionaries in the same folder. Some resource labels differ from the displayed car name.\n\nsource-data contains original IV/NextGen sidecars, not native VC-ready data. Do not copy the extraction wholesale into the game; convert supported models individually.\n''')
 # Validate every written file and original archive integrity.
 assert hashlib.sha256(source.read_bytes()).hexdigest()==sha
 for r in records:assert hashlib.sha256((resources/r['name']).read_bytes()).hexdigest()==r['sha256']
 return manifest
