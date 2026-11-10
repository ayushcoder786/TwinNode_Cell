"""
TwinNode EDA Visualization Generator
Generates high-resolution publication-quality plots and reports using Matplotlib and Seaborn.
Uses non-interactive Agg backend for safe server-side rendering.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports" / "eda"

class EDAVisualizer:
    """Generates charts and comprehensive visual reports for exploratory data analysis."""

    def __init__(self):
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        # Apply clean dark-industrial / scientific aesthetic
        sns.set_theme(style="whitegrid", palette="muted")
        plt.rcParams.update({
            "figure.autolayout": True,
            "axes.edgecolor": "#cbd5e1",
            "axes.linewidth": 1.2,
            "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Helvetica", "Arial"]
        })

    def generate_correlation_heatmap(self, df: pd.DataFrame, filename: str = "correlation_heatmap.png") -> str:
        """Generate Seaborn correlation heatmap."""
        cols = [c for c in [
            "temperature", "distance", "target_temperature", "target_distance",
            "temperature_error", "distance_error", "uart_latency_ms", "packet_loss", "response_delay_ms"
        ] if c in df.columns]

        if len(cols) < 2:
            return ""

        corr = df[cols].corr()
        fig, ax = plt.subplots(figsize=(9, 7))
        mask = np.triu(np.ones_like(corr, dtype=bool))
        
        sns.heatmap(
            corr,
            mask=mask,
            annot=True,
            fmt=".2f",
            cmap="vlag",
            vmin=-1.0,
            vmax=1.0,
            square=True,
            linewidths=0.5,
            cbar_kws={"shrink": 0.8},
            ax=ax
        )
        ax.set_title("TwinNode Sensor & Comms Correlation Heatmap", fontsize=14, weight="bold", pad=12)
        
        out_path = REPORTS_DIR / filename
        plt.savefig(out_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        return str(out_path)

    def generate_distribution_plots(self, df: pd.DataFrame, filename: str = "sensor_distributions.png") -> str:
        """Generate multi-panel sensor and latency distributions."""
        fig, axes = plt.subplots(2, 2, figsize=(12, 9))
        
        # 1. Temperature
        if "temperature" in df.columns:
            sns.histplot(df["temperature"].dropna(), kde=True, ax=axes[0, 0], color="#0284c7")
            axes[0, 0].set_title("LM35 Temperature Distribution (°C)", weight="bold")
            axes[0, 0].set_xlabel("Temperature (°C)")

        # 2. Distance
        if "distance" in df.columns:
            sns.histplot(df["distance"].dropna(), kde=True, ax=axes[0, 1], color="#10b981")
            axes[0, 1].set_title("HC-SR04 Distance Distribution (cm)", weight="bold")
            axes[0, 1].set_xlabel("Distance (cm)")

        # 3. UART Latency
        if "uart_latency_ms" in df.columns:
            sns.histplot(df["uart_latency_ms"].dropna(), kde=True, ax=axes[1, 0], color="#f59e0b")
            axes[1, 0].set_title("Inter-Node UART Latency (ms)", weight="bold")
            axes[1, 0].set_xlabel("Latency (ms)")

        # 4. Condition Classes
        if "condition_label" in df.columns:
            class_counts = df["condition_label"].value_counts()
            sns.barplot(x=class_counts.values, y=class_counts.index, ax=axes[1, 1], palette="flare")
            axes[1, 1].set_title("Condition Class Distribution", weight="bold")
            axes[1, 1].set_xlabel("Sample Count")

        out_path = REPORTS_DIR / filename
        plt.savefig(out_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        return str(out_path)

    def generate_full_eda_report_image(self, df: pd.DataFrame, filename: str = "twin_node_eda_summary.png") -> str:
        """Generate a complete 4-panel EDA report image for immediate download."""
        fig, axes = plt.subplots(3, 2, figsize=(14, 15))
        
        # Panel 1: Temp time-series snippet
        if "temperature" in df.columns:
            snippet = df.head(200)
            axes[0, 0].plot(snippet.index, snippet["temperature"], label="Actual Temp", color="#0284c7", lw=1.8)
            if "target_temperature" in snippet.columns:
                axes[0, 0].plot(snippet.index, snippet["target_temperature"], label="Target Temp", color="#ef4444", ls="--")
            axes[0, 0].set_title("Temperature Time-Series (First 200 Samples)", weight="bold")
            axes[0, 0].legend()

        # Panel 2: Distance time-series snippet
        if "distance" in df.columns:
            snippet = df.head(200)
            axes[0, 1].plot(snippet.index, snippet["distance"], label="Actual Dist", color="#10b981", lw=1.8)
            if "target_distance" in snippet.columns:
                axes[0, 1].plot(snippet.index, snippet["target_distance"], label="Target Dist", color="#f97316", ls="--")
            axes[0, 1].set_title("Distance Time-Series (First 200 Samples)", weight="bold")
            axes[0, 1].legend()

        # Panel 3: Outlier Boxplot
        num_cols = [c for c in ["temperature", "distance", "uart_latency_ms"] if c in df.columns]
        if num_cols:
            sns.boxplot(data=df[num_cols], ax=axes[1, 0], palette="Set2")
            axes[1, 0].set_title("Feature Spread & Outliers", weight="bold")

        # Panel 4: Error comparison
        if "temperature_error" in df.columns and "distance_error" in df.columns:
            sns.scatterplot(
                data=df,
                x="temperature_error",
                y="distance_error",
                hue="condition_label" if "condition_label" in df.columns else None,
                ax=axes[1, 1],
                alpha=0.6,
                palette="tab10"
            )
            axes[1, 1].set_title("Temperature vs Distance Tracking Error", weight="bold")

        # Panel 5: Class Counts
        if "condition_label" in df.columns:
            counts = df["condition_label"].value_counts()
            axes[2, 0].pie(counts.values, labels=counts.index, autopct="%1.1f%%", startangle=140, colors=sns.color_palette("pastel"))
            axes[2, 0].set_title("Operational Condition Distribution", weight="bold")

        # Panel 6: Latency vs Packet Loss
        if "uart_latency_ms" in df.columns and "packet_loss" in df.columns:
            sns.scatterplot(data=df, x="uart_latency_ms", y="packet_loss", ax=axes[2, 1], color="#8b5cf6")
            axes[2, 1].set_title("UART Latency vs Packet Loss", weight="bold")

        fig.suptitle("TwinNode Cell — Exploratory Data Analysis & Quality Audit", fontsize=16, weight="bold", y=1.00)
        out_path = REPORTS_DIR / filename
        plt.savefig(out_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        return str(out_path)

eda_visualizer = EDAVisualizer()
