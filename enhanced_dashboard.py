# 文件名: enhanced_dashboard.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import date, timedelta

# --- 页面基础设置 ---
st.set_page_config(
    page_title="交互仪表板",
    page_icon="🚀",
    layout="wide"
)

# --- 数据生成与缓存 ---
# 使用 Streamlit 的缓存装饰器，避免每次交互都重新生成数据
@st.cache_data
def generate_mock_data(start_date, end_date, categories):
    """生成模拟销售数据"""
    date_range = pd.date_range(start_date, end_date)
    num_days = len(date_range)
    data = []
    rng = np.random.default_rng(42) # 固定随机种子以便结果可复现

    for category in categories:
        # 为每个类别生成一些基础销量和随机波动
        base_sales = rng.integers(50, 200)
        daily_sales = base_sales + rng.normal(0, 30, num_days)
        daily_quantity = rng.integers(5, 30, num_days)

        # 确保销售额和数量不为负
        daily_sales[daily_sales < 0] = 0
        daily_quantity[daily_quantity < 0] = 0

        for i, d in enumerate(date_range):
            data.append({
                '日期': d,
                '类别': category,
                '销售额': int(daily_sales[i]),
                '销售数量': int(daily_quantity[i])
            })

    df = pd.DataFrame(data)
    # 确保日期列是 datetime 类型
    df['日期'] = pd.to_datetime(df['日期'])
    return df

# --- 侧边栏：控制与筛选 ---
st.sidebar.header("⚙️ 控制与筛选")

# 日期范围选择
default_start_date = date.today() - timedelta(days=90)
default_end_date = date.today()
start_date = st.sidebar.date_input("开始日期", default_start_date)
end_date = st.sidebar.date_input("结束日期", default_end_date)

# 验证日期范围
if start_date > end_date:
    st.sidebar.error("错误：开始日期不能晚于结束日期。")
    st.stop() # 如果日期无效，停止执行后续代码

# 定义类别并生成数据
categories_list = ['电子产品', '家居用品', '服饰鞋包', '图书音像']
df_raw = generate_mock_data(start_date, end_date, categories_list)

# 类别筛选 (多选)
selected_categories = st.sidebar.multiselect(
    "选择要查看的类别:",
    options=categories_list,
    default=categories_list # 默认全选
)

# 根据选择的类别筛选数据
if not selected_categories:
    st.warning("请至少选择一个类别。")
    df_filtered = pd.DataFrame(columns=df_raw.columns) # 返回空 DataFrame
    # st.stop() # 或者停止执行
else:
     df_filtered = df_raw[df_raw['类别'].isin(selected_categories)].copy() # 使用 .copy() 避免 SettingWithCopyWarning


# --- 主页面布局 ---
st.title("🚀 销售数据仪表板")
st.markdown(f"数据时间范围: `{start_date}` 至 `{end_date}`")
if selected_categories:
     st.markdown(f"已选类别: `{', '.join(selected_categories)}`")
else:
     st.markdown("未选择任何类别。")

st.markdown("---") # 分隔线

# --- KPIs 展示 ---
st.header("📊 关键绩效指标 (KPIs)")

# 检查是否有数据用于计算KPI
if not df_filtered.empty:
    total_sales = int(df_filtered['销售额'].sum())
    avg_sales_per_day = df_filtered.groupby(df_filtered['日期'].dt.date)['销售额'].sum().mean()
    total_quantity = int(df_filtered['销售数量'].sum())
    num_selected_categories = len(selected_categories)

    # 使用列布局并排显示 KPIs
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="总销售额 (元)", value=f"{total_sales:,.0f}") # 添加千位分隔符
    with col2:
        st.metric(label="日均销售额 (元)", value=f"{avg_sales_per_day:,.2f}") # 保留两位小数
    with col3:
        st.metric(label="总销售数量", value=f"{total_quantity:,.0f}")

    # 可以在下方添加更多指标...
    # col4, col5 = st.columns(2)
    # with col4:
    #     st.metric(label="已选类别数量", value=num_selected_categories)
    # etc.

else:
    st.info("没有符合筛选条件的数据来计算 KPIs。")

st.markdown("---")

# --- 选项卡：图表与数据 ---
st.header(" 图表&数据(Charts & Data)") # 使用了印地语 "चार्ट र डेटा" 仅为示例，可改为中文
tab1, tab2 = st.tabs(["📈 图表可视化", "📄 详细数据"])

with tab1:
    st.subheader("销售趋势与分布")

    if not df_filtered.empty:
        # 图表选择
        chart_to_show = st.selectbox(
            "选择图表:",
            ("按日销售额趋势 (折线图)", "按类别销售额分布 (条形图)", "销售额与数量关系 (散点图)")
        )

        # 根据选择绘制图表
        if chart_to_show == "按日销售额趋势 (折线图)":
            # 按日期聚合数据
            df_daily = df_filtered.groupby('日期')['销售额'].sum().reset_index()
            fig_line = px.line(df_daily, x='日期', y='销售额', title='每日总销售额趋势')
            st.plotly_chart(fig_line, use_container_width=True)

        elif chart_to_show == "按类别销售额分布 (条形图)":
            # 按类别聚合数据
            df_category = df_filtered.groupby('类别')['销售额'].sum().reset_index().sort_values(by='销售额', ascending=False)
            fig_bar = px.bar(df_category, x='类别', y='销售额', title='各类别总销售额对比', color='类别')
            st.plotly_chart(fig_bar, use_container_width=True)

        elif chart_to_show == "销售额与数量关系 (散点图)":
            fig_scatter = px.scatter(df_filtered, x='销售数量', y='销售额', color='类别',
                                     title='销售额与销售数量关系（按天和类别）',
                                     hover_data=['日期'])
            st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("没有符合筛选条件的数据可供可视化。")


with tab2:
    st.subheader("详细数据表")

    if not df_filtered.empty:
        st.dataframe(df_filtered, use_container_width=True) # 显示筛选后的数据

        # 添加下载按钮
        # 为了提供下载，需要先将 DataFrame 转换为 CSV 格式
        @st.cache_data # 缓存转换结果
        def convert_df_to_csv(df):
            # IMPORTANT: Cache the conversion to prevent computation on every rerun
            return df.to_csv(index=False).encode('utf-8-sig') # 使用 utf-8-sig 编码以更好兼容 Excel

        csv = convert_df_to_csv(df_filtered)

        st.download_button(
            label="📥 下载数据为 CSV 文件",
            data=csv,
            file_name=f"sales_data_{start_date}_to_{end_date}.csv", # 动态生成文件名
            mime='text/csv',
        )
    else:
        st.info("没有符合筛选条件的数据。")


# --- 页脚 ---
st.sidebar.markdown("---")
st.sidebar.info("贵州交通职业大学 2025 年 5 月 3 日")