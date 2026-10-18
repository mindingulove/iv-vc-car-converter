import hashlib,json,tempfile,unittest
from pathlib import Path
from conversion_audit import glass_report
from runtime_compat import require_glass_support,glass_support

class ConversionAuditTest(unittest.TestCase):
 def test_glass_inside_extras_and_windscreen_is_reported(self):
  materials=[{'extras':{'shader':'gta_vehicle_glass','textureName':'clear'}},{'extras':{'shader':'gta_vehicle_paint1','paint':True}}]
  r=glass_report({'extra1':[(0,[]),(1,[])],'windscreen_dummy':[(0,[])],'iv_window_fl0_hi':[(0,[])]},materials)
  self.assertEqual(r['detectedGlassTriangles'],3);self.assertEqual(r['requiredWindowGlassVersion'],2)
  self.assertEqual([p['part'] for p in r['detectedGlassParts'] if p['optional']],['extra1'])
 def test_paint_does_not_become_glass(self):
  self.assertEqual(glass_report({'bonnet_dummy':[(0,[])]},[{'extras':{'shader':'gta_vehicle_paint1'}}])['detectedGlassTriangles'],0)
 def test_old_runtime_refused_before_installation(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'NATIVE_CAR_ADDONS.json').write_text(json.dumps({'windowGlassVersion':1}))
   with self.assertRaisesRegex(RuntimeError,'requires native glass support 2'):require_glass_support({'requiredWindowGlassVersion':2},root)
   self.assertEqual(list(root.iterdir()),[root/'NATIVE_CAR_ADDONS.json'])
 def test_explicit_capability_supports_later_native_builds(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'NATIVE_CAR_ADDONS.json').write_text(json.dumps({'convertedWindowGlassVersion':2}))
   (root/'reVC').write_bytes(b'future build')
   self.assertEqual(require_glass_support({'requiredWindowGlassVersion':2},root),2)
 def test_known_build_recognition_checks_both_installed_executables(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'reVC').write_bytes(b'test known');(root/'reVC_metal').write_bytes(b'test old')
   known={hashlib.sha256(b'test known').hexdigest():{'windowGlassVersion':2}}
   real_loads=json.loads
   with patch('runtime_compat.json.loads',side_effect=lambda s:known if '10315a7f' in s else real_loads(s)):
    self.assertEqual(glass_support(root),0)

class TextureAndGlassPolicyTest(unittest.TestCase):
 def test_texture_hint_and_non_glass_masks(self):
  from material_policy import classify
  self.assertTrue(classify({'shader':'generic','textureName':'vehicle_generic_glasswindows2'})['glass'])
  for name in ['glasswindows_specmap','interior_glasswindows','windscreen_specular']:
   self.assertFalse(classify({'shader':'generic','textureName':name})['glass'])
 def test_invalid_mips_rejected_before_native_upload(self):
  import struct
  from vc_export import native_texture
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'bad.dds';header=bytearray(128);header[:4]=b'DDS ';struct.pack_into('<II',header,12,4,4);struct.pack_into('<I',header,28,4);header[84:88]=b'DXT1';path.write_bytes(header+b'0'*32)
   with self.assertRaisesRegex(ValueError,'Invalid mip count'):native_texture(path,'bad')
 def test_full_pane_feature_detection_survives_fps_rebuild(self):
  import struct
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'reVC_metal').write_bytes(struct.pack('<II',0xfeedfacf,0x0100000c)+b'DetectUnlistedImportedGlass\0DamageImportedGlass\0iv_window_auto_hi')
   self.assertEqual(glass_support(root),2)

if __name__=='__main__':unittest.main()
