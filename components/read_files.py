import pandas as pd


def parse_uploaded_file(uploaded_file, required_cols):
    try:
        # Detect file type by extension
        file_name = uploaded_file.name.lower()
        # Read file
        if file_name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif file_name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file)
        else:
            return "error", f"Unsupported file format.", None
        # Validate columns
        # Current columns
        current_cols = list(df.columns)
        # Check for missing columns
        missing_cols = list(set(required_cols) - set(current_cols))
        if missing_cols:
            return "error", f"Missing required columns: {', '.join(missing_cols)}", None
        else:
            return (
                "success",
                "All required columns are present. Proceed to 'Chat Sessions' tab!",
                df,
            )
    except Exception as e:
        return "error", f"Error reading the file: {e}", None
