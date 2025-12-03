import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- 1. 页面基础设置 ---
st.set_page_config(page_title="材料工程智能数据库", layout="wide", page_icon="🔩")

# --- 2. 强力数据加载器 (兼容 CSV 和 Excel) ---
@st.cache_data
def load_data():
    file_path = "data.csv"
    df = None
    
    if not os.path.exists(file_path):
        return None, "⚠️ 找不到 data.csv 文件"

    # 尝试多种编码和格式读取
    readers = [
        ('csv-utf8', lambda: pd.read_csv(file_path, encoding='utf-8')),
        ('csv-gbk', lambda: pd.read_csv(file_path, encoding='gbk')),
        ('excel', lambda: pd.read_excel(file_path, engine='openpyxl')),
    ]
    
    for name, reader in readers:
        try:
            df = reader()
            break
        except:
            continue
            
    if df is None:
        return None, "❌ 文件读取失败，请确保格式正确。"

    # 数据预处理：清洗数值列
    # 找出所有包含 'Avg' (平均值) 的列作为数值分析列
    num_cols = [c for c in df.columns if 'Avg' in c]
    
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    return df, num_cols

df, num_cols = load_data()

# --- 主界面逻辑 ---
if df is None:
    st.error(num_cols) # 这里 num_cols 是报错信息
else:
    st.title("🔩 材料工程智能数据库")
    st.markdown(f"📚 数据库共收录 **{len(df)}** 种材料 | 🟢 运行状态：正常")

    # 创建三个功能标签页
    tab1, tab2, tab3 = st.tabs(["🔍 正向查询 (查信息)", "🎯 反向查询 (找材料)", "📊 信息汇总 (做对比)"])

    # ==========================================
    # 功能 1: 正向查询 (根据问题查信息)
    # ==========================================
    with tab1:
        st.header("1. 智能检索")
        st.info("输入牌号、标准或关键词，系统将返回详细档案。")
        
        query = st.text_input("💬 请输入问题或关键词 (例如: '2083', '耐腐蚀', 'GB/T')：", key="search_box")
        
        if query:
            # 全文模糊搜索：只要任意一列包含这个关键词，就选出来
            mask = df.astype(str).apply(lambda x: x.str.contains(query, case=False)).any(axis=1)
            results = df[mask]
            
            if not results.empty:
                st.success(f"✅ 找到 {len(results)} 条相关记录：")
                st.dataframe(results, hide_index=True)
            else:
                st.warning("⚠️ 未找到匹配信息，请尝试更通用的关键词。")
        else:
            st.caption("👈 等待输入...")
            st.dataframe(df.head(5))

    # ==========================================
    # 功能 2: 反向查询 (根据要求找材料)
    # ==========================================
    with tab2:
        st.header("2. 条件筛选")
        col_filter1, col_filter2 = st.columns([1, 2])
        
        with col_filter1:
            st.subheader("⚙️ 设定指标")
            
            # 动态生成滑块：硬度
            hrc_min = 0.0
            hrc_max = 65.0
            if 'HRC_Avg' in df.columns:
                hrc_min, hrc_max = st.slider("硬度范围 (HRC)", 0.0, 70.0, (20.0, 60.0))
            
            # 动态生成滑块：关键化学成分
            cr_limit = st.slider("Cr (铬) 含量不低于 (%)", 0.0, 20.0, 0.0)
            c_limit = st.slider("C (碳) 含量不低于 (%)", 0.0, 3.0, 0.0)
            
        with col_filter2:
            st.subheader("🎯 筛选结果")
            
            # 执行筛选逻辑
            filtered_df = df.copy()
            if 'HRC_Avg' in df.columns:
                filtered_df = filtered_df[
                    (filtered_df['HRC_Avg'] >= hrc_min) & 
                    (filtered_df['HRC_Avg'] <= hrc_max)
                ]
            if 'Cr_Avg' in df.columns:
                filtered_df = filtered_df[filtered_df['Cr_Avg'] >= cr_limit]
            if 'C_Avg' in df.columns:
                filtered_df = filtered_df[filtered_df['C_Avg'] >= c_limit]
            
            st.write(f"共筛选出 **{len(filtered_df)}** 种符合要求的材料：")
            
            # 仅显示关键列
            show_cols = ['对比项目', '适用标准', '材料说明', 'HRC_Avg', 'Cr_Avg', 'C_Avg']
            final_cols = [c for c in show_cols if c in df.columns]
            st.dataframe(filtered_df[final_cols], hide_index=True)

    # ==========================================
    # 功能 3: 信息汇总 (对比分析)
    # ==========================================
    with tab3:
        st.header("3. 对比与汇总")
        
        # 多选框：选择要对比的材料
        material_list = df['对比项目'].unique().tolist() if '对比项目' in df.columns else []
        selected_materials = st.multiselect("请选择 2 个或更多材料进行对比：", material_list, default=material_list[:2] if len(material_list)>1 else None)
        
        if selected_materials:
            subset = df[df['对比项目'].isin(selected_materials)]
            
            # 1. 表格对比
            st.subheader("📋 参数对照表")
            st.dataframe(subset, hide_index=True)
            
            # 2. 自动生成汇总文字
            st.subheader("📝 智能汇总")
            avg_hrc = subset['HRC_Avg'].mean() if 'HRC_Avg' in subset.columns else 0
            max_cr = subset['Cr_Avg'].max() if 'Cr_Avg' in subset.columns else 0
            
            summary_text = f"""
            您对比了 **{len(selected_materials)}** 种材料。
            - 它们的平均硬度约为 **{avg_hrc:.1f} HRC**。
            - 其中铬(Cr)含量最高达到 **{max_cr:.1f}%** (通常意味着较好的耐腐蚀性)。
            - 建议根据具体的耐磨或耐腐蚀需求，参考上方的详细化学成分表。
            """
            st.info(summary_text)

            # 3. 雷达图对比 (如果有化学成分数据)
            chem_cols = ['C_Avg', 'Cr_Avg', 'Mn_Avg', 'Mo_Avg', 'Ni_Avg', 'V_Avg']
            valid_chem_cols = [c for c in chem_cols if c in df.columns]
            
            if valid_chem_cols:
                st.subheader("🕸️ 成分雷达图对比")
                
                # 数据归一化处理（为了让雷达图更好看）
                # 这里简单直接画图，不归一化方便看真实数值
                fig = go.Figure()
                
                for i, row in subset.iterrows():
                    fig.add_trace(go.Scatterpolar(
                        r=row[valid_chem_cols].values,
                        theta=valid_chem_cols,
                        fill='toself',
                        name=row['对比项目']
                    ))
                
                fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("请至少选择一种材料进行分析。")
