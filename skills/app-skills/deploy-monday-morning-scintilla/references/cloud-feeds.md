# Scintilla Cloud Feed capability manifest

The inventory script checks these exact canonical names. For renamed feeds, confirm equivalent grain and columns from `information_schema.columns` before mapping them.

## Core feeds

| Capability | Canonical feeds | Required evidence |
|---|---|---|
| Sales performance | `store_sales`, `omni_sales`, `upc_sales` | item/UPC, store or channel, period/date, sales amount and units |
| Product hierarchy | `item_dim`, `prod_dim`, `omni_item_dim` | Walmart item/catalog item/UPC plus department/category/brand descriptions |
| Store geography | `store_dim` | store number, market/region, location and status |
| Calendar | `calendar_dim` | calendar date and Walmart week/year |
| Inventory availability | `store_invt`, `hourly_store_invt`, `dc_invt` | item, location, date/hour and on-hand/in-transit/on-order measures |
| Out-of-stock diagnosis | `oos_root_cause`, `invt_adj`, `bkrm_adj` | item/store, reason and quantity/value adjustments |

## Expansion feeds

| Capability | Canonical feeds |
|---|---|
| Forecasting | `dly_dmnd_fcst`, `store_demand_forecast`, `order_demand_forecast` |
| E-commerce | `ecom_invt`, `ecom_instock_pct`, `fc_ecom_instock_pct`, `digital_transactability`, `ecom_prod_cntnt_score`, `ecom_returns` |
| Store fulfillment | `store_fulfillment`, `hourly_store_fulfillment` |
| Supply chain and OTIF | `purchase_order`, `po_line`, `po_line_destination`, `po_dc_receiver`, `po_dc_receiver_line`, `omni_otif`, `dc_alignment`, `dc_dim` |
| Pricing and funding | `sku_mumd`, `coops` |
| Returns | `store_customer_return`, `store_returns` |
| Assortment/modular | `store_modular`, `modular_plan`, `modular_plan_upc`, `modular_trait`, `modular_upc_loc`, `item_trait`, `store_trait`, `traits` |
| Affinity and bundles | `item_affinity`, `kit_sales` |

## Recommended curated layer

Do not point every dashboard query directly at multi-billion-row feeds. Build customer-owned, documented tables or materialized views at these grains:

- `fact_daily_sales`: item × store × day × channel.
- `fact_weekly_plan`: item × store × Walmart week with plan and actual.
- `fact_inventory`: item × store/DC × day, plus availability measures.
- `fact_demand_forecast`: item × store × forecast date × vintage.
- `fact_ecommerce_metrics`: catalog item × node/store × day/week.
- `fact_cpg_metrics`: executive weekly aggregates.
- `dim_sku`, `dim_store`, `dim_date`, category/subcategory dimensions.
- Gap attribution, outlier, pricing and inventory-recommendation tables derived transparently from the preceding facts.

Audience, campaign, email and shopper-note tables used by the full original demo are not Scintilla Cloud Feeds. Integrate customer first-party/RMN data separately or disable those features.
