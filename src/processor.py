import pandas as pd

def filter_expenses(transactions):
    """
    Safely converts transactions to a DataFrame.
    """
    valid_transactions = []
    
    for t in transactions:
        # If it has a .to_dict() method, use it
        if hasattr(t, 'to_dict'):
            valid_transactions.append(t.to_dict())
        # If it is already a dict, use it
        elif isinstance(t, dict):
            valid_transactions.append(t)
        # If it's a string, we skip it (it's probably an account name, not a transaction)
        else:
            continue

    if not valid_transactions:
        return pd.DataFrame()

    df = pd.DataFrame(valid_transactions)
    
    # Basic cleaning
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        
    return df