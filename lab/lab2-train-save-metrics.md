# Lab 2 - Model training and experiment tracking with MLflow

This lab continues the project started in Lab 1. You now have a git+dvc repo with the raw and processed Food-11 datasets tracked. In this lab you will write the training code, run a local MLflow tracking server, log parameters and metrics for each training run, and compare several runs in the MLflow UI.

> What you need to know:
> - mlflow organises tracking into *experiments* (a named group of runs, e.g. "food11") and *runs* (one training execution with its own params, metrics and artifacts)
> - a tracking server stores this metadata and serves the UI; without one, mlflow just writes to a local ./mlruns folder
> - a *param* is a value set before training and fixed for the run (learning rate, batch size, model architecture...); a *metric* is a value produced during or after training that can evolve over time (loss, accuracy...)
> - autologging can capture most of this automatically for common frameworks, but logging explicitly gives you control over exactly what gets recorded and when

## Environment Setup

### Install mlflow and the training libraries

```bash
uv add mlflow torch torchvision scikit-learn
```

> By default `torch`/`torchvision` install the CUDA-enabled build, which is a multi-GB download you don't need if your machine has no NVIDIA GPU (most laptops, all Macs). The mini dataset in this lab trains fine on CPU. To get the much smaller CPU-only wheels instead, add this to `pyproject.toml` **before** running `uv add`:
>
> ```toml
> [[tool.uv.index]]
> name = "pytorch-cpu"
> url = "https://download.pytorch.org/whl/cpu"
> explicit = true
>
> [tool.uv.sources]
> torch = { index = "pytorch-cpu" }
> torchvision = { index = "pytorch-cpu" }
> ```
>
> Then run the `uv add` command above as usual. If you do have an NVIDIA GPU and want CUDA acceleration, skip this and let uv install the default build.

> Question 1: Look at pyproject.toml and uv.lock. What changed?
--------------------------------------------------------------------------------------------------------------------------




pyproject.toml gained four direct dependencies (mlflow, torch, torchvision, scikit-learn), plus the [[tool.uv.index]] and [tool.uv.sources] blocks that point torch and torchvision at the CPU-only index. uv.lock grew by about 2,140 lines (from roughly 13 pinned packages to about 105), because it pins the exact version of every transitive dependency, including the +cpu builds of torch, so anyone running uv sync gets the same environment.









------------------------------------------------------------------------------------------------------------------------------

### Run a local mlflow tracking server

In its own terminal, from the root of your repo:

```bash
uv run mlflow server --host 127.0.0.1 --port 5000 --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns
```

Leave this running and open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser. You should see an empty "Default" experiment.

> Question 2: What is `--backend-store-uri` used for? What is `--default-artifact-root` used for? What is the difference between the metadata mlflow stores and the artifacts it stores?



--------------------------------------------------------------------------------------------------------------------

--backend-store-uri tells the server where to keep run metadata. Here it is the SQLite database mlflow.db.
--default-artifact-root tells the server where to keep artifacts. Here it is the ./mlruns folder.
Metadata is small, structured and queryable: experiments, runs, params, metrics, tags, timestamps. Artifacts are the files a run produces, such as the trained model, plots and checkpoints. They can be large, so they live on a file system or object store, and the database only stores a pointer to them.


------------------------------------------------------------------------------------------------------------------------------

Since `mlflow.db` and `mlruns/` are local run outputs, not code or versioned data, keep them out of git and dvc:

```bash
echo "mlflow.db" >> .gitignore
echo "mlruns/" >> .gitignore
git add .gitignore
git commit -m "Ignore local mlflow tracking files"
git push
```

> Question 3: Why shouldn't `mlflow.db` and `mlruns/` be tracked by git, and why shouldn't they be tracked by dvc either?



--------------------------------------------------------------------------------------------------------------------------------------



Git: mlflow.db is a binary file that changes with every run, so it produces unreadable diffs and merge conflicts. mlruns/ is large and generated.
dvc: dvc is for versioning datasets and models you want to reproduce. The tracking store is run history that mlflow manages itself, and it changes constantly. Versioning it would add noise and make the pointer file change on every run.
Both folders are also specific to your machine. Teams would share a real tracking server instead.






-----------------------------------------------------------------------------------------------------------------------------------------



### Point your code to the tracking server

Your training script will need to tell mlflow where the tracking server is, and which experiment to log into:

```python
mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("food11")
```

> Question 4: What happens the first time you call `set_experiment` with a name that doesn't exist yet? Check the mlflow UI.



-----------------------------------------------------------------------------------------------------------------------------------------


the first call to set_experiment("food11") creates the experiment automatically and gives it a new ID. It then appears in the UI's experiment list, and later runs are logged under it. If the name already exists, it just reuses it.



-----------------------------------------------------------------------------------------------------------------------------------------

## Training the model

### Training script

Create a file `./src/food11/train.py`. It should:

