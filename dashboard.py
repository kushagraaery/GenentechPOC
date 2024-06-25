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

# Set the working directory to the path where your dataset is located
os.chdir(r"C:\Users\kushagra.sharma1\OneDrive - Incedo Technology Solutions Ltd\Desktop\DashBoard")

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

    # Adding a chat window for the bot
    st.subheader("Chat with Data Bot")

    # Initialize the chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Function to display chat messages
    def display_messages():
        for msg in st.session_state.messages:
            st.write(f"{msg['role']}: {msg['content']}")
    
    # Display chat history
    display_messages()
    
    # Text input for the user query
    user_query = st.text_input("You:", "")
    
    # Process the user query
    if st.button("Send"):
        if user_query:
            st.session_state.messages.append({"role": "User", "content": user_query})
            llm = OpenAI(api_token=os.environ['OPENAI_API_KEY'])
            query_engine = SmartDataframe(df, config={"llm": llm})
            response = query_engine.chat(user_query)
            st.session_state.messages.append({"role": "Bot", "content": response})
            # Display the updated chat history
            display_messages()

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

# import streamlit as st
# import plotly.express as px
# import pandas as pd
# import os
# import warnings
# from pandasai import SmartDataframe
# from pandasai.llm import OpenAI
# import plotly.figure_factory as ff
# import boto3
# from google.oauth2.service_account import Credentials
# import gspread
# from sqlalchemy import create_engine
# import xlrd

# warnings.filterwarnings('ignore')

# st.set_page_config(page_title="Gen AI Dashboard!!!", page_icon=":bar_chart:", layout="wide")

# st.title(" :bar_chart: Gen AI Insight Generator")
# st.markdown('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)

# os.chdir(r"C:\Users\kushagra.sharma1\OneDrive - Incedo Technology Solutions Ltd\Desktop\DashBoard")
# df = pd.read_csv("Superstore.csv", encoding="ISO-8859-1")

# data_source = st.sidebar.selectbox("Choose Data Source", ["CSV", "Excel", "SQL Database", "AWS S3", "Google Sheets"])

# if data_source == "CSV":
#     fl = st.file_uploader(":file_folder: Upload a CSV file", type="csv")
#     if fl is not None:
#         df = pd.read_csv(fl, encoding="ISO-8859-1")
# elif data_source == "Excel":
#     fl = st.file_uploader(":file_folder: Upload an Excel file", type=["xlsx", "xls"])
#     if fl is not None:
#         df = pd.read_excel(fl)
# elif data_source == "SQL Database":
#     db_type = st.sidebar.selectbox("Choose Database Type", ["SQLite", "PostgreSQL", "MySQL", "Other"])
#     db_url = st.sidebar.text_input("Database URL")
#     if st.sidebar.button("Load Data"):
#         engine = create_engine(db_url)
#         query = st.text_area("Enter SQL Query")
#         if query:
#             df = pd.read_sql_query(query, engine)
# elif data_source == "AWS S3":
#     s3_bucket = st.sidebar.text_input("S3 Bucket Name")
#     s3_key = st.sidebar.text_input("S3 Key (file path)")
#     aws_access_key = st.sidebar.text_input("AWS Access Key", type="password")
#     aws_secret_key = st.sidebar.text_input("AWS Secret Key", type="password")
#     if st.sidebar.button("Load Data"):
#         s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
#         obj = s3.get_object(Bucket=s3_bucket, Key=s3_key)
#         df = pd.read_csv(obj['Body'])
# elif data_source == "Google Sheets":
#     google_sheet_url = st.sidebar.text_input("Google Sheet URL")
#     creds_file = st.sidebar.file_uploader("Upload Google Credentials JSON", type="json")
#     if creds_file and google_sheet_url:
#         creds = Credentials.from_service_account_info(creds_file.read())
#         client = gspread.authorize(creds)
#         sheet = client.open_by_url(google_sheet_url)
#         worksheet = sheet.sheet1
#         df = pd.DataFrame(worksheet.get_all_records())

# col1, col2 = st.columns((2))
# df["Order Date"] = pd.to_datetime(df["Order Date"])

# # Getting the min and max date 
# startDate = pd.to_datetime(df["Order Date"]).min()
# endDate = pd.to_datetime(df["Order Date"]).max()

# with col1:
#     date1 = pd.to_datetime(st.date_input("Start Date", startDate))

# with col2:
#     date2 = pd.to_datetime(st.date_input("End Date", endDate))

# df = df[(df["Order Date"] >= date1) & (df["Order Date"] <= date2)].copy()

# st.sidebar.header("Choose your filter: ")
# # Create for Region
# region = st.sidebar.multiselect("Pick your Region", df["Region"].unique())
# if not region:
#     df2 = df.copy()
# else:
#     df2 = df[df["Region"].isin(region)]

# # Create for State
# state = st.sidebar.multiselect("Pick the State", df2["State"].unique())
# if not state:
#     df3 = df2.copy()
# else:
#     df3 = df2[df2["State"].isin(state)]

