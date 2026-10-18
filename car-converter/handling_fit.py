"""Fit independent native VC handling to imported geometry; do not copy IV units."""
from pathlib import Path
import math

def stock_profiles(runtime):
 rows={}
 for raw in (Path(runtime)/'data/handling.cfg').read_text().splitlines():
  line=raw.strip()
  if not line or line[0] in ';#!%$^':continue
  fields=line.split()
  if len(fields)==33:rows[fields[0].upper()]=fields
 return rows

def fit_handling(runtime,donor_row,report,folder,name):
 rows=stock_profiles(runtime);key=donor_row[4].upper()
 if key not in rows:raise ValueError('No native handling profile for '+key)
 values=rows[key].copy();original=values.copy();lo,hi=report['bodyBounds'];radius=report['wheelDiameter']/2
 dims=[hi[i]-lo[i] for i in range(3)];dims[2]=max(dims[2],hi[2]-min(w[2]-radius for w in report['wheelCenters']))
 base_volume=math.prod(float(values[i]) for i in (2,3,4));ratio=math.prod(dims)/base_volume
 values[0]=name;values[1]=str(round(float(values[1])*max(.75,min(1.3,ratio**.35)),1))
 for i,v in zip((2,3,4),dims):values[i]=f'{v:.6f}'
 # Limit extension to a tyre-sized travel range, centred by native auto-fit.
 span=max(.12,min(.42,radius*.85));force=max(1.3,min(2.2,float(values[21])))
 values[21]=str(force);values[22]=str(max(.10,min(.25,float(values[22]))));values[26]=str(span-span/(4*force));values[27]=str(-span/(4*force));values[28]='0.5'
 data=Path(folder)/'data';data.mkdir(exist_ok=True);path=data/('cvh_'+name+'.cfg');path.write_text('; Native VC handling fitted to imported body/wheel dimensions. No IV-unit values.\n'+' '.join(values)+'\n')
 return {'version':1,'donor':key,'massKg':float(values[1]),'dimensions':dims,'wheelRadius':radius,'travelMeters':span,'springForce':force,'damping':float(values[22]),'originalTravelMeters':float(original[26])-float(original[27]),'file':'data/'+path.name,'source':'native VC donor scaled to imported geometry; transmission/brakes/traction retain matching vehicle class'}
