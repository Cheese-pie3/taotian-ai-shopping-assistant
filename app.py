from pathlib import Path

import pandas as pd
import streamlit as st

from modules.addon_recommender import find_candidate_in_message, generate_addon_candidates
from modules.decision_engine import choose_recommendation, wait_or_buy
from modules.llm_explainer import assistant_reply
from modules.price_sincerity import analyze_price
from modules.rule_engine import calc_price


DATA_DIR = Path(__file__).parent / "data"
INTENTS = ["最省钱", "不乱买", "最省心", "最快到", "等低价"]
THRESHOLDS = [3.0, 5.0, 7.0, 10.0, 15.0]
STEPS = [
    ("diagnosis", "诊断购物车"),
    ("coupon", "检查优惠"),
    ("addon", "判断凑单"),
    ("wait", "买/等决策"),
    ("price_protection", "价保提醒"),
]

STRATEGY_COPY = {
    "最省钱": ("策略：最省钱", "排序依据：优先比较少付金额，找最终实付最低的方案。"),
    "不乱买": ("策略：不乱买", "排序依据：优先降低闲置风险，不为小额优惠推荐无用商品。"),
    "最省心": ("策略：最省心", "排序依据：优先直接买，减少额外凑单和复杂操作。"),
    "最快到": ("策略：最快到", "排序依据：过滤发货慢或可能影响主商品发货的凑单品。"),
    "等低价": ("策略：等低价", "排序依据：重点关注后续加码、价格诚意和价保提醒。"),
}


