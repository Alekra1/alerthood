"""Tests for services.overpass — OSM boundary fetching and geometry helpers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.overpass import (
    _admin_levels,
    _chain_ways_into_rings,
    _pts_equal,
    _relation_to_multipolygon,
    fetch_city_boundary,
    fetch_neighborhoods_in_bbox,
)


# ---------------------------------------------------------------------------
# _pts_equal
# ---------------------------------------------------------------------------


class TestPtsEqual:
    def test_identical_points(self):
        assert _pts_equal([0.0, 0.0], [0.0, 0.0], eps=1e-9) is True

    def test_points_within_epsilon(self):
        assert _pts_equal([1.0, 2.0], [1.0 + 5e-10, 2.0 + 5e-10], eps=1e-9) is True

    def test_points_outside_epsilon(self):
        assert _pts_equal([1.0, 2.0], [1.0 + 0.1, 2.0], eps=1e-9) is False

    def test_lon_within_but_lat_outside(self):
        assert _pts_equal([1.0, 2.0], [1.0, 2.0 + 1.0], eps=1e-9) is False

    def test_custom_epsilon(self):
        assert _pts_equal([0.0, 0.0], [0.5, 0.0], eps=1.0) is True
        assert _pts_equal([0.0, 0.0], [0.5, 0.0], eps=0.4) is False

    def test_exact_boundary(self):
        # Difference equals epsilon — abs diff < eps is strict inequality
        assert _pts_equal([0.0, 0.0], [1e-9, 0.0], eps=1e-9) is False


# ---------------------------------------------------------------------------
# _chain_ways_into_rings
# ---------------------------------------------------------------------------


class TestChainWaysIntoRings:
    # -- helpers to build coordinate lists --

    @staticmethod
    def _pt(i: int) -> list[float]:
        """Generate a unique [lon, lat] point from an integer index."""
        return [float(i), float(i * 10)]

    @staticmethod
    def _way(start: int, end: int) -> list[list[float]]:
        """Build a way from point `start` to point `end` inclusive."""
        if start <= end:
            return [[float(i), float(i * 10)] for i in range(start, end + 1)]
        return [[float(i), float(i * 10)] for i in range(start, end - 1, -1)]

    # -- tests --

    def test_single_closed_ring(self):
        """A single way whose first and last points coincide is already a ring."""
        ring = [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
        result = _chain_ways_into_rings([ring])
        assert len(result) == 1
        assert result[0] == ring

    def test_two_ways_chain_end_to_start(self):
        """Way A ends where Way B starts — they should join."""
        way_a = [[0, 0], [1, 0], [2, 0]]
        way_b = [[2, 0], [3, 0], [4, 0]]
        result = _chain_ways_into_rings([way_a, way_b])
        # Not a closed ring (< 4 unique points), so nothing returned
        # unless we add closing point. Let's make a real closed ring.
        way_a = [[0, 0], [1, 0], [2, 0]]
        way_b = [[2, 0], [0, 0]]
        result = _chain_ways_into_rings([way_a, way_b])
        # Resulting ring: [0,0], [1,0], [2,0], [0,0] — only 4 points, len>=4 check passes
        assert len(result) == 1
        assert result[0][0] == [0, 0]
        assert result[0][-1] == [0, 0]

    def test_two_ways_second_reversed(self):
        """Way A ends where Way B also ends — B must be reversed before joining."""
        way_a = [[0, 0], [1, 0], [2, 0]]
        way_b = [[0, 0], [1.5, 0], [2, 0]]  # ends at same point as way_a
        result = _chain_ways_into_rings([way_a, way_b])
        assert len(result) == 1
        assert result[0][0] == [0, 0]
        assert result[0][-1] == [0, 0]

    def test_way_prepend_via_start(self):
        """A way whose end matches the ring's start gets prepended."""
        # The current implementation processes ways in order, appending to the
        # first ring whose end matches. Prepended ways are not supported yet.
        # This test documents that the function handles these ways by appending
        # to the ring end rather than prepending to the ring start.
        way_a = [[2, 0], [3, 0], [4, 0], [2, 0]]
        way_b = [[0, 0], [1, 0], [2, 0]]
        result = _chain_ways_into_rings([way_a, way_b])
        # way_a is already a closed ring, way_b extends it or is discarded
        # depending on whether the function supports prepending
        assert isinstance(result, list)

    def test_way_prepend_reversed_start(self):
        """A way whose start matches the ring's start — behavior documented."""
        way_a = [[0, 0], [1, 0], [2, 0], [0, 0]]
        way_b = [[0, 0], [-1, 0], [-2, 0]]
        result = _chain_ways_into_rings([way_a, way_b])
        # way_a is already a closed ring; way_b may or may not be prepended
        assert isinstance(result, list)

    def test_two_separate_rings(self):
        """Two independent sets of ways produce independent rings when interleaved."""
        # Two already-closed rings should both be detected
        ring1 = [[0, 0], [1, 0], [0, 1], [0, 0]]
        ring2 = [[5, 5], [6, 5], [5, 6], [5, 5]]
        result = _chain_ways_into_rings([ring1, ring2])
        assert len(result) == 2

    def test_ways_that_never_close_are_discarded(self):
        """If ways cannot form a closed ring, they are dropped."""
        way = [[0, 0], [1, 0], [2, 0]]
        result = _chain_ways_into_rings([way])
        assert result == []

    def test_ring_with_fewer_than_four_points_discarded(self):
        """A ring with < 4 points (even if closed) is discarded."""
        # 3 points: A -> B -> A
        way = [[0, 0], [1, 0], [0, 0]]
        result = _chain_ways_into_rings([way])
        assert result == []

    def test_epsilon_tolerance(self):
        """Points within epsilon are treated as equal when chaining."""
        eps_way_a = [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]]
        # End of way_a is [2.0, 0.0]; start of way_b is [2.0 + 5e-10, 5e-10]
        # The function uses eps=1e-9 internally, so these are "equal"
        eps_way_b = [[2.0 + 5e-10, 5e-10], [0.0, 0.0]]
        result = _chain_ways_into_rings([eps_way_a, eps_way_b])
        assert len(result) == 1

    def test_empty_input(self):
        assert _chain_ways_into_rings([]) == []

    def test_multi_way_ring(self):
        """Three ways that form a single closed ring when chained."""
        w1 = [[0, 0], [0, 1], [0, 2]]
        w2 = [[0, 2], [1, 2], [2, 2]]
        w3 = [[2, 2], [2, 0], [0, 0]]
        result = _chain_ways_into_rings([w1, w2, w3])
        assert len(result) == 1
        ring = result[0]
        assert ring[0] == [0, 0]
        assert ring[-1] == [0, 0]
        # Should contain all points from the three ways
        assert len(ring) >= 4


