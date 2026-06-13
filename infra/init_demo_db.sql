CREATE TABLE IF NOT EXISTS employees (id SERIAL PRIMARY KEY, name TEXT, salary INT);
CREATE TABLE IF NOT EXISTS secrets (id SERIAL PRIMARY KEY, code TEXT);
INSERT INTO secrets (code) VALUES ('FLAG{sql_injection_success}');
INSERT INTO employees (name, salary) VALUES ('Admin', 999999);
INSERT INTO employees (name, salary) VALUES ('User', 50000);