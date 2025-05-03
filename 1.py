# 文件名: enhanced_dashboard_mysql.py

import streamlit as st
import pandas as pd
# import numpy as np # Not needed for data generation anymore
import plotly.express as px
from datetime import date, timedelta, datetime # Keep datetime
import mysql.connector # Import MySQL connector
from mysql.connector import Error # Import Error class
from sqlalchemy import text

# --- Page Config ---
st.set_page_config(
    page_title="交互仪表板 (MySQL版)",
    page_icon="🚀",
    layout="wide"
)

# --- Database Connection ---
# Use st.connection which leverages secrets automatically
# This handles connection pooling and caching implicitly.
try:
    conn = st.connection("mysql_db", type="sql")
    st.sidebar.success("数据库连接成功！") # Indicate successful connection setup
except Exception as e:
    st.error(f"数据库连接失败，请检查 .streamlit/secrets.toml 文件配置: {e}")
    st.stop() # Stop execution if connection fails

# --- Data Fetching Function (with debugging) ---
# @st.cache_data # Temporarily disable caching for debugging
@st.cache_data # 保持缓存
@st.cache_data # 保持缓存
def fetch_sales_data(start_dt, end_dt, categories):
    """Fetches sales data using SQLAlchemy Core for robust parameter handling."""
    # st.write("--- fetch_sales_data (SQLAlchemy Core) called ---") # 已移除或注释掉
    # st.write(f"Input categories: {categories}") # 已移除或注释掉

    if not categories:
        return pd.DataFrame(columns=['sale_date', 'category', 'sales_amount', 'quantity'])

    try:
        category_param_names = [f"cat_{i}" for i in range(len(categories))]
        in_clause = ", ".join([f":{name}" for name in category_param_names])

        query_sql = f"""
            SELECT sale_date, category, sales_amount, quantity
            FROM sales_data
            WHERE sale_date BETWEEN :start_date AND :end_date
              AND category IN ({in_clause})
            ORDER BY sale_date
        """
        stmt = text(query_sql)

        params_dict = {"start_date": start_dt, "end_date": end_dt}
        for i, cat_name in enumerate(category_param_names):
            params_dict[cat_name] = categories[i]

        # st.write("DEBUG SQLAlchemy: Running Query:") # 已移除或注释掉
        # st.code(str(stmt), language='sql') # 已移除或注释掉
        # st.write("DEBUG SQLAlchemy: Parameters Dict:") # 已移除或注释掉
        # st.write(params_dict) # 已移除或注释掉

        with conn.session as s: # conn 应该是 st.connection("mysql_db", type="sql") 返回的对象
             df = pd.read_sql(stmt, con=s.connection(), params=params_dict)

        if df is not None:
            df['sale_date'] = pd.to_datetime(df['sale_date'])
            # st.write(f"--- SQLAlchemy Query successful, fetched {len(df)} rows ---") # 已移除或注释掉
            return df
        else:
             # st.warning("SQLAlchemy 查询返回 None。") # 可以保留或移除
             return pd.DataFrame(columns=['sale_date', 'category', 'sales_amount', 'quantity'])

    except Exception as e: # 保持错误处理
        st.error(f"执行数据库查询时发生错误 (SQLAlchemy): {type(e).__name__} - {e}")
        st.error("--- 查询信息 ---")
        st.code(query_sql, language='sql') # 仍保留出错时的查询语句打印
        st.error(f"参数: {params_dict}") # 仍保留出错时的参数打印
        return pd.DataFrame(columns=['sale_date', 'category', 'sales_amount', 'quantity'])



# --- Sidebar: Controls & Filters ---
st.sidebar.header("⚙️ 控制与筛选")

default_start_date = date.today() - timedelta(days=90)
default_end_date = date.today()
start_date = st.sidebar.date_input("开始日期", default_start_date)
end_date = st.sidebar.date_input("结束日期", default_end_date)

if start_date > end_date:
    st.sidebar.error("错误：开始日期不能晚于结束日期。")
    st.stop()

# Get available categories dynamically from DB
try:
    # Use a simple query; cache the result using Streamlit's primitive caching
    @st.cache_data(ttl=timedelta(hours=1))
    def get_distinct_categories():
        categories_df = conn.query("SELECT DISTINCT category FROM sales_data ORDER BY category;")
        return categories_df['category'].tolist()

    categories_list = get_distinct_categories()

    if not categories_list: # Handle case where table might be empty initially
        st.sidebar.warning("数据库中未找到任何类别数据。使用默认列表。")
        categories_list = ['电子产品', '家居用品', '服饰鞋包', '图书音像', '户外运动', '美妆个护'] # Fallback

except Exception as e:
    st.sidebar.error(f"无法从数据库加载类别: {e}. 使用默认列表。")
    categories_list = ['电子产品', '家居用品', '服饰鞋包', '图书音像', '户外运动', '美妆个护'] # Fallback


