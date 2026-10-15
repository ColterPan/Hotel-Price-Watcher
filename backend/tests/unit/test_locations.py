from hotel_watcher.locations import all_locations, find_by_key, search_locations


def test_bundled_cities_load_and_have_unique_keys():
    cities = all_locations()
    assert len(cities) >= 50
    assert len({c.location_key for c in cities}) == len(cities)
    assert all(c.latitude is not None and c.longitude is not None for c in cities)


def test_prefix_matches_come_first():
    names = [loc.name for loc in search_locations("sing")]
    assert names[0] == "Singapore"


def test_search_matches_country_and_ignores_accents_and_case():
    assert any(loc.name == "Tokyo" for loc in search_locations("JAPAN"))
    assert search_locations("kyōto")[0].name == "Kyoto"


def test_tripadvisor_url_resolves_to_known_city():
    url = "https://www.tripadvisor.com/Hotels-g294265-Singapore-Hotels.html"
    (loc,) = search_locations(url)
    assert loc.name == "Singapore"


def test_tripadvisor_url_for_unknown_area_still_works():
    url = "https://www.tripadvisor.co.uk/Hotels-g1234567-Somewhere-Hotels.html"
    (loc,) = search_locations(url)
    assert loc.location_key == "g1234567"
    assert loc.latitude is None


def test_bare_location_key_is_accepted():
    assert search_locations("g298184")[0].name == "Tokyo"


def test_empty_query_returns_a_short_default_list():
    assert 0 < len(search_locations("")) <= 8


def test_no_match_returns_empty():
    assert search_locations("zzzzzz") == ()


def test_find_by_key():
    assert find_by_key("g294265") is not None
    assert find_by_key("g1") is None
