import argparse
from pathlib import Path

import mlflow
import mlflow.pytorch
import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", choices=["processed", "mini"], default="mini")
    p.add_argument("--data-root", default="data")
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--lr", type=float, default=0.001)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--tracking-uri", default="http://127.0.0.1:5000")
    return p.parse_args()


def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss, correct, n = 0.0, 0, 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            out = model(x)
            total_loss += criterion(out, y).item() * x.size(0)
            correct += (out.argmax(1) == y).sum().item()
            n += x.size(0)
    return total_loss / n, correct / n


def main():
    args = parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    name = "food11_processed_mini" if args.dataset == "mini" else "food11_processed"
    root = Path(args.data_root) / name

    tfm = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    train_ds = datasets.ImageFolder(root / "training", tfm)
    val_ds = datasets.ImageFolder(root / "validation", tfm)
    test_ds = datasets.ImageFolder(root / "evaluation", tfm)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, num_workers=2)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, num_workers=2)

    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model.fc = nn.Linear(model.fc.in_features, 11)
    model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    mlflow.set_tracking_uri(args.tracking_uri)
    mlflow.set_experiment("food11")

    with mlflow.start_run():
        mlflow.log_params({
            "dataset": args.dataset,
            "epochs": args.epochs,
            "lr": args.lr,
            "batch_size": args.batch_size,
            "model": "resnet18",
        })

        for epoch in range(1, args.epochs + 1):
            model.train()
            running, n = 0.0, 0
            for x, y in train_loader:
                x, y = x.to(device), y.to(device)
                optimizer.zero_grad()
                loss = criterion(model(x), y)
                loss.backward()
                optimizer.step()
                running += loss.item() * x.size(0)
                n += x.size(0)
            train_loss = running / n
            val_loss, val_acc = evaluate(model, val_loader, criterion, device)

            mlflow.log_metric("train_loss", train_loss, step=epoch)
            mlflow.log_metric("val_loss", val_loss, step=epoch)
            mlflow.log_metric("val_accuracy", val_acc, step=epoch)
            print(f"epoch {epoch}: train_loss={train_loss:.4f} "
                  f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}")

        _, test_acc = evaluate(model, test_loader, criterion, device)
        mlflow.log_metric("test_accuracy", test_acc)
        print(f"test_accuracy={test_acc:.4f}")

        model.eval()
        model.cpu()
        example = torch.randn(1, 3, 128, 128).numpy()
        mlflow.pytorch.log_model(model, "model", input_example=example)


if __name__ == "__main__":
    main()