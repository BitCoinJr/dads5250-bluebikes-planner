import unittest
import pandas as pd
from bluebikes.inventory import inventory_proxy


class InventoryTests(unittest.TestCase):
    def test_hand_count_with_resets(self):
        # docks=4 initial=2; 5 depart -> supply3 inv0; 7 arrive -> collect3 inv4;
        # reset -> collect2. Total handling=8, balanced supply3/collection5 with net2 arrivals.
        h = pd.DataFrame({"station_key":["a","a"],"hour":pd.to_datetime(["2024-01-01 01:00","2024-01-01 02:00"]),
                          "departures":[5,0],"arrivals":[0,7],"ebike_departures":[2,0]})
        s = pd.DataFrame({"station_key":["a"],"city":["Boston"],"docks":[4]})
        daily, m = inventory_proxy(h,s)
        row=m.iloc[0]
        self.assertEqual(row.demand_bikes, 8)
        self.assertEqual(row.supply_bikes, 3)
        self.assertEqual(row.collection_bikes,3)
        self.assertEqual(row.reset_collection_bikes,2)
        self.assertEqual(row.ebike_departures,2)

    def test_same_hour_netting_and_odd_docks(self):
        h=pd.DataFrame({"station_key":["a"],"hour":pd.to_datetime(["2024-01-01"]),"departures":[100],"arrivals":[100],"ebike_departures":[0]})
        s=pd.DataFrame({"station_key":["a"],"city":["Cambridge"],"docks":[3]})
        _,m=inventory_proxy(h,s)
        self.assertEqual(m.iloc[0].demand_bikes,0)

    def test_daily_reset_is_not_monthly_net(self):
        h=pd.DataFrame({"station_key":["a","a"],"hour":pd.to_datetime(["2024-01-01","2024-01-02"]),"departures":[4,0],"arrivals":[0,4],"ebike_departures":[0,0]})
        s=pd.DataFrame({"station_key":["a"],"city":["Boston"],"docks":[4]})
        _,m=inventory_proxy(h,s)
        self.assertEqual(m.iloc[0].demand_bikes,8)


if __name__ == "__main__": unittest.main()
