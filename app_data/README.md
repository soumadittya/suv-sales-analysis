# app_data

Files written by `suv_research.ipynb`; the web app reads them. Do not edit them by hand: re-run the notebook (Restart & Run All) to rebuild them.

- Source: CarDekho, 1,399 SUV variants, New Delhi prices collected on 20 Nov 2026.
- Prices are in rupees (₹). 1 lakh = ₹1,00,000.
- An empty value means unknown (CarDekho doesn't list it). It never means "no".
- The full column meanings for `variants_clean.csv` are in the notebook's data dictionary (Step 2.6).

## variants_clean.csv

One row per variant: prices, clean numbers, standardised categories and 0/1 features. Used by search, filters, compare and the price breakdown (Step 2).

Rows: 1,399

Columns: `company`, `model`, `variant`, `ex_showroom_price`, `registration_charges`, `insurance`, `others`, `optional_accessories`, `on_road_price`, `on_road_city`, `emi_per_month`, `price_date`, `feature_rows`, `few_features`, `cardekho_url`, `fuel_type`, `transmission`, `gearbox_type`, `gears`, `power_bhp`, `torque_nm`, `engine_cc`, `cylinders`, `length_mm`, `width_mm`, `height_mm`, `wheelbase_mm`, `ground_clearance_mm`, `boot_litres`, `seats`, `touchscreen_in`, `cluster_in`, `speakers`, `airbags`, `wheel_in`, `battery_kwh`, `range_km`, `cng_km_per_kg`, `top_speed_kmph`, `accel_0_100_s`, `bharat_ncap_stars`, `global_ncap_stars`, `mileage_kmpl`, `fuel_tank_l`, `sunroof`, `drive`, `electric_seats`, `upholstery`, `parking_sensors`, `boot_opening`, `hybrid_type`, `on_road_without_accessories`, plus 180 `has_…` columns (1 / 0 / empty)

## spec_sheet.csv

Every feature as CarDekho writes it, by section, with merged names. Used by the variant page's full spec sheet (Step 2).

Rows: 182,707

Columns: `company`, `model`, `variant`, `category`, `feature_name`, `feature_details`

## feature_prices.csv

What each feature adds to the price when comparing trims of the same model, with a likely range; shown_in_app marks clear ones (Step 4c).

Rows: 41

Columns: `column`, `label`, `pct_added`, `low_pct`, `high_pct`, `rupees_at_median_price`, `clear`, `shown_in_app`

## fair_prices.csv

Fair price, % difference, badge, missing features versus price peers, and better-value alternatives for each variant (Step 4d-4e).

Rows: 1,399

Columns: `company`, `model`, `variant`, `ex_showroom_price`, `missing_vs_price_peers`, `fair_price`, `difference_pct`, `badge`, `better_value_alternatives`

## similar_variants.csv

The 10 most similar variants for each variant (weighted Gower distance, price not used). Used for rivals and alternatives (Step 4e).

Rows: 13,990

Columns: `company`, `model`, `variant`, `rank`, `similar_company`, `similar_model`, `similar_variant`, `distance`, `same_model`

## trim_ladders.csv

Every variant in ladder order: price jump, features added/removed, step value, value ratio, sweet spot, style versions (Step 5).

Rows: 1,399

Columns: `ladder`, `company`, `model`, `variant`, `fuel_type`, `transmission`, `position`, `rungs`, `ex_showroom_price`, `price_jump`, `jump_pct`, `features_added`, `features_removed`, `changes`, `step_value`, `value_ratio`, `sweet_spot`, `also_good`, `sweet_spot_stability`, `looks_only`, `paint_only`, `style_of`, `base_feature_share`

## automatic_premium.csv

Manual/automatic pairs of the same trim, with the price gap split into gearbox and extra features (Step 5.7).

Rows: 333

Columns: `company`, `model`, `fuel_type`, `manual_variant`, `automatic_variant`, `gearbox_type`, `price_gap`, `extra_features_part`, `gearbox_part`

## finder_flags.csv

The 32 Finder options as True/False for every variant (unknown = False). The Finder filters this live (Step 6.1).

Rows: 1,399

Columns: `company`, `model`, `variant`, `ex_showroom_price`, `Automatic`, `Diesel`, `Electric`, `CNG`, `Strong hybrid`, `Any sunroof`, `Panoramic sunroof`, `ADAS (automatic emergency braking)`, `Adaptive cruise control`, `Cruise control`, `360° camera`, `7 or more seats`, `4x4 / AWD`, `150+ bhp`, `Ventilated seats`, `Electric driver seat`, `Leather or leatherette seats`, `Wireless phone charging`, `Wireless Android Auto / Apple CarPlay`, `6 or more airbags`, `Automatic climate control`, `Digital instrument cluster`, `10-inch or bigger touchscreen`, `LED headlamps`, `Alloy wheels`, `Rear disc brakes`, `Paddle shifters`, `Heads-up display`, `Powered or hands-free boot`, `400+ litre boot`, `Front parking sensors`, `5-star crash rating (Bharat or Global NCAP)`

## entry_prices.csv

Cheapest variant with each option, overall and per brand, plus the price where half of variants have it (Step 6.2).

Rows: 681

Columns: `option`, `scope`, `cheapest_variant`, `cheapest_price`, `price_at_50pct`

## bundles.csv

Association rules: if a car has A it usually has B, with support, confidence and lift (Step 6.4).

Rows: 32

Columns: `if_a_car_has`, `it_usually_has`, `support`, `confidence`, `lift`

## dominated_variants.csv

Variants beaten by a cheaper variant with the same fuel, gearbox and seats, and the variant that beats each (Step 6.5).

Rows: 110

Columns: `company`, `model`, `variant`, `price`, `beaten_by_company`, `beaten_by_model`, `beaten_by_variant`, `beaten_by_price`, `saving`, `cheaper_options`
