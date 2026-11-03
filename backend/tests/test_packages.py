import ai
import server


def test_packages_import():
    assert ai.__doc__
    assert server.__version__ == "0.1.0"
