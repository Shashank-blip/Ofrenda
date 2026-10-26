from app.remember import citation_ok, filter_citations

ALLOWED = {"abc1234", "def5678"}


def test_unknown_sha_is_dropped():
    assert citation_ok("abc1234", ALLOWED)
    assert citation_ok("ABC1234extra", ALLOWED)
    assert not citation_ok("deadbee", ALLOWED)
    assert not citation_ok("deadbeef", ALLOWED)
    assert filter_citations(["deadbeef", "abc1234", "abc1234"], ALLOWED) == ["abc1234"]


def test_citations_must_be_a_list_of_strings():
    assert filter_citations("abc1234", ALLOWED) == []
    assert filter_citations([{"sha": "abc1234"}, 12, None], ALLOWED) == []
