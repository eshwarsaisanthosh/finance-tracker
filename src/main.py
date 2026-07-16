from src.fetcher import fetch_all_transactions
from src.processor import filter_expenses
from src.summarizer import generate_summary
from src.notifier import send_ntfy_alert

def main():
    print("🚀 Starting financial tracking loop...")
    
    # 1. Fetch
    raw_data = fetch_all_transactions()
    
    # 2. Process (Clean & Normalize)
    # (Assuming you already have the logic to extract the list from your dictionary)
    all_transactions = []
    if isinstance(raw_data, dict):
        for tx_list in raw_data.values():
            if isinstance(tx_list, list):
                all_transactions.extend(tx_list)
    else:
        all_transactions = raw_data
        
    clean_df = filter_expenses(all_transactions)
    
    # 3. Summarize (New modular step)
    report_text = generate_summary(clean_df)
    
    # 4. Notify
    if clean_df.empty:
        print("No new relevant expenses to report.")
    else:
        send_ntfy_alert(report_text, title="Finance Report")
        print("✅ Done! Report sent.")

if __name__ == "__main__":
    main()