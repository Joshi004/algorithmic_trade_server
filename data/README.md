# Seed Data

This directory contains seed data files that are automatically loaded into the database during application setup.

## Creating New Seed Files

1. Create a new SQL file in this directory with a `.sql` extension.
2. Add your SQL statements to the file. Each statement should end with a semicolon (`;`).
3. Use `INSERT` statements to add data. Each statement will be executed independently.
4. For tables with unique constraints, be aware that duplicate inserts will be skipped to prevent errors.

## Example Seed File Structure

```sql
-- Create sample algorithms
INSERT INTO algorithms (name, table_name, type, description)
VALUES ('example_algo', 'example_table', 'scanning', 'This is a description of an example algorithm');

-- Create default user configuration
INSERT INTO user_configurations (user_id, risk_appetite, min_reward_risk_ratio, max_reward_risk_ratio, trades_per_session)
VALUES (2, 7, 2.5, 18, 75);
```

## How Seed Files Are Tracked

The seed system keeps track of which seed files have been applied in a `seed_tracker` table. This ensures that:

1. Seed files are only applied once, preventing duplicate data
2. New seed files added later will be automatically applied on the next application startup

## Force Reapplying Seeds

If you need to force reapply all seed files (for example, after modifying them), you can run:

```bash
python manage.py seed_data --force
```

This will reapply all seed files, skipping any insert statements that would cause duplicate key errors. 