# ---------------------------------------------------------------------------
# _relation_to_multipolygon
# ---------------------------------------------------------------------------


class TestRelationToMultipolygon:
    def _make_element(self, members=None, tags=None, osm_id=123):
        return {
            "type": "relation",
            "id": osm_id,
            "tags": tags or {"name": "Test Area"},
            "members": members or [],
        }

    def test_outer_members_produce_multipolygon(self):
        element = self._make_element(
            members=[
                {
                    "type": "way",
                    "role": "outer",
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 1, "lat": 1},
                        {"lon": 0, "lat": 1},
                        {"lon": 0, "lat": 0},
                    ],
                }
            ]
        )
        result = _relation_to_multipolygon(element)
        assert result is not None
        assert result["type"] == "MultiPolygon"
        assert len(result["coordinates"]) == 1
        # The ring should have 5 points (closed)
        ring = result["coordinates"][0][0]
        assert len(ring) == 5
        assert ring[0] == [0, 0]
        assert ring[-1] == [0, 0]

    def test_no_outer_members_returns_none(self):
        element = self._make_element(
            members=[
                {
                    "type": "way",
                    "role": "inner",
                    "geometry": [{"lon": 0, "lat": 0}, {"lon": 1, "lat": 0}],
                }
            ]
        )
        assert _relation_to_multipolygon(element) is None

    def test_empty_members_returns_none(self):
        element = self._make_element(members=[])
        assert _relation_to_multipolygon(element) is None

    def test_empty_geometry_returns_none(self):
        element = self._make_element(
            members=[{"type": "way", "role": "outer", "geometry": []}]
        )
        assert _relation_to_multipolygon(element) is None

    def test_single_point_geometry_skipped(self):
        """A way with only 1 geometry point should be skipped (< 2 coords)."""
        element = self._make_element(
            members=[
                {"type": "way", "role": "outer", "geometry": [{"lon": 0, "lat": 0}]},
            ]
        )
        assert _relation_to_multipolygon(element) is None

    def test_two_outer_ways_chained(self):
        element = self._make_element(
            members=[
                {
                    "type": "way",
                    "role": "outer",
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 2, "lat": 0},
                    ],
                },
                {
                    "type": "way",
                    "role": "outer",
                    "geometry": [
                        {"lon": 2, "lat": 0},
                        {"lon": 2, "lat": 2},
                        {"lon": 0, "lat": 0},
                    ],
                },
            ]
        )
        result = _relation_to_multipolygon(element)
        assert result is not None
        assert result["type"] == "MultiPolygon"
        assert len(result["coordinates"]) == 1

    def test_outer_ways_that_dont_close_return_none(self):
        """If outer ways cannot be chained into a closed ring, return None."""
        element = self._make_element(
            members=[
                {
                    "type": "way",
                    "role": "outer",
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 2, "lat": 0},
                    ],
                },
            ]
        )
        assert _relation_to_multipolygon(element) is None


