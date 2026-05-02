# Salary Calculator Pro

A sleek, robust Indian income tax and salary calculator built with [Streamlit](https://streamlit.io/). This application is designed specifically for calculating in-hand salary and tax obligations under the **New Tax Regime** (applicable for FY 2025-26 and FY 2026-27).

## Features

- 💰 **Comprehensive Inputs:** Accurately input your monthly fixed earnings (Basic, HRA, PF, Gratuity, Special Allowances, and various other allowances) as well as annual variable bonuses and RSUs (with an adjustable USD to INR conversion rate).
- 🧮 **Advanced Tax Engine:** Automatically computes Base Tax, applies Rebate u/s 87A, calculates Surcharge with Marginal Relief, and adds the 4% Health & Education Cess. 
- 📊 **Detailed Breakdowns:** Provides transparent, easy-to-read panels detailing your exact tax slab breakdown, total deductions, and effective tax rates.
- 💸 **Accurate "In-Hand" Projections:** Differentiates between fixed monthly in-hand salary and net payout for variable bonuses/RSUs, factoring in the higher surcharge brackets triggered by annual bonuses.
- 🎨 **Modern Dark UI:** A custom-styled, fully responsive dark theme using Inter and Outfit fonts for an exceptional user experience.
- 🧹 **State Management:** Quick tools to clear all inputs or clear the Streamlit cache instantly.

## Getting Started

### Prerequisites

Ensure you have Python installed, along with `pip`. 

### Installation

1. Clone this repository (or navigate to the directory).
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the App

Run the application locally using Streamlit:

```bash
streamlit run streamlit_app.py
```

This will start a local server, and you can view the application in your web browser (typically at `http://localhost:8501`).

## Tech Stack

- **Python 3**
- **Streamlit** - For the interactive web interface.
- **Custom CSS** - For modern dark mode styling, hiding the default toolbar, and responsive layouts.
