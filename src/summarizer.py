"""Turn a cleaned expense DataFrame into a formatted text report."""


def generate_summary(df):
    """Return a Markdown-ish summary suitable for an ntfy message."""
    if df is None or df.empty:
        return "No new expenses found for this period."

    if "amount" not in df.columns:
        return "Transactions were found but had no 'amount' field to summarize."

    df = df.sort_values(by="amount", ascending=False)

    total_spent = df["amount"].sum()
    avg_spend = df["amount"].mean()
    transaction_count = len(df)

    multi_account = "account" in df.columns and df["account"].nunique() > 1

    lines = [
        "### 💸 Financial Summary",
        f"**Total Spent:** `${total_spent:,.2f}`",
        f"**Avg Transaction:** `${avg_spend:,.2f}`",
        f"**Count:** {transaction_count}",
    ]

    if multi_account:
        lines.append("\n**By Account:**")
        by_acct = df.groupby("account")["amount"].sum().sort_values(ascending=False)
        for acct, amt in by_acct.items():
            lines.append(f"- {acct}: `${amt:,.2f}`")

    lines.append("\n**Top 5 Expenses:**")
    for _, row in df.head(5).iterrows():
        name = str(row.get("name") or "Unknown")[:20]
        amount = row.get("amount", 0.0)
        tag = f" ({row.get('account')})" if multi_account else ""
        lines.append(f"- {name}{tag}: `${amount:,.2f}`")

    return "\n".join(lines)
