from brain.prefix import PrefixCache


def test_prefix_hit_after_warm_and_miss_on_new_system() -> None:
    cache = PrefixCache()
    cache.warm("sys-a", "[]")
    assert cache.hit() is True
    assert cache.hit("sys-a", "[]") is True
    assert cache.hit("sys-b", "[]") is False
