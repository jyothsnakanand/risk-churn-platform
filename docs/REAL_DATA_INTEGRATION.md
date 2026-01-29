# Real E-Commerce Dataset Integration

The platform now supports integration with a real e-commerce dataset containing actual customer behavior data from a cosmetics shop.

## Dataset Overview

**Source**: RetailRocket E-Commerce Dataset
**Size**: ~987MB (uncompressed)
**Records**: 2.7M user events, 1.7K categories, 20M+ item properties
**Period**: Approximately 4.5 months of activity

### Files

1. **events.csv** (90MB) - User interaction events
   - Columns: `timestamp`, `visitorid`, `event`, `itemid`, `transactionid`
   - Event types: `view`, `addtocart`, `transaction`
   - 2,756,102 events

2. **category_tree.csv** (14KB) - Product category hierarchy
   - Columns: `categoryid`, `parentid`
   - 1,670 categories

3. **item_properties_part1.csv** (462MB) - Product properties (part 1)
   - Columns: `timestamp`, `itemid`, `property`, `value`
   - 11M records

4. **item_properties_part2.csv** (390MB) - Product properties (part 2)
   - Columns: `timestamp`, `itemid`, `property`, `value`
   - 9.3M records

## Quick Start

### 1. Extract the Dataset

The dataset is included in the repository as `ecommerce-dataset.zip`:

```bash
# Extract to data directory
unzip ecommerce-dataset.zip -d data/ecommerce

# Verify extraction
ls -lh data/ecommerce/
```

### 2. Preprocess the Data

Convert raw events into customer-level features:

```bash
# Process a sample (100K events, ~1-2 minutes)
python scripts/preprocess_real_data.py --sample 100000

# Or process the full dataset (~10-15 minutes)
python scripts/preprocess_real_data.py --full
```

This creates `data/ecommerce/processed_customers.csv` with customer features.

### 3. Use the Real Data

#### Option A: Load Real Customers in Python

```python
from risk_churn_platform.data_generator import get_sample_customer, EcommerceDataLoader

# Get a random real customer
customer = get_sample_customer()
print(f"Customer {customer['customer_id']}")
print(f"  Orders: {customer['total_orders']}")
print(f"  Risk: {customer['true_risk_level']}")

# Load full dataset
loader = EcommerceDataLoader()
events = loader.load_events(sample_size=50000)
customers = loader.aggregate_customer_features(events)
```

#### Option B: Train Models on Real Data

```bash
# Train your models using the processed customer data
python scripts/train_on_real_data.py --input data/ecommerce/processed_customers.csv
```

## Feature Engineering

The preprocessing pipeline transforms raw events into the platform's feature schema:

### Available Features (from real data)

| Feature | Source | Description |
|---------|--------|-------------|
| `customer_age_days` | ✅ Calculated | Days since first event |
| `account_age_days` | ✅ Calculated | Same as customer_age_days |
| `total_orders` | ✅ Calculated | Count of unique transactions |
| `total_revenue` | ⚠️ Estimated | Orders × $100 (no price data) |
| `avg_order_value` | ⚠️ Estimated | $100 per order |
| `days_since_last_order` | ✅ Calculated | Days since last transaction |
| `order_frequency` | ✅ Calculated | Orders per month |
| `website_visits_30d` | ✅ Calculated | Session count (30min gaps) |
| `cart_abandonment_rate` | ✅ Calculated | (addtocart - transactions) / addtocart |
| `product_views_30d` | ✅ Calculated | Count of view events |
| `email_open_rate` | ❌ Default (0.5) | Not available in dataset |
| `support_tickets_*` | ❌ Default (0) | Not available in dataset |
| `returns_count` | ❌ Default (0) | Not available in dataset |
| `favorite_category` | 🔄 Future | Needs item properties join |
| `discount_usage_rate` | ❌ Default (0.3) | Not available in dataset |
| `premium_product_rate` | ❌ Default (0.2) | Not available in dataset |
| `payment_method` | ❌ Default | Not available in dataset |
| `shipping_method` | ❌ Default | Not available in dataset |
| `failed_payment_count` | ❌ Default (0) | Not available in dataset |

### Additional Real Data Features

The processed dataset includes extra fields from real data:

- `data_source`: "real" (vs "synthetic")
- `total_events`: Total interaction count
- `view_count`: Number of product views
- `addtocart_count`: Number of add-to-cart actions
- `transaction_count`: Number of completed purchases
- `unique_items_viewed`: Distinct products viewed

## Risk Level Assignment

