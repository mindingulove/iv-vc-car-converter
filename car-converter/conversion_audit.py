"""Report source glass without flattening selected extras or inventing missing panes."""
from material_policy import classify

def glass_report(buckets,materials):
 parts=[]
 for target,triangles in buckets.items():
  glass=[t for t in triangles if classify(materials[t[0]].get('extras',{}))['glass']]
  if not glass:continue
  separated=target.startswith(('iv_window_','iv_lamp_'))
  parts.append(dict(part=target,triangles=len(glass),optional=target.startswith('extra'),
                    materials=sorted({t[0] for t in glass}),
                    handling='separate pane' if separated else 'split after native component selection'))
 deferred=any(p['handling']!='separate pane' for p in parts)
 return dict(glassDetectionVersion=2,detectedGlassParts=parts,
             detectedGlassTriangles=sum(p['triangles'] for p in parts),
             requiredWindowGlassVersion=2 if deferred else 1 if parts else 0,
             glassPolicy='Preserve opaque trim/interiors and optional selection. The compatible native runtime separates connected glass inside windscreens and selected extras; shots/collision/repair are native behaviour, not baked textures.')

def summary(report):
 panes=report.get('detectedGlassParts',[])
 optional=sum(p.get('optional',False) for p in panes)
 channels=report.get('detectedPaintChannels',[])
 return (f"Glass: {len(panes)} detected groups ({optional} inside optional parts). "
         f"Optional parts: {len(report.get('optionalExtras',[]))}. "
         f"Paint channels: {', '.join(map(str,channels)) or 'none'}. "
         "Glass breakage, dirt and scratches require the compatible game runtime and gameplay testing.")
