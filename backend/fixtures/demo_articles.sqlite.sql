CREATE TABLE articles (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    source_name TEXT NOT NULL,
    published_at TEXT NOT NULL,
    language TEXT NOT NULL,
    topics_json TEXT NOT NULL,
    decision TEXT NOT NULL,
    confidence REAL NOT NULL,
    reason TEXT NOT NULL,
    suggested_tags_json TEXT NOT NULL
);

INSERT INTO articles VALUES (
    'sql_001',
    '冷库短时断电触发备用电源',
    '食品冷库在凌晨发生九分钟市电中断。备用发电机在二十秒内启动，库内最高温度上升零点三摄氏度。值班人员确认库存未超过温控上限。',
    '示例设施事件库',
    '2026-08-13',
    'zh-CN',
    '["冷链", "供电"]',
    'include',
    0.96,
    '材料同时包含供电事件、控制措施和量化影响。',
    '["冷链", "供电保障"]'
);

INSERT INTO articles VALUES (
    'sql_002',
    '商场会员积分促销开始',
    '商场本周推出会员积分翻倍活动，餐饮和电影消费均可参与。活动细则已在服务台公布。',
    '示例商业资讯库',
    '2026-08-14',
    'zh-CN',
    '["商业活动"]',
    'exclude',
    0.99,
    '促销信息不属于目标事件。',
    '["商业活动"]'
);

INSERT INTO articles VALUES (
    'sql_003',
    '山区列车受天气影响待确认',
    '气象站预报山区可能出现短时强降雨。铁路部门正在评估是否调整晚间列车速度，目前尚未发布运行调整命令。',
    '示例交通事件库',
    '2026-08-15',
    'zh-CN',
    '["铁路", "天气"]',
    'needs_followup',
    0.68,
    '存在潜在影响，但运行措施尚未确认。',
    '["铁路", "天气影响"]'
);
