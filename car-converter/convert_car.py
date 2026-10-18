#!/usr/bin/env python3
"""Native reVC car conversion/installation CLI. Run without arguments for the GUI."""
from pathlib import Path
import argparse,json,os,re,subprocess,sys,shutil,datetime,hashlib,tempfile
ROOT=Path(__file__).resolve().parents[1];SOURCE=Path(os.environ.get('REVC_SOURCE',str(ROOT.parent/'revc-metal'))).expanduser().resolve();DEFAULT_RUNTIME=Path.home()/'Documents/revc-metal-run'

def run(command,**kw):
 print('+',' '.join(map(str,command)),flush=True);subprocess.run(list(map(str,command)),check=True,**kw)

def car_rows(runtime):
 result={}
 for p in [runtime/'data/default.ide',*sorted((runtime/'modloader').rglob('*.ide'))]:
  if not p.exists():continue
  section=''
  for raw in p.read_text(errors='replace').splitlines():
   line=raw.strip()
   if not line or line.startswith('#'):continue
   if line.lower()=='end':section='';continue
   if line.lower()=='cars':section='cars';continue
   if section!='cars':continue
   cols=[v.strip() for v in line.split(',')]
   if len(cols)>=13 and cols[0].isdigit() and cols[3]=='car':result[int(cols[0])]=cols
 return result

def occupied_ids(runtime):
 ids=set(range(300))
 for p in runtime.rglob('*'):
  if not p.is_file() or p.suffix.lower()!='.ide':continue
  for line in p.read_text(errors='replace').splitlines():
   m=re.match(r'\s*(\d+)\s*[,\s]',line)
   if m:ids.add(int(m[1]))
 return ids

def setup():
 exe=ROOT/'gta4-webmap/extractor/bin/Release/net8.0/Gta4MapExtractor.dll'
 cs=ROOT/'gta4-webmap/extractor'
 if not exe.exists() or any(p.stat().st_mtime>exe.stat().st_mtime for p in cs.glob('*.cs')):
  run(['dotnet','build',cs/'Gta4MapExtractor.csproj','-c','Release','--nologo'])
 return exe

def validate(folder,name,diameter,metal=True):
 cmd=[sys.executable,SOURCE/'tools/run_imported_suspension_test.py',folder/(name+'.dff'),folder/(name+'.txd'),'--diameter='+str(diameter)]
 profile=folder/'data'/('cvh_'+name+'.cfg')
 if profile.exists():cmd.append('--fit-profile='+str(profile))
 if metal:cmd.append('--metal')
 result=subprocess.run(list(map(str,cmd)),capture_output=True,text=True);(folder/'native-validation.log').write_text(result.stdout+'\n'+result.stderr)
 if result.returncode:raise RuntimeError('Native asset/streaming validation failed; see '+str(folder/'native-validation.log'))
 print(result.stdout,flush=True)

