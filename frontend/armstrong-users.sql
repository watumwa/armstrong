BEGIN;

INSERT INTO public.users (name, email, role, password_hash)
VALUES
('Test Administrator', 'admin@armstrong.test', 'Administrator', '$2b$12$eNlCDpdwA6tRIpT7xx.fF.y5u3FovjvgjnY2RglwIwVpSHP9di.XC'),
('Test Supervisor', 'supervisor@armstrong.test', 'Supervisor', '$2b$12$vEPRNsJN1Fw7R5q1Q2/g3eJ9GDxVWg6zWD1G1NvQ.61gunlVdkLZq'),
('Test Waste Collector', 'collector@armstrong.test', 'Waste Collector', '$2b$12$ZXa9PQ2.xmY7f9olNVIFZu99es7SDWbUiPnvRM4vx3TPnV.kaL1ay'),
('Test Revenue Officer', 'revenue@armstrong.test', 'Revenue Officer', '$2b$12$WhXWbdiCFSDgTl/g2Z3fye6V//XspruNHDoldyylcMAJTnmbDAXeu')
ON CONFLICT (email) DO NOTHING;

COMMIT;

SELECT name, email, role, active
FROM public.users
WHERE email IN (
  'admin@armstrong.test',
  'supervisor@armstrong.test',
  'collector@armstrong.test',
  'revenue@armstrong.test'
)
ORDER BY role;