st.set_page_config(
    page_title="帮我凑对 V10",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
#MainMenu, header, footer {visibility: hidden;}
[data-testid="stSidebar"] {display: none;}
[data-testid="stAppViewContainer"] { background: linear-gradient(180deg,#fff3e8 0%,#fffaf6 42%,#ffffff 100%); }
.block-container { max-width:1180px; padding:1.2rem 1.2rem 2.5rem; }
.hero { background:linear-gradient(135deg,#ff5000 0%,#ff8a00 70%,#ffc247 100%); color:white; border-radius:20px; padding:24px 28px; box-shadow:0 12px 32px rgba(255,80,0,.18); margin-bottom:16px; }
.hero h1 { margin:0; font-size:32px; font-weight:850; letter-spacing:0; }
.hero p { font-size:15px; opacity:.96; margin:8px 0 0; line-height:1.7; }
.pill { display:inline-block; padding:5px 10px; border-radius:999px; border:1px solid rgba(255,255,255,.42); background:rgba(255,255,255,.20); color:white; font-size:12px; font-weight:800; margin-right:7px; }
.case-grid { display:grid; grid-template-columns:1.35fr 1fr 1fr; gap:12px; margin:0 0 16px; }
.case-card { background:white; border:1px solid #f4ddd2; border-radius:8px; padding:14px 15px; color:#1f2937; box-shadow:0 6px 18px rgba(31,41,55,.045); }
.case-title { font-size:13px; color:#6b7280; font-weight:850; margin-bottom:6px; }
.case-body { font-size:15px; line-height:1.65; color:#1f2937; font-weight:650; }
.case-body strong { color:#ff5000; }
.card, .setting-card, .panel, .addon-card, .coupon-card, .chat-wrap { color:#1f2937; }
.card { background:white; border:1px solid #f4ddd2; border-radius:8px; padding:16px; box-shadow:0 8px 24px rgba(31,41,55,.06); margin-bottom:14px; }
.setting-card { background:#fff8f2; border:1px solid #f4ddd2; border-radius:8px; padding:16px 18px; margin-bottom:18px; }
.setting-note { color:#1f2937; line-height:1.7; padding-top:2px; }
.cart-item { display:grid; grid-template-columns:34px 1fr 110px; gap:14px; align-items:center; padding:13px 0; border-bottom:1px solid #f6e7df; }
.cart-item.unselected { opacity:.62; }
.item-name { font-weight:900; font-size:16px; color:#1f2937; }
.muted { color:#6b7280; font-size:13px; line-height:1.6; }
.price { color:#ff5000; font-size:24px; font-weight:900; }
.metric-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-top:14px; }
.metric-card { background:#fff8f2; border:1px solid #f4ddd2; border-radius:8px; padding:12px; }
.metric-title { color:#6b7280; font-size:13px; font-weight:800; }
.metric-value { color:#1f2937; font-size:22px; font-weight:900; margin-top:4px; }
.panel { background:linear-gradient(180deg,#fff8f2 0%,#ffffff 100%); border:2px solid #ff5000; border-radius:8px; padding:16px; box-shadow:0 10px 30px rgba(255,80,0,.12); }
.assistant-head { display:flex; gap:10px; align-items:center; margin-bottom:14px; }
.bot-dot { width:42px; height:42px; border-radius:50%; background:#ff5000; color:white; display:flex; align-items:center; justify-content:center; font-size:23px; box-shadow:0 10px 24px rgba(255,80,0,.24); flex:0 0 auto; }
.assistant-title { font-size:21px; font-weight:900; color:#1f2937; }
.section { font-size:20px; font-weight:850; margin:0 0 12px; color:#1f2937; }
.button-grid { margin:8px 0 18px; }
.tag { display:inline-block; padding:5px 10px; border-radius:999px; background:#fff2e8; color:#ff5000; font-weight:800; font-size:13px; margin:4px 5px 4px 0; }
.intent-note { background:#fff7ed; border:1px solid #fed7aa; color:#7c2d12; padding:12px 13px; border-radius:8px; margin:10px 0 14px; line-height:1.7; }
.ai-structure { background:white; border:1px solid #f4ddd2; border-radius:8px; padding:14px; margin-bottom:10px; color:#1f2937; line-height:1.72; }
.ai-structure b { color:#1f2937; }
.ai-structure .line { margin:4px 0; }
.search-note { background:#fff7ed; border:1px solid #fed7aa; border-radius:8px; padding:10px 12px; color:#7c2d12; line-height:1.6; margin-bottom:10px; }
.pm-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-top:10px; }
.pm-card { background:#fff; border:1px solid #f4ddd2; border-radius:8px; padding:14px; color:#1f2937; line-height:1.7; }
.pm-card b { color:#ff5000; }
.addon-card, .coupon-card { background:white; border:1px solid #f4ddd2; border-radius:8px; padding:14px; margin-bottom:10px; }
.addon-title, .coupon-title { font-weight:900; font-size:16px; color:#1f2937; margin-bottom:5px; }
.addon-meta, .coupon-meta { color:#6b7280; font-size:13px; line-height:1.65; }
.green { color:#059669; font-weight:900; }
.red { color:#dc2626; font-weight:900; }
.ai-msg { background:#fff7ed; border:1px solid #fed7aa; padding:12px 14px; border-radius:8px; color:#7c2d12; margin-bottom:10px; line-height:1.7; }
.user-msg { background:#f9fafb; border:1px solid #e5e7eb; padding:10px 12px; border-radius:8px; color:#1f2937; margin-bottom:8px; line-height:1.7; }
.chat-wrap { background:#fff; border:1px solid #f4ddd2; border-radius:8px; padding:12px; margin-top:12px; }
.cart-check div[data-testid="stCheckbox"] { display:flex; align-items:center; justify-content:center; }
.cart-check label { min-height:auto !important; padding:0 !important; }
.cart-check p { display:none !important; }
.stButton > button { background:#fff7ed !important; color:#9a3412 !important; border:1px solid #fed7aa !important; border-radius:8px !important; font-weight:850 !important; min-height:52px; font-size:15px !important; line-height:1.2 !important; display:flex !important; align-items:center !important; justify-content:center !important; text-align:center !important; padding:8px 10px !important; }
.stButton > button:hover { background:#ff5000 !important; color:white !important; border-color:#ff5000 !important; }
.stButton > button p { width:100% !important; font-size:15px !important; line-height:1.2 !important; margin:0 !important; text-align:center !important; display:block !important; }
.stButton > button[kind="primary"] { background:#ff5000 !important; color:#ffffff !important; border-color:#ff5000 !important; box-shadow:0 8px 18px rgba(255,80,0,.18); }
.stButton > button[kind="primary"] p { color:#ffffff !important; -webkit-text-fill-color:#ffffff !important; }
div[data-baseweb="select"] > div,
div[data-baseweb="select"] div,
div[data-baseweb="select"] input { background:#ffffff !important; color:#1f2937 !important; border-color:#f4ddd2 !important; -webkit-text-fill-color:#1f2937 !important; }
div[data-baseweb="select"] svg { fill:#6b7280 !important; color:#6b7280 !important; }
div[data-baseweb="select"] span { color:#1f2937 !important; -webkit-text-fill-color:#1f2937 !important; }
div[data-baseweb="popover"], div[data-baseweb="menu"], div[role="listbox"] { background:#ffffff !important; color:#1f2937 !important; }
div[data-baseweb="popover"] *, div[data-baseweb="menu"] *, div[role="listbox"] * { background:#ffffff !important; color:#1f2937 !important; -webkit-text-fill-color:#1f2937 !important; }
div[role="listbox"] li, div[role="option"] { background:#ffffff !important; color:#1f2937 !important; -webkit-text-fill-color:#1f2937 !important; }
div[role="option"][aria-selected="true"] { background:#fff2e8 !important; color:#9a3412 !important; -webkit-text-fill-color:#9a3412 !important; }
div[data-baseweb="input"] input { color:#1f2937 !important; background:#ffffff !important; -webkit-text-fill-color:#1f2937 !important; }
div[data-testid="stAlert"] { background:#fff7ed !important; color:#1f2937 !important; border:1px solid #fed7aa !important; border-radius:8px !important; }
div[data-testid="stAlert"] * { color:#1f2937 !important; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_data():
    return {
        "cart": pd.read_csv(DATA_DIR / "cart.csv"),
        "coupons": pd.read_csv(DATA_DIR / "coupon_rules.csv"),
        "addons": pd.read_csv(DATA_DIR / "add_on_products.csv"),
        "calendar": pd.read_csv(DATA_DIR / "promotion_calendar.csv"),
        "tasks": pd.read_csv(DATA_DIR / "coupon_discovery_tasks.csv"),
        "price_history": pd.read_csv(DATA_DIR / "price_history.csv"),
    }


def money(value):
    try:
        text = f"¥{float(value):.2f}"
        return text.rstrip("0").rstrip(".")
    except Exception:
        return str(value)


def signed_result(diff):
    diff = float(diff)
    if diff > 0:
        return f"<span class='green'>比直接买少付 {money(diff)}</span>"
    if diff < 0:
        return f"<span class='red'>比直接买多付 {money(abs(diff))}</span>"
    return "<span class='muted'>与直接买持平</span>"


def conclusion_text(row):
    if bool(row["达到推荐门槛"]):
        return "已达到，推荐"
    return "未达到，不推荐"


def init_state():
    defaults = {
        "step": "diagnosis",
        "intent": "不乱买",
        "phase": "开门红",
        "min_saving": 10.0,
        "chat": [],
        "task_status": {},
        "price_protection": False,
        "feedback": [],
        "added_product_ids": [],
        "selected_coupon_ids": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def submit_chat(context, user_prompt):
    user_prompt = (user_prompt or "").strip()
    if not user_prompt:
        return
    mentioned = find_candidate_in_message(user_prompt, context["candidates"])
    reply_context = {
        **context,
        "mentioned_candidate": mentioned,
        "min_saving": st.session_state.min_saving,
    }
    reply = assistant_reply(user_prompt, reply_context)
    st.session_state.chat.append({"role": "user", "content": user_prompt})
    st.session_state.chat.append({"role": "assistant", "content": reply})


def addon_to_cart_row(item):
    return {
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


def search_addons(addons_df, query, added_ids):
    query = (query or "").strip().lower()
    pool = addons_df[~addons_df["product_id"].isin(added_ids)].copy()
    if not query:
        return pool.head(4)
    text = (
        pool["name"].astype(str)
        + " "
        + pool["category"].astype(str)
        + " "
        + pool["aliases"].fillna("").astype(str)
    ).str.lower()
    return pool[text.str.contains(query, regex=False)].head(4)


def phase_allowed(phase_rule, current_phase):
    phase_rule = str(phase_rule)
    if phase_rule == "all":
        return True
    return current_phase in [part.strip() for part in phase_rule.split(",")]


def recommended_coupon_ids(coupons_df, current_phase):
    available = coupons_df[
        coupons_df["phase"].apply(lambda phase: phase_allowed(phase, current_phase))
        & (coupons_df["stackable"].astype(str) == "yes")
        & (coupons_df["scope"].astype(str) != "live")
    ].copy()
    return available.sort_values(["priority", "discount"], ascending=[True, False])["coupon_id"].tolist()


def coupon_option_text(coupon):
    claim = "需领取" if str(coupon["need_claim"]) == "yes" else "自动生效"
    stack = "可叠加" if str(coupon["stackable"]) == "yes" else "不可叠加"
    return f"{coupon['coupon_name']}｜{stack}｜{claim}"


def ai_panel_block(conclusion, evidence, risk, next_step):
    st.markdown(
        f"""
        <div class="ai-structure">
          <div class="line"><b>结论：</b>{conclusion}</div>
          <div class="line"><b>关键证据：</b>{evidence}</div>
          <div class="line"><b>风险提醒：</b>{risk}</div>
          <div class="line"><b>下一步：</b>{next_step}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


data = load_data()
init_state()

st.markdown(
    """
<div class="hero">
  <span class="pill">产品案例</span><span class="pill">AI 交互原型</span><span class="pill">模拟规则验证</span>
  <h1>帮我凑对｜大促购物车 AI 下单陪跑助手</h1>
  <p>618 大促场景下，用户购物车已有商品但看不懂复杂优惠。本 Demo 演示 AI 如何帮助用户判断：直接买、凑单买，还是再等等。</p>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="case-grid">
  <div class="case-card">
    <div class="case-title">用户痛点</div>
    <div class="case-body">大促优惠规则复杂，用户不知道券是否用上、凑单是否真的省钱，也担心现在买后降价。</div>
  </div>
  <div class="case-card">
    <div class="case-title">原型目标</div>
    <div class="case-body">验证一条可解释链路：<strong>先算钱，再解释，再给下一步</strong>。</div>
  </div>
  <div class="case-card">
    <div class="case-title">Demo 边界</div>
    <div class="case-body">使用模拟购物车和规则引擎，不接真实淘系 API，不声称识别所有隐藏权益。</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="setting-card">', unsafe_allow_html=True)
s1, s2, s3 = st.columns([1.0, 1.25, 2.1])
with s1:
    phases = data["calendar"]["phase_name"].tolist()
    st.session_state.phase = st.selectbox(
        "当前大促阶段",
        phases,
        index=phases.index(st.session_state.phase) if st.session_state.phase in phases else 0,
    )
with s2:
    labels = {v: f"至少少付 {int(v)} 元" for v in THRESHOLDS}
    selected_label = st.selectbox(
        "凑单推荐标准",
        [labels[v] for v in THRESHOLDS],
        index=THRESHOLDS.index(float(st.session_state.min_saving))
        if float(st.session_state.min_saving) in THRESHOLDS
        else 3,
    )
    st.session_state.min_saving = next(v for v, label in labels.items() if label == selected_label)
with s3:
    st.markdown(
        f"<div class='setting-note'><b>当前大促阶段：</b>{st.session_state.phase}<br/>"
        f"<b>凑单推荐标准：</b>至少比直接买少付 {int(st.session_state.min_saving)} 元，才会推荐凑单</div>",
        unsafe_allow_html=True,
    )
st.markdown("</div>", unsafe_allow_html=True)

base_cart = data["cart"].copy()
added_ids = st.session_state.added_product_ids
added_rows = [
    addon_to_cart_row(item)
    for item in data["addons"][data["addons"]["product_id"].isin(added_ids)].to_dict("records")
]
full_cart = pd.concat([base_cart, pd.DataFrame(added_rows)], ignore_index=True) if added_rows else base_cart.copy()
for _, item in full_cart.iterrows():
    key = f"cart_selected_{item['product_id']}"
    if key not in st.session_state:
        st.session_state[key] = item["selected"] == "yes" or item["product_id"] in added_ids
selected_cart = full_cart[
    full_cart["product_id"].apply(lambda product_id: st.session_state.get(f"cart_selected_{product_id}", False))
].copy()
available_coupons = data["coupons"][
    data["coupons"]["phase"].apply(lambda phase: phase_allowed(phase, st.session_state.phase))
].copy()
recommended_ids = recommended_coupon_ids(data["coupons"], st.session_state.phase)
if not st.session_state.selected_coupon_ids:
    st.session_state.selected_coupon_ids = recommended_ids
for coupon_id in available_coupons["coupon_id"].tolist():
    key = f"coupon_selected_{coupon_id}"
    if key not in st.session_state:
        st.session_state[key] = coupon_id in st.session_state.selected_coupon_ids
active_coupon_ids = [
    coupon_id
    for coupon_id in available_coupons["coupon_id"].tolist()
    if st.session_state.get(f"coupon_selected_{coupon_id}", False)
]
st.session_state.selected_coupon_ids = active_coupon_ids
active_coupons = data["coupons"][data["coupons"]["coupon_id"].isin(active_coupon_ids)].copy()

original, current_pay, price_steps = calc_price(selected_cart, active_coupons)
if len(price_steps):
    used_steps = price_steps[price_steps["是否生效"] == True]
    unused_steps = price_steps[price_steps["是否生效"] == False]
else:
    used_steps = price_steps
    unused_steps = price_steps
candidates, details = generate_addon_candidates(
    selected_cart,
    active_coupons,
    data["addons"][~data["addons"]["product_id"].isin(added_ids)],
    current_pay,
    st.session_state.intent,
    st.session_state.min_saving,
)
decision_type, best_candidate, decision_reason = choose_recommendation(
    candidates, st.session_state.min_saving, st.session_state.intent
)
price_target_id = selected_cart.iloc[0]["product_id"] if len(selected_cart) else base_cart.iloc[0]["product_id"]
price_info = analyze_price(price_target_id, current_pay, data["price_history"])
buy_decision, now_reasons, wait_reasons = wait_or_buy(
    st.session_state.phase, selected_cart, price_info["level"]
)

left, right = st.columns([1.02, 1.0], gap="large")

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section">模拟购物车</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="search-note"><b>搜索模拟凑单品</b><br/>输入关键词后可把凑单品加入购物车，系统会实时重算商品总额、当前实付、优惠状态和 AI 推荐。</div>',
        unsafe_allow_html=True,
    )
    search_query = st.text_input(
        "搜索模拟凑单品",
        key="cart_add_search",
        placeholder="输入：纸巾、棉签、数据线、洗衣袋...",
    )
    matched_addons = search_addons(data["addons"], search_query, st.session_state.added_product_ids)
    if len(matched_addons):
        result_cols = st.columns(2)
        for idx, item in enumerate(matched_addons.to_dict("records")):
            with result_cols[idx % 2]:
                st.markdown(
                    f"<div class='addon-card'><div class='addon-title'>{item['name']} {money(item['price'])}</div>"
                    f"<div class='addon-meta'>{item['category']} · 发货 {item['shipping_days']} 天 · {item['return_policy']}</div></div>",
                    unsafe_allow_html=True,
                )
                if st.button("加入购物车", key=f"add_cart_{item['product_id']}", use_container_width=True):
                    st.session_state.added_product_ids.append(item["product_id"])
                    st.rerun()
    elif search_query:
        st.info("没有找到匹配商品，可以试试：纸巾、棉签、数据线、洗衣袋。")
    if st.session_state.added_product_ids:
        if st.button("清空已添加商品", key="clear_added_cart", use_container_width=True):
            for product_id in st.session_state.added_product_ids:
                st.session_state.pop(f"cart_selected_{product_id}", None)
            st.session_state.added_product_ids = []
            st.rerun()

    st.markdown('<div class="muted">购物车内共有商品，可手动勾选本次要结算的商品。</div>', unsafe_allow_html=True)
    for _, item in full_cart.iterrows():
        extra_tag = " · 新增" if item["product_id"] in st.session_state.added_product_ids else ""
        selected_now = st.session_state.get(f"cart_selected_{item['product_id']}", False)
        cols = st.columns([0.14, 0.62, 0.24])
        with cols[0]:
            st.markdown('<div class="cart-check">', unsafe_allow_html=True)
            st.checkbox(
                f"选择 {item['name']}",
                key=f"cart_selected_{item['product_id']}",
                label_visibility="collapsed",
            )
            st.markdown("</div>", unsafe_allow_html=True)
        with cols[1]:
            faded = "unselected" if not selected_now else ""
            st.markdown(
                f"""
            <div class="cart-item {faded}">
              <div></div>
              <div>
                <div class="item-name">{item['name']}</div>
                <div class="muted">类目：{item['category']} · 店铺：{item['shop_id']} · {item['return_policy']}{extra_tag}</div>
              </div>
              <div class="price">{money(item['price'])}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with cols[2]:
            st.markdown(
                f"<div class='muted' style='padding-top:18px;'>{'本次结算' if selected_now else '未勾选'}</div>",
                unsafe_allow_html=True,
            )
    if len(selected_cart) == 0:
        st.warning("当前没有勾选商品。请至少勾选一件商品后查看优惠和 AI 建议。")
    st.markdown(
        f"""
    <div class="metric-grid">
      <div class="metric-card"><div class="metric-title">已勾选商品</div><div class="metric-value">{len(selected_cart)} 件</div></div>
      <div class="metric-card"><div class="metric-title">商品总额</div><div class="metric-value">{money(original)}</div></div>
      <div class="metric-card"><div class="metric-title">当前实付</div><div class="metric-value">{money(current_pay)}</div></div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='muted'>未生效优惠：{len(unused_steps)} 个</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section">优惠来源</div>', unsafe_allow_html=True)
    st.markdown(
        f"<div class='muted'>系统已默认勾选 {len(active_coupon_ids)} 张可叠加优惠。你可以展开后手动调整，页面会重新计算实付金额。</div>",
        unsafe_allow_html=True,
    )
    with st.expander("展开查看 / 勾选优惠券", expanded=False):
        st.markdown(
            "<div class='search-note'><b>默认推荐逻辑</b><br/>优先勾选当前阶段可用、可叠加、非直播专属的优惠券；用户也可以手动取消或增加券。</div>",
            unsafe_allow_html=True,
        )
        action_cols = st.columns(2)
        if action_cols[0].button("恢复算法推荐勾选", use_container_width=True):
            st.session_state.selected_coupon_ids = recommended_ids
            for coupon_id in available_coupons["coupon_id"].tolist():
                st.session_state[f"coupon_selected_{coupon_id}"] = coupon_id in recommended_ids
            st.rerun()
        if action_cols[1].button("清空手动勾选", use_container_width=True):
            st.session_state.selected_coupon_ids = []
            for coupon_id in available_coupons["coupon_id"].tolist():
                st.session_state[f"coupon_selected_{coupon_id}"] = False
            st.rerun()

        for _, coupon in available_coupons.sort_values("priority").iterrows():
            coupon_id = coupon["coupon_id"]
            is_recommended = coupon_id in recommended_ids
            label = coupon_option_text(coupon)
            help_text = f"{coupon['note']}。默认推荐：{'是' if is_recommended else '否'}。"
            st.checkbox(label, key=f"coupon_selected_{coupon_id}", help=help_text)

        st.markdown("**当前已勾选优惠的计算结果**")
        if len(price_steps):
            for _, coupon in price_steps.iterrows():
                status_class = "green" if coupon["是否生效"] else "red"
                status = "已生效" if coupon["是否生效"] else "未生效"
                next_line = "已满足门槛" if coupon["是否生效"] else coupon["下一步动作"]
                st.markdown(
                    f"""
                    <div class="coupon-card">
                      <div class="coupon-title">{coupon['优惠来源']}</div>
                      <div class="coupon-meta">状态：<span class="{status_class}">{status}</span></div>
                      <div class="coupon-meta">优惠金额：-{money(coupon['优惠金额'])}</div>
                      <div class="coupon-meta">说明：{coupon['说明']}</div>
                      <div class="coupon-meta">下一步：{next_line}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("当前没有勾选任何优惠券。")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown(
        '<div class="assistant-head"><div class="bot-dot">🤖</div><div class="assistant-title">AI 下单陪跑</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="button-grid">', unsafe_allow_html=True)
    step_cols = st.columns(5)
    for idx, (step_id, name) in enumerate(STEPS):
        if step_cols[idx].button(
            name,
            key=f"step_button_{step_id}",
            type="primary" if st.session_state.step == step_id else "secondary",
            use_container_width=True,
        ):
            st.session_state.step = step_id
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("**你这次更在意什么？**")
    st.markdown('<div class="button-grid">', unsafe_allow_html=True)
    intent_cols = st.columns(5)
    for idx, intent in enumerate(INTENTS):
        if intent_cols[idx].button(
            intent,
            key=f"intent_button_{intent}",
            type="primary" if st.session_state.intent == intent else "secondary",
            use_container_width=True,
        ):
            st.session_state.intent = intent
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    title, body = STRATEGY_COPY[st.session_state.intent]
    st.markdown(f"<div class='intent-note'><b>{title}</b><br/>{body}</div>", unsafe_allow_html=True)

    if st.session_state.step == "diagnosis":
        if decision_type == "addon":
            conclusion = f"建议加入「{best_candidate['凑单品']}」后再下单。"
            evidence = f"当前直接买 {money(current_pay)}，加入后 {signed_result(best_candidate['比直接买少付'])}。"
            risk = f"仍需确认是否真的需要该凑单品，以及退货规则：{best_candidate['退货规则']}。"
            next_step = "进入“判断凑单”，查看候选品的完整计算过程。"
        elif decision_type == "optional":
            conclusion = "有方案能少付一点，但默认不建议为了小额优惠凑单。"
            evidence = f"推荐标准是至少少付 {int(st.session_state.min_saving)} 元，当前最佳方案未明显超过门槛。"
            risk = "用户可能为小额优惠购买低价值商品，造成闲置和退货成本。"
            next_step = "进入“判断凑单”，确认是否有本来就需要的商品。"
        else:
            conclusion = "这次不建议强行凑单，直接买更合适。"
            evidence = f"当前直接买 {money(current_pay)}；推荐门槛是至少少付 {money(st.session_state.min_saving)}。{decision_reason}"
            risk = "强行凑单可能让用户多付钱，或买到不需要的商品。"
            next_step = "如果不急用，可以切到“买/等决策”查看后续加码和价保解释。"
        ai_panel_block(conclusion, evidence, risk, next_step)

    elif st.session_state.step == "coupon":
        ai_panel_block(
            "先确认优惠是否已经生效，再判断是否值得为了未生效优惠凑单。",
            f"当前有 {len(used_steps)} 个优惠已生效，{len(unused_steps)} 个优惠未生效。",
            "未生效优惠不代表一定值得凑单；如果凑单后实付变高，就不应该推荐。",
            "点击下方按钮可模拟检查可能遗漏的会场券、直播券和会员券入口。",
        )
        if st.button("检查可能遗漏优惠", use_container_width=True):
            st.session_state.step = "missing"
            st.rerun()

    elif st.session_state.step == "addon":
        ai_panel_block(
            "凑单建议必须同时看省钱结果和商品风险。",
            f"系统会比较当前直接买 {money(current_pay)} 与加入候选凑单品后的实付差额。",
            "如果只是多买一个不需要的商品，哪怕触发优惠，也可能不是更优体验。",
            "优先看前三个候选；可切换不同意图观察排序变化。",
        )
        for _, row in candidates.head(6).iterrows():
            st.markdown(
                f"""
            <div class="addon-card">
              <div class="addon-title">凑单品：{row['凑单品']}</div>
              <div class="addon-meta">凑单成本：{money(row['凑单成本'])}</div>
              <div class="addon-meta">当前直接买：{money(current_pay)}</div>
              <div class="addon-meta">加入后实付：{money(row['凑单后实付'])}</div>
              <div class="addon-meta">结果：{signed_result(row['比直接买少付'])}</div>
              <div class="addon-meta">推荐门槛：至少少付 {money(st.session_state.min_saving)}</div>
              <div class="addon-meta">结论：<b>{conclusion_text(row)}</b></div>
              <div class="addon-meta">风险：闲置风险 {row['闲置风险']} · 发货 {row['发货天数']} 天 · {row['退货规则']}</div>
              <div class="addon-meta">当前策略影响：{row['策略说明']}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        c1, c2, c3 = st.columns(3)
        if c1.button("我不需要凑单品", use_container_width=True):
            st.session_state.feedback.append("不需要凑单品")
            st.success("已记录：后续降低类似凑单推荐优先级。")
        if c2.button("直接结算", use_container_width=True):
            st.success("模拟动作：进入结算页。")
        if c3.button("买/等决策", use_container_width=True):
            st.session_state.step = "wait"
            st.rerun()

    elif st.session_state.step == "wait":
        ai_panel_block(
            f"AI 建议：{buy_decision}。",
            f"当前阶段是「{st.session_state.phase}」，价格诚意判断为「{price_info['level']}」。",
            "不能承诺后续一定更便宜，只能提示可能加码、库存风险和价保兜底。",
            "急用且支持价保可买；不急用可等后续红包、品类券或直播间加码。",
        )
        c1, c2 = st.columns(2)
        c1.markdown(
            f"<div class='card'><b>现在买的理由</b><br/>{'<br/>'.join(now_reasons)}</div>",
            unsafe_allow_html=True,
        )
        c2.markdown(
            f"<div class='card'><b>再等等的理由</b><br/>{'<br/>'.join(wait_reasons)}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='card'><b>价格诚意检测</b><br/>价格诚意：<b>{price_info['level']}</b><br/>"
            f"{price_info['summary']}<br/><span class='muted'>本模块使用模拟价格历史，只展示判断逻辑。</span></div>",
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(3)
        if c1.button("现在结算", use_container_width=True):
            st.success("模拟动作：进入结算页。")
        if c2.button("等低价提醒", use_container_width=True):
            st.info("模拟动作：已设置提醒。")
        if c3.button("开启价保提醒", use_container_width=True):
            st.session_state.step = "price_protection"
            st.rerun()

    elif st.session_state.step == "price_protection":
        ai_panel_block(
            "价保提醒是降低现在下单后降价焦虑的辅助能力。",
            "Demo 使用模拟价保流程展示：下单、监控、发现降价、申请补差。",
            "真实落地需要订单、价保期、价格变化和补差入口数据。",
            "它不是替代平台价保，而是把价保变成主动提醒。",
        )
        if st.button("开启价保提醒", use_container_width=True):
            st.session_state.price_protection = True
        if st.session_state.price_protection:
            st.success("已开启价保提醒：价保期内如发现降价，将提醒你申请补差。")
        st.markdown(
            "<div class='card'><b>价保陪跑时间线</b><br/>"
            "<span class='tag'>下单</span><span class='tag'>价保监控</span>"
            "<span class='tag'>发现降价</span><span class='tag'>申请补差</span></div>",
            unsafe_allow_html=True,
        )

    elif st.session_state.step == "missing":
        ai_panel_block(
            "本 Demo 不假装知道用户账号里的所有隐藏券。",
            "它只把可能遗漏的入口结构化列出，让用户逐项确认。",
            "真实场景里，直播券、会员券、会场券都有强时效和账号差异。",
            "真实落地需要接入营销权益、会场、直播和用户已领券数据。",
        )
        categories = set(selected_cart["category"].astype(str).tolist())
        for _, task in data["tasks"].iterrows():
            task_categories = set(str(task["category"]).split(","))
            if task["category"] != "all" and not categories.intersection(task_categories):
                continue
            st.markdown(
                f"""
            <div class="coupon-card">
              <div class="coupon-title">{task['task_name']}</div>
              <div class="coupon-meta">{task['explain']}</div>
              <div class="coupon-meta">下一步：{task['next_action']}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            status_cols = st.columns(4)
            for col, option in zip(status_cols, ["已领取/支持", "没有", "不确定", "跳过"]):
                if col.button(option, key=f"{task['task_id']}_{option}", use_container_width=True):
                    st.session_state.task_status[task["task_id"]] = option
                    st.success(f"已记录：{task['task_name']} = {option}")
        if st.button("返回检查优惠", use_container_width=True):
            st.session_state.step = "coupon"
            st.rerun()

    chat_context = {
        "current_pay": current_pay,
        "best_candidate": best_candidate,
        "decision_type": decision_type,
        "candidates": candidates,
        "used_count": len(used_steps),
        "unused_count": len(unused_steps),
        "wait_buy_summary": f"AI 建议：{buy_decision}。现在买的理由：{'；'.join(now_reasons)}。再等等的理由：{'；'.join(wait_reasons)}。",
    }
    st.markdown("<div class='chat-wrap'><b>对话记录</b>", unsafe_allow_html=True)
    if not st.session_state.chat:
        st.markdown(
            "<div class='muted'>你可以问：为什么不买纸巾？这张券为什么没用上？现在买还是等？价保有什么用？</div>",
            unsafe_allow_html=True,
        )
    for message in st.session_state.chat[-8:]:
        cls = "user-msg" if message["role"] == "user" else "ai-msg"
        who = "你" if message["role"] == "user" else "AI"
        st.markdown(f"<div class='{cls}'><b>{who}：</b>{message['content']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.form("assistant_free_chat", clear_on_submit=True):
        custom_question = st.text_input(
            "自由提问",
            key="assistant_free_question",
            placeholder="可以直接输入：为什么不买纸巾？现在买还是等？",
        )
        sent = st.form_submit_button("发送问题", use_container_width=True)
        if sent:
            submit_chat(chat_context, custom_question)
            st.rerun()

    st.markdown('<div class="muted">也可以直接点下面的示例问题快速演示：</div>', unsafe_allow_html=True)
    question_cols = st.columns(2)
    quick_questions = [
        "为什么不买纸巾？",
        "这张券为什么没用上？",
        "现在买还是等？",
        "价保有什么用？",
    ]
    for idx, question in enumerate(quick_questions):
        if question_cols[idx % 2].button(question, key=f"quick_question_{idx}", use_container_width=True):
            submit_chat(chat_context, question)
            st.rerun()

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section">项目说明</div>', unsafe_allow_html=True)
st.markdown(
    """
<div class="pm-grid">
  <div class="pm-card">
    <b>产品价值</b><br/>
    这个原型验证的是大促下单前的决策链路：优惠是否生效、凑单是否真的省钱、现在买还是等。
  </div>
  <div class="pm-card">
    <b>落地依赖</b><br/>
    需要接入购物车、营销权益、会场券、直播券、用户已领券、价格历史、订单和价保 API。
  </div>
  <div class="pm-card">
    <b>验证指标</b><br/>
    可观察凑单建议采纳率、优惠使用率、下单转化率、价保提醒使用率、解释满意度和不必要凑单减少率。
  </div>
</div>
<div class="muted" style="margin-top:12px;">
当前为产品原型 Demo，使用模拟购物车和模拟优惠规则。不接入真实淘宝/京东 API，不声称识别所有隐藏优惠、直播券或真实历史价格。
</div>
""",
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)
