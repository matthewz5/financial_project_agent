#############################################################################################################
# Libraries and Environment Setup
#############################################################################################################

from agno.agent import Agent
from agno.tools.googlesheets import GoogleSheetsTools
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat
from agno.agent import Agent
from agno.db.sqlite import SqliteDb

import json
import csv
import os
from io import StringIO

from dotenv import load_dotenv # load environment variables
load_dotenv()

#############################################################################################################
# Google Sheets Setup Tools https://docs.agno.com/concepts/tools/toolkits/others/google_sheets
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

def calculate_total_expenses_per_column(data, column_name: str = ""):

    """
    Calculate the total expenses per column from the provided data.

    Args:
        data (List): The data containing expenses.
        column_name (str): Column to select in the data

    Returns:
        Dict: A dictionary with categories as keys and total expenses as values.
    """

    header = data[0]
    column_name_idx = header.index(column_name) # Assuming {column_name} is the header for the column to analyze
    amount_idx = header.index("Valor_total") # Assuming "Valor_total" is the header for the amount column

    expenses_per_column = {}

    for row in data[1:]:
        if len(row) > max(column_name_idx, amount_idx):
            column_name = row[column_name_idx]
            try:
                # Clean values and convert to float
                row[amount_idx] = row[amount_idx].replace(" ", "").replace("R$", "").replace(".", "").replace(",", ".").strip()
                amount = float(row[amount_idx])
            except ValueError:
                amount = 0.0

            if column_name in expenses_per_column:
                expenses_per_column[column_name] += amount
            else:
                expenses_per_column[column_name] = amount

    # order the dict by value desc
    expenses_per_column = dict(sorted(expenses_per_column.items(), key=lambda item: item[1], reverse=True))

    return expenses_per_column

def filter_data_by_categorical_value(data, categorical_value: str = ""):

    """
    Filter the data by the specified category value in 'Categoria' column.
    """

    header = data[0]
    category_idx = header.index("Categoria") # Assuming {category} is the header for the category column

    filtered = [
        row for row in data[1:] if len(row) > category_idx and row[category_idx] == categorical_value
    ]

    return [header] + filtered

def analyze_expenses_by_column(month: str = "", column_name: str = ""):

    """
    Use this function to reads the data, cleans it, filter by the specified month. And calculate the total expenses per Column chose by the user.

    Args:
        month (str): Month to filter the data by, in "MM" format.
        column_name (str): Column to filter the data by: ["Data", "Categoria", "Tipo_de_gasto", "Fonte", "Sub_fonte", "Local", "Item"]

    Returns:
        List: Dictionary with categories as keys and total expenses as values.
    """

    list_of_list_data_expenses = get_list_data_month_google_sheets(month)
    dict_expenses_per_column = calculate_total_expenses_per_column(list_of_list_data_expenses, column_name)

    return dict_expenses_per_column

def analyze_expenses_per_items_for_category_column(month: str = "", categorical_value: str = ""):

    """
    Use this function to reads the data, cleans it, filter by the specified month and Categoria. And calculate the total expenses per item.

    Args:
        month (str): Month to filter the data by, in "MM" format.
        categorical_value (str): Category value to filter the data in "Categoria" column
            
    Returns:
        List: Dictionary with items as keys and total expenses as values.
    """

    list_of_list_data_expenses = get_list_data_month_google_sheets(month)
    filtered_data = filter_data_by_categorical_value(list_of_list_data_expenses, categorical_value)
    dict_expenses_per_item = calculate_total_expenses_per_column(filtered_data, "Item")

    return dict_expenses_per_item

#############################################################################################################
# Agent Setup
#############################################################################################################

db = SqliteDb(db_file = "tpm/financial_data.db")

agent = Agent(
    name = "Financial Personal Analyst",
    # model = Groq(id="llama-3.3-70b-versatile"),
    model = OpenAIChat(id="gpt-5-nano-2025-08-07"),
    tools = [
        analyze_expenses_by_column,
        analyze_expenses_per_items_for_category_column
    ],
    instructions = [
        "You are a financial personal analyst helping users to understand their financial data.",
        "Give simple responses, in a nutshell, format in markdown and use tables to display data where possible.",
    ],
    db = db,
    add_history_to_context = True,
    num_history_runs = 5,
    debug_mode = True
)

agent.print_response("Analyze my current expenses in October per items on Categoria Lazer. " \
                     "Return insights about my spending habits (my income is R$ 6.100,00). " \
                     "Use the tools to get the data from my Google Sheets and calculate the total expenses per group selected. " \
                     "Format the response in a table.",
                     markdown=True,
                     stream=True)