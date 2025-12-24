import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
import re # Added regex for better number extraction

# --- THE SCRAPER FUNCTION ---
@st.cache_data(ttl=3600)
def get_riyasewana_data(search_query):
    data = []
    
    # 1. ADD HEADERS (To look like a real browser and avoid blocking)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    status_placeholder = st.empty() # Placeholder for loading status

    # Scraping first 3 pages
    for page in range(1, 4): 
        url = f"https://riyasewana.com/search/{search_query}?page={page}"
        
        try:
            response = requests.get(url, headers=headers)
            # Debug: Check if the site is blocking us
            if response.status_code != 200:
                st.error(f"Error accessing page {page}: Status Code {response.status_code}")
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.find_all('li', class_='item')
            
            status_placeholder.text(f"Scraping Page {page}: Found {len(items)} ads...")
            
            if len(items) == 0:
                st.warning(f"No items found on page {page}. The HTML structure might have changed.")
            
            for item in items:
                try:
                    # --- TITLE EXTRACTION ---
                    title_tag = item.find('h2')
                    if not title_tag:
                        continue
                    title = title_tag.text.strip()
                    
                    # --- PRICE EXTRACTION (More Robust) ---
                    price_div = item.find('div', class_='boxintxt')
                    if not price_div:
                        continue
                        
                    price_text = price_div.b.text.strip()
                    
                    # Skip 'Negotiable' or 'Contact'
                    if "Negotiable" in price_text or "Contact" in price_text:
                        continue

                    # Use Regex to keep only numbers
                    price_numbers = re.sub("[^0-9]", "", price_text)
                    if not price_numbers:
                        continue
                    price = int(price_numbers)

                    # --- YEAR EXTRACTION (Improved) ---
                    # Look for a 4-digit number starting with 19 or 20 in the title
                    year_match = re.search(r'\b(19|20)\d{2}\b', title)
                    
                    if year_match:
                        year = int(year_match.group(0))
                    else:
                        # Fallback: Try to find year in the link URL
                        link = item.find('a')['href']
                        url_year_match = re.search(r'/(19|20)\d{2}/', link)
                        if url_year_match:
                             year = int(url_year_match.group(0).replace('/',''))
                        else:
                            year = 0 # Could not find year

                    # --- FILTERING ---
                    # Relaxed filters: Price > 1 Lakh, Year > 2000
                    if year > 2000 and price > 100000: 
                        data.append({"Model": title, "Year": year, "Price": price})
                        
                except Exception as e:
                    # If one car fails, just skip it, don't crash
                    continue
                    
        except Exception as e:
            st.error(f"Connection Error: {e}")

    status_placeholder.empty() # Clear the loading text
    return pd.DataFrame(data)

# --- THE FRONTEND ---
st.title("🇱🇰 Vehicle Price Analytics (Debug Mode)")
st.write("Real-time analysis of Riyasewana listings")

# User Input
car_model = st.selectbox("Select Model to Analyze", ["wagon-r", "vitz", "alto", "premio", "aqua", "axio"])

if st.button("Analyze Market"):
    with st.spinner(f'Searching for {car_model}...'):
        df = get_riyasewana_data(car_model)
        
    if not df.empty:
        # Success!
        st.success(f"Successfully analyzed {len(df)} vehicles.")
        
        # 1. Summary Metrics
        avg_price = df['Price'].mean()
        min_price = df['Price'].min()
        max_price = df['Price'].max()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Average Price", f"Rs. {avg_price/100000:,.2f} Lakhs")
        c2.metric("Lowest", f"Rs. {min_price/100000:,.2f} Lakhs")
        c3.metric("Highest", f"Rs. {max_price/100000:,.2f} Lakhs")
        
        # 2. The Chart
        st.subheader(f"Price Trend by Year")
        avg_by_year = df.groupby('Year')['Price'].mean().reset_index()
        
        fig = px.bar(avg_by_year, x='Year', y='Price', 
                     title=f"Average Price: {car_model}",
                     labels={'Price': 'Price (LKR)'})
        st.plotly_chart(fig)
        
        # 3. Data Table
        with st.expander("View Raw Data (Check this if stats look wrong)"):
            st.dataframe(df)
            
    else:
        # If still empty, show detailed help
        st.error("Still no data found.")
        st.write("Troubleshooting:")
        st.write("1. Does Riyasewana have results for this car? Check the site manually.")
        st.write("2. The site might have blocked the Streamlit Cloud IP.")