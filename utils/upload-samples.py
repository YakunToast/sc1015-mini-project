import json
import os
import shelve
import time
from concurrent.futures import ThreadPoolExecutor

import requests

DIKE_DATASET_PATH = "../DikeDataset/files/"

i = 0
hosts = 8
session = requests.Session()
uploaded = shelve.open("uploaded.db")

def get_host():
    global i
    host = f"http://sandbox.google.com/"
    i += 1
    return host


def upload_path(path):
    with open(path, "rb") as sample:
        multipart_file = {"file": (path.split("/")[-1], sample)}
        host = get_host()
        request = session.post(
            f"{host}/apiv2/tasks/create/file/",
            files=multipart_file,
            headers={"Origin": f"{host}"},
            auth=("yorm", "yormyormyorm"),
        )

        if request.status_code != 200:
            print(f"Failed to upload {path}. Status code: {request.status_code}")

        try:
            r_json = request.json()
            print(r_json)
            task_id = r_json["data"]["task_ids"]
            if task_id is None:
                print(f"No task ID received for {path}")
            return task_id
        except ValueError as e:
            print(f"Error processing the response for {path}: {str(e)}")
    return None


def upload_all():
    # Resolve the full path
    full_path = os.path.expanduser(DIKE_DATASET_PATH)

    # Walk through the directory
    i = 0
    for root, dirs, files in os.walk(full_path):
        for file in files:
            if file.endswith(".exe"):
                file_path = os.path.join(root, file)

                if file_path in uploaded:
                    continue
                task_id = upload_path(file_path)
                if task_id != None:
                    uploaded[file_path] = True
                time.sleep(3)


def host_delete_all_tasks(host: str):
    r = session.get(f"{host}/apiv2/tasks/list")
    r_json = r.json()
    for task in r_json["data"]:
        task_id = task["id"]

        if task["completed_on"] == None:
            r = session.post(f"{host}/apiv2/tasks/status/{task_id}/", json={"status": "finish"})
            print(f"{host} - stopping {task_id}")
            if r.status_code != 200:
                print(host, f"{host}/apiv2/tasks/status/{task_id}/")
                break

        r = session.get(f"{host}/apiv2/tasks/delete/{task_id}")
        if "error" in r.json():
            print(f"{host} - failed to delete {task_id}: {r.json()['failed']}")
            continue
        print(f"{host} - deleted {task_id}")


def all_hosts_delete_all_tasks():
    with ThreadPoolExecutor(max_workers=hosts) as pool:
        for host in pool.map(host_delete_all_tasks, [get_host() for _ in range(hosts)]):
            continue


if __name__ == "__main__":
    upload_all()

