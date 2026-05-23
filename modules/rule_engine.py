
import pandas as pd

def category_allowed(coupon_scope, items_df):
    coupon_scope = str(coupon_scope)
    if coupon_scope == "all":
        return True
    if coupon_scope.startswith("category:"):
        cats = coupon_scope.replace("category:", "").split(",")
        return any(c in cats for c in items_df["category"].astype(str).tolist())
    if coupon_scope.startswith("shop:"):
        shop = coupon_scope.replace("shop:", "")
        return shop in items_df["shop_id"].astype(str).tolist()
    if coupon_scope == "live":
        return "yes" in items_df.get("is_live_item", pd.Series(["no"])).astype(str).tolist()
    return True

def apply_coupon(amount, coupon, items_df):
    if not category_allowed(coupon["scope"], items_df):
        return amount, 0.0, False, "适用范围不满足"
    threshold = float(coupon["threshold"])
    if amount < threshold:
        return amount, 0.0, False, f"还差 {threshold-amount:.2f} 元"
    dtype = str(coupon["discount_type"])
    if dtype == "fixed":
        discount = min(float(coupon["discount"]), amount)
        return amount - discount, discount, True, "已生效"
    if dtype == "percent":
        rate = float(coupon["discount"])
        after = amount * rate
        return after, amount - after, True, "已生效"
    return amount, 0.0, False, "暂不支持"

def calc_price(items_df, active_coupons):
    original = float(items_df["price"].sum())
    amount = original
    steps = []
    for _, c in active_coupons.sort_values("priority").iterrows():
        before = amount
        amount, discount, used, reason = apply_coupon(amount, c, items_df)
        steps.append({
            "优惠来源": c["coupon_name"],
            "优惠类型": c["coupon_type"],
            "使用前": round(before, 2),
            "优惠金额": round(discount, 2),
            "使用后": round(max(amount, 0), 2),
            "是否生效": bool(used),
            "生效状态": "已生效" if used else "未生效",
            "说明": reason,
            "下一步动作": "已生效" if used else ("判断是否值得凑单/确认领取" if "还差" in reason else "暂不处理"),
        })
    return round(original, 2), round(max(amount, 0), 2), pd.DataFrame(steps)
