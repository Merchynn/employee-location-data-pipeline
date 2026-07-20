CREATE OR REPLACE VIEW analytics.vw_employee_commute AS
SELECT
    employee_id,
    employee_code,
    full_name,
    branch,
    department,
    cost_center,
    admission_date,
    city,
    state,
    latitude,
    longitude,
    declared_commute_time,
    route_distance_km,
    route_duration_text,
    straight_line_distance_km,
    uses_train,
    uses_walking,
    uses_subway,
    uses_bus,
    uses_car,
    loaded_at_utc
FROM analytics.employee_location_snapshot;
