-- OPTIONAL DEMONSTRATION DATA ONLY. NOT REAL FACILITIES OR REAL TRANSACTIONS.
-- Run on a test database, never on a live operational database.
INSERT INTO facilities(code,name,type,address,district,phone,monthly_fee,collection_day)
VALUES
('DEMO-AGS-001','DEMO - Central Health Clinic','Clinic','Demo address, Kampala','Kampala','0000000000',40000,'Monday'),
('DEMO-AGS-002','DEMO - Community Laboratory','Laboratory','Demo address, Wakiso','Wakiso','0000000000',80000,'Wednesday'),
('DEMO-AGS-003','DEMO - District Pharmacy','Pharmacy','Demo address, Mukono','Mukono','0000000000',60000,'Friday')
ON CONFLICT(code) DO NOTHING;
