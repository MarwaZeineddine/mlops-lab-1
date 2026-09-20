import kagglehub

# Download latest version
path = kagglehub.dataset_download("karakaggle/food11")

print("Path to dataset files:", path)