# Import Libraries
import warnings

warnings.filterwarnings("ignore")
import re
import os
import uuid
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import traceback
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

# Langchain Imports
from langchain_core.tools import tool


# Preprocess data
def preprocess_expense_data(file_path, df_expenses=None):
    # Columns
    usecols = [
        "Region",
        "Country",
        "Category",
        "Brand",
        "Year",
        "Time Month",
        "Tier 1",
        "Tier 2",
        "Tier 3",
        "Expense Status",
        "Pending At",
        "Expense Logged by (NS)",
        "Audit Status",
        "Audit Comments",
        "Pep Share (USD)",
        "Bottler Share (USD)",
        "Total Expense (USD)",
    ]
    if df_expenses is None:
        # Load data (MODIFIED for new structure)
        df_expenses = pd.read_csv(
            file_path,
            usecols=usecols,
        )
    else:
        df_expenses = df_expenses[usecols]
    # Preprocessing
    for col in ["Pep Share (USD)", "Bottler Share (USD)", "Total Expense (USD)"]:
        df_expenses[col] = df_expenses[col].fillna(0)
        df_expenses[col] = df_expenses[col].astype(int)
    for col in ["Expense Status", "Audit Status"]:
        df_expenses[col] = df_expenses[col].str.title()
    # Renaming columns
    df_expenses = df_expenses.rename(
        columns={
            "Time Month": "Month",
            "Expense Logged by (NS)": "Expense Logged by",
            "Pep Share (USD)": "Pep Expense",
            "Bottler Share (USD)": "Bottler Expense",
            "Total Expense (USD)": "Total Expense",
        }
    )
    # Tier 3 renaming
    tier_3_mapping = {
        "Stands/ Racks, Other Trade Equipment": "Stands / Racks, Other Trade Equipment"
    }
    # Tier 2 renaming
    tier_2_mapping = {
        "In Store & POS Execution": "In-Store and POS Execution",
        "Capability Building/Other": "Capability Building/Others",
    }
    df_expenses["Tier 2"] = (
        df_expenses["Tier 2"]
        .str.strip()
        .apply(lambda x: tier_2_mapping[x] if tier_2_mapping.get(x) else x)
    )
    df_expenses["Tier 3"] = (
        df_expenses["Tier 3"]
        .str.strip()
        .apply(lambda x: tier_3_mapping[x] if tier_3_mapping.get(x) else x)
    )

    return df_expenses


