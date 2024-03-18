import torch

if torch.cuda.is_available():
    # Check if CUDA is available
    device = torch.device("cuda")

    # Create some random data
    x = torch.randn(3, 3).to(device)
    y = torch.randn(3, 3).to(device)

    # Perform a simple operation (e.g., matrix multiplication) on GPU
    z = torch.mm(x, y)

    # Print the result
    print(z)
else:
    print("Could not locate device")