# # Create for City
# city = st.sidebar.multiselect("Pick the City", df3["City"].unique())

# # Filter the data based on Region, State and City
# if not region and not state and not city:
#     filtered_df = df
# elif not state and not city:
#     filtered_df = df[df["Region"].isin(region)]
# elif not region and not city:
#     filtered_df = df[df["State"].isin(state)]
# elif state and city:
#     filtered_df = df3[df["State"].isin(state) & df3["City"].isin(city)]
# elif region and city:
#     filtered_df = df3[df["Region"].isin(region) & df3["City"].isin(city)]
# elif region and state:
#     filtered_df = df3[df["Region"].isin(region) & df3["State"].isin(state)]
# elif city:
#     filtered_df = df3[df3["City"].isin(city)]
# else:
#     filtered_df = df3[df3["Region"].isin(region) & df3["State"].isin(state) & df3["City"].isin(city)]

# category_df = filtered_df.groupby(by=["Category"], as_index=False)["Sales"].sum()

# with col1:
#     st.subheader("Category wise Sales")
#     fig = px.bar(category_df, x="Category", y="Sales", text=['${:,.2f}'.format(x) for x in category_df["Sales"]],
#                  template="seaborn", color="Category", color_discrete_sequence=px.colors.qualitative.Bold)
#     st.plotly_chart(fig, use_container_width=True)

# with col2:
#     st.subheader("Region wise Sales")
#     fig = px.pie(filtered_df, values="Sales", names="Region", hole=0.5, color_discrete_sequence=px.colors.qualitative.Prism)
#     fig.update_traces(text=filtered_df["Region"], textposition="outside")
#     st.plotly_chart(fig, use_container_width=True)

# cl1, cl2 = st.columns((2))
# with cl1:
#     with st.expander("Category_ViewData"):
#         st.write(category_df.style.background_gradient(cmap="Blues"))
#         csv = category_df.to_csv(index=False).encode('utf-8')
#         st.download_button("Download Data", data=csv, file_name="Category.csv", mime="text/csv",
#                            help='Click here to download the data as a CSV file')

# with cl2:
#     with st.expander("Region_ViewData"):
#         region = filtered_df.groupby(by="Region", as_index=False)["Sales"].sum()
#         st.write(region.style.background_gradient(cmap="Oranges"))
#         csv = region.to_csv(index=False).encode('utf-8')
#         st.download_button("Download Data", data=csv, file_name="Region.csv", mime="text/csv",
#                            help='Click here to download the data as a CSV file')

# filtered_df["month_year"] = filtered_df["Order Date"].dt.to_period("M")
# st.subheader('Time Series Analysis')

# linechart = pd.DataFrame(filtered_df.groupby(filtered_df["month_year"].dt.strftime("%Y : %b"))["Sales"].sum()).reset_index()
# fig2 = px.line(linechart, x="month_year", y="Sales", labels={"Sales": "Amount"}, height=500, template="gridon", 
#                color_discrete_sequence=["#636EFA"])
# fig2.update_layout(xaxis_title="Month-Year", yaxis_title="Sales", 
#                    title="Monthly Sales Over Time", title_x=0.5, 
#                    plot_bgcolor="rgba(0, 0, 0, 0)", paper_bgcolor="rgba(0, 0, 0, 0)",
#                    font=dict(color="white"))
# st.plotly_chart(fig2, use_container_width=True)

# with st.expander("View Data of TimeSeries:"):
#     st.write(linechart.T.style.background_gradient(cmap="Blues"))
#     csv = linechart.to_csv(index=False).encode("utf-8")
#     st.download_button('Download Data', data=csv, file_name="TimeSeries.csv", mime='text/csv')

# # Insights: Top-Selling Items
# st.subheader("Top-Selling Items Insights")
# top_items_df = filtered_df.groupby(['State', 'Sub-Category'])['Sales'].sum().reset_index()
# top_items_df = top_items_df.loc[top_items_df.groupby('State')['Sales'].idxmax()].reset_index(drop=True)

# fig_top_items = px.bar(top_items_df, x='State', y='Sales', color='Sub-Category',
#                        title="Top-Selling Items in Each State", template="plotly_white")
# st.plotly_chart(fig_top_items, use_container_width=True)

# with st.expander("View Top-Selling Items Data"):
#     st.write(top_items_df.style.background_gradient(cmap="Oranges"))
#     csv_top_items = top_items_df.to_csv(index=False).encode('utf-8')
#     st.download_button('Download Data', data=csv_top_items, file_name="Top_Selling_Items.csv", mime='text/csv')

# # Create a treemap based on Region, Category, Sub-Category
# st.subheader("Hierarchical view of Sales using TreeMap")
# fig3 = px.treemap(filtered_df, path=["Region", "Category", "Sub-Category"], values="Sales", hover_data=["Sales"],
#                   color="Sub-Category", color_discrete_sequence=px.colors.qualitative.Pastel)
# fig3.update_layout(width=800, height=650)
# st.plotly_chart(fig3, use_container_width=True)