def preprocess_budget_data(file_path, df_budget=None):
    # Columns
    usecols = [
        "Region",
        "Country",
        "Year",
        "Category",
        "Brand",
        "Tier 1",
        "Tier 2",
        "Tier 3",
        "Pep Budget",
        "Bottler Budget",
        "Budget",
    ]
    if df_budget is None:
        df_budget = pd.read_csv(
            file_path,
            usecols=usecols,
        )
    else:
        # Select relevant columns
        df_budget = df_budget[usecols]
    # Preprocessing
    for col in ["Pep Budget", "Bottler Budget", "Budget"]:
        df_budget[col] = df_budget[col].fillna(0)
        df_budget[col] = df_budget[col].astype(int)
    # Renaming columns
    df_budget = df_budget.rename(columns={"Budget": "Total Budget"})
    # Tier 3 renaming
    tier_3_expense_mapping = {
        "TV, Print, Radio, OOH, Production": "TV Print Radio OOH Prod",
        "In Store & POS Design / Development": "In Store and POS Design/Development",
        "Social Media / Influence Marketing": "Media Agency Fees",
        "Social Media/Influence Marketing": "Media Agency Fees",
        "Administrative fees": "All Other Non Working",
        "Agency out of pocket": "All Other Non Working",
        "CP out of pocket admin": "All Other Non Working",
        "Grassroots/experiential out of pocket": "All Other Non Working",
        "League/property- rights fee/options": "All Other Non Working",
        "Non-allocated NW": "All Other Non Working",
        "Other Non Working-non itemised talent": "All Other Non Working",
        "PR out of pocket administrative": "All Other Non Working",
        "Innovations": "Innovation",
        "Out of Scope Countries ( D8 Gastos)": "Future Use",
        "Package development": "Package Design",
        "Other Working - activation": "All Other Working",
        "Other Working - non allocated working": "All Other Working",
        "Other Working - PR execution": "All Other Working",
        "Coupons": "Coupons (Redemption)",
        "Sampling Execution": "Sample Executing",
        "Sponsorships-in game/ in show": "Sponsorships",
        "Sports-athlete/team contracts": "Sponsorships",
        "Sports-on field or in show props": "Sponsorships",
        "Sports-stadium contracts": "Sponsorships",
        "Capability Building Other": "Capability Building",
        "Capability Building/Other-Other": "Capability Building",
        "Stands/ Racks, Other Trade Equipment": "Stands / Racks, Other Trade Equipment",
        "Trade Equipment-Other": "Other",
        "Package design": "Package Design",
        "Post Mix / Pre Mix Equip.": "Other",
        "In-Store & POS Execution": "In-Store and POS Execution",
    }
    # Tier 2 renaming
    tier_2_expense_mapping = {
        "All Other Non-Working": "Other Non Working",
        "All Other Working": "Other Working",
        "In Store & POS Execution": "In-Store and POS Execution",
        "Capability Building/Other": "Capability Building/Others",
    }
    # Tier 2 & 3 renaming
    tier_2_3_expense_mapping = {
        ("Agency Fees", "Other"): ("Agency Fees", "Other Agency Fees"),
        ("All Other Non-Working", "Market Research"): (
            "Innovation and Insight",
            "Market Research",
        ),
        ("Other Non Working", "Market Research"): (
            "Innovation and Insight",
            "Market Research",
        ),
        ("Consumer Promotions", "Other"): (
            "Consumer Promotions",
            "Other Consumer Promotions",
        ),
        ("Media Placements", "Cinema"): ("Media Placements", "Media Placements"),
        ("Media Placements", "OOH - Out Of Home"): (
            "Media Placements",
            "Media Placements",
        ),
        ("Media Placements", "Print"): ("Media Placements", "Media Placements"),
        ("Media Placements", "Radio"): ("Media Placements", "Media Placements"),
        ("Media Placements", "TV"): ("Media Placements", "Media Placements"),
        ("Media Placements", "Digital"): ("Media Placements", "Digital Media"),
        ("Media Placements", "Other"): ("Media Placements", "Other Media"),
        ("Other Investments", "Capital (Coolers)"): ("Unilateral", "Capital Equipment"),
        ("Other Investments", "CDA's"): ("Unilateral", "CDAs"),
        ("Other Investments", "Price Support"): ("Unilateral", "Price Support"),
        ("Other Investments", "Vending / Racks"): (
            "Trade Equipment",
            "Stands / Racks, Other Trade Equipment",
        ),
        ("Other Trade", "Frozen Funds"): ("Trade Programs", "Future Use"),
        ("Other Trade", "Other Trade"): ("Trade Equipment", "Other"),
        ("Trade Equipment", "Coolers - New"): (
            "Trade Equipment",
            "On Premise Equipment",
        ),
        ("Trade Equipment", "Coolers - Refurbished"): (
            "Trade Equipment",
            "On Premise Equipment",
        ),
        ("Trade Equipment", "Vending / Racks"): (
            "Trade Equipment",
            "Stands / Racks, Other Trade Equipment",
        ),
    }
    df_budget["Tier 2"] = (
        df_budget["Tier 2"]
        .str.strip()
        .apply(
            lambda x: tier_2_expense_mapping[x] if tier_2_expense_mapping.get(x) else x
        )
    )
    df_budget["Tier 3"] = (
        df_budget["Tier 3"]
        .str.strip()
        .apply(
            lambda x: tier_3_expense_mapping[x] if tier_3_expense_mapping.get(x) else x
        )
    )
    for key in tier_2_3_expense_mapping:
        df_budget.loc[
            (df_budget["Tier 2"].str.strip() == key[0])
            & ((df_budget["Tier 3"].str.strip() == key[1])),
            ["Tier 2", "Tier 3"],
        ] = tier_2_3_expense_mapping[key]
    return df_budget


