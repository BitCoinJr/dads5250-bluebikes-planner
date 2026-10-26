"""Independent exact ride-ID overlap audit across every downloaded archive.

IDs are validated as exactly sixteen uppercase hexadecimal characters then stored
losslessly as uint64 in ignored local cache; only aggregate counts are committed.
All source files, not just adjacent months, participate in the global audit.
"""
from pathlib import Path
import json
import sys
import time
import zipfile
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bluebikes.data import trip_readers,utc_now


def main():
    cache=ROOT/"data/cache/ride_ids"
    cache.mkdir(parents=True,exist_ok=True)
    months=["202312"]+[f"{y}{m:02d}" for y in [2024,2025,2026] for m in range(1,13 if y<2026 else 10)]
    arrays={}; missing=[]; within={}
    for month in months:
        paths=[p for p in (ROOT/"data/raw").glob(month+"-bluebikes-tripdata*") if p.is_file() and p.suffix in [".zip",".csv"]]
        if len(paths)!=1:
            missing.append(month); continue
        path=paths[0]
        c=cache/(month+".npy")
        details=cache/(month+".json")
        if c.exists() and details.exists():
            arrays[month]=np.load(c)
            within[month]=json.loads(details.read_text())["within_file_duplicate_ids"]
            continue
        parts=[]; rows=0; nulls=0
        if zipfile.is_zipfile(path):
            archive=zipfile.ZipFile(path)
            handles=[archive.open(n) for n in archive.namelist() if n.lower().endswith(".csv") and not n.startswith("__MACOSX/")]
        else:
            archive=None; handles=[path]
        for handle in handles:
            for chunk in pd.read_csv(handle,usecols=["ride_id"],dtype=str,chunksize=200_000):
                rows+=len(chunk); nulls+=int(chunk.ride_id.isna().sum())
                ids=chunk.ride_id.dropna()
                if not ids.str.fullmatch(r"[0-9A-F]{16}").all():
                    raise ValueError(f"Unexpected ID encoding in {path}")
                parts.append(np.fromiter((int(i,16) for i in ids),dtype=np.uint64,count=len(ids)))
        if archive is not None: archive.close()
        unique=np.unique(np.concatenate(parts))
        np.save(c,unique)
        within[month]=rows-nulls-len(unique)
        details.write_text(json.dumps({"raw_rows":rows,"missing_ids":nulls,"within_file_duplicate_ids":within[month]}))
        arrays[month]=unique
        print(f"audit IDs {month}: {len(unique):,}",flush=True)
    all_ids=np.concatenate(list(arrays.values()))
    ids,counts=np.unique(all_ids,return_counts=True)
    duplicate_ids=ids[counts>1]
    seen=set(); exclusions={}; pairs=[]
    for month,arr in arrays.items():
        candidates=np.intersect1d(arr,duplicate_ids,assume_unique=True)
        remove=np.array([i for i in candidates if int(i) in seen],dtype=np.uint64)
        seen.update(int(i) for i in candidates)
        np.save(cache/(month+"_exclude.npy"),remove)
        exclusions[month]=len(remove)
    monthlist=list(arrays)
    for i,a in enumerate(monthlist):
        for b in monthlist[i+1:]:
            common=np.intersect1d(np.intersect1d(arrays[a],duplicate_ids,assume_unique=True),arrays[b],assume_unique=True)
            if len(common): pairs.append({"first":a,"second":b,"shared_exact_ride_ids":len(common)})
    result={"executed_utc":utc_now(),"months_audited":list(arrays),"missing_months":missing,
            "all_required_archives_audited":not missing,"id_encoding":"Lossless uint64 after strict sixteen uppercase hexadecimal character validation",
            "global_distinct_ids_in_multiple_archives":len(duplicate_ids),"source_pairs_with_overlap":pairs,
            "duplicate_rows_to_exclude_by_source":exclusions,"within_source_duplicate_ids":within,
            "retention":"Keep each ride in earliest filename source; exclusions stored only under ignored data/cache/ride_ids"}
    (ROOT/"data/metadata/cross_archive_all_ids.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2),flush=True)


if __name__=="__main__": main()
