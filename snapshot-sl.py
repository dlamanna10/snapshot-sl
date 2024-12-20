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

    if 'Reporting Date' in artist_data.columns:
            artist_data['Reporting Date'] = artist_data['Reporting Date'].astype(str)

            # Replace invalid entries (e.g., '#') with NaN
            artist_data['Reporting Date'] = artist_data['Reporting Date'].replace(r'^[#]+$', pd.NA, regex=True)

            # Convert valid Reporting Date to datetime
            artist_data['Reporting Date'] = pd.to_datetime(artist_data['Reporting Date'], errors='coerce', format='%Y-%m-%d')

            # For rows with missing Reporting Date, infer from Sale Month
            if 'Sale Month' in artist_data.columns:
                missing_reporting_date = artist_data['Reporting Date'].isna()
                artist_data.loc[missing_reporting_date, 'Reporting Date'] = pd.to_datetime(
                    artist_data.loc[missing_reporting_date, 'Sale Month'] + '-01', errors='coerce'
                )

            # Optional: Drop rows with invalid dates after all attempts to clean
            artist_data = artist_data.dropna(subset=['Reporting Date'])    

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
                ), title=None, margin=dict(l=0, r=0, t=0, b=0), height=400
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

            c1, c2 = st.columns(2)

            with c1:
                st.subheader('Stream Distribution by Platform')
                platform_streams = cad.groupby('Store')['Quantity'].sum().sort_values(ascending = False).reset_index()
                total_streams = platform_streams['Quantity'].sum()
                platform_streams['Percentage'] = (platform_streams['Quantity'] / total_streams) * 100
                
                threshold = 3
                large_stores = platform_streams[platform_streams['Percentage'] >= threshold]
                small_stores = platform_streams[platform_streams['Percentage'] < threshold]

                # Combine small stores into 'Other'
                other_row = pd.DataFrame({
                    'Store': ['Other'],
                    'Quantity': [small_stores['Quantity'].sum()],
                    'Percentage': [small_stores['Percentage'].sum()]
                })

                # Append the 'Other' category to large stores
                platform_data = pd.concat([large_stores, other_row], ignore_index=True)
                
                fig = px.pie(
                    platform_data, 
                    names='Store', 
                    values='Quantity', 
                    hover_data={'Percentage': ':.2f'},  # Show percentage with 2 decimal places
                    labels={'Quantity': 'Total Streams', 'Percentage': 'Percentage Contribution'},
                    color_discrete_sequence=px.colors.sequential.Mint
                )
                fig.update_traces(textinfo='percent+label', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)

            cad['Reporting Date'] = pd.to_datetime(cad['Reporting Date'], format = '%m/%d/%Y')
            cad['Year'] = cad['Reporting Date'].dt.year

            with c2:
                st.subheader('Total Streams by Year')
                yearly_streams = cad.groupby('Year')['Quantity'].sum().reset_index()

                fig = px.bar(
                    yearly_streams,
                    x = 'Year', y = 'Quantity',
                    labels = {'Quantity':'Total Streams', 'Year':'Year'},
                    color='Year'
                )
                st.plotly_chart(fig, use_container_width=True)

            st.subheader('Total Streams by Month')
            cad['Sale Month'] = pd.to_datetime(cad['Sale Month'], format='%Y-%m')
            cad['Month'] = cad['Sale Month'].dt.to_period('M') 
            monthly_streams = cad.groupby('Month')['Quantity'].sum().reset_index()
            monthly_streams['Month'] = monthly_streams['Month'].dt.to_timestamp()
            
            fig = px.line(
                monthly_streams, x='Month', y='Quantity',
                labels={'Quantity':'Total Streams', 'Month':'Month'},
                color_discrete_sequence=px.colors.sequential.Mint,
                line_shape='spline'
            )
            fig.update_traces(fill='tozeroy', fillcolor='rgba(186, 247, 221, 0.5)', opacity=0.2, line=dict(color='#37faa9'),mode='lines+markers')
            st.plotly_chart(fig, use_container_width=True)

            st.header('Release Analysis')
            selected_title = st.selectbox('Release:', options=cad['Title'].unique())
            c1a, c2a, c3a = st.columns(3)

            with c1a:
                title_data = cad[cad['Title'] == selected_title]
                platform_title_streams = title_data.groupby('Store')['Quantity'].sum().sort_values(ascending=False).reset_index()

                # Calculate total streams and percentage contribution
                total_streams = title_data['Quantity'].sum()
                platform_title_streams['Percentage'] = (platform_title_streams['Quantity'] / total_streams) * 100

                # Threshold for grouping small stores into 'Other'
                threshold = 1.5
                large_stores = platform_title_streams[platform_title_streams['Percentage'] >= threshold]
                small_stores = platform_title_streams[platform_title_streams['Percentage'] < threshold]

                # Combine small stores into 'Other' if necessary
                if not small_stores.empty:
                    other_row = pd.DataFrame({
                        'Store': ['Other'],
                        'Quantity': [small_stores['Quantity'].sum()],
                        'Percentage': [small_stores['Percentage'].sum()]
                    })
                    title_stream_data = pd.concat([large_stores, other_row], ignore_index=True)
                else:
                    title_stream_data = large_stores

                # Sort so "Other" appears last
                title_stream_data = title_stream_data.sort_values(by='Store', ascending=True)

                # Create the pie chart
                fig = px.pie(
                    title_stream_data, 
                    title='Stream Distribution by Platform',
                    names='Store', 
                    values='Quantity', 
                    hover_data={'Percentage': ':.2f'},
                    labels={'Quantity': 'Total Streams', 'Percentage': 'Percentage Contribution'},
                    color_discrete_sequence=px.colors.sequential.Mint
                )

                # Customize traces and layout
                fig.update_traces(
                    textinfo='percent+label', 
                    hole=0.4,
                    hovertemplate="<b>%{label}</b><br>Streams: %{value:,}<br>Percentage: %{customdata:.2f}%"
                )

                # Display the chart
                st.plotly_chart(fig, use_container_width=True)

            with c2a:
                yearly_streams = title_data.groupby('Year')['Quantity'].sum().reset_index()
                fig_year = px.bar(yearly_streams, x='Year', y='Quantity', title="Streams by Year",
                                labels={'Quantity': 'Total Streams', 'Year': 'Year'},
                                color='Year')
                st.plotly_chart(fig_year, use_container_width=True)

            with c3a:
                title_monthly_streams = title_data.groupby('Month')['Quantity'].sum().reset_index()
                title_monthly_streams['Month'] = title_monthly_streams['Month'].dt.to_timestamp()
                
                fig = px.line(
                    title_monthly_streams, x='Month', y='Quantity',
                    title='Streams by Month',
                    labels={'Quantity':'Total Streams', 'Month':'Month'},
                    color_discrete_sequence=px.colors.sequential.Mint,
                    line_shape='spline'
                )
                fig.update_traces(fill='tozeroy', fillcolor='rgba(186, 247, 221, 0.5)', opacity=0.2, line=dict(color='#37faa9'),mode='lines+markers')
                st.plotly_chart(fig, use_container_width=True)


            st.subheader('All Releases')
            def release_styling(title, value):
                return f"""
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <div style="font-size: 20px; font-weight: bold; color: white; text-align: left; width: fit-content;">
                        {title}
                    </div>
                    <div style="flex-grow: 1; height: 2px; background-image: linear-gradient(to right, white, #37faa9); margin: 0 10px;"></div>
                    <div style="font-size: 16px; font-weight: bold; color: #37faa9; text-align: right; width: fit-content;">
                        {value:,}
                    </div>
                </div>
                """

            earliest_year = cad.groupby('Title')['Year'].min().reset_index()
            total_streams = cad.groupby('Title')['Quantity'].sum().reset_index()
            title_summary = pd.merge(earliest_year, total_streams, on='Title')
            title_summary = title_summary.sort_values(by=['Year', 'Quantity'], ascending=[True, False])

            current_year = None
            for _, row in title_summary.iterrows():
                if row['Year'] != current_year:
                    st.markdown(f"<div style='font-size: 24px; font-weight: bold; color: #37faa9; margin-top: 20px;'>{row['Year']}</div>", unsafe_allow_html=True)
                    current_year = row['Year']
                st.markdown(release_styling(row['Title'], row['Quantity']), unsafe_allow_html=True)



        elif st.session_state.current_page == 'Earnings':
            st.title('Earnings Metrics')

            c1, c2 = st.columns(2)

            with c1:
                st.subheader('Earning Distribution by Platform')
                platform_earnings = cad.groupby('Store')['Earnings'].sum().sort_values(ascending = False).reset_index()
                platform_earnings['Earnings'] = platform_earnings['Earnings'].round(2)
                total_earnings = platform_earnings['Earnings'].sum()
                platform_earnings['Percentage'] = (platform_earnings['Earnings'] / total_earnings) * 100
                
                threshold = 3
                large_stores = platform_earnings[platform_earnings['Percentage'] >= threshold]
                small_stores = platform_earnings[platform_earnings['Percentage'] < threshold]

                # Combine small stores into 'Other'
                other_row = pd.DataFrame({
                    'Store': ['Other'],
                    'Earnings': [small_stores['Earnings'].sum()],
                    'Percentage': [small_stores['Percentage'].sum()]
                })

                # Append the 'Other' category to large stores
                platform_data = pd.concat([large_stores, other_row], ignore_index=True)
                
                fig = px.pie(
                    platform_data, 
                    names='Store', 
                    values='Earnings', 
                    hover_data={'Percentage': ':.2f'},  # Show percentage with 2 decimal places
                    labels={'Quantity': 'Total Earnings', 'Percentage': 'Percentage Contribution'},
                    color_discrete_sequence=px.colors.sequential.Mint
                )
                fig.update_traces(textinfo='percent+label', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)

            cad['Reporting Date'] = pd.to_datetime(cad['Reporting Date'], format = '%m/%d/%Y')
            cad['Year'] = cad['Reporting Date'].dt.year

            with c2:
                st.subheader('Total Earnings by Year')
                yearly_earnings = cad.groupby('Year')['Earnings'].sum().reset_index()
                yearly_earnings['Earnings'] = yearly_earnings['Earnings'].round(2)

                fig = px.bar(
                    yearly_earnings,
                    x = 'Year', y = 'Earnings',
                    labels = {'Earnings':'Total Earnings', 'Year':'Year'},
                    color='Year'
                )
                st.plotly_chart(fig, use_container_width=True)

            st.subheader('Total Earnings by Month')
            cad['Sale Month'] = pd.to_datetime(cad['Sale Month'], format='%Y-%m')
            cad['Month'] = cad['Sale Month'].dt.to_period('M') 
            monthly_earnings = cad.groupby('Month')['Earnings'].sum().reset_index()
            monthly_earnings['Earnings'] = monthly_earnings['Earnings'].round(2)
            monthly_earnings['Month'] = monthly_earnings['Month'].dt.to_timestamp()
            
            fig = px.line(
                monthly_earnings, x='Month', y='Earnings',
                labels={'Earnings':'Total Earnings', 'Month':'Month'},
                color_discrete_sequence=px.colors.sequential.Mint,
                line_shape='spline'
            )
            fig.update_traces(fill='tozeroy', fillcolor='rgba(186, 247, 221, 0.5)', opacity=0.2, line=dict(color='#37faa9'),mode='lines+markers')
            st.plotly_chart(fig, use_container_width=True)

            st.header('Release Analysis')
            selected_title = st.selectbox('Release:', options=cad['Title'].unique())
            c1a, c2a, c3a = st.columns(3)

            with c1a:
                title_data = cad[cad['Title'] == selected_title]
                platform_title_earnings = title_data.groupby('Store')['Earnings'].sum().sort_values(ascending=False).reset_index()
                platform_title_earnings['Earnings'] = platform_title_earnings['Earnings'].round(2)

                total_earnings = title_data['Earnings'].sum()
                platform_title_earnings['Percentage'] = (platform_title_earnings['Earnings'] / total_earnings) * 100

                threshold = 1.5
                large_stores = platform_title_earnings[platform_title_earnings['Percentage'] >= threshold]
                small_stores = platform_title_earnings[platform_title_earnings['Percentage'] < threshold]

                if not small_stores.empty:
                    other_row = pd.DataFrame({
                        'Store': ['Other'],
                        'Earnings': [small_stores['Earnings'].sum()],
                        'Percentage': [small_stores['Percentage'].sum()]
                    })
                    title_earning_data = pd.concat([large_stores, other_row], ignore_index=True)
                else:
                    title_earning_data = large_stores

                title_earning_data = title_earning_data.sort_values(by='Store', ascending=True)

                fig = px.pie(
                    title_earning_data, 
                    title='Earnings by Platform',
                    names='Store', 
                    values='Earnings', 
                    hover_data={'Percentage': ':.2f'},
                    labels={'Earnings': 'Total Earnings', 'Percentage': 'Percentage Contribution'},
                    color_discrete_sequence=px.colors.sequential.Mint
                )

                # Customize traces and layout
                fig.update_traces(
                    textinfo='percent+label', 
                    hole=0.4,
                    hovertemplate="<b>%{label}</b><br>Earnings: $%{value:,}<br>Percentage: %{customdata:.2f}%"
                )

                # Display the chart
                st.plotly_chart(fig, use_container_width=True)

            with c2a:
                yearly_earnings = title_data.groupby('Year')['Earnings'].sum().reset_index()
                yearly_earnings['Earnings'] = yearly_earnings['Earnings'].round(2)
                fig_year = px.bar(yearly_earnings, x='Year', y='Earnings', title="Earnings by Year",
                                labels={'Earnings': 'Total Earnings', 'Year': 'Year'},
                                color='Year')
                st.plotly_chart(fig_year, use_container_width=True)

            with c3a:
                title_monthly_streams = title_data.groupby('Month')['Earnings'].sum().reset_index()
                title_monthly_streams['Month'] = title_monthly_streams['Month'].dt.to_timestamp()
                
                fig = px.line(
                    title_monthly_streams, x='Month', y='Earnings',
                    title='Earnings by Month',
                    labels={'Earnings':'Total Earnings', 'Month':'Month'},
                    color_discrete_sequence=px.colors.sequential.Mint,
                    line_shape='spline'
                )
                fig.update_traces(fill='tozeroy', fillcolor='rgba(186, 247, 221, 0.5)', opacity=0.2, line=dict(color='#37faa9'),mode='lines+markers')
                st.plotly_chart(fig, use_container_width=True)


            st.subheader('All Releases (USD)')
            def release_styling(title, value):
                return f"""
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <div style="font-size: 20px; font-weight: bold; color: white; text-align: left; width: fit-content;">
                        {title}
                    </div>
                    <div style="flex-grow: 1; height: 2px; background-image: linear-gradient(to right, white, #37faa9); margin: 0 10px;"></div>
                    <div style="font-size: 16px; font-weight: bold; color: #37faa9; text-align: right; width: fit-content;">
                        ${value:,}
                    </div>
                </div>
                """

            earliest_year = cad.groupby('Title')['Year'].min().reset_index()
            total_earnings = cad.groupby('Title')['Earnings'].sum().reset_index()
            total_earnings['Earnings'] = total_earnings['Earnings'].round(2)
            title_summary = pd.merge(earliest_year, total_earnings, on='Title')
            title_summary = title_summary.sort_values(by=['Year', 'Earnings'], ascending=[True, False])

            current_year = None
            for _, row in title_summary.iterrows():
                if row['Year'] != current_year:
                    st.markdown(f"<div style='font-size: 24px; font-weight: bold; color: #37faa9; margin-top: 20px;'>{row['Year']}</div>", unsafe_allow_html=True)
                    current_year = row['Year']
                st.markdown(release_styling(row['Title'], row['Earnings']), unsafe_allow_html=True)

        elif st.session_state.current_page == 'Marketing':
            st.title('Marketing Strategies')
