## Environment notes
- The registry was created in Colab, so the Docker volume was seeded from the
  backup (`mlflow.db` and `mlruns`), and the Colab artifact paths stored in the
  database were rewritten to `/mlflow-data/mlruns`.
- The lab says "Staging"; I used the `champion` alias, since `serve.py` loads
  `models:/food11@champion`.
- `inference` mounts the volume read-write: the MLflow client reads local model
  files and writes a small metadata file next to them (a read-only mount failed).
- `--allowed-hosts "*"` was added to the MLflow command (newer MLflow rejects
  unknown Host headers).

### Question 1
Without a volume, `/mlflow-data` lives in the container's writable layer. A
standalone container on port 5001 showed only an empty `Default` experiment, and
after `docker rm -f` and a new container from the same image it was empty again
(fresh creation time). Data is deleted with the container; only a volume survives.

### Question 2
A named volume is managed by Docker: no host path dependency, same behaviour on
Windows/Mac/Linux, fewer permission and path problems. A bind mount would work
for local development, but ties the setup to one machine's folder layout, is
slower on Windows, and could put `mlflow.db` and `mlruns` inside the git repo
(which we ignore on purpose).

### Question 3
Compose creates a private network (`mlops-lab-1_default`) with an embedded DNS
server that resolves each service name to its container. In Lab 3 the container
was on the default bridge network, which has no name resolution between
containers, so we had to go through the host.

### Question 4
`inference` exists only as a Compose service name. A hardcoded name would not
resolve if the frontend image ran on its own. An environment variable lets the
same image work anywhere (`http://127.0.0.1:8000`, another host, production)
without a rebuild.

### Question 5
Only humans' browsers need `mlflow` and `frontend`. `inference` is called only by
the frontend over the Compose network, where all ports are reachable without
publishing; not publishing keeps it off the host. Verified from inside the
network: `docker compose exec frontend python -c "import requests;
print(requests.get('http://inference:8000/health').text)"` returned
`{"status":"ok"}`.

### Question 6
`depends_on` only waits for the MLflow container process to start. If `serve.py`
calls `load_model` before the server accepts connections, it raises at import,
uvicorn exits and the `inference` container stops (and stays down without a
restart policy). Fixes: a healthcheck on `mlflow` with
`depends_on: condition: service_healthy`, `restart: on-failure`, or a retry loop.
I saw the same crash after `down -v` (model not found), though that was a missing
model, not a startup-order problem.

### Question 7
`docker compose ps` shows `frontend` (`0.0.0.0:8501->8501`) and `mlflow`
(`0.0.0.0:5000->5000`) published, and `inference` showing only `8000/tcp`
(exposed inside the network, not published). This matches the compose file.

### Question 8
`serve.py` loads the model once at startup, so a running container keeps the
version it loaded. I registered version 2 and moved `champion` to it, then ran
`docker compose restart inference`, which re-resolves `champion` with no rebuild.
Version 2 has identical weights, so predictions did not change.

### Question 9
The image contains only code and the Python environment. The model is fetched at
startup through the registry URI, so a restart re-resolves `champion`.

### Question 10
After `docker compose down` then `up -d`, the registry survived because the named
volume was kept. After `down -v` the volume was deleted: the registry was empty
and `inference` failed with `RESOURCE_DOES_NOT_EXIST: Registered Model with
name=food11 not found`. I restored it by re-seeding the volume from the backup
(version 2 was lost, since it only existed in the deleted volume).

### Question 11
Compose has no built-in load balancer, multi-node scheduling, autoscaling or
cross-machine service discovery, so it cannot run three `inference` replicas
behind a load balancer in a useful way. For `mlflow` to survive a machine
failure, it would need multi-node scheduling with automatic rescheduling, a
database other than a SQLite file on one volume (e.g. Postgres), and shared
artifact storage (e.g. S3). Kubernetes provides replicas, health checks,
rescheduling and load balancing.