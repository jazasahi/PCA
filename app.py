import streamlit as st
import pandas as pd
import sqlite3

# Streamlit App Title
st.title("Pharmacy Claims Audit Tool")

# Upload CSV File
uploaded_file = st.file_uploader("Upload Pharmacy Claims Data (CSV)", type=["csv"])

if uploaded_file:
    # Load data into DataFrame
    df = pd.read_csv(uploaded_file)
    st.write("### Preview of Uploaded Data")
    st.dataframe(df.head())

    # Create SQLite Database
    conn = sqlite3.connect(":memory:")
    df.to_sql("pharmacy_claims", conn, index=False, if_exists="replace")

    # Filtering Options
    st.sidebar.header("Filter Options")
    min_cost = st.sidebar.number_input("Minimum Cost", min_value=0.0, value=0.0)
    max_cost = st.sidebar.number_input("Maximum Cost", min_value=0.0, value=1000.0)
    selected_pharmacy = st.sidebar.text_input("Pharmacy ID (optional)")
    selected_patient = st.sidebar.text_input("Patient ID (optional)")

    # Query: Detect Duplicate Claims
    query_duplicates = """
    SELECT patient_id, drug_ndc, prescriber_id, fill_date, COUNT(*) AS claim_count
    FROM pharmacy_claims
    GROUP BY patient_id, drug_ndc, prescriber_id, fill_date
    HAVING COUNT(*) > 1;
    """
    
    # Query: Detect Early Refills
    query_early_refills = """
    SELECT patient_id, drug_ndc, pharmacy_id, fill_date, days_supply,
           LAG(fill_date) OVER (PARTITION BY patient_id, drug_ndc ORDER BY fill_date) AS prev_fill_date
    FROM pharmacy_claims;
    """
    
    # Query: Detect High-Cost Claims with Risk Score
    query_high_cost = f"""
    SELECT claim_id, pharmacy_id, drug_ndc, submitted_cost, 
           AVG(submitted_cost) OVER (PARTITION BY drug_ndc) AS avg_cost,
           (submitted_cost - AVG(submitted_cost) OVER (PARTITION BY drug_ndc)) / AVG(submitted_cost) OVER (PARTITION BY drug_ndc) * 100 AS risk_score
    FROM pharmacy_claims
    WHERE submitted_cost BETWEEN {min_cost} AND {max_cost};
    """
    
    # Query Selection Dropdown
    query_options = {
        "Duplicate Claims": query_duplicates,
        "Early Refills": query_early_refills,
        "High-Cost Claims with Risk Score": query_high_cost,
    }
    selected_query = st.selectbox("Select Audit Type", list(query_options.keys()))
    
    # Run Query
    if st.button("Run Audit"):
        query_result = pd.read_sql(query_options[selected_query], conn)
        
        # Apply additional filters
        if selected_pharmacy:
            query_result = query_result[query_result["pharmacy_id"].astype(str) == selected_pharmacy]
        if selected_patient:
            query_result = query_result[query_result["patient_id"].astype(str) == selected_patient]
        
        st.write(f"### {selected_query} Results")
        st.dataframe(query_result)
    
    # Close Connection
    conn.close()
