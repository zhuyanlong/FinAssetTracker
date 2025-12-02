CREATE TABLE asset_data_snapshots (
    -- 元数据字段
    id SERIAL PRIMARY KEY,
    snapshot_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- 黄金和数字资产 (数量)
    gold_g NUMERIC(18, 2) NOT NULL,    -- 黄金克数，高精度
    gold_oz NUMERIC(18, 2) NOT NULL,   -- 黄金盎司数，高精度
    btc NUMERIC(18, 8) NOT NULL,       -- 比特币数量，高精度

    -- 人民币资产 (货币)
    retirement_funds_cny NUMERIC(15, 2) NOT NULL,
    savings_cny NUMERIC(15, 2) NOT NULL,
    funds_cny NUMERIC(15, 2) NOT NULL,
    housing_fund_cny NUMERIC(15, 2) NOT NULL,

    -- 新加坡元资产 (货币)
    funds_sgd NUMERIC(15, 2) NOT NULL,
    savings_sgd NUMERIC(15, 2) NOT NULL,

    -- 欧元资产 (货币)
    funds_eur NUMERIC(15, 2) NOT NULL,
    savings_eur NUMERIC(15, 2) NOT NULL,

    -- 港元资产 (货币)
    funds_hkd NUMERIC(15, 2) NOT NULL,
    savings_hkd NUMERIC(15, 2) NOT NULL,
    
    -- 其他货币和股票 (货币)
    deposit_gbp NUMERIC(15, 2) NOT NULL,
    savings_usd NUMERIC(15, 2) NOT NULL,
    stock_usd NUMERIC(15, 2) NOT NULL,
    btc_stock_usd NUMERIC(15, 2) NOT NULL
);
