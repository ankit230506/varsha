import argparse
import logging
from pathlib import Path
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping
from torch.utils.data import DataLoader

from varsha.data.dataset import VarshaDataset
from varsha.training.trainer import VarshaLightningModule

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VARSHA Training Script")
    parser.add_argument('--data_dir', type=str, required=True, help="Path to processed data directory")
    parser.add_argument('--batch_size', type=int, default=16, help="Batch size for training")
    parser.add_argument('--epochs', type=int, default=50, help="Maximum epochs")
    parser.add_argument('--lr', type=float, default=1e-4, help="Learning rate")
    parser.add_argument('--output_dir', type=str, default='checkpoints', help="Output directory for checkpoints")
    return parser.parse_args()

def main():
    """Main training entry point for VARSHA."""
    args = parse_args()
    
    logger.info("Initializing datasets...")
    train_dataset = VarshaDataset(data_dir=args.data_dir, split='train')
    val_dataset = VarshaDataset(data_dir=args.data_dir, split='val')
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=4)
    
    logger.info("Initializing Lightning Module...")
    model = VarshaLightningModule(
        c_sat=6,
        c_atm=12,
        c_static=7,
        num_horizons=6,
        learning_rate=args.lr,
        weight_decay=1e-5,
        max_epochs=args.epochs,
        focal_gamma=2.0,
        loss_alpha=0.4,
        loss_beta=0.4,
        loss_gamma=0.2,
    )

    # Callbacks — monitor BSS (higher is better) for best model selection
    checkpoint_callback = ModelCheckpoint(
        dirpath=args.output_dir,
        filename="varsha-{epoch:02d}-{val/bss:.4f}",
        save_top_k=3,
        monitor="val/total_loss",
        mode="min",
    )

    early_stopping = EarlyStopping(
        monitor="val/total_loss",
        patience=10,
        mode="min",
    )

    logger.info("Initializing Trainer...")
    trainer = pl.Trainer(
        max_epochs=args.epochs,
        callbacks=[checkpoint_callback, early_stopping],
        accelerator="auto",
        devices="auto",
        precision="16-mixed",
    )
    
    logger.info("Starting training...")
    trainer.fit(model, train_loader, val_loader)
    logger.info("Training complete. Best model saved.")

if __name__ == '__main__':
    main()
