import pandas as pd
import streamlit as st
import pycountry
import plotly.express as px

st.set_page_config(page_title = 'Snapshot', page_icon = '📊', layout = 'wide')
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

# Start of Dashboard Design

menu = st.sidebar.radio(
    'Dashboard',
    options = ['Home', 'Streams', 'Earnings', 'Marketing']
)

if uploaded_file:
    # Data processing input
    raw_data = pd.read_csv(uploaded_file)
    if raw_data.empty:
            st.error("The uploaded file is empty.")
            st.stop()
    cad = cleaning_process(raw_data)

    # Home menu design
    if menu == 'Home':
        st.title('At a glance...')
        c1, c2 = st.columns(2)
        
        # Key metrics for home page (at a glance)
        total_streams = cad['Quantity'].sum()
        total_earnings = cad['Earnings'].sum()
        avg_eps = total_earnings/total_streams

        def key_metric_styling(label, value):
            return f"""
            <div style="padding: 5px; text-align: left; display: inline-block; width: 100%;">
                <!-- Label styling -->
                <div style="color: white; font-size: 32px; font-weight: bold; background-color: transparent; padding: 5px; text-decoration: underline;">
                    {label}
                </div>
                <!-- Value styling -->
                <div style="align: right; background-color: white; color: black; font-size: 24px; font-weight: bold; text-align: right; padding: 5px; width: 80%;">
                    {value}
                </div>
            </div>
            """

        with c1:
            st.title('Key Metrics')
            st.markdown(key_metric_styling('Total Streams', f"{total_streams:,}"), unsafe_allow_html=True)
            st.markdown(key_metric_styling('Total Earnings (USD)', f"${round((total_earnings), 2):,} (USD)"), unsafe_allow_html=True)
            st.markdown(key_metric_styling('Average Earnings/Stream', f"${round((avg_eps), 5):,} (AES)"), unsafe_allow_html=True)
    
        with c2:
            # Add a radio button for the toggle
            st.title('International Reach')
            # Getting all countries for the graph
            all_countries = px.data.gapminder()[['country']].drop_duplicates()
            all_countries.columns = ['Country']

            country_streams = cad.groupby('Country')['Quantity'].sum().reset_index()
            country_streams_all = all_countries.merge(country_streams, on = 'Country', how = 'outer')
            country_streams_all['Quantity'] = country_streams_all['Quantity'].fillna(0)
            country_streams_exu = country_streams_all[country_streams_all['Country'] != 'Unknown']

            include_us = st.checkbox('Include US Data', value = False)
            if not include_us:
                country_streams_exu = country_streams_exu[country_streams_exu['Country'] != 'United States']
            fig = px.choropleth(
                        country_streams_exu, locations = 'Country', locationmode = 'country names', 
                        color = 'Quantity',
                        color_continuous_scale= 'gray',
                        range_color = (0, country_streams_exu['Quantity'].max())
            )

            fig.update_layout(
                    geo=dict(
                        bgcolor = 'black',
                        landcolor = 'white'
                    ),
                    title = None, margin = dict(l = 0, r = 0, t = 0, b = 0),
                    height = 400
            )
            
            # Allocating for streams with an unknown country of sale
            unknown_streams = country_streams[country_streams['Country'] == 'Unknown']['Quantity'].sum()

            st.plotly_chart(fig, use_container_width=True)
            

else:
    st.info('Please upload your data to begin.')