selected_categories = st.sidebar.multiselect(
    "选择要查看的类别:",
    options=categories_list,
    default=categories_list # Default selects all initially fetched categories
)

# --- Fetch Data based on Filters ---
df_filtered = fetch_sales_data(start_date, end_date, selected_categories)

# --- Main Page Layout ---
st.title("🚀 销售数据仪表板 (MySQL版)")
st.markdown(f"数据时间范围: `{start_date}` 至 `{end_date}`")
if selected_categories:
     st.markdown(f"已选类别: `{', '.join(selected_categories)}`")
else:
     st.markdown("未选择任何类别。")

st.markdown("---")

# --- KPIs Display ---
st.header("📊 关键绩效指标 (KPIs)")

if not df_filtered.empty:
    total_sales = float(df_filtered['sales_amount'].sum())
    avg_sales_per_day = df_filtered.groupby(df_filtered['sale_date'].dt.date)['sales_amount'].sum().mean()
    total_quantity = int(df_filtered['quantity'].sum())

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="总销售额 (元)", value=f"{total_sales:,.2f}")
    with col2:
        st.metric(label="日均销售额 (元)", value=f"{avg_sales_per_day:,.2f}")
    with col3:
        st.metric(label="总销售数量", value=f"{total_quantity:,.0f}")
else:
    st.info("没有符合筛选条件的数据来计算 KPIs。")

st.markdown("---")

# --- Tabs: Charts & Data ---
st.header("图表 & 数据")
tab1, tab2 = st.tabs(["📈 图表可视化", "📄 详细数据"])

with tab1:
    st.subheader("销售趋势与分布")

    if not df_filtered.empty:
        chart_to_show = st.selectbox(
            "选择图表:",
            ("按日销售额趋势 (折线图)", "按类别销售额分布 (条形图)", "销售额与数量关系 (散点图)")
        )

        if chart_to_show == "按日销售额趋势 (折线图)":
            # Group by date object for correct time series plotting
            df_daily = df_filtered.groupby(df_filtered['sale_date'].dt.date)['sales_amount'].sum().reset_index()
            df_daily.rename(columns={'sale_date': '日期'}, inplace=True)
            fig_line = px.line(df_daily, x='日期', y='sales_amount', title='每日总销售额趋势', labels={'sales_amount':'销售额'})
            st.plotly_chart(fig_line, use_container_width=True)

        elif chart_to_show == "按类别销售额分布 (条形图)":
            df_category = df_filtered.groupby('category')['sales_amount'].sum().reset_index().sort_values(by='sales_amount', ascending=False)
            df_category.rename(columns={'category': '类别', 'sales_amount': '销售额'}, inplace=True)
            fig_bar = px.bar(df_category, x='类别', y='销售额', title='各类别总销售额对比', color='类别')
            st.plotly_chart(fig_bar, use_container_width=True)

        elif chart_to_show == "销售额与数量关系 (散点图)":
            # Rename columns for better plot labels
            df_scatter_plot = df_filtered.rename(columns={'category': '类别', 'sales_amount': '销售额', 'quantity': '销售数量', 'sale_date':'日期'})
            fig_scatter = px.scatter(df_scatter_plot, x='销售数量', y='销售额', color='类别',
                                     title='销售额与销售数量关系',
                                     hover_data=['日期'])
            st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("没有符合筛选条件的数据可供可视化。")


with tab2:
    st.subheader("详细数据表")

    if not df_filtered.empty:
        # Prepare dataframe for display (rename columns for readability)
        df_display = df_filtered.rename(columns={'sale_date':'日期', 'category':'类别', 'sales_amount':'销售额', 'quantity':'销售数量'})
        # Display specific columns maybe? Or just all
        st.dataframe(df_display[['日期', '类别', '销售额', '销售数量']], use_container_width=True) # Display in specific order

        # Download button (keep caching for CSV conversion)
        @st.cache_data
        def convert_df_to_csv(df):
            # IMPORTANT: Cache the conversion to prevent computation on every rerun
            return df.to_csv(index=False).encode('utf-8-sig') # Use utf-8-sig for Excel compatibility

        # Use the display DataFrame for download
        csv = convert_df_to_csv(df_display[['日期', '类别', '销售额', '销售数量']])

        st.download_button(
            label="📥 下载数据为 CSV 文件",
            data=csv,
            file_name=f"sales_data_{start_date}_to_{end_date}.csv", # Dynamic filename
            mime='text/csv',
        )
    else:
        st.info("没有符合筛选条件的数据。")


# --- Footer ---
st.sidebar.markdown("---")
st.sidebar.info(f"贵州交通职业大学 (MySQL 数据源) {datetime.now().year}") # Updated footer