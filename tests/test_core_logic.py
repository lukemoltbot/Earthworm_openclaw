import unittest
import os
import pandas as pd
import numpy as np
import lasio

# Import core modules
from ..src.core import data_processor
from ..src.core import analyzer
from ..src.core import output_generator

class TestCoreLogic(unittest.TestCase):

    def setUp(self):
        """
        Set up a temporary .las file for testing.
        """
        self.test_las_file = 'test_data.las'
        self.output_csv_file = 'test_units_output.csv'
        self.create_test_las_file()

        self.mnemonic_map = {'gamma': 'GR', 'density': 'RHOB'}
        self.lithology_rules = [
            {'name': 'Coal', 'code': 'CO', 'gamma_min': 0, 'gamma_max': 20, 'density_min': 0, 'density_max': 1.8},
            {'name': 'Sandstone', 'code': 'SS', 'gamma_min': 21, 'gamma_max': 50, 'density_min': 2.0, 'density_max': 2.7},
            {'name': 'Shale', 'code': 'SH', 'gamma_min': 51, 'gamma_max': 100, 'density_min': 2.5, 'density_max': 3.0}
        ]
        self.null_value = -999.25

    def tearDown(self):
        """
        Clean up temporary files after tests.
        """
        if os.path.exists(self.test_las_file):
            os.remove(self.test_las_file)
        if os.path.exists(self.output_csv_file):
            os.remove(self.output_csv_file)

    def create_test_las_file(self):
        """
        Programmatically creates a small .las file for testing.
        """
        # Define curves
        depth = np.arange(0, 10, 0.5) # DEPT from 0 to 9.5 with 0.5 interval
        gr = np.array([
            15, 16, 18, # Coal (0-1.5)
            25, 28, 30, # Sandstone (2.0-3.0)
            60, 62, 65, # Shale (3.5-4.5)
            10, 12, 14, # Coal (5.0-6.0)
            35, 38, 40, # Sandstone (6.5-7.5)
            70, 72, 75, # Shale (8.0-9.0)
            -999.25, -999.25 # Null values
        ])
        rhob = np.array([
            1.5, 1.6, 1.7, # Coal
            2.2, 2.3, 2.4, # Sandstone
            2.6, 2.7, 2.8, # Shale
            1.2, 1.3, 1.4, # Coal
            2.1, 2.2, 2.3, # Sandstone
            2.7, 2.8, 2.9, # Shale
            -999.25, -999.25 # Null values
        ])

        # Ensure all arrays have the same length
        min_len = min(len(depth), len(gr), len(rhob))
        depth = depth[:min_len]
        gr = gr[:min_len]
        rhob = rhob[:min_len]

        # Create a LAS file object
        l = lasio.LASFile()

        # Append curve data
        l.append_curve(mnemonic='DEPT', data=depth, unit='M')
        l.append_curve(mnemonic='GR', data=gr, unit='API')
        l.append_curve(mnemonic='RHOB', data=rhob, unit='G/CM3')

        # Add some header information
        l.well.WELL = 'Test Well'
        l.well.FLD = 'Test Field'
        l.well.LOC = 'Test Location'
        l.well.PROV = 'Test Province'
        l.well.SRVC = 'Test Service'
        l.well.DATE = '2023-01-01'

        # Write to file
        l.write(self.test_las_file, version=2.0)

    def test_full_headless_pipeline(self):
        """
        Tests the entire headless data processing and analysis pipeline.
        """
        # 1. Load LAS file
        df, mnemonics = data_processor.load_las_file(self.test_las_file)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIsInstance(mnemonics, list)
        self.assertIn('DEPT', df.columns)
        self.assertIn('GR', mnemonics)
        self.assertIn('RHOB', mnemonics)

        # 2. Preprocess data
        processed_df = data_processor.preprocess_data(df, self.mnemonic_map, self.null_value)
        self.assertIsInstance(processed_df, pd.DataFrame)
        self.assertIn('gamma', processed_df.columns)
        self.assertIn('density', processed_df.columns)
        self.assertTrue(np.isnan(processed_df['gamma'].iloc[-1])) # Check for NaN replacement

        # 3. Classify rows
        classified_df = analyzer.classify_rows(processed_df, self.lithology_rules)
        self.assertIsInstance(classified_df, pd.DataFrame)
        self.assertIn('LITHOLOGY_CODE', classified_df.columns)
        self.assertFalse((classified_df['LITHOLOGY_CODE'] == 'UNCLASSIFIED').all()) # Ensure some classification happened

        # Check specific classifications
        # Coal: GR 15, RHOB 1.5 -> CO
        self.assertEqual(classified_df.loc[0, 'LITHOLOGY_CODE'], 'CO')
        # Sandstone: GR 25, RHOB 2.2 -> SS
        self.assertEqual(classified_df.loc[3, 'LITHOLOGY_CODE'], 'SS')
        # Shale: GR 60, RHOB 2.6 -> SH
        self.assertEqual(classified_df.loc[6, 'LITHOLOGY_CODE'], 'SH')
        # Check that null values remain unclassified or are handled correctly (should be NaN, so not classified)
        self.assertEqual(classified_df.loc[classified_df.index[-1], 'LITHOLOGY_CODE'], 'UNCLASSIFIED')


        # 4. Group into units
        units_df = analyzer.group_into_units(classified_df, 'DEPT')
        self.assertIsInstance(units_df, pd.DataFrame)
        self.assertIn('from_depth', units_df.columns)
        self.assertIn('to_depth', units_df.columns)
        self.assertIn('thickness', units_df.columns)
        self.assertIn('lithology_code', units_df.columns)
        self.assertGreater(len(units_df), 0)

        # Expected units based on test data and rules:
        # 0.0-1.5: CO (3 rows)
        # 2.0-3.0: SS (3 rows)
        # 3.5-4.5: SH (3 rows)
        # 5.0-6.0: CO (3 rows)
        # 6.5-7.5: SS (3 rows)
        # 8.0-9.0: SH (3 rows)
        # 9.5: UNCLASSIFIED (1 row)

        # Verify the first unit
        self.assertEqual(units_df.loc[0, 'from_depth'], 0.0)
        self.assertEqual(units_df.loc[0, 'to_depth'], 1.0) # Depth of last CO row is 1.0
        self.assertEqual(units_df.loc[0, 'lithology_code'], 'CO')
        self.assertAlmostEqual(units_df.loc[0, 'thickness'], 1.0)

        # Verify the second unit
        self.assertEqual(units_df.loc[1, 'from_depth'], 1.5) # Depth of first SS row is 1.5
        self.assertEqual(units_df.loc[1, 'to_depth'], 2.5) # Depth of last SS row is 2.5
        self.assertEqual(units_df.loc[1, 'lithology_code'], 'SS')
        self.assertAlmostEqual(units_df.loc[1, 'thickness'], 1.0)

        # Verify the third unit
        self.assertEqual(units_df.loc[2, 'from_depth'], 3.0) # Depth of first SH row is 3.0
        self.assertEqual(units_df.loc[2, 'to_depth'], 4.0) # Depth of last SH row is 4.0
        self.assertEqual(units_df.loc[2, 'lithology_code'], 'SH')
        self.assertAlmostEqual(units_df.loc[2, 'thickness'], 1.0)

        # Verify the last classified unit (Shale)
        self.assertEqual(units_df.loc[5, 'from_depth'], 7.5)
        self.assertEqual(units_df.loc[5, 'to_depth'], 8.5)
        self.assertEqual(units_df.loc[5, 'lithology_code'], 'SH')
        self.assertAlmostEqual(units_df.loc[5, 'thickness'], 1.0)

        # Verify the unclassified unit at the end
        self.assertEqual(units_df.loc[6, 'from_depth'], 9.0)
        self.assertEqual(units_df.loc[6, 'to_depth'], 9.5)
        self.assertEqual(units_df.loc[6, 'lithology_code'], 'UNCLASSIFIED')
        self.assertAlmostEqual(units_df.loc[6, 'thickness'], 0.5)


        # 5. Write units to CSV
        output_generator.write_units_to_csv(units_df, self.output_csv_file)
        self.assertTrue(os.path.exists(self.output_csv_file))

        # Verify CSV content
        read_csv = pd.read_csv(self.output_csv_file)
        pd.testing.assert_frame_equal(units_df, read_csv)

if __name__ == '__main__':
    unittest.main()
