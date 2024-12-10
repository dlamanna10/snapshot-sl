import pandas as pd
import streamlit as st
import pycountry
import plotly.express as ps

st.set_page_config(page_title = 'Snapshot', page_icon = '📊', layout = 'wide')
st.title('Your Dashboard')

# Upload DistroKid CSV (try and find way to convert from tsv to csv for them)
uploaded_file = st.file_uploader('Upload your DistroKid data here (convert to csv)', type=['csv'])

def cleaning_process(artist_data):
    # Drop unnecessary columns
    columns_to_drop = ['ISRC', 'UPC', 'Team Percentage', 'Song/Album', 'Songwriter Royalties Withheld']
    artist_data = artist_data.drop(columns=[col for col in columns_to_drop if col in artist_data.columns], errors='ignore')

    # Renaming 'Earnings (USD)' to 'Earnings'
    if 'Earnings (USD)' in artist_data.columns:
        artist_data['Earnings'] = artist_data['Earnings (USD)']
        artist_data = artist_data.drop(columns=['Earnings (USD)'])

    # Convert 2-letter country codes to full country names
    def get_country_name(alpha_2_code):
        if pd.isna(alpha_2_code) or alpha_2_code == 'OU':
            return 'Unknown'
        try:
            country = pycountry.countries.get(alpha_2=alpha_2_code.upper())
            return country.name if country else 'Unknown'
        except AttributeError:
            return 'Unknown'

    if 'Country of Sale' in artist_data.columns:
        artist_data['Country'] = artist_data['Country of Sale'].apply(get_country_name)
        artist_data = artist_data.drop(columns=['Country of Sale'])

    return artist_data

if uploaded_file:
    try:
        # Read the uploaded CSV
        raw_data = pd.read_csv(uploaded_file)

        # Validate the uploaded file
        if raw_data.empty:
            st.error("The uploaded file is empty.")
            st.stop()

        # Apply the cleaning process
        cad = cleaning_process(raw_data)

        # Display the cleaned data
        st.subheader('Cleaned Data')
        st.dataframe(cad)

    except Exception as e:
        st.error(f"An error occurred: {e}")
