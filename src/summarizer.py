import pandas as pd

def generate_summary(df):
    """
    Analyzes the DataFrame and returns a formatted string report.
    """
    if df.empty:
        return "No new expenses found for this period."

    # Sort data for the summary
    df = df.sort_values(by='amount', ascending=False)
    
    total_spent = df['amount'].sum()
    avg_spend = df['amount'].mean()
    transaction_count = len(df)
    
    # Header
    lines = [
        f"### 💸 Financial Summary",
        f"**Total Spent:** `${total_spent:,.2f}`",
        f"**Avg Transaction:** `${avg_spend:,.2f}`",
        f"**Count:** {transaction_count}",
        "\n**Top 5 Expenses:**"
    ]
    
    # Top 5 items
    for _, row in df.head(5).iterrows():
        name = row.get('name', 'Unknown')[:20]
        amount = row.get('amount', 0.0)
        lines.append(f"- {name}: `${amount:,.2f}`")
        
    return "\n".join(lines)