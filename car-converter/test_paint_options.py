import json,tempfile,unittest
from pathlib import Path
from paint_options import parse_colors,resolve_runtime,material_color
from material_policy import classify
class PaintOptionsTest(unittest.TestCase):
 def test_hex_and_validation(self):
  self.assertEqual(parse_colors(['1=#123456','4=ABCDEF']),{1:(18,52,86),4:(171,205,239)})
  for bad in ('0=#abcdef','17=#abcdef','1=#12345','1=red','x=#123456'):
   with self.assertRaises(ValueError):parse_colors([bad])
 def test_detect_channels_and_exclude_fixed_materials(self):
  for channel in (1,2,3,4,5,16):
   e=dict(paint=True,shader='gta_vehicle_paint3',textureName='specmap',shaderVectors={'185f047c':[2,channel,channel,0]})
   self.assertEqual(classify(e)['slot'],channel)
   for name in ('source_interior','source_sign_1'):
    self.assertEqual(classify(e|{'textureName':name})['slot'],0)
 def test_runtime_and_modloader_selection(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d).resolve();(root/'data').mkdir();(root/'data/default.ide').write_text('cars\nend\n')
   with self.assertRaises(ValueError):resolve_runtime(root)
   (root/'modloader').mkdir();self.assertEqual(resolve_runtime(root/'modloader'),root)
 def test_user_rgb_cannot_become_native_paint_sentinel(self):
  self.assertNotEqual(material_color((60,255,0)),(60,255,0,255))
  self.assertNotEqual(material_color((255,0,175)),(255,0,175,255))
if __name__=='__main__':unittest.main()
