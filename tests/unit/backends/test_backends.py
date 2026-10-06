from hydict.backends import Backend, MemoryBackend


def test_memory_backend_implements_backend():
    backend = MemoryBackend()

    assert isinstance(backend, Backend)

