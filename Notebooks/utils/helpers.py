import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error
from math import sqrt
import torch


class LSTMForsecasterHelper:
    def train_epoch(model, train_loader, criterion, optimizer, device):
        model.train()
        total_loss = 0
        for X_batch, y_batch in train_loader:
            y_batch = y_batch.squeeze(-1)
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)

            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                model.parameters(), max_norm=1.0
            )  # Gradient clipping
            optimizer.step()

            total_loss += loss.item()
        return total_loss / len(train_loader)

    def evaluate(model, test_loader, criterion, device):
        model.eval()
        total_loss = 0
        predictions = []
        actuals = []

        with torch.no_grad():
            for X_batch, y_batch in test_loader:
                y_batch = y_batch.squeeze(-1)
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                outputs = model(X_batch)
                loss = criterion(outputs, y_batch)
                total_loss += loss.item()

                predictions.append(outputs.cpu().numpy())
                actuals.append(y_batch.cpu().numpy())

        predictions = np.concatenate(predictions, axis=0)
        actuals = np.concatenate(actuals, axis=0)

        return total_loss / len(test_loader), predictions, actuals


class EarlyStopping:
    """Early stopping to prevent overfitting"""

    def __init__(self, patience=15, min_delta=1e-4):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = None
        self.early_stop = False

    def __call__(self, val_loss):
        if self.best_loss is None:
            self.best_loss = val_loss
        elif val_loss > self.best_loss - self.min_delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_loss = val_loss
            self.counter = 0
