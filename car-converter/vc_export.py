"""IV rigid vehicle -> VC native hierarchy/DFF/TXD. No Blender or GTA IV install."""
from pathlib import Path
import sys,struct,json,math,collections,hashlib
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'DragonFF'))
from gtaLib import dff as rw,txd,col
import numpy as np
from material_policy import classify
from paint_options import material_color

IDENTITY=rw.Matrix(rw.Vector(1,0,0),rw.Vector(0,1,0),rw.Vector(0,0,1))
def _native_texture(path,texname):
 data=path.read_bytes()
 if data[:4]==b'DDS ':
  if len(data)<128:raise ValueError(f'Truncated DDS header: {path.name}')
  h,w=struct.unpack_from('<II',data,12);levels=max(1,struct.unpack_from('<I',data,28)[0]);fourcc=data[84:88]
 elif data.startswith(b'\x89PNG\r\n\x1a\n'):
  from PIL import Image
  with Image.open(path) as image:w,h=image.size
  levels=1;fourcc=b''
 else:raise ValueError(f'Unsupported texture image: {path.name}; expected DDS or PNG')
 tex=txd.TextureNative();tex.platform_id=rw.NativePlatformType.D3D8;tex.name=texname;tex.filter_mode=6;tex.uv_addressing=0x11;tex.width=w;tex.height=h;tex.num_levels=levels;tex.raster_type=4;tex.raster_format_flags=0x500|(0x8000 if levels>1 else 0);tex.d3d_format=1;posn=128
 if fourcc in (b'DXT1',b'DXT3',b'DXT5'):
  tex.depth=16;tex.d3d_format=1 if fourcc!=b'DXT1' else 0;tex.platform_properties=SimpleNamespace(dxt_type=int(chr(fourcc[3])))
  for level in range(levels):
   size=max(1,(w+3)//4)*max(1,(h+3)//4)*(8 if fourcc==b'DXT1' else 16)
   if len(data)-posn<size:raise ValueError(f'Truncated DDS texture {path.name}, mip {level} ({w}x{h}): expected {size} bytes, found {max(0,len(data)-posn)}. Re-extract with the updated extractor.')
   tex.pixels.append(data[posn:posn+size]);posn+=size;w=max(1,w//2);h=max(1,h//2)
 else:
  from PIL import Image
  image=Image.open(path).convert('RGBA');tex.depth=32;tex.num_levels=1;tex.raster_format_flags=0x500;tex.platform_properties=SimpleNamespace(dxt_type=0);tex.pixels=[image.tobytes('raw','BGRA')]
 return tex

def native_texture(path,texname):
 try:return _native_texture(path,texname)
 except (OSError,struct.error) as error:raise ValueError(f'Cannot decode texture {path.name}: {error}') from error

def export(gltf_path,out,name,livery=None,paint_colors=None):
 d=json.loads(gltf_path.read_text());blob=(gltf_path.parent/d['buffers'][0]['uri']).read_bytes();nodes=d['nodes'];boneids=d['skins'][0]['joints'];bonecount=len(boneids);parents={ch:i for i,n in enumerate(nodes) for ch in n.get('children',[])};nameids={nodes[i]['name']:i for i in boneids}
 def acc(i):
  a=d['accessors'][i];v=d['bufferViews'][a['bufferView']];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];fmt={5121:'B',5123:'H',5125:'I',5126:'f'}[a['componentType']];size=struct.calcsize(fmt)*n;off=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',size)
  return [struct.unpack_from('<'+fmt*n,blob,off+j*stride) for j in range(a['count'])]
 C=np.array([[1,0,0],[0,0,-1],[0,1,0]])
 def vc(v):return tuple(C@np.asarray(v))
 worlds={}
 def world(i):
  if i in worlds:return worlds[i]
  n=nodes[i];x,y,z,w=n.get('rotation',[0,0,0,1]);m=np.eye(4);m[:3,:3]=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]];m[:3,3]=n.get('translation',[0,0,0]);p=parents.get(i)
  if p in boneids:m=world(p)@m
  worlds[i]=m;return m
 def pos(i):return vc(world(i)[:3,3])
 model=rw.dff();clump=rw.Clump();model.clumps=[clump];frames={};pivots={}
 def frame(label,parent=-1,pivot=(0,0,0)):
  if len(label)>23:raise ValueError('VC node name exceeds 23 bytes: '+label)
  f=rw.Frame();f.name=label;f.parent=parent;f.position=rw.Vector(*pivot);f.rotation_matrix=IDENTITY;clump.frame_list.append(f);frames[label]=len(clump.frame_list)-1;pivots[label]=np.array(pivot);return frames[label]
 root=frame(name);chassis=frame('chassis_dummy',root)
 mapping={'chassis':'chassis_dummy','bodyshell':'chassis_dummy','door_dside_f':'door_lf_dummy','door_dside_r':'door_lr_dummy','door_pside_f':'door_rf_dummy','door_pside_r':'door_rr_dummy','bonnet':'bonnet_dummy','boot':'boot_dummy','bumper_f':'bump_front_dummy','bumper_r':'bump_rear_dummy','wing_lf':'wing_lf_dummy','wing_rf':'wing_rf_dummy','windscreen':'windscreen_dummy'}
 for bone in nameids:
  if bone.startswith('extra_') and bone[6:].isdigit() and 1<=int(bone[6:])<=9:
   label='extra'+bone[6:];frame(label,chassis,pos(nameids[bone]));mapping[bone]=label
 if name=='rhino':mapping['windscreen']='chassis_dummy';mapping['misc_a']='windscreen_dummy'
 for bone,target in list(mapping.items()):
  if bone in nameids and target!='chassis_dummy' and target not in frames:frame(target,chassis,pos(nameids[bone]))
 for suffix,native in [('lf','lf'),('lr','lb'),('rf','rf'),('rr','rb'),('lm','lm'),('rm','rm')]:
  wheel='wheel_'+suffix
  if wheel not in nameids:
   if suffix in ('lm','rm'):continue
   raise ValueError('This importer needs a four-wheel car: missing '+wheel)
  target='wheel_'+native+'_dummy';frame(target,root,pos(nameids[wheel]));mapping[wheel]=target
  hub='hub_'+suffix
  if hub in nameids:frame('iv_'+hub,chassis,pos(nameids[wheel]));mapping[hub]='iv_'+hub
  arm='suspension_'+suffix
  if arm in nameids:frame('iv_'+arm,chassis,pos(nameids[arm]));mapping[arm]='iv_'+arm
 for bone in ('transmission_f','transmission_r','transmission_m'):
  if bone in nameids:frame('iv_'+bone,chassis,pos(nameids[bone]));mapping[bone]='iv_'+bone
 # Optional panels authored under an animated bonnet/door must keep that parent.
 # Bake them in the parent component's coordinates so native selected extras can
 # share that frame, including hinge damage and component visibility transitions.
 extraParents={}
 for bone,target in list(mapping.items()):
  if not bone.startswith('extra_'):continue
  parent=parents.get(nameids[bone]);native=None
  while parent in boneids:
   candidate=mapping.get(nodes[parent]['name'])
   if candidate in frames and candidate!=target:
    native=candidate;break
   parent=parents.get(parent)
  if native and native not in ('chassis_dummy',) and not native.startswith(('wheel_','iv_','extra')):
   f=clump.frame_list[frames[target]];f.parent=frames[native];f.position=rw.Vector(0,0,0)
   pivots[target]=pivots[native].copy();extraParents[target]=native
 for target,bones in [('ped_frontseat',['seat_pside_f','seat_dside_f']),('ped_backseat',['seat_pside_r','seat_dside_r']),('headlights',['headlight_r','headlight_l']),('taillights',['taillight_r','taillight_l']),('exhaust',['exhaust','exhaust_2'])]:
  bone=next((b for b in bones if b in nameids),None)
  if bone:frame(target,root,pos(nameids[bone]))
 wheel_instances=[]
 for index,node in enumerate(nodes):
  if 'mesh' in node and 'skin' not in node:
   parent=parents.get(index)
   if parent not in boneids or not nodes[parent]['name'].startswith('wheel_'):
    raise ValueError('Non-wheel fragment geometry needs a separate component importer: '+node['name'])
 for n in nodes:
  if 'mesh' in n and 'skin' not in n:
   idx=nodes.index(n);parent=parents.get(idx)
   if parent in boneids and nodes[parent]['name'].startswith('wheel_'):wheel_instances.append((nodes[parent]['name'],n['mesh']))
 if not wheel_instances:raise ValueError('No wheel fragment geometry found; integrated-wheel source needs an additional importer path')
 wheel_meshes=dict(wheel_instances);frontmesh=wheel_meshes.get('wheel_lf',wheel_instances[0][1]);pts=[v for p in d['meshes'][frontmesh]['primitives'] for v in acc(p['attributes']['POSITION'])];diameter=max(v[1] for v in pts)-min(v[1] for v in pts)
 if not .12<diameter<2.5:raise ValueError('Implausible wheel diameter '+str(diameter))
 # RAGE paint3 keeps its livery in DiffuseSampler2, not the primary specular mask.
 # Retain both UV sets and inspect the authored alpha to distinguish baked finishes from overlays.
 from PIL import Image
 for source in d['materials']:
  e=source.get('extras',{});layer=e.get('shaderTextures',{}).get('05645204')
  if livery=='none' or not e.get('paint') or not layer or not layer.get('texture'):continue
  if livery and livery!='source':
   variants=e.get('liveryVariants',{});wanted=''.join(ch for ch in livery.lower() if ch.isalnum())
   if wanted not in variants:raise ValueError('Unknown livery '+livery+'; available: '+', '.join(variants))
   layer=variants[wanted]
  path=gltf_path.parent/layer['texture']
  if not path.exists():raise ValueError('Missing authored livery: '+str(path))
  with Image.open(path) as im:amin,amax=im.convert('RGBA').getchannel('A').getextrema()
  if amax==0:continue
  e.update(texture=layer['texture'],textureName=layer['name'],liveryMode='fixed' if amin==255 else 'decal',liveryUV=1)
 materials=[];textures={};texnames={};missing=[];paint_materials=[];paint_colors=paint_colors or {}
 for source in d['materials']:
  e=source.get('extras',{});policy=classify(e);shader=e.get('shader','');paint=policy['slot']>0;glass=policy['glass'];m=rw.Material();m.flags=0;m.surface_properties=rw.GeomSurfPro(1,policy['specular'],1);m.is_textured=0
  m.color=rw.RGBA(*(material_color(paint_colors[policy['slot']]) if policy['slot'] in paint_colors else policy['color']))
  if policy['slot']:paint_materials.append(dict(index=len(materials),channel=policy['slot'],sourceMaterial=source['name'],defaultColor=list(policy['color'])))
  if policy['textured']:
   path=gltf_path.parent/e['texture'] if e.get('texture') else None
   if path and path.exists():
    key=e['textureName'].lower();key=('ivd_'+key) if e.get('liveryMode')=='decal' else key;texname=key if len(key)<=31 and '/' not in key else key.split('/')[-1][:23]+'_'+hashlib.sha256(key.encode()).hexdigest()[:7]
    if texname in texnames and texnames[texname]!=key:raise ValueError('Texture name collision')
    texnames[texname]=key;textures[texname]=path;t=rw.Texture();t.name=texname;t.filters=6;t.uv_addressing=0x11;m.textures=[t];m.is_textured=1
   else:missing.append(e['textureName'])
  materials.append(m)
 if missing:raise ValueError('Missing diffuse textures: '+', '.join(sorted(set(missing))))
 def targetbone(i):
  while True:
   bone=nodes[i]['name'];target=mapping.get(bone)
   if target in frames:return target
   p=parents.get(i)
   if p not in boneids:return 'chassis_dummy'
   i=p
 buckets=collections.defaultdict(list);mixed=0;weighted=0
 body=next(n for n in nodes if n.get('skin')==0 and 'mesh' in n)
 for p in d['meshes'][body['mesh']]['primitives']:
  if d['materials'][p['material']].get('extras',{}).get('omitMissingDecal'):continue
  a=p['attributes'];v=acc(a['POSITION']);norm=acc(a['NORMAL']);uv=acc(a.get('TEXCOORD_1',a['TEXCOORD_0']) if d['materials'][p['material']].get('extras',{}).get('liveryUV') else a['TEXCOORD_0']);j=acc(a['JOINTS_0']);w=acc(a['WEIGHTS_0']);ind=[t[0] for t in acc(p['indices'])];assigned=[]
  for joints,weights in zip(j,w):
   weighted+=sum(x>0 for x in weights)>1;assigned.append(targetbone(boneids[joints[max(range(4),key=lambda k:weights[k])]]))
  for offset in range(0,len(ind),3):
   ids=ind[offset:offset+3];targets=[assigned[i] for i in ids];target=collections.Counter(targets).most_common(1)[0][0];mixed+=len(set(targets))>1;wheel=target.startswith('wheel_');verts=[]
   for i in ids:
    point=np.asarray(vc(v[i]))-pivots[target];normal=np.asarray(vc(norm[i]))
    if wheel:
     point/=diameter
     if '_l' in target:point[:2]*=-1;normal[:2]*=-1
    verts.append((tuple(point),tuple(normal),tuple(uv[i])))
   buckets[target].append((p['material'],verts))
 if weighted:raise ValueError('Source has blended deforming vertices; this rigid-car importer cannot preserve them safely')
 if mixed:raise ValueError('Source has triangles spanning moving joints; panel separation needs manual authoring')
 # Main-drawable rims/brakes can accompany a tyre fragment. Some converted
 # sources reuse left-facing rigid geometry on the right bone. Detect that
 # against its actual left counterpart rather than flipping already mirrored parts.
 wheelBodyMirrors=[]
 def body_signature(tris,left=False,mirror=False):
  result=set()
  for _,tri in tris:
   for v,n,uv in tri:
    x,y,z=v;nx,ny,nz=n
    if left:x,y,nx,ny=-x,-y,-nx,-ny
    if mirror:x,nx=-x,-nx
    result.add(tuple(round(a,3) for a in (x,y,z,nx,ny,nz,*uv)))
  return result
 for left,right in [('lf','rf'),('lb','rb'),('lm','rm')]:
  l='wheel_'+left+'_dummy';r='wheel_'+right+'_dummy'
  if not buckets.get(l) or not buckets.get(r):continue
  same=body_signature(buckets[l],left=True);mirrored=body_signature(buckets[l],left=True,mirror=True);actual=body_signature(buckets[r])
  sameScore=len(same & actual)/max(1,len(same));mirrorScore=len(mirrored & actual)/max(1,len(mirrored))
  if sameScore>.7 and sameScore>mirrorScore+.1:
   fixed=[]
   for material,tri in buckets[r]:
    vertices=[((-v[0],v[1],v[2]),(-n[0],n[1],n[2]),uv) for v,n,uv in tri];vertices[1],vertices[2]=vertices[2],vertices[1];fixed.append((material,vertices))
   buckets[r]=fixed;wheelBodyMirrors.append(dict(frame=r,sameSideScore=sameScore,alreadyMirroredScore=mirrorScore))
 for suffix,native in [('lf','lf'),('lr','lb'),('rf','rf'),('rr','rb'),('lm','lm'),('rm','rm')]:
  target='wheel_'+native+'_dummy'
  if target not in frames:continue
  mesh=wheel_meshes.get('wheel_'+suffix,frontmesh)
  for p in d['meshes'][mesh]['primitives']:
   a=p['attributes'];v=acc(a['POSITION']);normal=acc(a['NORMAL']);uv=acc(a['TEXCOORD_0']);ind=[t[0] for t in acc(p['indices'])]
   for offset in range(0,len(ind),3):
    verts=[]
    for i in ind[offset:offset+3]:
     point=np.asarray(vc(v[i]))/diameter;n=np.asarray(vc(normal[i]))
     if suffix.startswith('l'):point[:2]*=-1;n[:2]*=-1
     else:point[0]*=-1;n[0]*=-1
     verts.append((tuple(point),tuple(n),tuple(uv[i])))
    if suffix.startswith('r'):verts[1],verts[2]=verts[2],verts[1]
    buckets[target].append((p['material'],verts))
 # Identify long longitudinal suspension leaves from the authored part bounds.
 leafparts=[]
 for target in list(buckets):
  if not target.startswith('iv_suspension_'):continue
  pts=np.array([v for _,tri in buckets[target] for v,_,_ in tri]);span=np.ptp(pts,axis=0)
  if span[1]>.55 and span[1]>2*max(span[0],span[2]):
   label=target.replace('iv_suspension_','iv_leaf_');fi=frames.pop(target);frames[label]=fi;clump.frame_list[fi].name=label;pivots[label]=pivots.pop(target);buckets[label]=buckets.pop(target);leafparts.append(label)
 drawgroups=[]
 for target,tris in buckets.items():
  if target.startswith(('wheel_','iv_','extra')):drawgroups.append((target,False,tris));continue
  for transparent in (False,True):
   group=[t for t in tris if (materials[t[0]].color.a<250)==transparent]
   if group:drawgroups.append((target,transparent,group))
 for target,transparent,tris in drawgroups:
  g=rw.Geometry();g.surface_properties=rw.GeomSurfPro(1,0,1);g.uv_layers=[[]];g.has_vertices=1;g.has_normals=1;used=sorted({mi for mi,_ in tris});local={m:i for i,m in enumerate(used)};g.materials=[materials[m] for m in used];lookup={}
  for mi,verts in tris:
   ids=[]
   for v,n,uv in verts:
    if not all(math.isfinite(x) for x in (*v,*n,*uv)):raise ValueError('Non-finite vertex attributes')
    key=(v,n,uv)
    if key not in lookup:lookup[key]=len(g.vertices);g.vertices.append(rw.Vector(*v));g.normals.append(rw.Vector(*n));g.uv_layers[0].append(rw.TexCoords(*uv))
    ids.append(lookup[key])
   g.triangles.append(rw.Triangle(ids[1],ids[0],local[mi],ids[2]))
  if len(g.vertices)>=65536:raise ValueError('One component exceeds VC 16-bit mesh index capacity')
  g.bounding_sphere=rw.Sphere(0,0,0,max(math.sqrt(sum(x*x for x in v)) for v in g.vertices));fi=frames[target] if target.startswith(('wheel_','iv_','extra')) else frame(target.replace('_dummy','')+('_hi_ok_g' if transparent else '_hi_ok'),frames[target]);a=rw.Atomic();a.frame=fi;a.geometry=len(clump.geometry_list);a.flags=5;a.unk=0;a.extensions={};clump.atomic_list.append(a);clump.geometry_list.append(g)
 if not buckets or not any(g.triangles for g in clump.geometry_list):raise ValueError('No triangles exported; source topology is unsupported')
 # RenderWare reads frames in order and requires the parent to exist first.
 order=[];remaining=set(range(len(clump.frame_list)))
 while remaining:
  ready=[i for i in sorted(remaining) if clump.frame_list[i].parent<0 or clump.frame_list[i].parent in order]
  if not ready:raise ValueError('Cycle in converted component hierarchy')
  order.extend(ready);remaining.difference_update(ready)
 remap={old:new for new,old in enumerate(order)};clump.frame_list=[clump.frame_list[i] for i in order]
 for i,f in enumerate(clump.frame_list):
  f.parent=remap.get(f.parent,-1);assert f.parent<i
 for atomic in clump.atomic_list:atomic.frame=remap[atomic.frame]
 out.mkdir(parents=True,exist_ok=True);model.write_file(str(out/(name+'.dff')),0x33002)
 dictionary=txd.txd();dictionary.device_id=0
 for texname,path in textures.items():dictionary.native_textures.append(native_texture(path,texname))
 dictionary.write_file(str(out/(name+'.txd')),0x33002)
 reread=rw.dff();reread.load_file(str(out/(name+'.dff')));t=txd.txd();t.load_file(str(out/(name+'.txd')));assert len(reread.clumps[0].atomic_list)==len(drawgroups);assert len(t.native_textures)==len(textures)
 bodypoints=np.array([np.array(v)+pivots[target] for target,tris in buckets.items() if not target.startswith('wheel_') for _,verts in tris for v,_,_ in verts]);bounds=[bodypoints.min(axis=0).tolist(),bodypoints.max(axis=0).tolist()]
 nativeExtras=sorted(k for k in buckets if k.startswith('extra'))
 requiredBonnet=[nativeExtras.index(k) for k,v in extraParents.items() if v=='bonnet_dummy' and k in nativeExtras]
 rules=0
 if requiredBonnet:
  selected=requiredBonnet[:3];comps=sum(v<<(4*i) for i,v in enumerate(selected))
  for i in range(len(selected),3):comps|=15<<(4*i)
  rules=0x3fff0000|0x1000|comps
 paint_locations=[]
 for gi,g in enumerate(clump.geometry_list):
  for mi,m in enumerate(g.materials):
   for source in paint_materials:
    if m is materials[source['index']]:paint_locations.append(dict(geometry=gi,material=mi,channel=source['channel'],defaultColor=source['defaultColor']))
 return dict(paintMaterialLocations=paint_locations,name=name,rigVersion=3,extrasVersion=2,componentRules=rules,sourceExtraParents=extraParents,extrasPolicy='Automatically detected authored optional parts; select at most one when source combination rules are unavailable, preventing overlapping roofs',sourceExtraMap={bone:target for bone,target in mapping.items() if bone.startswith('extra_') and target in buckets},materialPolicyVersion=3,paintMaterials=paint_materials,detectedPaintChannels=sorted({m["channel"] for m in paint_materials}),paintColors={str(k):list(v) for k,v in paint_colors.items()},liverySelection=livery or 'source',liveryLayers=[dict(material=m['name'],mode=m.get('extras',{}).get('liveryMode'),texture=m.get('extras',{}).get('textureName')) for m in d['materials'] if m.get('extras',{}).get('liveryMode')],wheelBodyMirrors=wheelBodyMirrors,wheelFragmentMaterials={side:len(d['meshes'][wheel_meshes.get('wheel_'+suffix,frontmesh)]['primitives']) for suffix,side in [('lf','lf'),('lr','lb'),('rf','rf'),('rr','rb'),('lm','lm'),('rm','rm')] if 'wheel_'+side+'_dummy' in frames},glassAtomics=sum(int(transparent) for _,transparent,_ in drawgroups),optionalExtras=[k for k in buckets if k.startswith('extra')],paintChannels=[{'material':m['name'],'shaderDiffuse':m.get('extras',{}).get('shaderVectors',{}).get('185f047c')} for m in d['materials'] if m.get('extras',{}).get('paint')],rigParts={k:len(v) for k,v in buckets.items() if k.startswith('iv_')},leafClassification='Longitudinal suspension mesh aspect ratio; authored geometry only',bodyBounds=bounds,wheelCenters=[pivots['wheel_'+side+'_dummy'].tolist() for side in ('lf','lb','rf','rb')],wheelDiameter=diameter,textureCount=len(textures),textureSources={k:str(v.resolve()) for k,v in textures.items()},parts={k:len(v) for k,v in buckets.items()},vertices=sum(len(g.vertices) for g in clump.geometry_list),sourceBones=bonecount,limitations=['Four/six-wheel rigid RSC5 car importer; not YFT/YTD, bikes, boats or deforming rigs; native middle wheels share rear suspension contact physics','No authored damaged-part variants; native LocalDent handles deformation','Gameplay appearance and performance require an in-game check'])

