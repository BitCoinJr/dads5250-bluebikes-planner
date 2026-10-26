import unittest
import pandas as pd
from bluebikes.forecast import forecast_2026,error_metrics


class ForecastTest(unittest.TestCase):
    def setUp(self):
        self.data=pd.DataFrame([dict(year=y,month=m,city=c,demand_bikes=100.*m)
                                for y in [2024,2025] for m in range(1,13) for c in ['Boston','Cambridge']])

    def test_no_2026_leakage(self):
        a,_,_=forecast_2026(self.data)
        poisoned=pd.concat([self.data,pd.DataFrame([dict(year=2026,month=1,city='Boston',demand_bikes=1e12)])])
        b,_,_=forecast_2026(poisoned)
        pd.testing.assert_frame_equal(a,b)
        self.assertEqual(len(a),24)

    def test_missing_month_fails(self):
        with self.assertRaises(ValueError): forecast_2026(self.data.iloc[1:])

    def test_wape(self):
        self.assertAlmostEqual(error_metrics([100,200],[120,180])['wape'],40/300)


if __name__=='__main__': unittest.main()
