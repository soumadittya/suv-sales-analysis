from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import json
import pandas as pd
import os

input_data_path = './input_cardekho.csv'
output_data_directory = './output_cardekho'
car_list = (pd.read_csv(input_data_path)).values.tolist()
root_url = 'https://www.cardekho.com/overview/' # '/' at the end is mandatory

if os.path.isdir(output_data_directory) == False:
    print('CREATING OUTPUT DIRECTORY')
    os.mkdir(output_data_directory)
    print('OUTPUT DIRECTORY CREATED')

driver = webdriver.Chrome()


for car in car_list:
    feature_list = []
    price_list = []
    full_car_name = car[0] + ' ' + car[1] + ' ' + car[2]
    print('CURRENT CAR:', full_car_name)
    url = root_url + car[0].replace(' ', '_') + '_' + car[1].replace(' ', '_') + '/' + car[0].replace(' ', '_') + '_' + car[1].replace(' ', '_') + '_' + car[2].replace(' ', '_') + '.htm'
    print('CURRENT URL:', url)
    driver.get(url)
    time.sleep(4)
    # extracting features
    print('EXTRACTING FEATURES FOR', full_car_name)
    for i in range(1, 10):
        current_table = driver.find_element(By.XPATH, '//*[@id="scrollDiv"]/table' + '[' + str(i) + ']')
        for row in current_table.find_elements(By.TAG_NAME, 'tr'):
            cells = row.find_elements(By.TAG_NAME, 'td')
            if len(cells) == 2:
                if cells[1].text == '':
                    icon = cells[1].find_element(By.TAG_NAME, 'i')
                    if icon.get_attribute('class') == "icon-deletearrow":
                        feature_details = 'NO'
                    elif icon.get_attribute('class') == "icon-check":
                        feature_details = 'YES'
                else:
                    feature_details = cells[1].text
                feature_list.append([car[0], car[1], car[2], cells[0].text, feature_details])
   
    # extracting ex-showroom price
    print('EXTRACTING EX-SHOWROOM PRICE FOR', full_car_name)
    ex_showroom_price = driver.find_element(By.XPATH, "//*[@id='OnRoadPrice']/table/tbody/tr[1]/td[2]").text
    price_list.append(['Ex-Showroom Price', ex_showroom_price]) 

    # extracting on-road price
    print('EXTRACTING ON-ROAD PRICE FOR', full_car_name)
    for row in driver.find_elements(By.XPATH, "//*[@id='rf01']/div[1]/div/main/div/div[2]/div/div[2]/div/div[1]/div/div/table/tbody/tr"):
        cells = row.find_elements(By.TAG_NAME, 'td')
        price_list.append([cells[0].text, cells[1].text])
    
    try:
        print('CREATING DATAFRAME FOR', full_car_name)
        df_feature_list = pd.DataFrame(feature_list, columns=["company", "model", "variant", 'feature_name', 'feature_details'])
        df_price_list = pd.DataFrame(price_list, columns = ['Ex-Showroom/ On-Road', 'Price'])
        print('DATAFRAME CREATED SUCCESSFULLY FOR', full_car_name)
    except Exception as e:
        print('CANNOT CREATE DATAFRAME FOR', full_car_name, e)
    try:
        print('CREATING CSV FILE FOR', full_car_name)
        df_feature_list.to_csv(os.path.join(output_data_directory, full_car_name + ' features.csv'), index = False)
        df_price_list.to_csv(os.path.join(output_data_directory, full_car_name + ' price.csv'), index = False)
        print('CSV FILE CREATED SUCCESSFULLY FOR', full_car_name)
    except Exception as e:
        print('CANNOT CREATE CSV FILE FOR', full_car_name, e)

# df = pd.Dataframe(complete_data)
# df.to_csv('demo.csv')
            








