
def analyze_price(product_id, current_pay, history_df):
    df = history_df[history_df["product_id"] == product_id]
    if df.empty:
        return {"level":"未知", "summary":"暂无模拟价格历史。", "median":None, "lowest":None, "pre_event":None}
    median = float(df["final_price"].median())
    lowest = float(df["final_price"].min())
    pre = df[df["event_tag"] == "pre_event_raise"]
    pre_event = float(pre["listed_price"].iloc[-1]) if len(pre) else float(df["listed_price"].iloc[-1])
    real_discount = (median - float(current_pay)) / median if median else 0
    raise_risk = pre_event > median * 1.10
    if real_discount >= 0.12 and not raise_risk:
        level = "较高"; summary = "当前到手价明显低于日常中位价。"
    elif real_discount > 0 and raise_risk:
        level = "一般"; summary = "当前低于日常价，但大促前出现标价上调，页面折扣力度可能被放大。"
    elif real_discount > 0:
        level = "一般"; summary = "当前略低于日常中位价，但不是明显低价。"
    else:
        level = "偏低"; summary = "当前到手价未明显低于日常中位价，不急用可以观察。"
    return {"level":level, "summary":summary, "median":round(median,2), "lowest":round(lowest,2), "pre_event":round(pre_event,2)}
