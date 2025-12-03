import streamlit as st
import pandas as pd
import xgboost as xgb
import plotly.express as px
import os

# --- 1. 页面配置 ---
st.set_page_config(page_title="材料工程AI平台", layout="wide", page_icon="🔩")

# --- 2. 超级数据读取函数 (专治各种格式问题) ---
@st.cache_resource
def load_data():
    file_path = "data.csv"
    df = None
    msg = ""
    
    if not os.path.exists(file_path):
        return None, "⚠️ 找不到 data.csv，请检查文件是否上传。"

    # 第一招：尝试作为标准 CSV (UTF-8) 读取
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        msg = "✅ 模式: CSV (UTF-8)"
    except:
        # 第二招：尝试作为 CSV (GBK/中文编码) 读取
        try:
            df = pd.read_csv(file_path, encoding='gbk')
            msg = "✅ 模式: CSV (GBK)"
        except:
            # 第三招：尝试作为 Excel 读取 (防止是改了后缀名的xlsx)
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
                msg = "✅ 模式: Excel兼容模式"
            except:
                return None, "❌ 文件读取失败，请确保文件内容正常。"

    # --- 数据清洗与预处理 ---
    if df is not None:
        # 1. 确保核心化学成分列存在且为数字
        chem_cols = ['C_Avg', 'Cr_Avg', 'Mn_Avg', 'Mo_Avg', 'Ni_Avg', 'V_Avg']
        target_col = 'HRC_Avg'
        
        # 自动填充缺失列，防止报错
        for col in chem_cols + [target_col]:
            if col not in df.columns:
                df[col] = 0
            # 强制转为数字，非数字变0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    return df, msg

# 加载数据
df, status_msg = load_data()

# --- 3. 界面逻辑 ---
if df is None:
    st.error(status_msg)
else:
    # 准备模型数据
    X = df[['C_Avg', 'Cr_Avg', 'Mn_Avg', 'Mo_Avg', 'Ni_Avg', 'V_Avg']]
    y = df['HRC_Avg']
    
    # 训练模型 (XGBoost)
    model = xgb.XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.1)
    model.fit(X, y)

    # === 网页显示开始 ===
    st.title("🔩 材料工程技术垂类模型")
    st.caption(f"系统状态: {status_msg} | 数据集: {len(df)} 条材料")

    # [左侧] 参数调整区
    st.sidebar.header("🧪 成分配比调整")
    st.sidebar.info("拖动滑块调整化学成分(%)")
    
    def user_input():
        c = st.sidebar.slider('C (碳)', 0.0, 3.5, 0.45)
        cr = st.sidebar.slider('Cr (铬)', 0.0, 20.0, 1.5)
        mn = st.sidebar.slider('Mn (锰)', 0.0, 5.0, 0.6)
        mo = st.sidebar.slider('Mo (钼)', 0.0, 5.0, 0.2)
        ni = st.sidebar.slider('Ni (镍)', 0.0, 5.0, 0.0)
        v = st.sidebar.slider('V (钒)', 0.0, 5.0, 0.0)
        return pd.DataFrame([[c, cr, mn, mo, ni, v]], columns=X.columns)

    input_df = user_input()

    # [主区域] 分两列
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🎯 性能预测")
        pred_val = model.predict(input_df)[0]
        st.metric("预测 HRC 硬度", f"{pred_val:.1f}")
        
        # 智能判定逻辑
        if pred_val > 55:
            st.warning("🔥 高硬度范围：适合冷作模具、刀具等高耐磨场景")
        elif pred_val > 35:
            st.info("⚖️ 中硬度范围：适合塑料模具、热作模具或结构件")
        else:
            st.success("🛡️ 低硬度/预硬：韧性较好，易切削加工")

    with col2:
        st.subheader("📊 影响因子分析")
        importance = pd.DataFrame({'元素': X.columns, '权重': model.feature_importances_})
        st.plotly_chart(px.bar(importance, x='元素', y='权重', title="各元素对硬度的贡献度"), use_container_width=True)

    st.divider()

    # [底部] 智能检索
    st.subheader("🔍 材料知识库检索")
    query = st.text_input("输入关键词（如：'耐腐蚀', 'Cr12', 'GB'）：", placeholder="在此搜索...")

    if query:
        # 在所有文本列中模糊搜索
        mask = df.astype(str).apply(lambda x: x.str.contains(query, case=False)).any(axis=1)
        res = df[mask]
        if not res.empty:
            st.success(f"找到 {len(res)} 个相关材料：")
            # 优先展示关键列
            show_cols = ['对比项目', '适用标准', '材料说明', 'HRC_Avg']
            final_cols = [c for c in show_cols if c in df.columns]
            st.dataframe(res[final_cols], hide_index=True)
        else:
            st.warning("未找到匹配结果，请尝试其他关键词。")
    else:
        with st.expander("查看原始数据预览"):
            st.dataframe(df.head(10))