def donor_collision(runtime,donor,name,out,report=None):
 c=col.coll();c.load_file(str(runtime/'models/coll/vehicles.col'));model=next((m for m in c.models if m.model_name.lower()==donor.lower()),None)
 if model is None:raise ValueError('No stock collision model for donor '+donor)
 if report and report.get('bodyBounds'):
  oldmin=np.array(model.bounds.min);oldmax=np.array(model.bounds.max)
  lo,hi=map(lambda v:np.array(v,dtype=float),report['bodyBounds'])
  # The invisible donor chassis must not touch the road before the imported tyres.
  floor=max(w[2]-report['wheelDiameter']/2 for w in report['wheelCenters'])+.06
  lo[2]=max(lo[2],floor)
  if np.any(hi-lo < .1):raise ValueError('Invalid collision fitting bounds')
  scale=(hi-lo)/(oldmax-oldmin)
  def point(v):return col.TVertex(*(lo+(np.array(v)-oldmin)*scale))
  model.spheres=[sphere._replace(center=point(sphere.center),radius=sphere.radius*float(min(scale))) for sphere in model.spheres]
  model.boxes=[box._replace(min=point(box.min),max=point(box.max)) for box in model.boxes]
  model.mesh_verts=[point(v) for v in model.mesh_verts]
  center=(lo+hi)/2;model.bounds=model.bounds._replace(min=col.TVertex(*lo),max=col.TVertex(*hi),center=col.TVertex(*center),radius=float(np.linalg.norm((hi-lo)/2)))
  report['collisionFit']={'bounds':[lo.tolist(),hi.tolist()],'tyreClearance':.06,'scale':scale.tolist()}
 model.model_name=name;model.model_id=0;one=col.coll(model);one.write_file(str(out/(name+'.col')));test=col.coll();test.load_file(str(out/(name+'.col')));assert len(test.models)==1 and test.models[0].model_name==name
