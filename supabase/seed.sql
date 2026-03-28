INSERT INTO inventory (sku, quantity, warehouse) VALUES
    ('SKU-A1B2C3', 150, 'us-east-1'),
    ('SKU-D4E5F6',  75, 'us-west-2'),
    ('SKU-G7H8I9', 200, 'eu-west-1'),
    ('SKU-J0K1L2',   0, 'us-east-1'),
    ('SKU-M3N4O5', 500, 'ap-southeast-1')
ON CONFLICT (sku) DO NOTHING;
