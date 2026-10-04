# VARSHA: Vulnerability-Aware Regional Severe-weather Hazard Anticipation System

**An AI-based severe weather early warning system for India.**

## Problem Statement
India faces frequent and severe weather events, including intense precipitation, flash floods, and thunderstorms, which cause significant loss of life and property. Existing numerical weather prediction models often lack the spatial and temporal resolution required for accurate 2-6 hour nowcasting.

VARSHA addresses this by leveraging state-of-the-art AI techniques to provide rapid, high-resolution, probabilistic forecasts of severe weather and subsequent flash flood risks.

## Architecture Overview
VARSHA employs a two-stage architecture:
1.  **Atmospheric Nowcasting (Stage 1):** A deep learning model (VarshaNet) ingests multi-spectral satellite imagery and reanalysis data to predict short-term rainfall rates, convective potential, and extreme weather probabilities.
2.  **Flash Flood Risk Module (Stage 2):** An ML model (FloodRiskModule) combines the predicted precipitation with static and dynamic hydrological features (DEM, antecedent moisture) to predict localized flash flood risks.

## Key Features
-   **Satellite-First:** Primarily relies on rapid-update satellite data (INSAT-3D/3DR) for low-latency nowcasting.
-   **Multi-Hazard:** Predicts both heavy rainfall and flash flood potential.
-   **Terrain-Aware:** Integrates high-resolution Digital Elevation Model (DEM) data to understand local hydrology.
-   **Probabilistic Forecasts:** Outputs probabilities for threshold exceedances, essential for risk-based decision-making.
-   **Explainable AI (XAI):** Incorporates XAI tools (Captum) to provide insights into model predictions, building trust with forecasters.

## Data Sources
-   **Satellite:** INSAT-3D/3DR (Thermal IR, Water Vapor, Shortwave IR)
-   **Atmospheric Reanalysis:** ECMWF ERA5 (Training) / NCEP GFS (Inference/Operational)
-   **Precipitation (Target):** NASA IMERG Final Run (Training)
-   **Elevation:** Copernicus GLO-30 DEM

## Quick Start
*Instructions for setting up the environment and running a quick test will go here.*

## Project Structure
```text
varsha/
├── api/          # FastAPI application for model serving
├── config/       # Configuration management (YAML and Python)
├── data/         # Data downloading, processing, and loading (PyTorch Datasets)
├── evaluation/   # Model evaluation scripts and metrics calculation
├── flood/        # Flash flood risk module (Stage 2)
├── inference/    # Operational inference pipelines
├── models/       # Deep learning model architectures (VarshaNet)
├── training/     # PyTorch Lightning training scripts
├── utils/        # Utility functions (geospatial, constants, logging)
└── xai/          # Explainable AI integration
```

## Team
Placeholder for Smart India Hackathon (SIH) team information.
