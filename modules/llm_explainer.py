def money(value):
    text = f"¥{float(value):.2f}"
    return text.rstrip("0").rstrip(".")


def explain_candidate(candidate, current_pay, min_saving):
    if not candidate:
        return "我没有识别到你问的是哪个凑单品。可以换成：纸巾、棉签、洗衣袋、数据线、牙线、袜子、收纳盒或香薰。"

    name = candidate.get("凑单品", "该商品")
    diff = float(candidate.get("比直接买少付", 0))
    after = float(candidate.get("凑单后实付", 0))
    reached = bool(candidate.get("达到推荐门槛", False))
    result = f"比直接买少付 {money(diff)}" if diff > 0 else f"比直接买多付 {money(abs(diff))}" if diff < 0 else "与直接买持平"
    conclusion = "已达到推荐门槛，可以作为凑单候选。" if reached else "未达到推荐门槛，不推荐为它额外凑单。"

    return (
        f"我看的是「{name}」。当前直接买是 {money(current_pay)}，加入后实付是 {money(after)}，"
        f"结果是{result}。你的推荐标准是至少少付 {money(min_saving)}，所以{conclusion}"
        f"风险信息：{candidate.get('退货规则', '暂无退货规则')}，发货 {candidate.get('发货天数', '未知')} 天，"
        f"闲置风险 {candidate.get('闲置风险', '未知')}。"
    )


def assistant_reply(user_message, context):
    msg = (user_message or "").strip().lower()
    current_pay = context.get("current_pay", 0)
    min_saving = context.get("min_saving", 5)
    mentioned = context.get("mentioned_candidate")
    best = context.get("best_candidate")

    if not msg:
        return "你可以问我：为什么不买纸巾？这张券为什么没用上？现在买还是等？价保有什么用？"

    product_terms = ["纸巾", "棉签", "洗衣袋", "数据线", "牙线", "袜子", "收纳盒", "香薰", "蜡烛"]
    if any(term in msg for term in product_terms):
        return explain_candidate(mentioned, current_pay, min_saving)

    if "为什么" in msg and ("凑" in msg or "买" in msg):
        return explain_candidate(best, current_pay, min_saving)

    if "券" in msg or "优惠" in msg:
        return (
            f"当前有 {context.get('used_count', 0)} 个优惠已生效，"
            f"{context.get('unused_count', 0)} 个优惠未生效。未生效的原因通常是门槛不够、适用范围不匹配，"
            "或需要先领取。是否值得为它凑单，要看加入凑单品后的实付是不是真的更低。"
        )

    if "直播" in msg:
        return "直播间券通常是限时领取，当前 Demo 只提示检查入口，不声称一定存在。真实落地需要接入直播券和用户权益数据。"

    if "等" in msg or "现在买" in msg or "买还是等" in msg:
        return context.get(
            "wait_buy_summary",
            "如果急用且支持价保，可以现在买；如果不急，可以等后续红包或品类券加码，但不能保证一定更便宜。",
        )

    if "价保" in msg:
        return "价保的作用是降低现在下单后的降价焦虑。下单后如果价保期内降价，可以提醒你去平台入口申请补差。"

    if "价格" in msg or "先提价" in msg:
        return "当前 Demo 的价格诚意检测使用模拟价格历史，只展示判断逻辑。真实平台落地需要接入历史价、加购价、券后价和价保数据。"

    return "我可以根据当前购物车、优惠状态和凑单结果解释下一步建议。你可以问：为什么不买纸巾？这张券为什么没用上？现在买还是等？"
