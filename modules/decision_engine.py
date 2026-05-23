
def choose_recommendation(candidates, min_saving=5.0, intent="不乱买"):
    if candidates is None or len(candidates) == 0:
        return "direct", None, "没有可用凑单候选。"
    if intent in ["最省心", "等低价"]:
        # These intents are more conservative.
        eligible = candidates[(candidates["达到推荐门槛"] == True) & (candidates["闲置风险"] <= 0.2)]
    else:
        eligible = candidates[candidates["达到推荐门槛"] == True]
    if len(eligible):
        best = eligible.iloc[0].to_dict()
        return "addon", best, f"存在比直接买至少少付 {min_saving:g} 元且符合「{intent}」策略的方案。"
    best = candidates.iloc[0].to_dict()
    if best["比直接买少付"] > 0:
        return "optional", best, f"有方案能少付一点，但未达到「{intent}」下的默认推荐标准。"
    return "direct", best, f"在「{intent}」策略下，候选凑单品没有让你明显少付钱，直接买更合适。"

def wait_or_buy(phase, cart_df, price_level):
    urgent = "yes" in cart_df["urgent"].astype(str).tolist()
    support_pp = "yes" in cart_df["support_price_protection"].astype(str).tolist()
    now = []
    wait = []
    if urgent:
        now.append("购物车中有急用商品")
    if support_pp:
        now.append("部分商品支持价保")
    if price_level == "较高":
        now.append("当前价格诚意较高")
    if phase in ["预热期", "开门红", "品类加码日"]:
        wait.append("后续可能有红包、品类券或直播券加码")
    if price_level in ["一般", "偏低"]:
        wait.append("当前不是明显低价")
    if urgent and support_pp:
        decision = "急用可买"
    elif len(wait) > len(now):
        decision = "不急可等"
    else:
        decision = "现在可以买"
    return decision, now or ["当前优惠已基本生效"], wait or ["等待可能错过库存或券"]
