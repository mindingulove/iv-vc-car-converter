"""Source vehicle shader semantics mapped to native VC paint and glass."""
import math

def classify(extras):
 shader=extras.get('shader','').lower();name=(extras.get('textureName') or '').lower()
 diffuse=extras.get('shaderVectors',{}).get('185f047c',[2,1,1,0])
 close=lambda v:len(diffuse)>=3 and all(abs(a-b)<.01 for a,b in zip(diffuse[:3],v))
 glass='glass' in shader
 livery=extras.get('liveryMode')=='fixed' or (not extras.get('liveryMode') and any(word in name for word in ('_sign_', 'livery', 'paintjob')))
 mask=any(word in name for word in ('specmap','specular','dirtmap'))
 interior=any(word in name for word in ('interior','leather','seat','carpet','dash','softtop','canvas','fabric','cloth'))
 slot=0
 if extras.get('paint') and not interior and not livery:
  if close((2,1,1)):slot=1
  elif close((2,2,2)) or close((1,2,1)):slot=2
  elif len(diffuse)>=3 and abs(diffuse[0]-2)<.01 and abs(diffuse[1]-diffuse[2])<.01 and abs(diffuse[1]-round(diffuse[1]))<.01 and 3<=round(diffuse[1])<=16:slot=round(diffuse[1])
 color=(60,255,0,255) if slot==1 else (255,0,175,255) if slot==2 else (255,255,255,249 if glass else 255)
 # The paint sampler is a specular/dirt mask, not a diffuse body texture.
 # Authored upholstery diffuse textures remain neutral and independent of paint.
 textured=bool(name) and (not extras.get('paint') or interior or livery or extras.get('liveryMode')=='decal')
 return dict(slot=slot,color=color,textured=textured,glass=glass,interior=interior,livery=livery,specular=.65 if glass else .4 if (slot or livery or extras.get('liveryMode')=='decal') else 0.)
