from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import time
import json
import os

date_start = 'Dec-20'
date_end = 'May-21'
url = "https://demo.vizta.in/publicdashboard?workbookid=67c81d1ab4575679de094f9a&sheetid=67c81d1a191569bcdea0bfda&filterbar=true"
file_path_checkbox_id = './checkbox_id.json'
column_names = ['date', 'company', 'model', 'monthly_sales', 'total_sales']
output_directory = './output_data'

driver = webdriver.Chrome()
driver.get(url)
time.sleep(4)

element_dropdown = driver.find_element(By.XPATH, "//*[@id='root']/main/main/aside/div/section[1]/main[2]/div/button/button/span[2]")
element_dropdown.click()
print('Dropdown element expanded')
time.sleep(4)

element_checkbox_all = driver.find_element(By.ID, "checkbox-all")
if element_checkbox_all.is_selected() == True:
    print('checkbox-all initially checked')
    element_checkbox_all.click()
    print('checkbox-all turned to unchecked')
else:
    print('checkbox-all initially unchecked')
    element_checkbox_all.click()
    print('checkbox-all turned to checked')
    time.sleep(2)
    element_checkbox_all.click()
    print('checkbox-all turned to unchecked')

time.sleep(2)

# reading the checkbox_id details from the json file in which the months and the corresponding checkbox-ids are listed
with open(file_path_checkbox_id, 'r') as file:
    checkbox_id = json.load(file)

checkbox_id_keys = [key for key in checkbox_id.keys()]
start_index = checkbox_id_keys.index(date_start)
end_index = checkbox_id_keys.index(date_end)

#print('CHECKBOX_ID_KEYS', checkbox_id_keys)
# print('START ', start_index)
# print('END_INDEX', end_index)


for index in range(start_index, end_index + 1):
    print('CURRENT CHECKBOX ID:', checkbox_id[checkbox_id_keys[index]])
    element_checkbox_current = driver.find_element(By.ID, checkbox_id[checkbox_id_keys[index]])
    element_checkbox_current.click()
    time.sleep(4)
    table = driver.find_element(By.TAG_NAME, "table")
    table_body = driver.find_element(By.TAG_NAME, "tbody")
    rows = table_body.find_elements(By.TAG_NAME, "tr")
    complete_data = []
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) == 4:
            cell_company = cells[0].text
            print('CURRENT NAME:', cell_company)
            current_row = [cell.text for cell in cells]
        elif len(cells) == 3:
             current_row = [cell.text for cell in cells]
             current_row.insert(0, cell_company)
        current_row.insert(0, checkbox_id_keys[index])
        complete_data.append(current_row)
    element_checkbox_current.click()
    # creating dataframe
    print('Creating dataframe:', checkbox_id_keys[index])
    try:
        df = pd.DataFrame(data = complete_data, columns = column_names)
        print('Dataframe created', checkbox_id_keys[index])
    except Exception as e:
        print('Cannot create dataframe', e)
    # creating csv file
    try:
        if os.path.isdir(output_directory) == False:
            os.mkdir(output_directory)
            print('Output directory created')
        df.to_csv(output_directory + '/' + checkbox_id_keys[index] + '.csv', index = False)
        print('CSV file created successfully: ', output_directory + checkbox_id_keys[index] + '.csv')
    except Exception as e:
        print('Cannot save csv file', e)

print('TASK COMPLETED')
driver.quit()