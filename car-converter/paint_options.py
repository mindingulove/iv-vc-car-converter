"""Conversion-time paint choices; never modify a game's shared colour palette."""
from pathlib import Path
import re

CHANNEL_NAMES={1:'Primary',2:'Secondary',3:'Tertiary',4:'Quaternary'}
def channel_name(channel):return CHANNEL_NAMES.get(channel,f'Paint channel {channel}')
def material_color(rgb):
 # These two exact RGB triplets are native RenderWare paint-channel sentinels.
 rgb=tuple(rgb)
 if rgb==(60,255,0):rgb=(60,254,0)
 if rgb==(255,0,175):rgb=(254,0,175)
 return rgb+(255,)

def parse_colors(values):
 result={}
 for value in values or []:
  match=re.fullmatch(r'(\d{1,2})=(?:#)?([0-9a-fA-F]{6})',value.strip())
  if not match or not 1<=int(match[1])<=16:raise ValueError('Use --paint CHANNEL=#RRGGBB (channels 1–16).')
  result[int(match[1])]=tuple(bytes.fromhex(match[2]))
 return result

def resolve_runtime(value):
 path=Path(value).expanduser().resolve()
 if path.name.casefold()=='modloader':path=path.parent
 if not path.is_dir():raise ValueError('Choose an existing game folder.')
 mods=[p for p in path.iterdir() if p.is_dir() and p.name.casefold()=='modloader']
 if len(mods)!=1:raise ValueError('The game folder must contain one Modloader folder.')
 # The native runtime uses this conventional path; reject ambiguous names instead of installing elsewhere.
 if mods[0].name!='modloader':raise ValueError('Rename the Modloader folder to modloader for this native port.')
 if not (path/'data/default.ide').is_file():raise ValueError('The selected folder is missing data/default.ide.')
 return path

def patch_material_colors(data,locations,colors):
 import struct
 data=bytearray(data)
 def chunks(start,end):
  while start<end:
   if start+12>end:raise ValueError('Truncated RenderWare chunk')
   kind,size,version=struct.unpack_from('<III',data,start);body=start+12;stop=body+size
   if stop>end:raise ValueError('Invalid RenderWare chunk size')
   yield kind,body,stop
   start=stop
 def one(kind,start,end):
  found=[(b,e) for k,b,e in chunks(start,end) if k==kind]
  if len(found)!=1:raise ValueError('Expected one RenderWare chunk '+str(kind))
  return found[0]
 cb,ce=one(16,0,len(data));gb,ge=one(26,cb,ce)
 geometries=[(b,e) for k,b,e in chunks(gb,ge) if k==15]
 for loc in locations:
  b,e=geometries[loc['geometry']];mb,me=one(8,b,e)
  mats=[(b,e) for k,b,e in chunks(mb,me) if k==7];b,e=mats[loc['material']];sb,se=one(1,b,e)
  if se-sb<16:raise ValueError('Invalid material structure')
  rgba=material_color(colors[loc['channel']]) if loc['channel'] in colors else tuple(loc['defaultColor'])
  data[sb+4:sb+8]=bytes(rgba)
 return bytes(data)

def recolor(folder,colors,validate,render):
 import json,hashlib,shutil,tempfile,os
 folder=Path(folder).resolve();report=json.loads((folder/'conversion.json').read_text());name=report['name']
 locations=report.get('paintMaterialLocations')
 if locations is None:raise ValueError('Convert this car again to detect its paint channels before recolouring.')
 detected=set(report.get('detectedPaintChannels',[]));unknown=set(colors)-detected
 if unknown:raise ValueError('Car has no detected paint channel(s): '+', '.join(map(str,sorted(unknown))))
 # Patch only material colour bytes. Preserve all streamed hierarchy/plugins exactly.
 patched=patch_material_colors((folder/(name+'.dff')).read_bytes(),locations,colors)
 with tempfile.TemporaryDirectory(prefix='car-paint-',dir=folder.parent) as tmp:
  stage=Path(tmp)/'package';shutil.copytree(folder,stage,ignore=shutil.ignore_patterns('work'))
  (stage/(name+'.dff')).write_bytes(patched)
  report['paintColors']={str(k):list(v) for k,v in colors.items()};report['nativeValidated']=False
  (stage/'conversion.json').write_text(json.dumps(report,indent=2)+'\n');validate(stage,name,report['wheelDiameter'])
  report['assetHashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [stage/(name+s) for s in ('.dff','.txd','.col')]};report['nativeValidated']=True
  (stage/'conversion.json').write_text(json.dumps(report,indent=2)+'\n');render(stage,name,report['textureSources'],stage/'preview.png')
  for filename in (name+'.dff','preview.png','native-validation.log','conversion.json'):os.replace(stage/filename,folder/filename)
 return report
