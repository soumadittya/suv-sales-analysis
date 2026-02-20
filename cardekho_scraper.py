from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import json
import pandas as pd
import os

input_data_path = './top_20_models.csv'
output_data_directory = './output_cardekho_top_20_models'
car_list = (pd.read_csv(input_data_path)).values.tolist()
root_url_model = 'https://www.cardekho.com/'
root_url_variant = 'https://www.cardekho.com/overview/' # '/' at the end is mandatory

if os.path.isdir(output_data_directory) == False:
    print('CREATING OUTPUT DIRECTORY')
    os.mkdir(output_data_directory)
    print('OUTPUT DIRECTORY CREATED')

driver = webdriver.Chrome()

failure_list = []
for model in car_list:
    # extracting variants
    print('CURRENT MODEL NAME:', model[0] + ' ' + model[1])
    model_url = root_url_model + model[0].replace(' ', '_') + '/' + model[1].replace(' ', '_')
    print('CURRENT MODEL URL:', model_url)
    try:
        driver.get(model_url)
    except:
        failure_list.append(full_car_name + ': ' + 'variant page not accessed')

    time.sleep(4)
    try:
        button_view_all_variants = driver.find_elements(By.XPATH, "//*[contains(@class,'BottomLinkViewAll expand')]")
        if button_view_all_variants:
            button_view_all_variants[0].click()
            print('VIEW ALL VARIANTS BUTTON CLICKED')
        else:
            print('VIEW ALL VARIANTS BUTTON DOES NOT EXIST')
    except:
        failure_list.append(full_car_name + ': ' + 'button view all variants failed')
    # //*[@id="rf01"]/div[1]/div/main/div[6]/div[1]/section[2]/div/table/tbody/tr[1]/td[1]/a
                                                # //*[@id="rf01"]/div[1]/div/main/div[4]/div[1]/section[2]/div/table/tbody/tr[2]/td[1]/a
    
    try:
        variant_table = (driver.find_element(By.XPATH, "//*[contains(@class,'allvariant contentHold')]")).find_element(By.TAG_NAME, "tbody")
        variant_list = []
        # print('LENGTH OF TABLE:', len(variant_table.find_elements(By.TAG_NAME, 'tr')))
        # variant_rows = variant_table.find_elements(By.TAG_NAME, 'tr')
        for variant_row in variant_table.find_elements(By.TAG_NAME, 'tr'):
            variant_cell = variant_row.find_elements(By.TAG_NAME, 'td')[0]
            variant_name = variant_cell.find_element(By.TAG_NAME, 'a').text
            variant_list.append(variant_name)
        print(variant_list)
    except:
        failure_list.append(full_car_name + ': ' + 'extractedvariant list not ')

    # extracting features
    try:
        print('EXTRACTING FEATURES FOR', )
        for variant in variant_list:
            full_car_name = model[0] + '-' + model[1] + '-' + variant
            print('CURRENT CAR:', full_car_name)
            variant_url = root_url_variant + model[0].replace(' ', '_') + '_' + model[1].replace(' ', '_') + '/' + model[0].replace(' ', '_') + '_' + variant.replace(' ', '_') + '.htm'
            print("CURRENT VARIANT URL:", variant_url)
            driver.get(variant_url)
            time.sleep(4)
            feature_list = []
            for i in range(1, 10):
                current_feature_table = driver.find_element(By.XPATH, '//*[@id="scrollDiv"]/table' + '[' + str(i) + ']')
                for row in current_feature_table.find_elements(By.TAG_NAME, 'tr'):
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
                        feature_list.append([model[0], model[1], variant, cells[0].text, feature_details])
            
            # extracting ex-showroom price
            price_list = []
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
    except:
        failure_list.append(full_car_name + ': ' + 'details not extracted')

print('FAILURE REPORT', failure_list)
print('TASK COMPLETED')

# df = pd.Dataframe(complete_data)
# df.to_csv('demo.csv')
            








