import atexit
import csv
import itertools
import json
import shelve

import pandas as pd
import requests
from loguru import logger as log
from pandas import *

downloaded = shelve.open("downloaded.db", writeback=True)

benign = read_csv("../DikeDataset/labels/benign.csv")["hash"].tolist()
malware = read_csv("../DikeDataset/labels/malware.csv")["hash"].tolist()


@atexit.register
def write_db():
    global calls
    # add to dataframe
    with open("downloaded.csv", "w") as f:
        csvwriter = csv.DictWriter(f, fieldnames=next(itertools.chain(*downloaded.values())).keys(), delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writeheader()
        for x in itertools.chain(*downloaded.values()):
            csvwriter.writerow(x)


def deduplicate(data):
    tortoise = data[0]
    hare = data[0]
    mu = 0

    # Find the intersection point of the two sequences
    while True:
        tortoise = data[mu % len(data)]
        hare = data[(2 * mu) % len(data)]
        if tortoise == hare:
            break
        mu += 1

    # Find the start of the cycle
    mu = 0
    tortoise = data[0]
    while tortoise != hare:
        tortoise = data[mu % len(data)]
        hare = data[mu % len(data)]
        mu += 1

    # Deduplicate based on process_id
    seen = set()
    deduplicated_data = []
    for i in range(mu, len(data)):
        if data[i]["process_id"] not in seen:
            seen.add(data[i]["process_id"])
            deduplicated_data.append(data[i])

    return deduplicated_data


for i in  range(1, 5000):
    if str(i) in downloaded:
        continue

    r = requests.get(f"http://sandbox.google.com/apiv2/tasks/get/report/{i}/")
    try:
        r_json = r.json()

        sha256 = r_json["target"]["file"]["sha256"]
        if sha256 not in benign and sha256 not in malware:
            continue

        malicious = 2
        if sha256 in malware:
            malicious = 1
        if sha256 in benign:
            malicious = 0

        # loop through all processes
        calls = []
        for process_id, process in enumerate(r_json["behavior"]["processes"]):
            # build api calls
            for api_call in process["calls"]:
                # build calls
                call = {
                    "file_id": i,
                    "file_hash": sha256,
                    "process_id": process_id,
                    "malicious": malicious,
                    "api": api_call["api"],
                    "tid": api_call["thread_id"],
                    "index": api_call["id"],
                }

                # add to calls
                calls.append(call)

        # # attempt to deduplicate calls
        # if len(calls) > 5:
        #     calls = deduplicate(calls)
        
        # add to database
        downloaded[str(i)] = calls
    except Exception as e:
        log.exception(e)
        # print(r.text)
        # print(r_json)

