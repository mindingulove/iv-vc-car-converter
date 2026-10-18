"""Read-only compatibility checks; never infer glass support from an unrelated version."""
import hashlib,json,struct
from pathlib import Path

def glass_support(runtime):
 runtime=Path(runtime);marker=runtime/'NATIVE_CAR_ADDONS.json'
 data=json.loads(marker.read_text()) if marker.exists() else {}
 version=max(data.get('convertedWindowGlassVersion',0),data.get('windowGlassVersion',0))
 # Earlier installed builds did not expose a distinct full-pane version marker.
 # Recognize those exact signed artifacts. Unknown later builds must declare their support.
 known=json.loads(Path(__file__).with_name('runtime_glass_builds.json').read_text())
 versions=[]
 for name in ('reVC','reVC_metal'):
  binary=runtime/name
  if binary.is_file():
   with binary.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
   supported=known.get(digest,{}).get('windowGlassVersion',0)
   if supported<2:
    artifact=binary.read_bytes()
    # Unstripped local FPS rebuilds retain the same glass implementation. Check its
    # named splitter and hit path in the executable, not a stale installation manifest.
    arm64=len(artifact)>=8 and struct.unpack_from('<II',artifact)==(0xfeedfacf,0x0100000c)
    if arm64 and all(token in artifact for token in (b'DetectUnlistedImportedGlass',b'DamageImportedGlass',b'iv_window_auto_hi')):supported=2
   versions.append(max(version,supported))
 return min(versions) if versions else version

def require_glass_support(report,runtime):
 required=report.get('requiredWindowGlassVersion',report.get('windowGlassVersion',0))
 actual=glass_support(runtime)
 if required>actual:
  raise RuntimeError(f'This car requires native glass support {required}; detected {actual}. Install a matching native vehicle build (windscreen and selected-extra panes), or have the build declare convertedWindowGlassVersion={required} in NATIVE_CAR_ADDONS.json. No game files were changed.')
 return actual
