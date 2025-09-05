#############################################################################################################
# Libraries and Environment Setup
#############################################################################################################

from agno.agent import Agent
from agno.tools.googlesheets import GoogleSheetsTools
from agno.models.groq import Groq

import pandas as pd
import json
import csv
import os
from io import StringIO

from dotenv import load_dotenv
load_dotenv()

#############################################################################################################
# Google Sheets Setup Tools https://docs.agno.com/tools/toolkits/others/google_sheets
#############################################################################################################

SAMPLE_SPREADSHEET_ID = os.getenv("SAMPLE_SPREADSHEET_ID")
SAMPLE_RANGE_NAME = os.getenv("SAMPLE_RANGE_NAME")

google_sheets_tools = GoogleSheetsTools(
    spreadsheet_id=SAMPLE_SPREADSHEET_ID,
    spreadsheet_range=SAMPLE_RANGE_NAME
)

#############################################################################################################
# Tools to agent
#############################################################################################################

def clean_data(data):

    """
    Clean the data by removing empty rows and replacing empty cells with "N/A".

    Args:
        data (List): The raw data to be cleaned.

    Returns:
        List: Cleaned data with no empty rows and "N/A" in place of empty cells.
    """

    # Remove empty rows
    staging_data = [row for row in data if row and any(str(cell).strip() for cell in row)]
    # Replace empty cells with "N/A"
    trusted_data = [[cell if cell else "N/A" for cell in row] for row in staging_data]

    return trusted_data

def filter_by_month(data, month: str = ""):

    """
    Filter the data by the specified month.

    Args:
        data (List): The data to be filtered.
        month (str): Month to filter the data by, in "MM" format.

    Returns:
        List: Filtered data containing only rows from the specified month.
    """

    header = data[0]

    date_idx = header.index("Data") # Assuming "Data" is the header for the date column

    filtered = [
        row for row in data[1:]
        if len(row) > date_idx and row[date_idx][3:5] == month and row[date_idx][6:10] == "2025" # Year fixed to 2025
    ]

    return [header] + filtered

def get_list_data_month_google_sheets(month: str = ""):

    """
    Reads the data, cleans it, and filters it by the specified month.

    Args:
        month (str): Month to filter the data by, in "MM" format.

    Returns:
        List: Cleaned and filtered data from the Google Sheets.
    """

    # Get raw data as a list of lists
    raw_data = google_sheets_tools.read_sheet()

    # Handle case where raw_data is a JSON string
    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except json.JSONDecodeError:
            raw_data = list(csv.reader(StringIO(raw_data)))

    # Clean the data
    trusted_data = clean_data(raw_data)

    # Filter the data by the specified month
    filtered_data = filter_by_month(trusted_data, month=month)

    # df_data = pd.DataFrame(filtered_data[1:], columns=filtered_data[0])

    return filtered_data

def calculate_total_expenses_per_category(data, category: str = ""):

    """
    Calculate the total expenses per category from the provided data.

    Args:
        data (List): The data containing expenses.
        category (str): Category to select in the data

    Returns:
        Dict: A dictionary with categories as keys and total expenses as values.
    """

    header = data[0]
    category_idx = header.index(category) # Assuming {category} is the header for the category column
    amount_idx = header.index("Valor_total") # Assuming "Valor_total" is the header for the amount column

    expenses_per_category = {}

    for row in data[1:]:
        if len(row) > max(category_idx, amount_idx):
            category = row[category_idx]
            try:
                # Clean values and convert to float
                row[amount_idx] = row[amount_idx].replace(" ", "").replace("R$", "").replace(".", "").replace(",", ".").strip()
                amount = float(row[amount_idx])
            except ValueError:
                amount = 0.0

            if category in expenses_per_category:
                expenses_per_category[category] += amount
            else:
                expenses_per_category[category] = amount

    # order the dict by value desc
    expenses_per_category = dict(sorted(expenses_per_category.items(), key=lambda item: item[1], reverse=True))

    return expenses_per_category

def analyze_expenses_by_category(month: str = "", category: str = ""):

    """
    Use this function to reads the data, cleans it, filter by the specified month. And calculate the total expenses per category.

    Args:
        month (str): Month to filter the data by, in "MM" format.
        category (str): Category to filter the data by: ["Data", "Categoria", "Tipo_de_gasto", "Fonte", "Sub_fonte", "Local", "Item"]

    Returns:
        List: Dictionary with categories as keys and total expenses as values.
    """

    list_of_list_data_expenses = get_list_data_month_google_sheets(month)
    dict_expenses_per_category = calculate_total_expenses_per_category(list_of_list_data_expenses, category)

    return dict_expenses_per_category

def analyze_itens_for_category(month: str = "", category: str = ""):

    ...

#############################################################################################################
# Agent Setup
#############################################################################################################

agent = Agent(
    model=Groq(id="llama-3.3-70b-versatile"),
    tools=[
        analyze_expenses_by_category
    ],
    instructions=[
        "You are a financial personal analyst helping users to understand their financial data.",
        "Give simple responses, in a nutshell, format in markdown and use tables to display data where possible.",
    ],
    show_tool_calls=True,
    debug_mode=True
)


agent.print_response("Analyze my current expenses in September by items. Use the tools to get the data from my Google Sheets and calculate the total expenses per group selected. Format the response in a table and give me insights about my expenses and how can I save more.",
                     markdown=True,
                     stream=True)