def extract_code_segments(response_text):
    """Extract code segments from the API response using regex."""
    segments = {}

    # Extract approach section
    approach_match = re.search(r"<approach>(.*?)</approach>", response_text, re.DOTALL)
    if approach_match:
        segments["approach"] = approach_match.group(1).strip()

    # Extract content between <code> tags
    code_match = re.search(r"<code>(.*?)</code>", response_text, re.DOTALL)
    if code_match:
        segments["code"] = code_match.group(1).strip()

    # Extract content between <chart> tags
    chart_match = re.search(r"<chart>(.*?)</chart>", response_text, re.DOTALL)
    if chart_match:
        segments["chart"] = chart_match.group(1).strip()

    # Extract content between <answer> tags
    answer_match = re.search(r"<answer>(.*?)</answer>", response_text, re.DOTALL)
    if answer_match:
        segments["answer"] = answer_match.group(1).strip()

    return segments


def display_saved_plot(plot_path: str) -> None:
    """Loads and displays a saved plot from the given path."""
    if os.path.exists(plot_path):
        print(f"Plot saved at: {plot_path}")
    else:
        print(f"Plot not found at {plot_path}")


@tool
def execute_analysis(input_dict, response_text, PLOT_DIR):
    """Execute the extracted code segments on the provided dataframe and store formatted answer."""
    results = {
        "approach": None,
        "answer": None,
        "figure": None,
        "code": None,
        "chart_code": None,
    }

    try:
        print("Response Text:")
        print(response_text)
        print(110 * "-")
        # Extract code segments
        segments = extract_code_segments(response_text)
        print("Segments:")
        print(segments)
        print(110 * "-")
        if not segments:
            print("No code segments found in the response")
            return results

        # Store the approach and raw code
        if "approach" in segments:
            results["approach"] = segments["approach"]
        if "code" in segments:
            results["code"] = segments["code"]
        if "chart" in segments:
            results["chart_code"] = segments["chart"]

        # Create a single namespace for all executions
        namespace = {"pd": pd, "px": px, "go": go, "pio": pio}
        namespace = {**namespace, **input_dict}

        # Execute analysis code and answer template
        if "code" in segments and "answer" in segments:
            # Properly dedent the code before execution
            code_lines = segments["code"].strip().split("\n")
            min_indent = float("inf")
            for line in code_lines:
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    min_indent = min(min_indent, indent)

            dedented_code = "\n".join(
                line[min_indent:] if line.strip() else "" for line in code_lines
            )

            # Combine code with answer template
            combined_code = f"""
{dedented_code}

# Format the answer template
answer_text = f'''{segments['answer']}'''
"""
            exec(combined_code, namespace)
            results["answer"] = namespace.get("answer_text")

        # Execute chart code if present
        if "chart" in segments and "fig" in segments["chart"]:
            # Properly dedent the code before execution
            chart_lines = segments["chart"].strip().split("\n")
            chart_lines = [x for x in chart_lines if "fig.show" not in x]
            min_indent = float("inf")
            for line in chart_lines:
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    min_indent = min(min_indent, indent)

            dedented_chart = "\n".join(
                line[min_indent:] if line.strip() else "" for line in chart_lines
            )
            # Save the figure
            plot_path = os.path.join(PLOT_DIR, f"plot_{uuid.uuid4().hex}.json")
            dedented_chart += f"\npio.write_json(fig, '{plot_path}')"
            # Run code
            exec(dedented_chart, namespace)
            # Save figure path
            results["figure"] = plot_path
        return results

    except Exception as e:
        print(f"Error during execution: {str(e)} \n{traceback.format_exc()}")
        return results