1. Load a Food-11 dataset with `torchvision.datasets.ImageFolder` and a `DataLoader` (use `food11_processed_mini` while you're developing the script, it's much faster to iterate on).
2. Build a model by taking a pretrained `resnet18` from `torchvision.models` and replacing its final layer so it outputs 11 classes instead of 1000.
3. Accept its hyperparameters as command-line arguments, at least: `--dataset` (processed or mini), `--epochs`, `--lr`, `--batch-size`.
4. Wrap the whole training in `with mlflow.start_run():` and:
   - log the hyperparameters with `mlflow.log_param(...)` (or `mlflow.log_params({...})`) once, at the start
   - at the end of every epoch, log `train_loss`, `val_loss` and `val_accuracy` with `mlflow.log_metric(name, value, step=epoch)`
   - at the end of training, log the final test accuracy and the trained model itself with `mlflow.pytorch.log_model(model, "model")`

```bash
uv run python ./src/food11/train.py --dataset mini --epochs 5 --lr 0.001 --batch-size 32
```

> Question 5: What is the difference between `mlflow.log_param` and `mlflow.log_metric`? Why does `log_metric` take a `step` argument and `log_param` doesn't?



------------------------------------------------------------------------------------------------------------------------------


**Answer:**

`mlflow.log_param` records a value that is set once before training and stays fixed for the whole run (learning rate, batch size, architecture, dataset). Logging the same param key again with a different value in the same run raises an error.

`mlflow.log_metric` records a measured value that changes over time (loss, accuracy). It takes a `step` argument (here the epoch number) so MLflow stores a series of values for the same metric and can draw it as a curve in the UI. A param is a single fixed value, so it has no time axis and no step.

In `train.py`, the params are logged once at the start with `mlflow.log_params({...})`, and `train_loss`, `val_loss` and `val_accuracy` are logged at the end of every epoch with `step=epoch`.


------------------------------------------------------------------------------------------------------------------------------------

> Question 6: Open the run in the mlflow UI. Find the params, the metric charts, and the logged model artifact. Where does the model artifact actually live on disk?


------------------------------------------------------------------------------------------------------------------------------------

This one you read off the UI. Open a run and find the Artifact location on its page. The model is stored under the ./mlruns folder on Colab's disk (/content/mlops-lab-1/mlruns/1/95c1beac76b942bb80e0799ba6451178/artifacts), not in the database, which only keeps a pointer to it. Write the exact path you see.
------------------------------------------------------------------------------------------------------------------------------------



### Run several experiments and compare

Now run the training script several times, changing one hyperparameter at a time, for example:

```bash
uv run python ./src/food11/train.py --dataset mini --epochs 5 --lr 0.01 --batch-size 32
uv run python ./src/food11/train.py --dataset mini --epochs 5 --lr 0.001 --batch-size 32
uv run python ./src/food11/train.py --dataset mini --epochs 5 --lr 0.0001 --batch-size 32
uv run python ./src/food11/train.py --dataset mini --epochs 5 --lr 0.001 --batch-size 64
```

> Question 7: In the mlflow UI, open the `food11` experiment. Select these runs and click "Compare". Which learning rate gave the best `val_accuracy`? Is higher always better?





------------------------------------------------------------------------------------------------------------------------------------

lr = 0.0001 gave the best val_accuracy (0.7117), ahead of 0.001 (about 0.57) and 0.01 (0.23). Higher is not better. At lr = 0.01 training was unstable: val_loss hit 14.17 in epoch 1 and accuracy stayed near 0.1-0.23. We're fine-tuning a pretrained ResNet18, so a large learning rate overwrites the useful pretrained weights. Only three values were tested, so an even lower rate might do better still.




------------------------------------------------------------------------------------------------------------------------------------


> Question 8: Use the parallel coordinates plot on the compare page to look at `lr`, `batch_size` and `val_accuracy` together. What pattern do you see?

------------------------------------------------------------------------------------------------------------------------------------

In the parallel coordinates plot, val_accuracy falls steadily as lr rises, and lr is clearly the dominant factor. Batch size 32 vs 64 at lr = 0.001 made almost no difference (0.5739 vs 0.5776), so batch size mattered much less in this test. That's a single comparison with one seed, so treat it as a hint rather than a conclusion.


------------------------------------------------------------------------------------------------------------------------------------





> Question 9: Sort the runs table by `val_accuracy` descending. Which run is the best one? Note its run ID, you'll need it in the next lab.




------------------------------------------------------------------------------------------------------------------------------------

The best run is rogue-auk-924 (lr = 0.0001, batch_size = 32) with val_accuracy = 0.7117 and test_accuracy = 0.7546. Its run ID is 95c1beac76b942bb80e0799ba6451178. Verify that the UI shows the same ID when you sort by val_accuracy. The 1-epoch test run (illustrious-mole-659, val_accuracy = 0.3613) will also appear in the table, so ignore it when comparing.

------------------------------------------------------------------------------------------------------------------------------------





## Commit your training code

The code is versioned with git; the run metadata and metrics stay in mlflow, not in git or dvc.

```bash
git add src/food11/train.py pyproject.toml uv.lock
git commit -m "Add training script with mlflow tracking"
git push
```
