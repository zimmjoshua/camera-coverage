#!/usr/bin/env python3
"""Decide whether a set of hardware cameras can act as one software camera.

Each hardware camera covers one closed rectangle in (subject distance, light
level) space: it can take a shot only when both measurements fall inside its
ranges. The software camera has to support every combination inside the
required distance range and the required light range, so the hardware
rectangles must cover that whole required rectangle.

Covering each axis separately is not enough. A camera that handles far
subjects only in bright light does not help with a far, dark subject.
"""

import math
import random
import unittest
from collections.abc import Sequence

Number = float
Range = tuple[Number, Number]
Camera = tuple[Range, Range]


def cameras_suffice(required_distance, required_light, cameras):
    """Return True when `cameras` can take every required shot.

    required_distance: (low, high), inclusive
    required_light: (low, high), inclusive
    cameras: iterable of ((distance_low, distance_high), (light_low, light_high))

    All four endpoints of a range are included. Two cameras that meet at an
    endpoint together cover that point. Comparisons are exact, so callers
    should pass the real endpoints rather than rounded measurements.

    Time is O(n^2 log n) and extra space is O(n), where n is the number of
    cameras that intersect the required rectangle. A segment tree on the light
    axis would bring the checks down to O(n log n); the sweep below is the
    part that decides the question.
    """
    distance = _parse_range(required_distance, "required distance")
    light = _parse_range(required_light, "required light")
    clipped = []
    for index, camera in enumerate(cameras):
        camera_distance, camera_light = _parse_camera(camera, index)
        overlap_distance = _intersect(camera_distance, distance)
        overlap_light = _intersect(camera_light, light)
        if overlap_distance is None or overlap_light is None:
            continue
        clipped.append((overlap_distance, overlap_light))

    if not clipped:
        return False

    # Sweep across subject distance. At each camera edge, the active cameras
    # are those whose closed distance range contains that x. Their light
    # ranges have to cover the required light range, both at the edge and on
    # the open span leading up to it.
    events = []
    for index, (camera_distance, _) in enumerate(clipped):
        events.append((camera_distance[0], index, "start"))
        events.append((camera_distance[1], index, "end"))
    events.sort(key=lambda event: event[0])

    if events[0][0] > distance[0]:
        return False

    active_light = {}
    previous_x = distance[0]
    cursor = 0
    while cursor < len(events):
        x = events[cursor][0]
        if x > distance[1]:
            break

        starts = []
        ends = []
        while cursor < len(events) and events[cursor][0] == x:
            _, index, kind = events[cursor]
            if kind == "start":
                starts.append(index)
            else:
                ends.append(index)
            cursor += 1

        if x > previous_x and not _intervals_cover(active_light.values(), light):
            return False

        for index in starts:
            active_light[index] = clipped[index][1]

        if not _intervals_cover(active_light.values(), light):
            return False

        for index in ends:
            del active_light[index]

        previous_x = x

    if previous_x < distance[1]:
        return _intervals_cover(active_light.values(), light)
    return True


def _parse_camera(camera, index):
    label = "camera %d" % index
    try:
        distance, light = camera
    except (TypeError, ValueError) as error:
        raise TypeError("%s must be (distance_range, light_range)" % label) from error
    return _parse_range(distance, "%s distance" % label), _parse_range(light, "%s light" % label)


def _parse_range(value, label):
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 2:
        raise ValueError("%s must be a (low, high) pair" % label)
    low = _parse_number(value[0], "%s low" % label)
    high = _parse_number(value[1], "%s high" % label)
    if low > high:
        raise ValueError("%s low must be less than or equal to high" % label)
    return (low, high)


def _parse_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or isinstance(value, complex):
        raise TypeError("%s must be a real number" % label)
    if not math.isfinite(value):
        raise ValueError("%s must be finite" % label)
    return value


def _intersect(left, right):
    low = left[0] if left[0] > right[0] else right[0]
    high = left[1] if left[1] < right[1] else right[1]
    if low > high:
        return None
    return (low, high)


