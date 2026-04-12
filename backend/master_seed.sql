START TRANSACTION;

DELETE FROM notifications;
DELETE FROM documents;
DELETE FROM maintenance_requests;
DELETE FROM payments;
DELETE FROM leases;
DELETE FROM properties;
DELETE FROM users;
DELETE FROM tenant_orgs;

INSERT INTO tenant_orgs (id, name) VALUES
  ('t1', 'QuantumQuest Demo');

INSERT INTO users (
  id, tenant_id, email, hashed_password, role, first_name, last_name, phone, avatar_initials
) VALUES
  ('u1', 't1', 'alex.thompson@example.com', '$2b$12$fwD.k3yF97Yv/thq8VxfVe5ESO4o8l28tEebRP9SldJhl5cqR.nEW', 'owner', 'Alex', 'Thompson', '+1 (555) 012-3456', 'AT'),
  ('u2', 't1', 'sarah.chen@example.com', '$2b$12$fwD.k3yF97Yv/thq8VxfVe5ESO4o8l28tEebRP9SldJhl5cqR.nEW', 'manager', 'Sarah', 'Chen', '+1 (555) 234-5678', 'SC'),
  ('u3', 't1', 'marcus.johnson@example.com', '$2b$12$fwD.k3yF97Yv/thq8VxfVe5ESO4o8l28tEebRP9SldJhl5cqR.nEW', 'tenant', 'Marcus', 'Johnson', '+1 (555) 345-6789', 'MJ'),
  ('u4', 't1', 'olivia.reed@example.com', '$2b$12$fwD.k3yF97Yv/thq8VxfVe5ESO4o8l28tEebRP9SldJhl5cqR.nEW', 'tenant', 'Olivia', 'Reed', '+1 (555) 456-7890', 'OR');

INSERT INTO properties (
  id, tenant_id, owner_id, name, address, city, state, zip, property_type, bedrooms, bathrooms, sqft, status, rent_amount, image_color
) VALUES
  ('p1', 't1', 'u1', '2454 Ronald McNair Way', '2454 Ronald McNair Way', 'Sacramento', 'CA', '95834', 'residential', 4, 3, 0, 'occupied', 2245, '#6366f1'),
  ('p2', 't1', 'u1', '2580 N McArthur Ave', '2580 N McArthur Ave', 'Fresno', 'CA', '93727', 'residential', 3, 3, 0, 'vacant', 2395, '#06b6d4'),
  ('p3', 't1', 'u1', '4053 Penny Terrace', '4053 Penny Terrace', 'Fremont', 'CA', '94538', 'residential', 2, 3, 0, 'vacant', 3450, '#10b981'),
  ('p4', 't1', 'u1', '4008 Gunnar Dr', '4008 Gunnar Dr', 'Roseville', 'CA', '95747', 'residential', 3, 3, 0, 'vacant', 3085, '#f59e0b'),
  ('p5', 't1', 'u1', '6670 E Madison Ave', '6670 E Madison Ave', 'Fresno', 'CA', '93727', 'residential', 4, 3, 0, 'maintenance', 2750, '#ef4444');

INSERT INTO leases (
  id, property_id, tenant_user_id, tenant_name, start_date, end_date, rent_amount, security_deposit, status
) VALUES
  ('l1', 'p1', 'u3', 'Marcus Johnson', '2026-01-01', '2026-12-31', 2245, 2245, 'active'),
  ('l2', 'p5', 'u4', 'Olivia Reed', '2026-01-01', '2026-12-31', 2750, 2750, 'active');

INSERT INTO payments (
  id, lease_id, tenant_name, property_name, amount, due_date, paid_date, payment_method, status, late_fee, transaction_ref
) VALUES
  ('pay1', 'l1', 'Marcus Johnson', '2454 Ronald McNair Way', 2245, '2026-03-01', '2026-03-02', 'bank_transfer', 'paid', 0, 'TXN-DEMO1001'),
  ('pay2', 'l1', 'Marcus Johnson', '2454 Ronald McNair Way', 2245, '2026-04-01', NULL, 'bank_transfer', 'late', 75, 'TXN-DEMO1002'),
  ('pay3', 'l2', 'Olivia Reed', '6670 E Madison Ave', 2750, '2026-04-01', '2026-04-01', 'credit_card', 'paid', 0, 'TXN-DEMO1003');

INSERT INTO maintenance_requests (
  id, property_id, tenant_user_id, property_name, tenant_name, category, description, urgency, status, assigned_vendor, estimated_cost
) VALUES
  ('mr1', 'p5', 'u4', '6670 E Madison Ave', 'Olivia Reed', 'HVAC', 'Air conditioning stopped cooling and the indoor temperature is rising in the afternoon.', 'high', 'assigned', 'Central Valley HVAC', 850),
  ('mr2', 'p1', 'u3', '2454 Ronald McNair Way', 'Marcus Johnson', 'Plumbing', 'Kitchen sink drain is backing up after normal use.', 'medium', 'submitted', NULL, NULL);

INSERT INTO documents (
  id, uploaded_by, document_type, file_name, file_size, mime_type, related_entity
) VALUES
  ('d1', 'Sarah Chen', 'lease', 'Marcus_Johnson_Lease_Agreement.pdf', '248 KB', 'application/pdf', '2454 Ronald McNair Way'),
  ('d2', 'Sarah Chen', 'policy', 'Residential_Pet_Policy.pdf', '96 KB', 'application/pdf', 'All Homes'),
  ('d3', 'Sarah Chen', 'policy', 'Maintenance_Approval_Workflow.pdf', '134 KB', 'application/pdf', 'All Homes');

COMMIT;
