import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px

# --- THE SCRAPER FUNCTION ---
@st.cache_data(ttl=3600) # Cache data for 1 hour so you don't spam Riyasewana
def get_riyasewana_data(search_query):
    data = []
    # Scraping first 3 pages (approx 40-50 cars)
    for page in range(1, 4): 
        url = f"https://riyasewana.com/search/{search_query}?page={page}"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        items = soup.find_all('li', class_='item')
        
        for item in items:
            try:
                # Extract Name/Title
                title = item.find('h2').text.strip()
                
                # Extract Price (Cleaning the "Rs." and commas)
                price_text = item.find('div', class_='boxintxt').b.text
                if "Negotiable" in price_text or "Contact" in price_text:
                    continue # Skip if no price listed
                price = int(price_text.replace('Rs.', '').replace(',', '').strip())
                
                # Extract Year (Usually in the title or description, heavily simplified here)
                # In Riyasewana, year is often in the link text or details
                # For this MVP, let's assume the user puts the year in the title for now
                # In a real app, you need regex here.
                year = 0
                for word in title.split():
                    if word.isdigit() and len(word) == 4 and word.startswith('20'):
                        year = int(word)
                        break
                
                if year > 2010 and price > 1000000: # Simple filter
                    data.append({"Model": title, "Year": year, "Price": price})
            except:
                continue
                
    return pd.DataFrame(data)

# --- THE FRONTEND (Streamlit) ---
st.title("🇱🇰 Vehicle Price Analytics (MVP)")
st.write("Real-time analysis of Riyasewana listings")

# User Input
car_model = st.selectbox("Select Model to Analyze", ["wagon-r", "vitz", "alto", "premio"])

if st.button("Analyze Market"):
    with st.spinner('Scraping data from Riyasewana...'):
        df = get_riyasewana_data(car_model)
        
    if not df.empty:
        # 1. Summary Metrics
        avg_price = df['Price'].mean()
        min_price = df['Price'].min()
        max_price = df['Price'].max()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Average Price", f"Rs. {avg_price/100000:,.2f} Lakhs")
        c2.metric("Lowest Market Price", f"Rs. {min_price/100000:,.2f} Lakhs")
        c3.metric("Highest Market Price", f"Rs. {max_price/100000:,.2f} Lakhs")
        
        # 2. The Chart
        st.subheader(f"Price Trend by Year ({car_model.title()})")
        # Group by year to get average price per year
        avg_by_year = df.groupby('Year')['Price'].mean().reset_index()
        
        fig = px.bar(avg_by_year, x='Year', y='Price', 
                     title="Average Market Price vs Year of Manufacture",
                     labels={'Price': 'Price (LKR)'})
        st.plotly_chart(fig)
        
        # 3. Raw Data Table (Optional)
        with st.expander("View Raw Data"):
            st.dataframe(df)
            
    else:
        st.error("Could not find enough data. Try a different car.")