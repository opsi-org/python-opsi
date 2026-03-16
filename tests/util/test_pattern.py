from opsi.util.pattern import Singleton


def test_singleton() -> None:
	class TestSingleton(metaclass=Singleton):
		pass

	assert id(TestSingleton()) == id(TestSingleton())
