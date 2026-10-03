"""Pick the fastest torch device: Apple GPU (MPS) locally, CUDA on a cloud box, else CPU."""


def best_device():
    import torch

    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")
