
# Zerodha Algo Trading Backtest

This project is a Python-based backtesting framework for intraday algo trading on Indian markets using 5-minute candle data.  
It includes popular technical indicators, dynamic ATR-based stop loss/take profit, and supports both long and short positions.

---

## Features

- Technical Indicators: MACD, RSI, EMA(20), EMA(50), Bollinger Bands, ADX, ATR  
- Signals: Buy, Sell, Short, Cover with dynamic SL/TP based on ATR  
- Backtest with position management and trade logging  
- Performance metrics: total return, win rate, max drawdown  
- Equity curve plotting and detailed trade/daily logs saved as CSV  
- Modular code structure with helper functions separated in `utils/`

---

## ## Installation

1. Clone the repository:
   git clone https://github.com/Ganesh13477/Trading.git
   cd Trading
2. Create and activate a virtual environment:
   python -m venv venv
   source venv/bin/activate # On Windows: venv\Scripts\activate
3. Install dependencies:
   pip install -r requirements.txt

## Setup

1. Clone or download this repository.  
2. Create a Python virtual environment (recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
Install required packages:


pip install -r requirements.txt
Prepare your data:
Place your cleaned 5-minute OHLC data CSV file under the data/ folder. The CSV should have columns including at least:
date, open, high, low, close, volume

## Project Structure
<pre lang="text"> ```text zerodha_algo/ ├── data/ │ └── niftybees_zerodha_prepared_2.csv # your input data ├── logs/ # generated trade and daily logs saved here ├── scripts/ │ └── backtest_ss_improved.py # main backtest script ├── utils/ │ ├── indicators.py # functions to add indicators to data │ ├── signals.py # signal generation logic │ └── backtest_helpers.py # trade logging, metrics, plotting, helpers ├── requirements.txt # required Python packages └── README.md # this file ``` </pre>
## Usage
Run the backtest with:

python -m scripts.backtest_ss_improved
This will:

Load the data CSV from data/ folder

## Calculate indicators

Run the backtest loop with signal generation and trade management

Print performance summary to console

Save trade and daily balance logs in the logs/ folder

## Plot the equity curve with trade markers

Dependencies
pandas

matplotlib

pandas_ta

Install via pip:

pip install pandas matplotlib pandas_ta
## Customization
Modify scripts/backtest_ss_improved.py to change initial balance, trade quantity, or add new features.

Adjust signal rules inside utils/signals.py.

Add more indicators or tweak existing ones in utils/indicators.py.

## License
This project is open-source and free to use. Please credit if used in your work.

## Contact
For questions or suggestions, please open an issue or contact me.


Let me know if you want me to help with a requirements.txt file or anything else!









Tools


