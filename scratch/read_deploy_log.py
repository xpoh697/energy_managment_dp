import os
import sys

paths = [
    r"robocopy_deploy.log",
    r"robocopy_deploy_diag.log",
]

for p in paths:
    print(f"--- {p} ---")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            print(f.read())
    else:
        print("Does not exist")
