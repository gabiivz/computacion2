import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from analizadores.scheduling import parsear_politica


class TestParsearPolitica(unittest.TestCase):
    """Tests de parsear_politica() —
    prueba la traducción de código numérico a nombre de política."""

    def test_other(self):
        self.assertEqual(parsear_politica("0"), "OTHER")

    def test_fifo(self):
        self.assertEqual(parsear_politica("1"), "FIFO")

    def test_round_robin(self):
        self.assertEqual(parsear_politica("2"), "RR")

    def test_batch(self):
        self.assertEqual(parsear_politica("3"), "BATCH")

    def test_idle(self):
        self.assertEqual(parsear_politica("5"), "IDLE")

    def test_deadline(self):
        self.assertEqual(parsear_politica("6"), "DEADLINE")

    def test_codigo_entero_tambien_funciona(self):
        # /proc se lee como string, pero la función debe tolerar un int también
        self.assertEqual(parsear_politica(0), "OTHER")

    def test_codigo_desconocido(self):
        self.assertEqual(parsear_politica("99"), "UNKNOWN(99)")


if __name__ == "__main__":
    unittest.main()