def install(folder,runtime):
 report=json.loads((folder/'conversion.json').read_text());name=report['name']
 from paint_options import resolve_runtime
 runtime=resolve_runtime(runtime)
 if report['mode']=='replace':
  target=car_rows(runtime).get(report['modelId'])
  if not target or target[1]!=name:raise ValueError('This replacement targets a different game/model ID. Convert it using the selected game folder first.')
 if not report.get('nativeValidated'):raise ValueError('Package has not passed native validation')
 marker=runtime/'NATIVE_CAR_ADDONS.json';capabilities=json.loads(marker.read_text()) if marker.exists() else {}
 if capabilities.get('convertedHandlingVersion',0)>=1 and not report.get('handlingFit'):raise RuntimeError('This package predates the suspension/handling fix. Convert it again before installing so it cannot restore the old raised suspension.')
 for suffix in ('.dff','.txd','.col'):
  p=folder/(name+suffix)
  if hashlib.sha256(p.read_bytes()).hexdigest()!=report['assetHashes'][p.name]:raise ValueError('Assets changed after validation; convert again')
 for rel,expected in report.get('dataHashes',{}).items():
  if hashlib.sha256((folder/rel).read_bytes()).hexdigest()!=expected:raise ValueError('Handling/data changed after validation; convert again')
 for process in ('reVC_metal','reVC'):
  if subprocess.run(['pgrep','-x',process],stdout=subprocess.DEVNULL).returncode==0:raise RuntimeError('Close Vice City before installing. Converted files are ready; use Install again after closing it.')
 if capabilities.get('convertedExtrasVersion',0)>=1 and report.get('extrasVersion',0)<1:raise RuntimeError('This package predates automatic extras and colour preservation. Convert it again before installing so it cannot restore merged roofs or exterior-coloured interiors.')
 from runtime_compat import require_glass_support
 require_glass_support(report,runtime)
 if report.get('lampGlassVersion',0)>capabilities.get('convertedLampGlassVersion',0):raise RuntimeError('Install the native breakable lamp-glass update before installing this car.')
 if report.get('extrasVersion',0)>capabilities.get('convertedExtrasVersion',0) or report.get('materialPolicyVersion',0)>capabilities.get('convertedMaterialVersion',0):raise RuntimeError('Install the native converted extras/material update before installing this newly converted car.')
 if report.get('handlingFit') and json.loads((runtime/'NATIVE_CAR_ADDONS.json').read_text()).get('convertedHandlingVersion',0)<1:raise RuntimeError('Install the native per-car handling update before this package')
 if report.get('suspension',{}).get('autoFit') and json.loads((runtime/'NATIVE_CAR_ADDONS.json').read_text()).get('convertedSuspensionVersion',0)<1:raise RuntimeError('Install the native converted-suspension update before this package')
 # Require the add-on-capable native build installed by this project.
 if report['mode']=='add' and not (runtime/'NATIVE_CAR_ADDONS.json').exists():raise RuntimeError('This runtime needs the native add-on car update before installing new IDs')
 dest=runtime/'modloader'/('Converted '+name);stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
 if dest.exists():shutil.copytree(dest,runtime/'backups'/('converted-'+name+'-'+stamp))
 elif report['mode']=='add' and report['modelId'] in occupied_ids(runtime):raise RuntimeError('The allocated model ID is now occupied. Convert again to allocate another ID.')
 temp=runtime/('converted-install-'+name);temp.mkdir(exist_ok=True)
 for p in folder.iterdir():
  if p.is_file() and (p.suffix in ('.dff','.txd','.col','.json','.md','.png','.log','.txt')):shutil.copy2(p,temp/p.name)
 if (folder/'data').exists():shutil.copytree(folder/'data',temp/'data',dirs_exist_ok=True)
 if dest.exists():shutil.rmtree(dest)
 temp.replace(dest)
 ini=runtime/'modloader/modloader.ini';text=ini.read_text();key=dest.name+'=80'
 if not re.search(r'(?m)^'+re.escape(dest.name)+r'\s*=',text):text=text.replace('[Profiles.Default.Priority]','[Profiles.Default.Priority]\n'+key);ini.write_text(text)
 report['installed']=str(dest);(folder/'conversion.json').write_text(json.dumps(report,indent=2)+'\n');print('Installed:',dest,flush=True);return dest

def suspension(args):
 values=[float(args.ride_height)/100,float(args.stiffness),float(args.damping),float(args.travel)]
 limits=[(-.3,.3),(.25,4),(.25,4),(.25,2)]
 if not all(lo<=v<=hi for v,(lo,hi) in zip(values,limits)):raise ValueError('Suspension values outside supported ranges')
 return [int(args.auto_fit),*values]

