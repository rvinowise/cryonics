import importlib.util
import pathlib
import unittest

path = pathlib.Path(__file__).resolve().parent / "test_dewar_parameters.py"
spec = importlib.util.spec_from_file_location("test_dewar_parameters", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

suite = unittest.defaultTestLoader.loadTestsFromModule(module)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)