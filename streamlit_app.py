import logging
from urllib.parse import quote_plus

import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
import re

# --- THE SCRAPER FUNCTION ---
logging.basicConfig(level=logging.INFO)


@st.cache_data(ttl=3600)
def get_riyasewana_data(search_query):
    """Scrape Riyasewana for `search_query` and return a DataFrame.

    This function is side-effect free (no Streamlit calls) so it can be cached.
    """
    data = []
    scraper = cloudscraper.create_scraper()

    q = quote_plus(search_query)
    for page in range(1, 4):
        url = f"https://riyasewana.com/search/{q}?page={page}"
        try:
            response = scraper.get(url, timeout=10)
            if response.status_code == 403:
                logging.warning("Access Forbidden (403) for %s", url)
                continue
            if response.status_code != 200:
                logging.warning("Unexpected status %s for %s", response.status_code, url)
                continue

            soup = BeautifulSoup(response.content, "html.parser")
            items = soup.find_all("li", class_="item")

            for item in items:
                try:
                    title_tag = item.find("h2")
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)

                    price_div = item.find("div", class_="boxintxt")
                    b_tag = price_div.find("b") if price_div else None
                    if not b_tag:
                        continue
                    price_text = b_tag.get_text(strip=True)
                    if "Negotiable" in price_text or "Contact" in price_text:
                        continue

                    price_numbers = re.sub(r"[^0-9]", "", price_text)
                    if not price_numbers:
                        continue
                    price = int(price_numbers)

                    year = 0
                    year_match = re.search(r"\b(19|20)\d{2}\b", title)
                    if year_match:
                        year = int(year_match.group(0))
                    else:
                        link_tag = item.find("a")
                        link = link_tag["href"] if link_tag and link_tag.has_attr("href") else ""
                        url_year_match = re.search(r"/((?:19|20)\d{2})/", link)
                        if url_year_match:
                            year = int(url_year_match.group(1))

                    if year > 2000 and price > 100000:
                        data.append({"Model": title, "Year": year, "Price": price})
                except Exception:
                    logging.exception("Error parsing item on page %s", page)
                    continue

        except Exception:
            logging.exception("Connection error for page %s (query=%s)", page, search_query)
            continue

    return pd.DataFrame(data)

# --- THE FRONTEND ---
st.title("🇱🇰 Vehicle Price Analytics")

car_model = st.selectbox("Select Model", ["wagon-r", "vitz", "alto", "premio", "aqua"])

if st.button("Analyze Market"):
    # Clear cache if needed manually
    # get_riyasewana_data.clear() 
    
    with st.spinner(f'Searching for {car_model}...'):
        df = get_riyasewana_data(car_model)
        
    if not df.empty:
        st.success(f"Found {len(df)} listings.")
        
        avg_price = df['Price'].mean()
        
        c1, c2 = st.columns(2)
        c1.metric("Average Price", f"Rs. {avg_price/100000:,.2f} Lakhs")
        c2.metric("Min Price", f"Rs. {df['Price'].min()/100000:,.2f} Lakhs")
        
        avg_by_year = df.groupby('Year')['Price'].mean().reset_index()
        fig = px.bar(avg_by_year, x='Year', y='Price', title="Price vs Year")
        st.plotly_chart(fig)
        
        with st.expander("Show Data"):
            st.dataframe(df)
    else:
        st.error("No data found. If you see 'Access Forbidden' above, run this LOCALLY.")
        st.info("Why is this happening? Riyasewana blocks Cloud Servers (AWS/Google). Run this script on your own laptop (Localhost) and it will work perfectly.")