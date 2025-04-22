import torch
from torch.utils.data import Dataset

class RegimeDataset(Dataset):
    def __init__(self,X,Y):
        self.X= torch.tensor(X, dtype=torch.float)
        self.Y= torch.tensor(Y, dtype=torch.long)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.Y[idx]

