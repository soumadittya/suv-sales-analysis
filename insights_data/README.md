# insights_data

Files written by `notebooks/suv_insights.ipynb`; the web app reads them. Do not edit them by hand: re-run the notebook (Restart & Run All) to rebuild them.

- Source: CarDekho data cleaned by `notebooks/suv_research.ipynb` (`app_data/`), with its fair prices.
- Prices are ex-showroom, in rupees. 1 lakh = ₹1,00,000; 1 crore = ₹1,00,00,000.
- In the answers files, rows with `item_type` = note (rank 0) sum up an answer or explain a short or empty list.
- In `segments.csv`, an empty `to_lakh` means the segment has no upper price limit.
- Averages and standard deviations are of ex-showroom prices, with each variant counted once. The standard deviation is the population one (every listed variant is included), so a model with one variant has `std_price` 0.

## segments.csv

Rows: 7

Columns: `segment_id`, `segment`, `from_lakh`, `to_lakh`, `variants`, `models`, `brands`, `from_price`, `to_price`, `avg_price`, `std_price`, `cheapest_variant`

## segment_models.csv

Rows: 213

Columns: `segment_id`, `segment`, `company`, `model`, `model_name`, `variants`, `from_price`, `to_price`

## brands.csv

Rows: 25

Columns: `brand`, `variants`, `models`, `brands`, `from_price`, `to_price`, `cheapest_variant`, `segments`

## models.csv

Rows: 136

Columns: `company`, `model`, `model_name`, `variants`, `from_price`, `to_price`, `avg_price`, `std_price`

## variants.csv

Rows: 1,399

Columns: `segment_id`, `segment`, `company`, `model`, `variant`, `name`, `model_name`, `ex_showroom_price`, `on_road_price`, `fuel`, `fuel_type`, `gearbox`, `gearbox_source`, `is_automatic`, `drive_type`, `seats`, `engine_cc`, `engine_size`, `battery_kwh`, `power_bhp`, `torque_nm`, `airbags`, `adas`, `crash_stars`, `crash_test`, `fair_price`, `difference_pct`, `badge`, `feature_score`, `features_present`, `basics_missing_count`, `basics_missing`, `feature_list`, `modern_score`, `modern_list`, `safety_score`, `safety_equipment`, `crash_points`, `safety_list`, `cardekho_url`, `price_date`

## questions.csv

Rows: 60

Columns: `tab`, `question_id`, `order`, `category`, `category_order`, `number`, `question`, `asked_as`, `kind`, `list_size`

## answers_segments.csv

Rows: 1,014

Columns: `tab`, `group`, `question_id`, `rank`, `item_type`, `name`, `company`, `model`, `variant`, `price`, `metric`, `highlight`, `reason`

## answers_brands.csv

Rows: 2,388

Columns: `tab`, `group`, `question_id`, `rank`, `item_type`, `name`, `company`, `model`, `variant`, `price`, `metric`, `highlight`, `reason`

## answers_overall.csv

Rows: 62

Columns: `tab`, `group`, `question_id`, `rank`, `item_type`, `name`, `company`, `model`, `variant`, `price`, `metric`, `highlight`, `reason`

## feature_lists.csv

Rows: 64

Columns: `list`, `feature`, `points`
