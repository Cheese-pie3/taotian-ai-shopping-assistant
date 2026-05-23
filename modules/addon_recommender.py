import pandas as pd

from .rule_engine import calc_price


def score_addon(item, diff, intent):
    saving_weight = {
        "最省钱": 0.58,
        "不乱买": 0.25,
        "最省心": 0.14,
        "最快到": 0.22,
        "等低价": 0.12,
    }.get(intent, 0.25)
    idle_penalty = {
        "最省钱": 0.08,
        "不乱买": 0.45,
        "最省心": 0.36,
        "最快到": 0.18,
        "等低价": 0.32,
    }.get(intent, 0.30)
    ship_penalty = 0.32 if intent == "最快到" else 0.06
    operation_penalty = 0.16 if intent == "最省心" else 0.02
    wait_penalty = 0.18 if intent == "等低价" and diff < 10 else 0.0

    score = (
        saving_weight * max(diff, 0) / 80
        + 0.24 * item["necessity_score"]
        + 0.16 * item["preference_match"]
        + 0.10 * item["consumable"]
        - idle_penalty * item["idle_risk"]
        - ship_penalty * max(item["shipping_days"] - 1, 0) / 5
        - operation_penalty
        - wait_penalty
    )
    return round(score * 100, 1)


def strategy_text(intent):
    return {
        "最省钱": "优先按少付金额和最终实付排序。",
        "不乱买": "优先压低闲置风险，避免为了小优惠买无用商品。",
        "最省心": "优先减少额外凑单和复杂操作。",
        "最快到": "发货越快优先级越高，发货慢会被降权。",
        "等低价": "更保守，除非明显少付，否则建议关注后续加码。",
    }.get(intent, "综合比较少付金额、风险和发货。")


def generate_addon_candidates(
    cart_df,
    active_coupons,
    addons_df,
    current_pay,
    intent="不乱买",
    min_saving=5.0,
):
    rows = []
    details = {}
    for item in addons_df.to_dict("records"):
        add = pd.DataFrame(
            [
                {
                    "product_id": item["product_id"],
                    "name": item["name"],
                    "price": item["price"],
                    "category": item["category"],
                    "shop_id": item["shop_id"],
                    "selected": "yes",
                    "urgent": "no",
                    "support_price_protection": "no",
                    "shipping_days": item["shipping_days"],
                    "return_policy": item["return_policy"],
                    "is_live_item": "no",
                }
            ]
        )
        new_cart = pd.concat([cart_df, add], ignore_index=True)
        _, new_pay, steps = calc_price(new_cart, active_coupons)
        diff = round(float(current_pay) - float(new_pay), 2)
        scoring_item = {
            "necessity_score": float(item["necessity_score"]),
            "preference_match": float(item["preference_match"]),
            "consumable": int(item["consumable"]),
            "idle_risk": float(item["idle_risk"]),
            "shipping_days": float(item["shipping_days"]),
        }
        reached = diff >= float(min_saving)
        rows.append(
            {
                "凑单品": item["name"],
                "别名": item.get("aliases", ""),
                "凑单成本": round(float(item["price"]), 2),
                "凑单后实付": round(float(new_pay), 2),
                "比直接买少付": diff,
                "必要性": scoring_item["necessity_score"],
                "闲置风险": scoring_item["idle_risk"],
                "发货天数": int(item["shipping_days"]),
                "退货规则": item["return_policy"],
                "达到推荐门槛": reached,
                "门槛状态": "已达到" if reached else "未达到",
                "推荐结论": "推荐" if reached else "不推荐",
                "真实更省": diff > 0,
                "推荐分": score_addon(scoring_item, diff, intent),
                "策略说明": strategy_text(intent),
            }
        )
        details[item["name"]] = steps

    df = pd.DataFrame(rows)
    if intent == "最省钱":
        df = df.sort_values(["比直接买少付", "凑单后实付", "推荐分"], ascending=[False, True, False])
    elif intent == "最省心":
        df = df.sort_values(["达到推荐门槛", "闲置风险", "凑单成本", "推荐分"], ascending=[False, True, True, False])
    elif intent == "最快到":
        df = df.sort_values(["发货天数", "达到推荐门槛", "推荐分"], ascending=[True, False, False])
    elif intent == "等低价":
        df = df.sort_values(["达到推荐门槛", "比直接买少付", "闲置风险"], ascending=[False, False, True])
    else:
        df = df.sort_values(["达到推荐门槛", "闲置风险", "必要性", "推荐分"], ascending=[False, True, False, False])
    return df.reset_index(drop=True), details


def find_candidate_in_message(message, candidates):
    text = str(message or "").lower()
    if candidates is None or len(candidates) == 0:
        return None

    keyword_map = {
        "纸巾": ["纸巾", "抽纸", "纸巾小包"],
        "棉签": ["棉签"],
        "洗衣袋": ["洗衣袋", "袋子"],
        "数据线": ["数据线", "充电线"],
        "牙线棒": ["牙线", "牙线棒"],
        "袜子": ["袜子"],
        "收纳盒": ["收纳盒", "盒子"],
        "香薰蜡烛": ["香薰", "蜡烛"],
    }
    for canonical, terms in keyword_map.items():
        if any(term.lower() in text for term in terms):
            match = candidates[candidates["凑单品"].astype(str).str.contains(canonical, regex=False)]
            if len(match):
                return match.iloc[0].to_dict()

    for _, row in candidates.iterrows():
        terms = [str(row["凑单品"])]
        aliases = str(row.get("别名", ""))
        if aliases and aliases != "nan":
            terms.extend([part.strip() for part in aliases.split(",") if part.strip()])
        if any(term.lower() in text for term in terms if term):
            return row.to_dict()
    return None