Customers are assigned risk levels based on actual behavior:

- **Low Risk**:
  - Last order < 30 days ago
  - 3+ total orders

- **High Risk**:
  - No orders OR last order > 90 days ago

- **Medium Risk**:
  - Everything else

## Dataset Statistics

After preprocessing 100K events:

```
Total customers: ~8,000-12,000
Risk distribution:
  - Low: ~10-15%
  - Medium: ~25-30%
  - High: ~60-70%

Avg orders per customer: ~1.5
Customers with 0 orders: ~65-70%
Customers with 3+ orders: ~10-15%
```

## Use Cases

### 1. Model Training

Train your churn prediction model on real customer behavior:

```python
import pandas as pd
from sklearn.model_selection import train_test_split

# Load processed customers
customers = pd.read_csv("data/ecommerce/processed_customers.csv")

# Create labels (1 = churned, 0 = active)
customers["churned"] = (customers["true_risk_level"] == "high").astype(int)

# Features for training
feature_cols = [
    "customer_age_days",
    "total_orders",
    "days_since_last_order",
    "order_frequency",
    "cart_abandonment_rate",
    "product_views_30d",
    # ... etc
]

X = customers[feature_cols]
y = customers["churned"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Train your model
# model.fit(X_train, y_train)
```

### 2. Realistic Testing

Test your platform with real customer profiles:

```python
from risk_churn_platform.data_generator import get_sample_customer
import requests

# Get real customer
customer = get_sample_customer()

# Make prediction
response = requests.post(
    "http://localhost:8000/predict",
    json=customer
)
print(response.json())
```

### 3. Hybrid Data Generation

Combine synthetic and real data:

```python
from risk_churn_platform.data_generator import (
    SyntheticDataGenerator,
    EcommerceDataLoader
)
import pandas as pd

# Generate synthetic customers
synthetic_gen = SyntheticDataGenerator()
synthetic = synthetic_gen.generate_batch(5000)

# Load real customers
real_df = pd.read_csv("data/ecommerce/processed_customers.csv")
real = real_df.sample(1000).to_dict("records")

# Combine
all_customers = synthetic + real
```

## Limitations

### Missing Features

The following features are not available in the raw dataset and use default values:

- Email engagement metrics
- Customer support interactions
- Returns and refunds
- Payment failures
- Shipping preferences
- Exact product prices/revenue

### Workarounds

1. **Revenue**: Estimated at $100 per order (adjustable)
2. **Email metrics**: Use typical industry averages (0.3-0.5)
3. **Support tickets**: Assume zero unless customer has issues
4. **Categories**: Can be enhanced by joining item properties

### Future Enhancements

- Join with item properties to get actual favorite categories
- Use item properties to estimate premium vs budget products
- Infer support issues from cart abandonment patterns
- Add time-based features (seasonality, day of week)

## Performance Considerations

### Processing Time

- **Sample (100K events)**: 1-2 minutes, ~10K customers
- **Full dataset (2.7M events)**: 10-15 minutes, ~200K+ customers

### Memory Usage

- **Sample**: ~500MB RAM
- **Full**: ~2-3GB RAM

### Optimization Tips

```python
# Process in chunks for large datasets
loader = EcommerceDataLoader()

chunk_size = 100000
for i in range(0, total_events, chunk_size):
    events = loader.load_events(sample_size=chunk_size)
    # Process chunk
```

## Data Quality

### Event Distribution

```
Event Type        Count          %
view             2,664,312     96.7%
addtocart           69,332      2.5%
transaction         22,458      0.8%
```

### Customer Segmentation

Based on order count:
- 0 orders (browsers): ~65-70%
- 1-2 orders (occasional): ~15-20%
- 3-5 orders (regular): ~8-12%
- 6+ orders (loyal): ~3-5%

## Troubleshooting

### Issue: "Data directory not found"

```bash
# Make sure dataset is extracted
ls data/ecommerce/
# Should show: category_tree.csv, events.csv, item_properties_part1.csv, item_properties_part2.csv
```

### Issue: "Memory error during processing"

```bash
# Use smaller sample
python scripts/preprocess_real_data.py --sample 50000

# Or increase system memory
```

### Issue: "Processed file not found"

```bash
# Run preprocessing first
python scripts/preprocess_real_data.py
```

## Examples

See `examples/real_data_examples.py` for complete usage examples.

## References

- Dataset Source: [Kaggle - RetailRocket E-Commerce Dataset](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset)
- Original Use Case: Recommender systems
- Our Use Case: Churn prediction and risk scoring
