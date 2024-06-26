import streamlit as st
import plotly.express as px
import pandas as pd
import os
import warnings
import plotly.figure_factory as ff
import boto3
from google.oauth2.service_account import Credentials
import gspread
from sqlalchemy import create_engine
import xlrd
from openai import OpenAI

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Gen AI Insight Generator", page_icon=":bar_chart:", layout="wide")

st.markdown("""
    <style>
    body {
        background-color: #f0f2f6;
        color: #31333f;
    }
    .block-container {
        padding-top: 2rem;
    }
    .css-18e3th9 {
        padding: 2rem 1rem 1rem;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 8px;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .css-1v3fvcr {
        background-color: white;
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
        transition: 0.3s;
    }
    .css-1v3fvcr:hover {
        box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
    }
    .stDataFrame, .stTable {
        border-radius: 8px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

st.title(" :bar_chart: Gen AI Insight Generator")
st.markdown('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)

# Data Source Selection
st.sidebar.header("Step 1: Choose Data Source")
data_source = st.sidebar.selectbox("Choose Data Source", ["CSV", "Excel", "SQL Database", "AWS S3", "Google Sheets"])

if data_source == "CSV":
    fl = st.file_uploader(":file_folder: Upload a CSV file", type="csv")
    if fl is not None:
        df = pd.read_csv(fl, encoding="ISO-8859-1")
elif data_source == "Excel":
    fl = st.file_uploader(":file_folder: Upload an Excel file", type=["xlsx", "xls"])
    if fl is not None:
        df = pd.read_excel(fl)
elif data_source == "SQL Database":
    db_type = st.sidebar.selectbox("Choose Database Type", ["SQLite", "PostgreSQL", "MySQL", "Other"])
    db_url = st.sidebar.text_input("Database URL")
    if st.sidebar.button("Load Data"):
        engine = create_engine(db_url)
        query = st.text_area("Enter SQL Query")
        if query:
            df = pd.read_sql_query(query, engine)
elif data_source == "AWS S3":
    s3_bucket = st.sidebar.text_input("S3 Bucket Name")
    s3_key = st.sidebar.text_input("S3 Key (file path)")
    aws_access_key = st.sidebar.text_input("AWS Access Key", type="password")
    aws_secret_key = st.sidebar.text_input("AWS Secret Key", type="password")
    if st.sidebar.button("Load Data"):
        s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
        obj = s3.get_object(Bucket=s3_bucket, Key=s3_key)
        df = pd.read_csv(obj['Body'])
elif data_source == "Google Sheets":
    google_sheet_url = st.sidebar.text_input("Google Sheet URL")
    creds_file = st.sidebar.file_uploader("Upload Google Credentials JSON", type="json")
    if creds_file and google_sheet_url:
        creds = Credentials.from_service_account_info(creds_file.read())
        client = gspread.authorize(creds)
        sheet = client.open_by_url(google_sheet_url)
        worksheet = sheet.sheet1
        df = pd.DataFrame(worksheet.get_all_records())

if 'df' in locals():
    # Display the dataframe at the start
    st.subheader("Dataset Overview Before Cleaning")
    st.dataframe(df) 

    # Column selection for processing
    st.sidebar.header("Step 2: Select Columns for Processing")
    selected_columns = st.sidebar.multiselect("Select Columns", df.columns.tolist(), default=df.columns.tolist())
    df = df[selected_columns]

    # Data Cleaning: Remove empty rows and columns
    df.dropna(how='all', inplace=True)  # Remove rows that are completely empty
    df.dropna(axis=1, how='all', inplace=True)  # Remove columns that are completely empty

    # Display the dataframe after cleaning
    st.subheader("Dataset Overview After Cleaning")
    st.dataframe(df)  

    # Download cleaned DataFrame
    def convert_df_to_csv(df):
        return df.to_csv(index=False).encode('utf-8')

    csv = convert_df_to_csv(df)

    st.download_button(
        label="Download Cleaned Data as CSV",
        data=csv,
        file_name='cleaned_data.csv',
        mime='text/csv',
    )

    st.sidebar.header("Step 3: Apply Filters")

    # Date Filter
    col1, col2 = st.columns((2))
    df["Order Date"] = pd.to_datetime(df["Order Date"])

    # Getting the min and max date 
    startDate = pd.to_datetime(df["Order Date"]).min()
    endDate = pd.to_datetime(df["Order Date"]).max()

    with col1:
        date1 = pd.to_datetime(st.date_input("Start Date", startDate))

    with col2:
        date2 = pd.to_datetime(st.date_input("End Date", endDate))

    df = df[(df["Order Date"] >= date1) & (df["Order Date"] <= date2)].copy()

    st.sidebar.header("Choose your filter: ")

    # Brand Filter
    brand = st.sidebar.multiselect("Pick your Brand", df["Brand"].unique())
    if not brand:
        df2 = df.copy()
    else:
        df2 = df[df["Brand"].isin(brand)]

    # Order Status Details Filter
    order_status = st.sidebar.multiselect("Pick the Order Status Details", df2["Order Status Details"].unique())
    if not order_status:
        filtered_df = df2.copy()
    else:
        filtered_df = df2[df2["Order Status Details"].isin(order_status)]

    # Displaying charts in a different alignment
    col1, col2 = st.columns(2)

    with col1:
        # Brand & Qty Shipped w/Returns by Order Date
        st.subheader("Brand & Qty Shipped w/Returns by Order Date")
        brand_qty_returns_df = filtered_df.groupby(by=["Brand"], as_index=False)["Qty Shipped w/Returns by Order Date"].sum()
        fig1 = px.pie(brand_qty_returns_df, values="Qty Shipped w/Returns by Order Date", names="Brand", 
                      title="Quantity Shipped with Returns by Brand",
                      color="Brand", color_discrete_sequence=px.colors.qualitative.Prism)
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        # Qty Ordered vs Order Status Details
        st.subheader("Qty Ordered vs Order Status Details")
        qty_order_status_df = filtered_df.groupby(by=["Order Status Details"], as_index=False)["Qty Ordered"].sum()
        fig2 = px.bar(qty_order_status_df, x="Qty Ordered", y="Order Status Details", 
                      orientation='h', title="Quantity Ordered by Order Status Details",
                      color="Order Status Details", color_discrete_sequence=px.colors.qualitative.Vivid)
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        # OPHTHA Region vs Qty Shipped w/Returns by Order Date
        st.subheader("OPHTHA Region vs Qty Shipped w/Returns by Order Date")
        ophtha_region = st.sidebar.multiselect("Pick the OPHTHA Region", df2["OPHTHA Region"].unique())
        if not ophtha_region:
            df3 = df2.copy()
        else:
            df3 = df2[df2["OPHTHA Region"].isin(ophtha_region)]

        ophtha_region_qty_returns_df = df3.groupby(by=["OPHTHA Region"], as_index=False)["Qty Shipped w/Returns by Order Date"].sum()
        fig3 = px.bar(ophtha_region_qty_returns_df, x="Qty Shipped w/Returns by Order Date", y="OPHTHA Region", 
                      orientation='h', title="Quantity Shipped with Returns by OPHTHA Region",
                      color="OPHTHA Region", color_discrete_sequence=px.colors.qualitative.Dark2)
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        # OPHTHA HDs vs Qty Ordered
        st.subheader("OPHTHA HDs vs Qty Ordered")
        ophtha_hds = st.sidebar.multiselect("Pick the OPHTHA HDs", df2["OPHTHA HDs"].unique())
        if not ophtha_hds:
            df4 = df2.copy()
        else:
            df4 = df2[df2["OPHTHA HDs"].isin(ophtha_hds)]

        ophtha_hds_qty_ordered_df = df4.groupby(by=["OPHTHA HDs"], as_index=False)["Qty Ordered"].sum()
        fig4 = px.bar(ophtha_hds_qty_ordered_df, x="Qty Ordered", y="OPHTHA HDs", 
                      orientation='h', title="Quantity Ordered by OPHTHA HDs",
                      color="OPHTHA HDs", color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig4, use_container_width=True)

    col5, col6 = st.columns(2)

    with col5:
        # Order Status Details by Order Date
        st.subheader("Order Status Details by Order Date")
        order_status_by_date_df = filtered_df.groupby(by=["Order Date"], as_index=False)["Order Status Details"].count()
        fig4 = px.area(order_status_by_date_df, x="Order Date", y="Order Status Details",
                       title="Order Status Details over Time",
                       color_discrete_sequence=px.colors.qualitative.Light24)
        st.plotly_chart(fig4, use_container_width=True)

    with col6:
        # Chart for Qty Ordered vs Month
        st.subheader("Qty Ordered vs Month")
    
        # Month filter
        month_options = filtered_df["Month"].unique()
        selected_months = st.sidebar.multiselect("Select Month(s)", options=month_options, default=month_options)
    
        # Filter data based on selected months
        if selected_months:
            filtered_month_df = filtered_df[filtered_df["Month"].isin(selected_months)]
        else:
            filtered_month_df = filtered_df.copy()
    
        # Group data by Month
        month_qty_ordered_df = filtered_month_df.groupby("Month")["Qty Ordered"].sum().reset_index()
    
        fig_qty_ordered_month = px.pie(month_qty_ordered_df, values="Qty Ordered", names="Month", 
                                        title="Qty Ordered vs Month", template="plotly_white",
                                        color_discrete_sequence=px.colors.qualitative.Vivid)
        fig_qty_ordered_month.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_qty_ordered_month, use_container_width=True)
    
    # Adding statistical report of the dataframe
    st.subheader("Statistical Analysis Report")
    st.write(df.describe())

    # Chart Editor Section
    st.sidebar.header("Chart Editor")

    # Select x and y columns
    x_column = st.sidebar.selectbox("Select X-axis column", options=df.columns)
    y_column = st.sidebar.selectbox("Select Y-axis column", options=df.columns)

    # Select chart type
    chart_type = st.sidebar.selectbox("Select Chart Type", options=["Line", "Bar", "Scatter", "Pie"])

    if st.sidebar.button("Generate Chart"):
        if chart_type == "Line":
            fig = px.line(df, x=x_column, y=y_column, title=f"{y_column} vs {x_column}")
        elif chart_type == "Bar":
            fig = px.bar(df, x=x_column, y=y_column, title=f"{y_column} vs {x_column}")
        elif chart_type == "Scatter":
            fig = px.scatter(df, x=x_column, y=y_column, title=f"{y_column} vs {x_column}")
        elif chart_type == "Pie":
            fig = px.pie(df, values=y_column, names=x_column, title=f"{y_column} distribution by {x_column}")
        
        st.plotly_chart(fig, use_container_width=True)


    st.sidebar.header("Chat Bot Key")

    with st.sidebar:
        openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
        "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
        "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"
    
    st.title("💬 Chatbot")
    st.caption("🚀 Chatbot powered by OpenAI")
    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]
    
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])
    
    if prompt := st.chat_input():
        if not openai_api_key:
            st.info("Please add your OpenAI API key to continue.")
            st.stop()
    
        client = OpenAI(api_key=openai_api_key)
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        response = client.chat.completions.create(model="gpt-3.5-turbo", messages=st.session_state.messages)
        msg = response.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": msg})
        st.chat_message("assistant").write(msg)
