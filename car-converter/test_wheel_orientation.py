"""Check authored left/right rim geometry after native VC rest-frame transforms."""
from pathlib import Path
import sys,collections,json
from vc_export import rw

def signature(geom,left,expected_right=False,min_material=0):
 ids={i for t in geom.triangles if t.material>=min_material for i in (t.a,t.b,t.c)}
 result=collections.defaultdict(list)
 for i,v in enumerate(geom.vertices):
  if i not in ids:continue
  n=geom.normals[i];uv=geom.uv_layers[0][i]
  x,y,z=v;nx,ny,nz=n
  if left:x,y,nx,ny=-x,-y,-nx,-ny
  if expected_right:x,nx=-x,-nx
  result[tuple(round(a,3) for a in uv)].append((x,y,z,nx,ny,nz))
 return result

def check(path):
 report=json.loads((path.parent/'conversion.json').read_text());d=rw.dff();d.load_file(str(path));c=d.clumps[0];geoms={c.frame_list[a.frame].name:c.geometry_list[a.geometry] for a in c.atomic_list}
 for l,r in [('lf','rf'),('lb','rb'),('lm','rm')]:
  left=geoms.get('wheel_'+l+'_dummy');right=geoms.get('wheel_'+r+'_dummy')
  if left is None and right is None:continue
  assert left is not None and right is not None
  minimum=0 if any(m['frame']=='wheel_'+r+'_dummy' for m in report.get('wheelBodyMirrors',[])) else len(left.materials)-report['wheelFragmentMaterials'][l]
  a=signature(left,True,True,minimum);b=signature(right,False,False,minimum)
  assert a.keys()==b.keys(),(path.name,l,r,'rim normals/UV mismatch')
  import numpy as np
  for key in a:
   assert len(a[key])==len(b[key]),(path.name,l,r,'rim vertex count mismatch')
   distances=np.max(np.abs(np.asarray(a[key])[:,None,:]-np.asarray(b[key])[None,:,:]),axis=2)
   assert distances.min(0).max()<1.e-4 and distances.min(1).max()<1.e-4,(path.name,l,r,'rim geometry side mismatch')
  # Mirroring reverses handedness, so right triangle winding must be reversed
  # as well; geometric face normals must agree with the supplied vertex normals.
  for g in (left,right):
   import numpy as np
   scores=[]
   for t in g.triangles:
    v=np.array([g.vertices[i] for i in (t.a,t.b,t.c)]);normal=np.mean([g.normals[i] for i in (t.a,t.b,t.c)],axis=0)
    score=np.dot(np.cross(v[1]-v[0],v[2]-v[0]),normal)
    if abs(score)>1.e-9:scores.append(score>0)
   assert not scores or sum(scores)/len(scores)>.95,(path.name,'wheel faces inverted')
for path in sys.argv[1:]:check(Path(path));print('PASS',Path(path).name)
