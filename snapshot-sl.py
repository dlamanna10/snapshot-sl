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
    upload_button = st.button('🗃️ Upload Data')

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
            c1, c2, c3 = st.columns(3)

            # Key metrics for home page
            total_streams = cad['Quantity'].sum()
            total_earnings = cad['Earnings'].sum()
            avg_eps = total_earnings / total_streams

            def key_metric_styling(label, value):
                return f"""
                <div style="padding: 5px; text-align: left; display: inline-block; width: 100%;">
                    <div style="color: white; font-size: 30px; font-weight: bold; background-color: transparent; padding: 5px; text-decoration: underline;">
                        {label}
                    </div>
                    <div style="align: right; background-image: linear-gradient(to right, transparent, #37faa9); color: white; 
                        font-size: 24px; font-weight: bold; text-align: left; padding: 5px; width: 100%;">
                        {value}
                    </div>
                </div>
                """
            
            with c1:
                st.markdown(key_metric_styling('Total Streams', f"{total_streams:,}"), unsafe_allow_html=True)
            with c2:
                st.markdown(key_metric_styling('Total Earnings (USD)', f"${round(total_earnings, 2):,}"), unsafe_allow_html=True)
            with c3:
                st.markdown(key_metric_styling('Average Earnings/Stream', f"${round(avg_eps, 5):,} (AES)"), unsafe_allow_html=True)

            st.subheader('International Reach')
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
            
            # Top 5 Section
            c1a, c2a, c3a = st.columns([2, 0.3, 2])
            
            # Styling for Top 5 section
            def top_5_styling(label, value):
                return f"""
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <div style="font-size: 20px; font-weight: bold; color: white; text-align: left; width: fit-content;">
                        {label}
                    </div>
                    <div style="flex-grow: 1; height: 2px; background-image: linear-gradient(to right, white, #37faa9); margin: 0 10px;"></div>
                    <div style="font-size: 16px; font-weight: bold; color: #37faa9; text-align: right; width: fit-content;">
                        {value}
                    </div>
                </div>
                """
            
            # Top 5 - Streams
            with c1a:
                st.header('Top 5 Releases')
                st.subheader('Streams')
                top5releases_s = cad.groupby('Title')['Quantity'].sum().sort_values(ascending = False).head()
                for title, quantity in top5releases_s.items():
                    st.markdown(top_5_styling(title, quantity), unsafe_allow_html=True)
                st.write('') # Empty for spacing

                st.header('Top 5 Countries')
                st.subheader('Streams')
                top5countries_s = cad[cad['Country'] != 'Unknown'].groupby('Country')['Quantity'].sum().sort_values(ascending = False).head()
                for country, title in top5countries_s.items():
                    st.markdown(top_5_styling(country, title), unsafe_allow_html=True)
                st.write('') # Empty for spacing
            
                st.header('Top 5 Platforms')
                st.subheader('Streams')
                top5platforms_s = cad.groupby('Store')['Quantity'].sum().sort_values(ascending = False).head()
                for store, quantity in top5platforms_s.items():
                    st.markdown(top_5_styling(store, quantity), unsafe_allow_html=True)

            # Spacing column
            with c2a:
                st.write('')

            # Top 5 - Earnings
            with c3a:
            # Top 5 Earnings section
                st.header('') # Empty for spacing
                st.subheader('Earnings (USD)')
                top5releases_e = cad.groupby('Title')['Earnings'].sum().sort_values(ascending = False).head()
                for title, earnings in top5releases_e.items():
                    st.markdown(top_5_styling(title, f"${round(earnings, 2):,}"), unsafe_allow_html=True)
                st.write('') # Empty for spacing

                st.header('') # Empty for spacing
                st.subheader('Earnings (USD)')
                top5countries_e = cad[cad['Country'] != 'Unknown'].groupby('Country')['Earnings'].sum().sort_values(ascending = False).head()
                for country, earnings in top5countries_e.items():
                    st.markdown(top_5_styling(country, f"${round(earnings, 2):,}"), unsafe_allow_html=True)
                st.write('') # Empty for spacing

                st.header('') # Empty for spacing
                st.subheader('Earnings (USD)')
                top5platforms_e = cad.groupby('Store')['Earnings'].sum().sort_values(ascending = False).head()
                for store, earnings in top5platforms_e.items():
                    st.markdown(top_5_styling(store, f"${round(earnings, 2):,}"), unsafe_allow_html=True)

        elif st.session_state.current_page == 'Streams':
            st.title('Streaming Metrics')
            st.subheader('Stream Distribution by Platform')
            platform_streams = cad.groupby('Store')['Quantity'].sum().sort_values(ascending = False).reset_index()
            platform_streams = platform_streams[platform_streams['Quantity'] > 1000]
            fig = px.pie(
                platform_streams, names = 'Platform', values = 'Quantity', 
                hover_data = {'Quantity' : True}, labels = {'Quantity' : 'Total Streams'},
                color_discrete_sequence = px.colors.sequential.Mint
            )           
            fig.update_traces(textinfo = 'percent+label')
            st.plotly_chart(fig, use_conntainer_width=True) 

        elif st.session_state.current_page == 'Earnings':
            st.title('Earnings Metrics')

        elif st.session_state.current_page == 'Marketing':
            st.title('Marketing Strategies')
