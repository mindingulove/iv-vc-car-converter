from pathlib import Path
import sys,json,math
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'DragonFF'))
from gtaLib import dff

def render(folder,name,texture_sources,output,selected_extras=()):
 m=dff.dff();m.load_file(str(folder/(name+'.dff')));c=m.clumps[0];dia=json.loads((folder/'conversion.json').read_text())['wheelDiameter'];textures={}
 for key,p in texture_sources.items():
  try:textures[key]=np.asarray(Image.open(p).convert('RGBA'))/255
  except Exception:pass
 def matrix(i):
  f=c.frame_list[i];r=f.rotation_matrix;a=np.eye(4);a[:3,:3]=np.array([r.right,r.up,r.at]).T;a[:3,3]=f.position
  if f.name.startswith('wheel_'):
   a[:3,:3]*=dia
   if '_l' in f.name:a[:3,:3]=a[:3,:3]@np.diag([-1,-1,1])
  return (matrix(f.parent)@a) if f.parent>=0 else a
 from PIL import ImageDraw
 W,H=720,480
 views=[]
 for az in [-52,128]:
  az=math.radians(az);el=math.radians(21);eye=np.array([math.cos(az)*math.cos(el),math.sin(az)*math.cos(el),math.sin(el)]);right=np.cross([0,0,1],eye);right/=np.linalg.norm(right);up=np.cross(eye,right);camera=np.array([right,up,eye]);img=np.full((H,W,3),.87);depth=np.full((H,W),-np.inf)
  for a in c.atomic_list:
   part=c.frame_list[a.frame].name
   if part.startswith('extra') and part not in selected_extras:continue
   g=c.geometry_list[a.geometry];mat=matrix(a.frame);vertices=np.array([(*v,1) for v in g.vertices])@mat.T;projected=vertices[:,:3]@camera.T;projected[:,:2]*=90;projected[:,0]+=W/2;projected[:,1]=H/2-projected[:,1]
   for t in g.triangles:
    ids=[t.a,t.b,t.c];worldv=vertices[ids,:3];n=np.cross(worldv[1]-worldv[0],worldv[2]-worldv[0]);n/=max(np.linalg.norm(n),1.e-12)
    if np.dot(n,eye)<0:continue
    p=projected[ids];xmin=max(0,int(np.floor(p[:,0].min())));xmax=min(W-1,int(np.ceil(p[:,0].max())));ymin=max(0,int(np.floor(p[:,1].min())));ymax=min(H-1,int(np.ceil(p[:,1].max())))
    if xmin>xmax or ymin>ymax:continue
    x,y=np.meshgrid(np.arange(xmin,xmax+1)+.5,np.arange(ymin,ymax+1)+.5);den=(p[1,1]-p[2,1])*(p[0,0]-p[2,0])+(p[2,0]-p[1,0])*(p[0,1]-p[2,1])
    if abs(den)<1.e-12:continue
    b0=((p[1,1]-p[2,1])*(x-p[2,0])+(p[2,0]-p[1,0])*(y-p[2,1]))/den;b1=((p[2,1]-p[0,1])*(x-p[2,0])+(p[0,0]-p[2,0])*(y-p[2,1]))/den;b2=1-b0-b1;z=b0*p[0,2]+b1*p[1,2]+b2*p[2,2];target=depth[ymin:ymax+1,xmin:xmax+1];mask=(b0>=0)&(b1>=0)&(b2>=0)&(z>target)
    if not mask.any():continue
    material=g.materials[t.material];color=np.array(material.color[:3])/255
    if tuple(material.color[:3])==(60,255,0):color=np.array([.3,.42,.55])
    elif tuple(material.color[:3])==(255,0,175):color=np.array([.05,.05,.05])
    if material.textures:
     tex=textures.get(material.textures[0].name)
     if tex is not None:
      uv=np.array([g.uv_layers[0][i] for i in ids]);u=(b0*uv[0,0]+b1*uv[1,0]+b2*uv[2,0])%1;v=(b0*uv[0,1]+b1*uv[1,1]+b2*uv[2,1])%1;sample=tex[(v*tex.shape[0]).astype(int)%tex.shape[0],(u*tex.shape[1]).astype(int)%tex.shape[1]];color=np.asarray(color)*(1-sample[:,:,3:4])+sample[:,:,:3]*sample[:,:,3:4] if material.textures[0].name.startswith('ivd_') else color*sample[:,:,:3]
    shade=.6+.4*max(0,np.dot(n,np.array([.3,.3,.9])));patch=img[ymin:ymax+1,xmin:xmax+1];shaded=np.broadcast_to(color*shade,patch.shape)
    patch[mask]=shaded[mask];target[mask]=z[mask]
  views.append(Image.fromarray(np.uint8(np.clip(img,0,1)*255)))
 out=Image.new('RGB',(W*2,H+40),'#dddddd');out.paste(views[0],(0,40));out.paste(views[1],(W,40));ImageDraw.Draw(out).text((20,12),name+' — converted asset preview (not a game screenshot)',fill='black');out.save(output)
