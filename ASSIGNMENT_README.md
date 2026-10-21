# Assignment 3: Unit Test Automation (cachetools)

Project: [cachetools](https://github.com/tkem/cachetools) (version 7.2.4, forked)
Python used: 3.14.7 on Windows
Group: Mian Dawood (24F-3053), Muhammad Dawood (24F-3054)

## Setup

```
git clone https://github.com/MuhammadDawood149/cachetools.git
cd cachetools
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
pip install pytest pytest-xdist pytest-order
pytest
```

Expected result: the project's own 366 tests pass.

- Setup evidence (terminal output): `assignment_docs/setup_output_muhammad.txt`
- Setup video: `assignment_docs/setup_video.mp4`

## Running the assignment tests

```
pytest assignment_tests -q
```

## Layout

| Path | Contents |
|---|---|
| `notes/` | ECP/BVA notes, one file per person |
| `assignment_tests/` | Automated unit tests, one or more files per person |
| `assignment_docs/` | Setup evidence and setup video |

## Who did what

| Item | Muhammad Dawood | Mian Dawood |
|---|---|---|
| Task 1: setup evidence and instructions | Yes | |
| Task 1: setup video | | Yes |
| Task 2: classes covered | `LRUCache` (all methods), `TTLCache` expiry half (`ttl`, `timer`, `__contains__`, `__iter__`, `expire`) | (Mian fills in his own classes and files here) |
| Task 2: notes | `notes/ecp_bva_muhammad.md` | (Mian fills in) |
| Task 2: tests | `assignment_tests/test_lru_muhammad.py`, `assignment_tests/test_ttl_expiry_muhammad.py` | (Mian fills in) |
| Task 3 | (to be filled in) | (to be filled in) |
| Task 4 | (to be filled in) | (to be filled in) |

Note on commit authorship: the first commit (`ae6f5c6`, "Task 1: add setup evidence
and run instructions") was made by Muhammad Dawood on a shared laptop whose global
Git identity was set to `saimqamar149`, so GitHub shows that username as the author.
All later commits use each person's own Git identity.