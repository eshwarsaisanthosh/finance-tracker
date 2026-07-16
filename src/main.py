from src.fetcher import fetch_all_transactions
from src.processor import filter_expenses
from src.notifier import send_ntfy_alert

def main():
    print("🚀 Starting financial tracking loop...")
    
    # 1. Fetch data
    raw_data = fetch_all_transactions()
    
    # --- SMART DATA EXTRACTION ---
    # We now handle two scenarios: 
    # 1. A single 'transactions' list
    # 2. A dictionary organized by Account Names (e.g., {'Chase': [...], 'Amex': [...]})
    all_transactions = []
    
    if isinstance(raw_data, dict):
        if 'transactions' in raw_data:
            all_transactions = raw_data['transactions']
        else:
            # It's a dictionary of accounts, so we loop through all keys
            # and combine every transaction list into one master list
            for account_name, tx_list in raw_data.items():
                print(f"DEBUG: Found account '{account_name}' with {len(tx_list) if isinstance(tx_list, list) else 0} items.")
                if isinstance(tx_list, list):
                    all_transactions.extend(tx_list)
    else:
        # If it's already a list, use it as-is
        all_transactions = raw_data
    # -----------------------------
    
    if not all_transactions:
        print("No transactions found in any accounts.")
        return
        
    # 2. Filter
    clean_df = filter_expenses(all_transactions)
    
    # 3. Handle Empty Data
    if clean_df.empty:
        print("No new relevant expenses to report.")
        return

    # 4. Format Message
    total_spent = clean_df['amount'].sum()
    
    message_lines = [
        f"💰 Total Spent: ${total_spent:,.2f}",
        f"Transactions: {len(clean_df)}",
        "---"
    ]
    
    for _, row in clean_df.iterrows():
        name = row.get('name', 'Unknown')[:20]
        amount = row.get('amount', 0.0)
        message_lines.append(f"{name}: ${amount:.2f}")
        
    final_message = "\n".join(message_lines)

    # 5. Send Notification
    send_ntfy_alert(final_message, title="Finance Report")
    print("✅ Done! Notification sent.")

if __name__ == "__main__":
    main()