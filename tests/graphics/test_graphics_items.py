import VectorGraphics.graphics.graphics_items as gf
import unittest
import numpy.testing as np
from PyQt6.QtGui import QColor

class TestRbg(unittest.TestCase):
    def setUp(self):
        self.red = QColor('red')

    def test_red(self):
        self.assertEqual(gf.color_to_rgb(self.red), "rgb(255, 0, 0)")


class TestMatrixCombine(unittest.TestCase):
    def setUp(self):
        self.translate = gf.translate_matrix(7.2, 19.325)
        self.scale = gf.scale_matrix(0.16, -0.16)
        self.scale_str = "scale(0.16 -0.16)"
        self.translate_str = "translate(7.2 19.325)"


    def test_translate(self):
        matrix = gf.combine_transforms_from_string([self.translate_str])
        np.assert_equal(matrix, self.translate, verbose=True), f"\n{matrix}\n not equal to\n{self.translate}"

    def test_scale(self):
        matrix = gf.combine_transforms_from_string([self.scale_str])
        np.assert_equal(matrix, self.scale, verbose=True), f"\n{matrix}\n not equal to\n{self.translate}"

#    def test_composition(self):
#        translate_and_scale =
if __name__ == "__main__":
    unittest.main()
