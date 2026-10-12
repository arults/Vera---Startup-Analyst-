"""Synthetic cohort-key regressions; not scientific outcome validation."""
import itertools
import unittest

from src.phase1c.reporting import (
    CellStats, adjacent_pool_order, maturity_block, pool_adjacent_years,
)


class PoolKeyIntegrityTests(unittest.TestCase):
    def test_out_of_scope_target_never_reports_neighbor(self):
        cells = [CellStats(year, 30, 5, 30) for year in range(2020, 2026)]
        for target in (2019, 2026, -1, 9999):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'year_out_of_scope'):
                pool_adjacent_years(target, cells)

    def test_invalid_year_types_all_entry_points(self):
        for year in (True, False, None, '2022', 2022.0, 2022.5,
                     float('nan'), float('inf'), [], {}):
            for fn in (
                lambda: CellStats(year, 30, 5, 30),
                lambda: maturity_block(year),
                lambda: adjacent_pool_order(year),
                lambda: pool_adjacent_years(year, [CellStats(2022, 30, 5, 30)]),
                lambda: pool_adjacent_years(year, []),
            ):
                with self.subTest(year=repr(year)), self.assertRaisesRegex(ValueError, 'invalid_year'):
                    fn()

    def test_cell_year_scope_rejected_at_construction(self):
        for year in (2019, 2026):
            with self.subTest(year=year), self.assertRaisesRegex(ValueError, 'year_out_of_scope'):
                CellStats(year, 30, 5, 30)

    def test_conflicting_duplicate_cells_rejected_in_every_order(self):
        low = CellStats(2022, 2, 0, 0)
        high = CellStats(2022, 30, 5, 30)
        adjacent = CellStats(2021, 20, 3, 18)
        for cells in itertools.permutations((low, high, adjacent)):
            with self.subTest(cells=cells), self.assertRaisesRegex(ValueError, 'duplicate_year_cell'):
                pool_adjacent_years(2022, list(cells))

    def test_identical_duplicate_cells_not_silently_deduplicated(self):
        cell = CellStats(2022, 30, 5, 30)
        with self.assertRaisesRegex(ValueError, 'duplicate_year_cell'):
            pool_adjacent_years(2022, [cell, cell])

    def test_duplicate_outside_target_block_not_silently_ignored(self):
        cells = [CellStats(2022, 30, 5, 30), CellStats(2024, 0, 0, 0),
                 CellStats(2024, 1, 0, 0)]
        with self.assertRaisesRegex(ValueError, 'duplicate_year_cell'):
            pool_adjacent_years(2022, cells)

    def test_all_valid_targets_keep_original_order(self):
        expected = {
            2020: [2020, 2021, 2022, 2023],
            2021: [2021, 2020, 2022, 2023],
            2022: [2022, 2021, 2023, 2020],
            2023: [2023, 2022, 2021, 2020],
            2024: [2024, 2025], 2025: [2025, 2024],
        }
        for target, order in expected.items():
            with self.subTest(target=target):
                self.assertEqual(adjacent_pool_order(target), order)

    def test_valid_unique_cell_permutations_preserve_result(self):
        cells = [CellStats(2022, 18, 3, 16), CellStats(2021, 20, 3, 18),
                 CellStats(2023, 5, 0, 4), CellStats(2024, 100, 50, 100)]
        expected = pool_adjacent_years(2022, cells)
        self.assertEqual(expected.years, (2021, 2022))
        self.assertEqual((expected.n, expected.informative_events, expected.ascertained), (38, 6, 34))
        for permutation in itertools.permutations(cells):
            with self.subTest(permutation=permutation):
                self.assertEqual(pool_adjacent_years(2022, list(permutation)), expected)

    def test_maturity_boundary_stays_separate(self):
        result = pool_adjacent_years(2025, [CellStats(2023, 100, 50, 100),
                                          CellStats(2024, 10, 1, 10),
                                          CellStats(2025, 10, 1, 10)])
        self.assertEqual(result.years, (2024, 2025))
        self.assertTrue(result.suppressed)
        self.assertFalse(result.crossed_maturity_boundary)

    def test_empty_valid_target_preserves_suppression(self):
        result = pool_adjacent_years(2022, [])
        self.assertEqual(result.years, ())
        self.assertEqual(result.n, 0)
        self.assertTrue(result.suppressed)

    def test_inputs_unchanged_after_success_and_rejection(self):
        cells = [CellStats(2022, 18, 3, 16), CellStats(2021, 20, 3, 18)]
        original = cells.copy()
        pool_adjacent_years(2022, cells)
        self.assertEqual(cells, original)
        cells.append(cells[0]); original = cells.copy()
        with self.assertRaises(ValueError):
            pool_adjacent_years(2022, cells)
        self.assertEqual(cells, original)


if __name__ == '__main__':
    unittest.main()
