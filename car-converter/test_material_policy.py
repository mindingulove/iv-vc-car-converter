import unittest
from material_policy import classify
class MaterialPolicyTest(unittest.TestCase):
 def material(self,selector,name='vehicle_generic_smallspecmap'):
  return classify(dict(shader='gta_vehicle_paint3',paint=True,textureName=name,shaderVectors={'185f047c':selector}))
 def test_native_paint_slots(self):
  self.assertEqual(self.material([2,1,1,0])['slot'],1)
  self.assertEqual(self.material([2,2,2,0])['slot'],2)
  self.assertFalse(self.material([2,2,2,0])['textured'])
 def test_interior_texture_is_independent_of_body(self):
  for s in ([2,1,1,0],[2,2,2,0],[2,6,6,0]):
   m=self.material(s,'torero_interior');self.assertEqual(m['slot'],0);self.assertTrue(m['textured']);self.assertEqual(m['color'],(255,255,255,255))
 def test_glass_does_not_inherit_paint(self):
  m=classify(dict(shader='gta_vehicle_vehglass',paint=False,textureName='glass'));self.assertTrue(m['glass']);self.assertEqual(m['slot'],0);self.assertLess(m['color'][3],250)
 def test_glass_keeps_source_opacity_and_reflects(self):
  m=classify(dict(shader='gta_vehicle_vehglass',textureName='vehicle_generic_glasswindows2'))
  self.assertGreater(m['specular'],0);self.assertGreaterEqual(m['color'][3],245)
 def test_authored_livery_is_not_discarded_or_repainted(self):
  m=self.material([2,1,1,0],'marbella_sign_1')
  self.assertTrue(m['textured']);self.assertTrue(m['livery']);self.assertEqual(m['slot'],0);self.assertGreater(m['specular'],0)
 def test_decal_keeps_repaintable_body_and_opaque_material(self):
  m=classify(dict(shader='gta_vehicle_paint3',paint=True,textureName='cabbie_sign_1',liveryMode='decal',shaderVectors={'185f047c':[2,1,1,0]}))
  self.assertEqual(m['slot'],1);self.assertTrue(m['textured']);self.assertEqual(m['color'][3],255)
if __name__=='__main__':unittest.main()