def tune_package(folder,args):
 # Reuse the normal installer for its stopped-game check, backup and atomic package swap.
 folder=Path(folder).resolve();report=json.loads((folder/'conversion.json').read_text())
 with tempfile.TemporaryDirectory(prefix='revc-tune-') as tmp:
  stage=Path(tmp)/folder.name;shutil.copytree(folder,stage,ignore=shutil.ignore_patterns('work'))
  row=next(v for v in car_rows_from_file(stage/'data/default.ide') if v[1]==report['name'])
  row=row[:13]+list(map(str,suspension(args)));(stage/'data/default.ide').write_text('cars\n'+', '.join(row)+'\nend\n')
  report['suspension']=dict(zip(('autoFit','rideHeightMeters','stiffness','damping','travel'),suspension(args)))
  report['dataHashes']={str(p.relative_to(stage)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (stage/'data').rglob('*') if p.is_file()}
  (stage/'conversion.json').write_text(json.dumps(report,indent=2)+'\n')
  install(stage,Path(args.runtime).resolve())

def car_rows_from_file(path):
 return [[v.strip() for v in line.split(',')] for line in path.read_text().splitlines() if ',' in line and line.split(',')[0].strip().isdigit()]

def convert(args):
 from resource_input import prepare
 from vc_export import export,donor_collision
 from handling_fit import fit_handling
 from asset_preview import render
 if not 1<=args.frequency<=30:raise ValueError('Traffic frequency must be between 1 and 30')
 from paint_options import resolve_runtime,parse_colors
 runtime=resolve_runtime(args.runtime);paint_colors=parse_colors(args.paint);rows=car_rows(runtime);donors={v[1]:v for v in rows.values()};donor=args.replace if args.mode=='replace' else args.donor
 if donor not in donors:raise ValueError('Unknown existing VC donor/target: '+str(donor))
 row=donors[donor].copy();name=donor if args.mode=='replace' else re.sub(r'[^a-z0-9_]','_',args.name.lower().strip()).strip('_')
 if not name or len(name)>19:raise ValueError('Choose a car name of 1 to 19 letters/digits/underscores')
 if args.mode=='add' and name in donors:raise ValueError('This name already exists; choose another name or use Replace mode')
 if args.mode=='add':
  taken=occupied_ids(runtime);model_id=next((i for i in range(6000,6500) if i not in taken),None)
  if model_id is None:raise ValueError('No unused model ID remains in the 6000-6499 add-on range')
 else:model_id=int(row[0])
 folder=Path(args.output or ROOT/'exports'/name).expanduser().resolve()
 # A fresh work folder prevents old textures or stale geometry from masking missing inputs.
 source=Path(args.source).expanduser().resolve()
 if source.is_relative_to(folder/'work'):raise ValueError('Source is inside the output work folder. Copy it elsewhere before converting.')
 folder.mkdir(parents=True,exist_ok=True);work=folder/'work'
 if work.exists():shutil.rmtree(work)
 work.mkdir();source=Path(args.source).expanduser().resolve();manifest=prepare(source,work/'game',ROOT/'cache'/(hashlib.sha256(str(source).encode()).hexdigest()[:16]+'.json'),args.entry,args.model)
 exe=setup();env=dict(os.environ,DOTNET_ROLL_FORWARD='Major');run(['dotnet',exe,'--extract-vehicles',work/'game',work/'gltf',work/'gltf/textures','textures/','inputcar'],env=env)
 gltf=work/'gltf/inputcar.gltf'
 if not gltf.exists():raise ValueError('The source parser could not export this car. Check the extraction error above.')
 report=export(gltf,folder,name,args.livery,paint_colors);
 unknown=set(paint_colors)-set(report['detectedPaintChannels'])
 if unknown:raise ValueError('No detected paint channels: '+str(sorted(unknown)))
 donor_collision(runtime,donor,name,folder,report)
 report['handlingFit']=fit_handling(runtime,row,report,folder,name)
 row[0]=str(model_id);row[1]=row[2]=name;row[5]=('CV'+str(model_id)) if args.mode=='add' else row[5];row=row[:13];row[10]=format(report.get('componentRules',0),'x');row[11]='-1';row[12]=str(report['wheelDiameter']);row[7]=row[7] if args.traffic else 'ignore';row[8]=str(max(1,args.frequency));row+=list(map(str,suspension(args)));data=folder/'data';data.mkdir(exist_ok=True);(data/'default.ide').write_text('cars\n'+', '.join(row)+'\nend\n')
 # Preserve donor colour palette; no global colour table is replaced.
 colors=None
 for line in (runtime/'data/carcols.dat').read_text(errors='replace').splitlines():
  parts=[v.strip() for v in line.split(',')]
  if parts[0].lower()==donor:colors=parts[1:];break
 if not colors:colors=['0','0','1','1','2','2','3','3']
 (data/'carcols.dat').write_text('car\n'+name+', '+', '.join(colors)+'\nend\n')
 report.update(mode=args.mode,modelId=model_id,donor=donor,traffic=args.traffic,frequency=args.frequency,sourceManifest=manifest,nativeValidated=False,suspension=dict(zip(('autoFit','rideHeightMeters','stiffness','damping','travel'),suspension(args))),collision='Stock '+donor+' shapes fitted to imported body bounds and tyre clearance; not authored IV collision')
 (folder/'conversion.json').write_text(json.dumps(report,indent=2)+'\n');render(folder,name,report['textureSources'],folder/'preview.png');validate(folder,name,report['wheelDiameter']);report['nativeValidated']=True;report['dataHashes']={str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in data.rglob('*') if p.is_file()};report['assetHashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [folder/(name+s) for s in ('.dff','.txd','.col')]};(folder/'conversion.json').write_text(json.dumps(report,indent=2)+'\n')
 readme=f'''# Converted {name}\n\nMode: {args.mode}. Model ID: {model_id}. Handling/collision donor: {donor}. Traffic: {args.traffic}, frequency {args.frequency}. Native model/texture streaming and wheel hierarchy validated on Metal.\n\nThe preview is an offline asset rendering, not a game screenshot. Verify appearance, collisions, driving and performance in game. Four- and six-wheel IV RSC5 rigid-car importer; other formats and blended rigs are rejected. Authored extras are detected automatically and kept optional; source combinations unavailable in the asset use a conservative single-extra policy to avoid overlapping roofs. Primary/secondary paint selectors and fixed interior textures are converted automatically, and glass uses separate transparent geometry. No separately authored damage variants. Existing donor collision shapes are fitted to the body and tyre ground clearance. Suspension auto-fit uses authored wheel centres; use the converter ride-height, spring, damping and travel controls to tune it. Original donor car stays intact in Add mode.\n\nSource: {manifest['source']}\nEmbedded source: {manifest.get('embeddedName',[])}\n\nAuthor credits belong to the source pack. Do not redistribute source assets without the authors' permission.\n''';(folder/'README.md').write_text(readme)
 for credit in ('SOURCES & CREDITS.txt','readme.txt','AUTHOR_README.txt'):
  for parent in [source.parent,*list(source.parents)[:5]]:
   p=parent/credit
   if p.exists():shutil.copy2(p,folder/('SOURCE_'+credit));break
 if args.install:install(folder,runtime)
 from conversion_audit import summary
 print(summary(report),flush=True)
 print('Conversion ready:',folder,flush=True);return folder

def main():
 parser=argparse.ArgumentParser(description='Convert IV/NextGen WFT/WTD cars for native Vice City; Add a named car or replace a selected model.')
 parser.add_argument('--paint',action='append',default=[],help='Conversion-time paint override CHANNEL=#RRGGBB; repeat for detected channels');parser.add_argument('--recolor-package');parser.add_argument('--livery',default=None,help='Authored livery key, source, or none for plain body paint');parser.add_argument('--extract-all',action='store_true');parser.add_argument('--source');parser.add_argument('--entry',type=int);parser.add_argument('--model');parser.add_argument('--list',action='store_true');parser.add_argument('--mode',choices=['add','replace'],default='add');parser.add_argument('--name',default='custom_car');parser.add_argument('--donor',default='rancher');parser.add_argument('--replace',default='rancher');parser.add_argument('--runtime',default=str(DEFAULT_RUNTIME));parser.add_argument('--output');parser.add_argument('--frequency',type=int,default=5);parser.add_argument('--no-traffic',dest='traffic',action='store_false');parser.add_argument('--install',action='store_true');parser.add_argument('--install-package');parser.add_argument('--ride-height',type=float,default=0,help='Chassis ride-height offset in cm; negative lowers');parser.add_argument('--stiffness',type=float,default=1);parser.add_argument('--damping',type=float,default=1);parser.add_argument('--travel',type=float,default=1);parser.add_argument('--no-auto-fit',dest='auto_fit',action='store_false');parser.add_argument('--tune-package');args=parser.parse_args()
 from paint_options import resolve_runtime,parse_colors,recolor
 if args.recolor_package:
  from asset_preview import render
  recolor(Path(args.recolor_package),parse_colors(args.paint),validate,render);return
 if args.tune_package:
  args.runtime=str(resolve_runtime(args.runtime));tune_package(args.tune_package,args);return
 if args.install_package:install(Path(args.install_package).resolve(),resolve_runtime(args.runtime));return
 if not args.source:
  from gui import start
  start();return
 if args.extract_all:
  from extract_archive import extract_archive
  source=Path(args.source).expanduser().resolve();archives=sorted(source.rglob('*.img')) if source.is_dir() else [source]
  archives=[p for p in archives if p.name.lower()=='vehicles.img']
  if not archives:raise ValueError('No vehicles.img archives found')
  base=Path(args.output or ROOT/'extracted-packs').expanduser().resolve();summaries=[]
  for archive in archives:
   edition=archive.parents[3].name;dest=base/edition if len(archives)>1 or not args.output else base
   report=extract_archive(archive,dest,ROOT/'cache'/(hashlib.sha256(str(archive).encode()).hexdigest()[:16]+'.json'));summaries.append({'folder':str(dest),'models':report['modelCount'],'textureDictionaries':report['textureDictionaryCount'],'sourceSha256':report['sourceArchiveSha256']});print(json.dumps(summaries[-1]),flush=True)
  return
 if args.list:
  from resource_input import scan,models
  source=Path(args.source).expanduser().resolve()
  if source.is_dir():
   files=list(source.rglob('vehicles.img'))
   if len(files)!=1:raise ValueError('Select an exact archive or edition folder')
   source=files[0]
  entries,_,_=scan(source,ROOT/'cache'/(hashlib.sha256(str(source).encode()).hexdigest()[:16]+'.json'));print(json.dumps(models(entries),indent=2));return
 convert(args)

if __name__=='__main__':
 try:main()
 except (ValueError,RuntimeError,subprocess.CalledProcessError) as error:print('ERROR:',error,file=sys.stderr);sys.exit(1)