# chart1, chart2 = st.columns((2))
# with chart1:
#     st.subheader('Segment wise Sales')
#     fig = px.pie(filtered_df, values="Sales", names="Segment", template="plotly_dark",
#                  color_discrete_sequence=px.colors.sequential.RdBu)
#     fig.update_traces(text=filtered_df["Segment"], textposition="inside")
#     st.plotly_chart(fig, use_container_width=True)

# with chart2:
#     st.subheader('Category wise Sales')
#     fig = px.pie(filtered_df, values="Sales", names="Category", template="gridon",
#                  color_discrete_sequence=px.colors.qualitative.Set3)
#     fig.update_traces(text=filtered_df["Category"], textposition="inside")
#     st.plotly_chart(fig, use_container_width=True)

# st.subheader(":point_right: Month wise Sub-Category Sales Summary")
# with st.expander("Summary_Table"):
#     df_sample = df[0:5][["Region", "State", "City", "Category", "Sales", "Profit", "Quantity"]]
#     fig = ff.create_table(df_sample, colorscale="Cividis")
#     st.plotly_chart(fig, use_container_width=True)

#     st.markdown("Month wise sub-Category Table")
#     filtered_df["month"] = filtered_df["Order Date"].dt.month_name()
#     sub_category_Year = pd.pivot_table(data=filtered_df, values="Sales", index=["Sub-Category"], columns="month")
#     st.write(sub_category_Year.style.background_gradient(cmap="Blues"))

# # Create a scatter plot
# st.subheader("Relationship between Sales and Profits using Scatter Plot")

# # Scatter Plot Animation
# data1 = px.scatter(filtered_df, x="Sales", y="Profit", size="Quantity", color="Category",
#                    color_discrete_sequence=px.colors.qualitative.T10, animation_frame="month_year")
# data1.update_layout(title="Relationship between Sales and Profits", title_x=0.5,
#                     xaxis_title="Sales", yaxis_title="Profit",
#                     plot_bgcolor="rgba(0, 0, 0, 0)", paper_bgcolor="rgba(0, 0, 0, 0)",
#                     font=dict(color="white"))
# st.plotly_chart(data1, use_container_width=True)

# # Additional charts
# st.subheader("Additional Charts")

# # Chart for Profit by Region
# with st.container():
#     st.subheader("Profit by Region")
#     region_profit_df = filtered_df.groupby("Region")["Profit"].sum().reset_index()
#     fig = px.bar(region_profit_df, x="Region", y="Profit", text=['${:,.2f}'.format(x) for x in region_profit_df["Profit"]],
#                  template="plotly_white", color="Region", color_discrete_sequence=px.colors.qualitative.Pastel1)
#     st.plotly_chart(fig, use_container_width=True)

# # Chart for Sales and Profit by Sub-Category
# with st.container():
#     st.subheader("Sales and Profit by Sub-Category")
#     sub_category_df = filtered_df.groupby("Sub-Category")[["Sales", "Profit"]].sum().reset_index()
#     fig = px.bar(sub_category_df, x="Sub-Category", y=["Sales", "Profit"], barmode="group", template="plotly_white",
#                  color_discrete_sequence=px.colors.qualitative.Vivid)
#     st.plotly_chart(fig, use_container_width=True)

# # Scatter plot for Quantity vs Discount
# with st.container():
#     st.subheader("Quantity vs Discount")
#     fig = px.scatter(filtered_df, x="Discount", y="Quantity", color="Region", size="Sales", hover_data=["Category"],
#                      template="plotly_white", color_discrete_sequence=px.colors.qualitative.T10)
#     st.plotly_chart(fig, use_container_width=True)

# with st.expander("View Data"):
#     st.write(filtered_df.iloc[:500, 1:20:2].style.background_gradient(cmap="Oranges"))

# with st.expander("Dataframe preview"):
#     st.write(df.tail(5))

# # Download original DataSet
# csv = df.to_csv(index=False).encode('utf-8')
# st.download_button('Download Data', data=csv, file_name="Data.csv", mime="text/csv")

# # Adding a chat window for the bot
# st.subheader("Chat with Data Bot")

# # Initialize the chat history
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# # Function to display chat messages
# def display_messages():
#     for msg in st.session_state.messages:
#         st.write(f"{msg['role']}: {msg['content']}")

# # Display chat history
# display_messages()

# # Text input for the user query
# user_query = st.text_input("You:", "")

# # Process the user query
# if st.button("Send"):
#     if user_query:
#         st.session_state.messages.append({"role": "User", "content": user_query})
#         llm = OpenAI(api_token=os.environ['OPENAI_API_KEY'])
#         query_engine = SmartDataframe(df, config={"llm": llm})
#         response = query_engine.chat(user_query)
#         st.session_state.messages.append({"role": "Bot", "content": response})
