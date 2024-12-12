import pandas as pd
import streamlit as st
import pycountry
import plotly.express as px

st.set_page_config(page_title='Snapshot', page_icon='📊', layout='wide')

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

if 'uploaded_file' not in st.session_state:
    st.session_state['uploaded_file'] = None
if 'cad' not in st.session_state:
    st.session_state['cad'] = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'Upload'

with st.sidebar:
    st.title("🎯 Dashboard")
    home_button = st.button("🏠 Home")
    streams_button = st.button("🎵 Streams")
    earnings_button = st.button("💲 Earnings")
    marketing_button = st.button("📣 Marketing")
    upload_button = st.button('Upload Data')

    # Update current page based on button clicks
    if upload_button:
        st.session_state.current_page = 'Upload'
    elif st.session_state.uploaded_file:
        if home_button:
            st.session_state.current_page = 'Home'
        elif streams_button:
            st.session_state.current_page = 'Streams'
        elif earnings_button:
            st.session_state.current_page = 'Earnings'
        elif marketing_button:
            st.session_state.current_page = 'Marketing'
    else:
        st.session_state.current_page = 'Upload'

if st.session_state.current_page == 'Upload':
    st.title('Data Upload')
    st.write('Upload your DistroKid data here (convert to csv before beginning)')

    uploaded_file = st.file_uploader("Upload your file here", type=['csv'])

    if uploaded_file is not None:
        st.session_state['uploaded_file'] = uploaded_file
        raw_data = pd.read_csv(uploaded_file)
        st.session_state['cad'] = cleaning_process(raw_data)
        st.success("File uploaded successfully! You can now navigate to other pages.")

else:
    if st.session_state['cad'] is None:
        st.title('Please upload data to begin.')
    else:
        cad = st.session_state['cad']
        if st.session_state.current_page == 'Home':
            st.title('At a glance...')
            c1, c2 = st.columns(2)

            # Key metrics for home page
            total_streams = cad['Quantity'].sum()
            total_earnings = cad['Earnings'].sum()
            avg_eps = total_earnings / total_streams

            def key_metric_styling(label, value):
                return f"""
                <div style="padding: 5px; text-align: left; display: inline-block; width: 100%;">
                    <div style="color: white; font-size: 32px; font-weight: bold; background-color: transparent; padding: 5px; text-decoration: underline;">
                        {label}
                    </div>
                    <div style="align: right; background-color: white; color: black; font-size: 24px; font-weight: bold; text-align: right; padding: 5px; width: 80%;">
                        {value}
                    </div>
                </div>
                """

            with c1:
                st.title('Key Metrics')
                st.markdown(key_metric_styling('Total Streams', f"{total_streams:,}"), unsafe_allow_html=True)
                st.markdown(key_metric_styling('Total Earnings (USD)', f"${round(total_earnings, 2):,}"), unsafe_allow_html=True)
                st.markdown(key_metric_styling('Average Earnings/Stream', f"${round(avg_eps, 5):,} (AES)"), unsafe_allow_html=True)

            with c2:
                st.title('International Reach')
                # Getting all countries for the graph
                all_countries = px.data.gapminder()[['country']].drop_duplicates()
                all_countries.columns = ['Country']

                country_streams = cad.groupby('Country')['Quantity'].sum().reset_index()
                country_streams_all = all_countries.merge(country_streams, on='Country', how='outer')
                country_streams_all['Quantity'] = country_streams_all['Quantity'].fillna(0)
                country_streams_exu = country_streams_all[country_streams_all['Country'] != 'Unknown']

                include_us = st.checkbox('Include US Data', value=False)
                if not include_us:
                    country_streams_exu = country_streams_exu[country_streams_exu['Country'] != 'United States']

                mint_green_scale = [
                    (0.0, '#e3faf0'),
                    (0.3, '#baf7dd'),
                    (0.6, '#84f5c5'),
                    (1.0, '#37faa9')
                ]

                fig = px.choropleth(
                    country_streams_exu, locations='Country', locationmode='country names',
                    color='Quantity',
                    color_continuous_scale=mint_green_scale
                )

                fig.update_layout(
                    geo=dict(
                        bgcolor='black',
                        landcolor='white'
                    ),
                    title=None, margin=dict(l=0, r=0, t=0, b=0),
                    height=400
                )

                st.plotly_chart(fig, use_container_width=True)
            
            c1a, c2a, c3a = st.columns(3)

            with c1a:
                st.header('Top 5 Releases')
                top5releases = cad.groupby('Title')['Quantity'].sum()
                st.write(top5releases.head())
            
            with c2a:
                st.header('Top 5 Countries')
                st.write(country_streams_exu.head())
            
            with c3a:
                st.header('Top 5 Platforms')
                top5platforms = cad.groupby('Store')['Quantity'].sum()
                st.write(top5platforms.head())

        elif st.session_state.current_page == 'Streams':
            st.title('Streaming Metrics')

        elif st.session_state.current_page == 'Earnings':
            st.title('Earnings Metrics')

        elif st.session_state.current_page == 'Marketing':
            st.title('Marketing Strategies')
