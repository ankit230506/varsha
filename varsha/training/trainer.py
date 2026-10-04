"""PyTorch Lightning training module for VARSHA Stage 1."""

import logging
from typing import Any, Dict, Optional

import torch
import torch.nn as nn
import pytorch_lightning as pl
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

from varsha.models.varsha_net import VarshaNet
from varsha.models.losses import FocalLoss, CompositeLoss
from varsha.evaluation.metrics import (
    critical_success_index,
    probability_of_detection,
    false_alarm_ratio,
    brier_skill_score,
)

logger = logging.getLogger(__name__)


class VarshaLightningModule(pl.LightningModule):
    """PyTorch Lightning module for VARSHA Stage 1 training.

    Handles:
    - Forward pass through VarshaNet
    - Composite loss computation (BCE + Focal + MSE)
    - Metric logging (CSI, POD, FAR, BSS per threshold per horizon)
    - Optimizer and scheduler configuration
    - Validation step with comprehensive metrics

    Args:
        c_sat: Number of satellite input channels.
        c_atm: Number of atmospheric input channels.
        c_static: Number of static DEM channels.
        num_horizons: Number of forecast horizons.
        learning_rate: Learning rate for AdamW.
        weight_decay: L2 regularization weight.
        max_epochs: Total epochs (used for cosine scheduler T_max).
        focal_gamma: Gamma for focal loss on extreme thresholds.
        loss_alpha: Weight for BCE loss (mild thresholds).
        loss_beta: Weight for focal loss (extreme thresholds).
        loss_gamma: Weight for MSE loss (regression).
    """

    def __init__(
        self,
        c_sat: int = 6,
        c_atm: int = 12,
        c_static: int = 7,
        num_horizons: int = 6,
        learning_rate: float = 1e-4,
        weight_decay: float = 1e-5,
        max_epochs: int = 50,
        focal_gamma: float = 2.0,
        loss_alpha: float = 0.4,
        loss_beta: float = 0.4,
        loss_gamma: float = 0.2,
    ):
        super().__init__()
        self.save_hyperparameters()

        # Model
        self.model = VarshaNet(
            c_sat=c_sat,
            c_atm=c_atm,
            c_static=c_static,
            num_horizons=num_horizons,
        )

        # Losses
        self.bce_loss = nn.BCEWithLogitsLoss()
        self.focal_loss = FocalLoss(gamma=focal_gamma)
        self.mse_loss = nn.MSELoss()

        # Loss weights
        self.loss_alpha = loss_alpha
        self.loss_beta = loss_beta
        self.loss_gamma = loss_gamma

    def forward(
        self,
        satellite: torch.Tensor,
        atmospheric: torch.Tensor,
        static: torch.Tensor,
    ) -> Dict[str, torch.Tensor]:
        """Forward pass through VarshaNet.

        Args:
            satellite: (B, T, C_sat, H, W) satellite brightness temperatures.
            atmospheric: (B, C_atm, H, W) reanalysis atmospheric fields.
            static: (B, C_dem, H, W) DEM-derived terrain features.

        Returns:
            Dict with keys: rainfall_probs, extreme_probs,
            convective_probs, rainfall_regression.
        """
        return self.model(satellite, atmospheric, static)

    def _compute_loss(
        self,
        preds: Dict[str, torch.Tensor],
        labels: Dict[str, torch.Tensor],
    ) -> Dict[str, torch.Tensor]:
        """Compute multi-task composite loss.

        Args:
            preds: Model output dict.
            labels: Ground truth dict with matching keys.

        Returns:
            Dict with 'total' loss and individual component losses.
        """
        losses = {}

        # --- BCE for mild rainfall thresholds (1 mm/h, 10 mm/h) ---
        # rainfall_probs contains all thresholds×horizons concatenated
        l_bce = self.bce_loss(
            preds["rainfall_probs"],
            labels["rainfall_probs"],
        )
        losses["bce"] = l_bce

        # --- Focal loss for extreme thresholds ---
        pred_extreme = torch.sigmoid(preds["extreme_probs"])
        l_focal = self.focal_loss(pred_extreme, labels["extreme_probs"])
        losses["focal"] = l_focal

        # --- Focal loss for convective hazard ---
        pred_conv = torch.sigmoid(preds["convective_probs"])
        l_conv = self.focal_loss(pred_conv, labels["convective_probs"])
        losses["convective"] = l_conv

        # --- MSE for rainfall regression ---
        l_mse = self.mse_loss(
            preds["rainfall_regression"],
            labels["rainfall_regression"],
        )
        losses["mse"] = l_mse

        # Composite
        losses["total"] = (
            self.loss_alpha * (l_bce + l_conv)
            + self.loss_beta * l_focal
            + self.loss_gamma * l_mse
        )

        return losses

    def training_step(
        self, batch: Dict[str, Any], batch_idx: int
    ) -> torch.Tensor:
        """Single training step."""
        preds = self.forward(
            batch["satellite"], batch["atmospheric"], batch["static"]
        )
        losses = self._compute_loss(preds, batch["labels"])

        # Log all loss components
        for name, val in losses.items():
            self.log(
                f"train/{name}_loss",
                val,
                on_step=True,
                on_epoch=True,
                prog_bar=(name == "total"),
            )

        return losses["total"]

    def validation_step(
        self, batch: Dict[str, Any], batch_idx: int
    ) -> Dict[str, torch.Tensor]:
        """Single validation step with comprehensive metrics."""
        preds = self.forward(
            batch["satellite"], batch["atmospheric"], batch["static"]
        )
        losses = self._compute_loss(preds, batch["labels"])

        self.log(
            "val/total_loss",
            losses["total"],
            on_epoch=True,
            prog_bar=True,
        )

        # --- Compute skill metrics for key thresholds ---
        # Use first horizon (shortest lead time) as primary validation metric
        with torch.no_grad():
            rain_prob = torch.sigmoid(preds["rainfall_probs"])
            # Assuming rainfall_probs has shape (B, N_thresh*N_horiz, H, W)
            # and labels["rainfall_probs"] matches
            num_pixels = rain_prob.numel()
            if num_pixels > 0:
                # Flatten for metric computation
                pred_flat = rain_prob.view(-1).cpu()
                true_flat = labels_flat = (
                    batch["labels"]["rainfall_probs"].view(-1).cpu()
                )

                # CSI at 0.5 decision threshold
                csi = critical_success_index(
                    true_flat.numpy(), (pred_flat > 0.5).float().numpy()
                )
                pod = probability_of_detection(
                    true_flat.numpy(), (pred_flat > 0.5).float().numpy()
                )
                far = false_alarm_ratio(
                    true_flat.numpy(), (pred_flat > 0.5).float().numpy()
                )
                bss = brier_skill_score(
                    true_flat.numpy(), pred_flat.numpy()
                )

                self.log("val/csi", csi, on_epoch=True)
                self.log("val/pod", pod, on_epoch=True)
                self.log("val/far", far, on_epoch=True)
                self.log("val/bss", bss, on_epoch=True, prog_bar=True)

        return {"val_loss": losses["total"]}

    def configure_optimizers(self):
        """Configure AdamW optimizer and CosineAnnealingLR scheduler."""
        optimizer = AdamW(
            self.parameters(),
            lr=self.hparams.learning_rate,
            weight_decay=self.hparams.weight_decay,
        )

        scheduler = CosineAnnealingLR(
            optimizer,
            T_max=self.hparams.max_epochs,
            eta_min=1e-6,
        )

        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "interval": "epoch",
            },
        }
