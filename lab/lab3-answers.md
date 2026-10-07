## Environment note

Application Control on the managed laptop blocks MLflow and PyTorch, so the model
was registered in Google Colab (from the Lab 2 best run). The MLflow server and
registry were then run in a Docker container on the laptop, using the backup of
`mlflow.db` and `mlruns`, mounted at the same path stored in the database
(`/content/mlops-lab-1`). The API ran in a second container, built from the
Dockerfile. The container used `host.docker.internal:5000` to reach MLflow.

### Question 1: version number, artifact vs registered model
The model got **version 1**. A run's logged model artifact is just files inside
one run, found through the run ID. A registered model gives the model a stable
name and numbered versions independent of any run, with aliases and tags. It is
what other systems pull from.

### Question 2: aliases, versioning, flexibility
Aliases (such as `champion` and `challenger`) replaced the old stages. Versioning
separately from the run lets us reproduce, compare and roll back models without
caring which run produced them. An alias is more flexible than a fixed stage
because we can create any number of names and move one to another version without
changing code. A service that loads `models:/food11@champion` picks up the new
model automatically.

### Question 3: loading through a model URI
The URI asks the registry for whatever `champion` currently points to, so the code
does not depend on a file path, a run ID or the training framework. To serve a
newer model, register it as a new version and move the alias:
`client.set_registered_model_alias("food11", "champion", <new version>)`.
`serve.py` and the image do not change; the API only needs a restart to reload.

### Question 4: layer order and build cache
Docker caches each layer. Dependencies change rarely and source code changes
often, so `pyproject.toml` and `uv.lock` are copied and `uv sync` runs first. If
only `serve.py` changes, only the later `COPY src` layer is rebuilt, and the slow
dependency layer (about 16 minutes here) is reused from the cache. Copying
everything at once would reinstall every dependency after each code edit.

### Question 5: image size
The multi-stage image is **2.01 GB on disk (429 MB compressed content)**.
`docker history` shows the biggest layer is `COPY /opt/venv /opt/venv` at
**1.44 GB** (torch, torchvision, mlflow, pandas, scipy and the other
dependencies). The Python base layers are about 42 MB and 88 MB, and `src` is
53 kB. A single-stage image was not built, so no measured comparison is given.
It would additionally keep uv and its download cache in the final image.

### Question 6: no .dockerignore
Without `.dockerignore`, the whole folder is sent to the Docker daemon as build
context, including `data/` (over 1 GB), `.venv`, `mlruns`, `mlflow.db` and
`.git`. Builds become slower because of the transfer, and the cache can be
invalidated whenever any of those files change. With this Dockerfile, which only
copies `pyproject.toml`, `uv.lock` and `src`, none of them would strictly break
the build, but they would be sent anyway. They would break a build that used
`COPY . .`: a host `.venv` contains Windows binaries that do not work in the Linux
image and would overwrite the virtual environment built inside it. `data/`
would bloat the image, and `mlruns` and `mlflow.db` would put local run state
(possibly sensitive) into the image. With the `.dockerignore`, the build context
was only a few hundred bytes.

### Question 7: reaching MLflow from the container
Inside a container, `127.0.0.1` is the container itself, not the host, and nothing
listens on port 5000 there. `host.docker.internal` is a DNS name that Docker
Desktop resolves to the host machine's address, so the container can reach the
MLflow server on the host. I used `http://host.docker.internal:5000`.

### Question 8: restarting from the same image
A new container started from the same image loaded the model again without a
rebuild, and `/health` returned `{"status":"ok"}`. The image contains only the
code and the Python environment. The model is not baked in: it is fetched at
startup from the MLflow registry (`models:/food11@champion`), with the artifact
files supplied by the mounted `mlruns` folder.

### Question 9: what is missing to run the image elsewhere
The image exists only on this laptop. To run it on a CI runner or Kubernetes, it
must be pushed to a container registry (Docker Hub, GHCR, ECR) with a version tag
or digest instead of `latest`. It also needs a reachable MLflow tracking server
(not `host.docker.internal`) and access to the model artifacts, which here are in
a local folder (they would need to be in shared storage such as S3). An automated
pipeline to build, test and push the image is also missing, which is likely the
next lab.