def _intervals_cover(intervals, required):
    low, high = required
    covered_to = low
    covered_anything = False
    for start, end in sorted(intervals):
        if end < low:
            continue
        if start > covered_to:
            return False
        covered_anything = True
        if end > covered_to:
            covered_to = end
        if covered_to >= high:
            return True
    return covered_anything and covered_to >= high


class CamerasSufficeTests(unittest.TestCase):
    def test_one_camera_covers_the_required_rectangle(self):
        cameras = [((0, 10), (0, 10))]
        self.assertTrue(cameras_suffice((0, 10), (0, 10), cameras))

    def test_a_camera_larger_than_the_requirement_covers_it(self):
        cameras = [((-20, 40), (-5, 50))]
        self.assertTrue(cameras_suffice((0, 10), (1, 4), cameras))

    def test_a_camera_that_misses_either_axis_is_not_enough(self):
        self.assertFalse(cameras_suffice((0, 10), (0, 10), [((0, 10), (0, 9))]))
        self.assertFalse(cameras_suffice((0, 10), (0, 10), [((0, 9), (0, 10))]))

    def test_no_cameras_cannot_cover_a_shot(self):
        self.assertFalse(cameras_suffice((0, 0), (3, 3), []))

    def test_cameras_can_split_the_work_by_distance(self):
        cameras = [
            ((0, 5), (0, 10)),
            ((5, 10), (0, 10)),
        ]
        self.assertTrue(cameras_suffice((0, 10), (0, 10), cameras))

    def test_cameras_can_split_the_work_by_light(self):
        cameras = [
            ((0, 10), (0, 4)),
            ((0, 10), (4, 10)),
        ]
        self.assertTrue(cameras_suffice((0, 10), (0, 10), cameras))

    def test_a_gap_between_cameras_leaves_shots_uncovered(self):
        cameras = [
            ((0, 4), (0, 10)),
            ((6, 10), (0, 10)),
        ]
        self.assertFalse(cameras_suffice((0, 10), (0, 10), cameras))

    def test_meeting_at_an_endpoint_counts_as_covered(self):
        cameras = [
            ((0, 5), (0, 10)),
            ((5, 10), (0, 10)),
        ]
        self.assertTrue(cameras_suffice((0, 10), (0, 10), cameras))

    def test_axis_coverage_alone_does_not_cover_the_rectangle(self):
        # Distance 0..10 is covered, and light 0..10 is covered, but a far
        # dark shot is not. Checking the two ranges independently would be wrong.
        cameras = [
            ((0, 5), (0, 10)),
            ((5, 10), (7, 10)),
        ]
        self.assertFalse(cameras_suffice((0, 10), (0, 10), cameras))

    def test_partial_light_on_part_of_the_distance_range_fails(self):
        cameras = [
            ((0, 10), (0, 5)),
            ((0, 5), (5, 10)),
        ]
        self.assertFalse(cameras_suffice((0, 10), (0, 10), cameras))

    def test_a_grid_of_cameras_covers_when_every_cell_is_present(self):
        cameras = [
            ((0, 5), (0, 5)),
            ((0, 5), (5, 10)),
            ((5, 10), (0, 5)),
            ((5, 10), (5, 10)),
        ]
        self.assertTrue(cameras_suffice((0, 10), (0, 10), cameras))
        self.assertFalse(
            cameras_suffice(
                (0, 10),
                (0, 10),
                cameras[:-1],
            )
        )

    def test_overlap_and_cameras_outside_the_target_are_fine(self):
        cameras = [
            ((-10, 6), (-10, 20)),
            ((4, 30), (0, 10)),
            ((100, 120), (100, 120)),
        ]
        self.assertTrue(cameras_suffice((0, 10), (0, 10), cameras))

    def test_a_single_required_point_needs_a_camera_that_contains_it(self):
        cameras = [((0, 5), (0, 5))]
        self.assertTrue(cameras_suffice((5, 5), (5, 5), cameras))
        self.assertFalse(cameras_suffice((6, 6), (5, 5), cameras))

    def test_a_zero_width_light_range_is_a_line_that_must_be_covered(self):
        cameras = [
            ((0, 4), (2, 2)),
            ((4, 8), (2, 2)),
        ]
        self.assertTrue(cameras_suffice((0, 8), (2, 2), cameras))
        self.assertFalse(cameras_suffice((0, 8), (3, 3), cameras))

    def test_fractional_ranges_use_exact_endpoints(self):
        halves = [
            ((0, 0.5), (0, 1)),
            ((0.5, 1), (0, 1)),
        ]
        self.assertTrue(cameras_suffice((0, 1), (0, 1), halves))
        gap = [
            ((0, 0.5), (0, 1)),
            ((0.75, 1), (0, 1)),
        ]
        self.assertFalse(cameras_suffice((0, 1), (0, 1), gap))

    def test_negative_ranges(self):
        cameras = [
            ((-10, -5), (-2, 0)),
            ((-5, 0), (-2, 0)),
        ]
        self.assertTrue(cameras_suffice((-10, 0), (-2, 0), cameras))

    def test_duplicate_cameras_do_not_create_extra_coverage(self):
        camera = ((0, 3), (0, 3))
        self.assertFalse(cameras_suffice((0, 4), (0, 3), [camera, camera]))

    def test_rejects_inverted_and_non_numeric_ranges(self):
        with self.assertRaises(ValueError):
            cameras_suffice((5, 4), (0, 1), [])
        with self.assertRaises(ValueError):
            cameras_suffice((0, 1), (1, 0), [])
        with self.assertRaises(ValueError):
            cameras_suffice((0, 1), (0, 1), [((2, 1), (0, 1))])
        with self.assertRaises(TypeError):
            cameras_suffice((True, 1), (0, 1), [])
        with self.assertRaises(ValueError):
            cameras_suffice((0, float("inf")), (0, 1), [])
        with self.assertRaises(TypeError):
            cameras_suffice((0, 1), (0, 1), [((0, 1),)])

    def test_matches_cell_coverage_for_random_integer_ranges(self):
        rng = random.Random(6)
        for _ in range(300):
            distance = _random_range(rng, 0, 12)
            light = _random_range(rng, 0, 12)
            cameras = [
                (_random_range(rng, -1, 14), _random_range(rng, -1, 14))
                for _ in range(rng.randint(0, 7))
            ]
            expected = _integer_rectangles_cover(distance, light, cameras)
            actual = cameras_suffice(distance, light, cameras)
            self.assertEqual(
                actual,
                expected,
                "distance=%s light=%s cameras=%s" % (distance, light, cameras),
            )


