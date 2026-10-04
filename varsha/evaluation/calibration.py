import torch
import torch.nn as nn
from torch.utils.data import DataLoader

class TemperatureScaling(nn.Module):
    """Post-hoc probability calibration using temperature scaling.
    
    Learns a single temperature parameter T per output head.
    Calibrated probability: sigma(logit / T)
    
    Platt, J. (1999). Probabilistic outputs for SVMs.
    """
    
    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        """Apply temperature scaling to logits.
        
        Args:
            logits (torch.Tensor): Uncalibrated logits.
            
        Returns:
            torch.Tensor: Calibrated probabilities.
        """
        return torch.sigmoid(logits / self.temperature)

    def calibrate(self, valid_loader: DataLoader, model: nn.Module, device: str = 'cuda'):
        """Fit the temperature parameter using a validation set.
        
        Args:
            valid_loader (DataLoader): Validation dataloader.
            model (nn.Module): Trained base model.
            device (str): Compute device.
        """
        self.to(device)
        model.to(device)
        model.eval()
        
        nll_criterion = nn.BCEWithLogitsLoss()
        optimizer = torch.optim.LBFGS([self.temperature], lr=0.01, max_iter=50)
        
        logits_list = []
        labels_list = []
        
        with torch.no_grad():
            for batch in valid_loader:
                # Mock extraction assuming simple structures
                # In practice, access inputs correctly
                satellite = batch['satellite'].to(device)
                labels = batch['labels']['rainfall_1mm'].to(device) # example target
                
                # Mock forward pass
                out = model(satellite)
                if isinstance(out, dict):
                    logits_list.append(out['rainfall_1mm'])
                else:
                    logits_list.append(out)
                labels_list.append(labels)
                
        logits = torch.cat(logits_list, dim=0)
        labels = torch.cat(labels_list, dim=0)
        
        def eval_loss():
            optimizer.zero_grad()
            loss = nll_criterion(logits / self.temperature, labels)
            loss.backward()
            return loss
            
        optimizer.step(eval_loss)
        print(f"Optimal temperature: {self.temperature.item():.4f}")
