"""Recover unencrypted RSC5 payloads from a loose WFT or an encrypted-directory IMG.
No game executable or decryption key is used. Original archive slot names are unknown.
"""
from pathlib import Path
import struct,zlib,re,json,math,hashlib

def resource(data):
 if data[:4]!=b'RSC\5':raise ValueError('Expected GTA IV RSC5 resource (WFT/WTD); other formats need another importer')
 typ,flags=struct.unpack_from('<II',data,4);d=zlib.decompressobj(-15);raw=d.decompress(data[14:])
 if not d.eof:raise ValueError('Truncated resource')
 length=len(data)-len(d.unused_data)+4;copy=bytearray(data[:length]);old=struct.unpack_from('>I',copy,length-4)[0];checksum=zlib.adler32(raw)&0xffffffff;struct.pack_into('>I',copy,length-4,checksum)
 names=[v.decode(errors='replace') for v in re.findall(rb'pack:/([^\x00]{1,110})\x00',raw)]
 return dict(typ=typ,flags=flags,length=length,names=names,checksumRepaired=old!=checksum,data=bytes(copy))

def scan(path,cache):
 blob=path.read_bytes();sha=hashlib.sha256(blob).hexdigest()
 if cache.exists():
  saved=json.loads(cache.read_text())
  if saved['sha256']==sha:return saved['entries'],blob,sha
 starts=[i for i in range(0,len(blob),2048) if blob[i:i+4]==b'RSC\5'];entries=[]
 for o in starts:
  e=resource(blob[o:]);e.pop('data');e['offset']=o;e['index']=len(entries);entries.append(e)
 if not entries:raise ValueError('No readable RSC5 resources in this archive')
 cache.parent.mkdir(parents=True,exist_ok=True);cache.write_text(json.dumps(dict(sha256=sha,entries=entries),indent=2));return entries,blob,sha

def models(entries):
 return [dict(index=e['index'],name=e['names'][0] if e['names'] else '?',textureHints=entries[i+1]['names'][:5] if i+1<len(entries) and entries[i+1]['typ']==8 else []) for i,e in enumerate(entries) if e['typ']==112]

def write_img(game,items):
 names=b''.join(name.encode()+b'\0' for name in items);toc=len(items)*16+len(names);offset=math.ceil((20+toc)/2048)*2048;table=[];blocks=[]
 for name,e in items.items():
  data=e['data'];used=math.ceil(len(data)/2048);pad=used*2048-len(data);table.append(struct.pack('<IIIhh',e['flags'],e['typ'],offset//2048,used,pad|0x2000));blocks.append(data+b'\0'*pad);offset+=used*2048
 header=struct.pack('<IIIIhh',0xA94E2A52,3,len(items),toc,16,0)+b''.join(table)+names;header+=b'\0'*(-len(header)%2048);dest=game/'pc/models/cdimages/vehicles.img';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(header+b''.join(blocks))

def prepare(source,game,cache,entry=None,model=None):
 if source.is_dir():
  files=list(source.rglob('vehicles.img'))
  if len(files)!=1:raise ValueError('Choose an edition folder or an exact vehicles.img; multiple/no archives found')
  source=files[0]
 name='inputcar';items={};manifest={'source':str(source),'naming':'Embedded labels, not authenticated original archive slot names.'}
 if source.suffix.lower()=='.wft':
  e=resource(source.read_bytes());assert e['typ']==112;items[name+'.wft']=e;texture=source.with_suffix('.wtd')
  if not texture.exists():raise ValueError('The matching .wtd texture file is required beside the .wft')
  items[name+'.wtd']=resource(texture.read_bytes());manifest['sourceSha256']=hashlib.sha256(source.read_bytes()).hexdigest()
  for p in source.parent.glob('vehshare*.wtd'):items[p.name.lower()]=resource(p.read_bytes())
 else:
  entries,blob,sha=scan(source,cache);choices=models(entries)
  if entry is not None:selected=next((e for e in entries if e['index']==entry and e['typ']==112),None)
  else:
   matches=[e for e in entries if e['typ']==112 and e['names'] and e['names'][0].lower()==(model or '').lower()]
   if len(matches)!=1:raise ValueError('Use --list, then select --entry NUMBER; embedded model names can be duplicated')
   selected=matches[0]
  if not selected:raise ValueError('Selected entry is not a model')
  i=selected['index'];texture=entries[i+1] if i+1<len(entries) else None
  if not texture or texture['typ']!=8:raise ValueError('No adjacent texture dictionary for selected model; provide loose WFT/WTD instead')
  for filename,e in [(name+'.wft',selected),(name+'.wtd',texture)]:items[filename]=resource(blob[e['offset']:e['offset']+e['length']])
  shared=[e for j,e in enumerate(entries) if e['typ']==8 and (j==0 or entries[j-1]['typ']!=112)]
  for n,e in enumerate(shared):
   hints=' '.join(e['names']).lower()
   label='vehshare_truck' if 'vehicle_generic_truck_interior' in hints and len(e['names'])<10 else 'vehshare' if n==0 else 'vehshare2' if n==1 else 'vehshare_extra'
   if label+'.wtd' in items:label+='_'+str(n)
   items[label+'.wtd']=resource(blob[e['offset']:e['offset']+e['length']])
  manifest.update(sourceSha256=sha,entry=i,embeddedName=selected['names'][:1],resourceOffset=selected['offset'])
 write_img(game,items);data=game/'common/data';data.mkdir(parents=True,exist_ok=True)
 (data/'vehicles.ide').write_text('cars\ninputcar, inputcar, car, ADMIRAL, INPUT, VEH@VAN, NULL, 1, 0, 0.36, 0.36, 0, 3, 1.5, 0, ext_gang\nend\n');(data/'carcols.dat').write_text('col\n255,255,255\nend\ncar\ninputcar, 0,0\nend\n');(data/'handling.dat').write_text('')
 manifest['resources']=[dict(name=k,sha256=hashlib.sha256(v['data']).hexdigest(),checksumRepaired=v['checksumRepaired']) for k,v in items.items()];return manifest
