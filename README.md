This project presents a complete analysis of the Indian SUV market, focusing on the top 20 most-sold SUVs between 2020 and 2025. It studies each vehicle’s sales performance alongside its key specifications to understand which characteristics customers value the most—such as size, engine displacement, pricing, and feature set. By combining sales insights with technical attributes, the project highlights which SUVs dominate the market, which price segments attract buyers, and what patterns emerge across the highest-selling models, offering a clear, data-driven picture of India’s evolving SUV preferences.


From a technical standpoint, the project is built entirely from scratch, including the creation of a fully custom dataset. Sales figures were scraped from Auto Punditz, and detailed car specifications were scraped from CarDekho.com, both using Selenium to reliably extract data from dynamically loaded webpages. The dataset was then cleaned, merged, and processed using Python libraries such as Pandas for data manipulation, NumPy for numerical operations, Requests and BeautifulSoup for additional scraping support, and Matplotlib/Seaborn for generating insightful visualizations. These visualizations help uncover relationships between price, dimensions, engine size, and sales, making trends easier to interpret and compare.


This analysis is valuable for anyone interested in the automotive landscape—buyers looking for clarity, automobile enthusiasts exploring market trends, industry analysts studying consumer behaviour, and manufacturers seeking insights into customer preferences. It also serves as a learning resource for data analysts and data science practitioners, as it demonstrates how to build a complete end-to-end workflow: data scraping, dataset creation, cleaning, modeling, and visualization. With the entire codebase and dataset made publicly available, the project empowers others to extend the analysis, validate findings, or explore new dimensions of the Indian SUV market on their own.

🔧 Getting Started: How to Run, Explore, and Modify the Code

Before running the project, it’s important to understand how the repository is organized and what each script or notebook is responsible for. The workflow follows a very logical sequence—from scraping raw data, to cleaning and merging it, to analyzing and visualizing it. Below is a clear breakdown of every major component.

📁 Key Folders
    • scraped_auto_punditz_sales_data/
      Stores all raw sales data scraped from AutoPunditz across the selected years.
    • scraped_cardekho_top_20_models_features/
      Contains feature details and price information scraped from CarDekho for the top 20 SUVs.



🧩 Scripts & Notebooks Explained (in execution order)

1️⃣ checkbox_id_generator.py

This script dynamically generates the file checkbox_id.json, which contains the checkbox IDs corresponding to year filters on the AutoPunditz website.
This JSON file is required by auto_punditz_sales_data_scraper.py to automatically select the years when scraping sales data.

2️⃣ auto_punditz_sales_data_scraper.py

This script performs the actual scraping of monthly and yearly SUV sales data from AutoPunditz.com.
It uses Selenium to:
    • Load the website
    • Select years based on the checkbox_id.json file
    • Extract sales numbers
    • Save the results inside scraped_auto_punditz_sales_data/.

3️⃣ filter_top_20_highest_selling_SUVs.ipynb

After scraping, this notebook processes the raw sales data to:
    • Aggregate sales
    • Rank all SUV models
    • Identify the top 20 highest-selling SUVs across 2020–2025
    • Output a clean CSV containing only these models

This filtered output becomes the input for the next scraping step.

4️⃣ cardekho_features_data_scraper.py

Using the top 20 SUV list produced earlier, this script goes to CarDekho.com and automatically extracts:
    • Technical specifications
    • Safety features
    • Convenience & comfort features
    • Prices (start price, average price, max price)

All scraped details are stored inside scraped_cardekho_top_20_models_features/.

5️⃣ filter_top_20_highest_selling_SUVs.ipynb (Data Preparation Stage)

This notebook now combines:
    • Sales data
    • Technical features
    • Safety features
    • Essentials/features
    • Price information

It produces four new CSV files (specifications, safety, essentials, others).
These CSVs are individually analyzed in the corresponding notebooks below.

📊 Analysis Notebooks

📘 specifications.ipynb

Analyzes core vehicle specifications such as:
    • Length
    • Engine displacement
    • Power output
    • Torque
    • Wheelbase
    • Mileage

Includes comparison charts and pattern visualizations to understand what specifications top-selling SUVs share.

📘 safety.ipynb

Focuses on safety-related data such as:
    • Number of airbags
    • ABS, EBD, ESC, Hill Assist
    • 5-star / 4-star safety ratings (if available)
    • Safety equipment distribution across models

This notebook helps identify whether safety contributes meaningfully to higher sales.

📘 essentials.ipynb

Covers customer-essential features like:
    • Infotainment
    • Sunroof (single/double)
    • Cruise control
    • Rear camera & sensors
    • Connected car features
    • Automatic climate control

It visualizes which essential features appear most frequently among top sellers.

📘 others.ipynb

Includes analysis of all remaining features which people might like to have but are not essential such as sunroof, etc.