def _random_range(rng, low, high):
    start = rng.randint(low, high)
    end = rng.randint(start, high)
    return (start, end)


def _integer_rectangles_cover(distance, light, cameras):
    """Exact cover check for ranges whose endpoints are integers.

    Integer-edged rectangles tile the required area into unit cells, and a
    unit cell is covered only when one camera contains it completely.
    """
    d0, d1 = distance
    l0, l1 = light
    if d0 == d1 and l0 == l1:
        return any(cd[0] <= d0 <= cd[1] and cl[0] <= l0 <= cl[1] for cd, cl in cameras)
    if d0 == d1:
        return all(
            any(cd[0] <= d0 <= cd[1] and cl[0] <= y and cl[1] >= y + 1 for cd, cl in cameras)
            for y in range(l0, l1)
        )
    if l0 == l1:
        return all(
            any(cl[0] <= l0 <= cl[1] and cd[0] <= x and cd[1] >= x + 1 for cd, cl in cameras)
            for x in range(d0, d1)
        )
    return all(
        any(cd[0] <= x and cd[1] >= x + 1 and cl[0] <= y and cl[1] >= y + 1 for cd, cl in cameras)
        for x in range(d0, d1)
        for y in range(l0, l1)
    )


if __name__ == "__main__":
    unittest.main()
