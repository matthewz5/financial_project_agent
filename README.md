# Agent Financial Project

This project provides a personal finance analysis agent that connects to Google Sheets to analyze your expenses. It uses AI to help you understand your spending patterns, offering insights and suggestions for saving.

## Features

- Reads and cleans financial data from Google Sheets
- Filters expenses by month and category
- Calculates total expenses per category
- Provides markdown-formatted responses with tables and insights

## Usage

1. Set up your Google Sheets and update `.env` with your spreadsheet ID and range.
2. Run `_project_gsheet.py` to interact with the agent and analyze your expenses.

## Requirements

- Python 3.8+
- `agno`, `pandas`, `python-dotenv`