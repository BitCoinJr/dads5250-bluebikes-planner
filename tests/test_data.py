from contextlib import contextmanager
import unittest
from pathlib import Path
from uuid import uuid4
import pandas as pd
from bluebikes.data import aggregate_trips, normalize_name

TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "cache" / "tests"


@contextmanager
def temporary_directory():
    # Workspace-local temp files also work under Windows restricted sandboxes.
    folder = TEMP_ROOT / uuid4().hex
    folder.mkdir(parents=True)
    try:
        yield folder
    finally:
        for child in folder.iterdir():
            child.unlink()
        folder.rmdir()


class DataTests(unittest.TestCase):
    def test_endpoint_time_and_dedup_across_chunks(self):
        rows=[{"ride_id":"0001","started_at":"2024-01-31 23:59:00","ended_at":"2024-02-01 00:02:00","start_station_name":" A ","end_station_name":"B","start_station_id":"001","end_station_id":"002","rideable_type":"electric_bike"}]
        rows.append(rows[0].copy())
        rows.append(dict(rows[0],ride_id="0002",start_station_name="unmatched",ended_at="invalid"))
        stations=pd.DataFrame({"station_key":["a","b"]})
        with temporary_directory() as d:
            p=Path(d)/"trips.csv"
            pd.DataFrame(rows).to_csv(p,index=False)
            h,stats=aggregate_trips(p,stations,chunksize=1)
        self.assertEqual(stats["duplicate_ride_ids_removed"],1)
        self.assertEqual(stats["invalid_timestamps_or_negative_duration"],1)
        self.assertEqual(h.departures.sum(),1)
        self.assertEqual(h.arrivals.sum(),1)
        self.assertEqual(h.loc[h.arrivals.eq(1),"hour"].iloc[0],pd.Timestamp("2024-02-01"))
        self.assertEqual(h.ebike_departures.sum(),1)
        self.assertEqual(normalize_name(" A  St "),"a st")

    def test_unmatched_endpoint_not_guessed(self):
        row={"ride_id":"x","started_at":"2024-01-01","ended_at":"2024-01-01 01:00","start_station_name":"missing","end_station_name":"known","rideable_type":"classic_bike"}
        with temporary_directory() as d:
            p=Path(d)/"trip.csv"; pd.DataFrame([row]).to_csv(p,index=False)
            h,s=aggregate_trips(p,pd.DataFrame({"station_key":["known"]}))
        self.assertEqual(h.departures.sum(),0)
        self.assertEqual(h.arrivals.sum(),1)
        self.assertEqual(s["start_join_rate"],0)
        self.assertEqual(s["end_join_rate"],1)

    def test_cross_archive_exclusion(self):
        row={"ride_id":"0000000000000001","started_at":"2024-05-31 23:59","ended_at":"2024-06-01 00:01","start_station_name":"known","end_station_name":"known"}
        with temporary_directory() as d:
            p=Path(d)/"trip.csv"; pd.DataFrame([row]).to_csv(p,index=False)
            h,s=aggregate_trips(p,pd.DataFrame({"station_key":["known"]}),exclude_ride_ids={"0000000000000001"})
        self.assertEqual(s["raw_rows"],1)
        self.assertEqual(s["valid_rows"],0)
        self.assertEqual(s["cross_archive_duplicate_ids_removed"],1)
        self.assertTrue(h.empty)


if __name__ == "__main__": unittest.main()