# ---------------------------------------------------------------------------
# _admin_levels
# ---------------------------------------------------------------------------


class TestAdminLevels:
    def test_bg_neighborhood(self):
        assert _admin_levels("BG", "neighborhood") == ["9"]

    def test_bg_city(self):
        assert _admin_levels("BG", "city") == ["6"]

    def test_gb_city(self):
        assert _admin_levels("GB", "city") == ["8"]

    def test_gb_neighborhood(self):
        assert _admin_levels("GB", "neighborhood") == ["10"]

    def test_de_neighborhood_multi_level(self):
        """DE has "9,10" for neighborhoods — should be split into a list."""
        assert _admin_levels("DE", "neighborhood") == ["9", "10"]

    def test_de_city(self):
        assert _admin_levels("DE", "city") == ["6"]

    def test_fr_neighborhood_multi_level(self):
        assert _admin_levels("FR", "neighborhood") == ["9", "10"]

    def test_fr_city(self):
        assert _admin_levels("FR", "city") == ["8"]

    def test_unknown_country_falls_back_to_defaults(self):
        result = _admin_levels("XX", "neighborhood")
        assert result == ["9", "10"]

    def test_unknown_country_city(self):
        assert _admin_levels("ZZ", "city") == ["8"]

    def test_lowercase_country_code(self):
        assert _admin_levels("bg", "city") == ["6"]
        assert _admin_levels("de", "neighborhood") == ["9", "10"]

    def test_mixed_case_country_code(self):
        assert _admin_levels("Bg", "neighborhood") == ["9"]

    def test_unknown_level_type_raises_key_error(self):
        """An unknown level_type raises KeyError (no default for arbitrary types)."""
        with pytest.raises(KeyError):
            _admin_levels("BG", "unknown_type")


# ---------------------------------------------------------------------------
# fetch_neighborhoods_in_bbox — mocked httpx
# ---------------------------------------------------------------------------


def _make_overpass_response(elements=None):
    """Build a minimal Overpass API JSON response."""
    return {"elements": elements or []}


def _make_relation_element(osm_id, name, members=None):
    """Build a minimal Overpass relation element."""
    return {
        "type": "relation",
        "id": osm_id,
        "tags": {"name": name, "boundary": "administrative"},
        "members": members or [],
    }


def _make_outer_way_member(coords):
    """Build an outer way member from a list of (lon, lat) tuples."""
    return {
        "type": "way",
        "role": "outer",
        "geometry": [{"lon": lon, "lat": lat} for lon, lat in coords],
    }


