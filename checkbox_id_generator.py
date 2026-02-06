import calendar
import json

file_name = 'checkbox_id.json'
year_range_start = 2011
year_range_end = 2025
date_checkbox_id = {}
current_id = 0
for year in range(int(str(year_range_start)[2:]), int(str(year_range_end)[2:]) + 1):
    for month in calendar.month_name[1:]:
        date_checkbox_id[month[:3] + '-' + str(year)] =  'checkbox-' + str(current_id)
        current_id += 1 
    
with open(file_name, "w") as f:
    json.dump(date_checkbox_id, f, indent=4)
    print('File generated successfully. File name:', file_name)