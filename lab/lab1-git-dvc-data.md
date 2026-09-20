# Lab 1 - git/dvc and data preparation

## Remote Solution Adopted

I adopted **Option 1: Local remote**. The dvc remote is set to a local folder
(`../dvc-local-storage`) outside the git repository, rather than pushing to DagsHub.
This avoided upload speed/size issues while still demonstrating the full git+dvc
workflow (add, commit, push, pull, checkout).

---

### Question 1: uv init files

- `pyproject.toml` — project metadata (name, Python version requirement, dependencies list, build system). Modern replacement for `requirements.txt` + `setup.py`.
- `.python-version` — pins the exact Python version (3.14) for reproducibility.
- `src/mlops_lab_1/` — the actual Python package folder.
- `README.md` — empty placeholder for docs.
- No `.gitignore` was created by `uv init` — had to add one manually.
- No `uv.lock` yet — only appears after the first `uv add`.

### Question 2: dvc init files

- `.dvc/config` — stores dvc remote settings (empty until a remote is configured).
- `.dvc/.gitignore` — auto-created, excludes dvc's internal cache/tmp folders from git.
- `.dvc/tmp/` — dvc's internal scratch space, git-ignored.
- `.dvcignore` — dvc's own ignore file (like `.gitignore` but for dvc).

All of these except `.dvc/tmp/` should be (and were) pushed to git — they're small
metadata files, not the actual data.

### Question 3: dvc remote credentials

- `--global`: stored in a machine-wide dvc config (outside any repo), applies to all
  dvc projects on that machine.
- `--local`: stored in `.dvc/config.local`, inside the repo but automatically excluded
  from git via `.dvc/.gitignore`.
- Default (no flag): stored in `.dvc/config`, which **is** committed to git — fine for
  non-secret settings like a remote URL, but never for credentials.
- Since I used a local folder remote, no credentials were needed at all — the "remote"
  is just a filesystem path.
- Credentials should **never** be pushed to GitHub. This is exactly why `--local`
  exists: secrets should never enter git history, even briefly, since history is hard
  to fully erase once pushed.

### Question 4: .gitignore after `dvc add data`

`dvc add data` automatically appended `/data` to `.gitignore`. This tells git to stop
tracking the contents of the `data/` folder entirely — dvc now owns that folder. Git
only tracks the small pointer file (`data.dvc`) going forward.

### Question 5: data.dvc contents

Yes, a `data.dvc` file was created:

```yaml
outs:
- md5: a3a457d03c51ff8b037a833440f6ad13.dir
  size: 1188442712
  nfiles: 16643
  hash: md5
  path: data
```

It contains a directory hash (checksum of the whole `data/` folder's contents), the
total size in bytes, the file count, and the tracked path. This tiny file is what git
commits instead of the actual data — dvc uses it to reconstruct/verify the exact data
state later.

### Question 6: GitHub / DagsHub visibility

On GitHub (`main` branch):
- **Code**: present (`src/`, `pyproject.toml`, `uv.lock`, etc.)
- **Data**: NOT present — no `data/` folder in the repo listing.
- **Pointer file**: `data.dvc` is present, pointing to the data's location/hash.

DagsHub: not applicable — I used a local remote (Option 1), so there is no DagsHub
data storage involved. The actual data instead lives in `../dvc-local-storage`,
completely outside git.

### Question 7: Fresh clone test

After cloning the repo into a new folder, `data/` did not exist — only code and
`data.dvc` came from GitHub. Running `dvc pull` is needed to restore the data folder.

One nuance from using a local relative-path remote: the relative path in
`.dvc/config` (`../../dvc-local-storage`) only resolves correctly if the clone sits at
the same folder depth as the original repo. In my test clone (nested one level
deeper), `dvc pull` initially failed because the relative path pointed to a
non-existent location. I fixed this by running:

```bash
dvc remote modify origin --local url "<absolute-path-to-dvc-local-storage>"
```

After that, `dvc pull` succeeded and fetched all 16,643 files. With a real remote
like DagsHub (an absolute URL), this issue wouldn't occur — it's a trade-off specific
to the local-remote workaround.

### Question 8: Checking out an old commit

At the commit before `food11_processed`/`food11_processed_mini` were added
(`git log --oneline -- data.dvc` showed two commits touching that file), checking out
the older commit + running `dvc checkout` left only `food11_raw` — the newer
processed folders were gone, confirming the data changes with the commit.

Note: `dvc checkout` did not automatically delete the newer folders in my case (they
had to be removed manually) — likely because they existed as untracked extra
directories carried over from the newer commit's already-materialized workspace. On a
fresh clone this wouldn't happen, since those folders would never have existed
locally to begin with.

After switching back to `main` and running `dvc checkout` again, both
`food11_processed` and `food11_processed_mini` were correctly restored.