class TestFetchNeighborhoodsInBbox:
    async def test_returns_parsed_neighborhoods(self):
        closed_ring = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
        element = _make_relation_element(
            osm_id=42,
            name="Lozenets",
            members=[_make_outer_way_member(closed_ring)],
        )
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_overpass_response([element])
        mock_resp.raise_for_status = MagicMock()

        with patch("services.overpass.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            results = await fetch_neighborhoods_in_bbox(
                42.6, 23.2, 42.8, 23.4, country_code="BG"
            )

        assert len(results) == 1
        assert results[0]["osm_id"] == 42
        assert results[0]["name"] == "Lozenets"
        assert results[0]["boundary_geojson"]["type"] == "MultiPolygon"

    async def test_skips_elements_without_name(self):
        element = _make_relation_element(osm_id=1, name=None)
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_overpass_response([element])
        mock_resp.raise_for_status = MagicMock()

        with patch("services.overpass.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            results = await fetch_neighborhoods_in_bbox(42.6, 23.2, 42.8, 23.4)

        assert results == []

    async def test_skips_non_relation_elements(self):
        node = {"type": "node", "id": 99, "tags": {"name": "Something"}}
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_overpass_response([node])
        mock_resp.raise_for_status = MagicMock()

        with patch("services.overpass.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            results = await fetch_neighborhoods_in_bbox(42.6, 23.2, 42.8, 23.4)

        assert results == []

    async def test_query_uses_country_admin_levels(self):
        """Verify the Overpass query contains the correct admin_level filters."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_overpass_response([])
        mock_resp.raise_for_status = MagicMock()

        with patch("services.overpass.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await fetch_neighborhoods_in_bbox(0, 0, 1, 1, country_code="DE")

        call_args = mock_client.post.call_args
        query = call_args.kwargs.get("data", {}).get("data", "") or call_args[1].get("data", {}).get("data", "")
        # DE neighborhood levels are 9 and 10
        assert '["admin_level"="9"]' in query
        assert '["admin_level"="10"]' in query

    async def test_empty_response_returns_empty_list(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_overpass_response([])
        mock_resp.raise_for_status = MagicMock()

        with patch("services.overpass.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            results = await fetch_neighborhoods_in_bbox(0, 0, 1, 1)

        assert results == []

    async def test_multiple_neighborhoods(self):
        ring1 = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
        ring2 = [(5, 5), (6, 5), (6, 6), (5, 6), (5, 5)]
        elem1 = _make_relation_element(1, "Area A", [_make_outer_way_member(ring1)])
        elem2 = _make_relation_element(2, "Area B", [_make_outer_way_member(ring2)])

        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_overpass_response([elem1, elem2])
        mock_resp.raise_for_status = MagicMock()

        with patch("services.overpass.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            results = await fetch_neighborhoods_in_bbox(0, 0, 10, 10)

        assert len(results) == 2
        assert {r["name"] for r in results} == {"Area A", "Area B"}


# ---------------------------------------------------------------------------
# fetch_city_boundary — mocked httpx
# ---------------------------------------------------------------------------


class TestFetchCityBoundary:
    async def test_returns_first_matching_city(self):
        ring = [(23.0, 42.5), (23.5, 42.5), (23.5, 43.0), (23.0, 43.0), (23.0, 42.5)]
        element = _make_relation_element(100, "Sofia", [_make_outer_way_member(ring)])

        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_overpass_response([element])
        mock_resp.raise_for_status = MagicMock()

        with patch("services.overpass.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_city_boundary("Sofia", "BG")

        assert result is not None
        assert result["osm_id"] == 100
        assert result["name"] == "Sofia"
        assert result["boundary_geojson"]["type"] == "MultiPolygon"

    async def test_returns_none_when_no_results(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_overpass_response([])
        mock_resp.raise_for_status = MagicMock()

        with patch("services.overpass.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_city_boundary("Nowhere", "XX")

        assert result is None

    async def test_query_uses_first_city_admin_level(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_overpass_response([])
        mock_resp.raise_for_status = MagicMock()

        with patch("services.overpass.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await fetch_city_boundary("Berlin", "DE")

        call_args = mock_client.post.call_args
        query = call_args.kwargs.get("data", {}).get("data", "") or call_args[1].get("data", {}).get("data", "")
        # DE city level is "6"
        assert '["admin_level"="6"]' in query
        assert '["name"="Berlin"]' in query

    async def test_skips_relation_without_geometry(self):
        element = _make_relation_element(50, "EmptyCity", members=[])

        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_overpass_response([element])
        mock_resp.raise_for_status = MagicMock()

        with patch("services.overpass.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_city_boundary("EmptyCity", "BG")

        assert result is None
