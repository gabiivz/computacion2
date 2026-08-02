import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from analizadores.senales import decodificar_mascara


class TestDecodificarMascara(unittest.TestCase):
    """Tests de decodificar_mascara() — 
    prueba la conversión de máscara hexadecimal a lista de señales."""

    def test_mascara_vacia(self):
        self.assertEqual(decodificar_mascara("0000000000000000"), [])

    def test_un_solo_bit_sigint(self):
        # SIGINT es la señal 2 -> bit 1 -> 0x2
        self.assertEqual(decodificar_mascara("0000000000000002"), ["SIGINT"])

    def test_un_solo_bit_sigterm(self):
        # SIGTERM es la señal 15 -> bit 14 -> 0x4000
        self.assertEqual(decodificar_mascara("0000000000004000"), ["SIGTERM"])

    def test_varios_bits_combinados(self):
        # SIGINT (2) + SIGTERM (15): 0x2 | 0x4000 = 0x4002
        resultado = decodificar_mascara("0000000000004002")
        self.assertIn("SIGINT", resultado)
        self.assertIn("SIGTERM", resultado)
        self.assertEqual(len(resultado), 2)

    def test_mascara_invalida_no_rompe(self):
        # Si /proc devolviera algo corrupto, no debería tirar excepción
        self.assertEqual(decodificar_mascara("no_es_hex"), [])


if __name__ == "__main__":
    unittest.main()