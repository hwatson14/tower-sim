# Wiki cache audit report

## Summary
- Total tables: 10
- PROMOTABLE: 7
- PROMOTABLE_WITH_GAPS: 0
- NOT_PROMOTABLE: 3

## Tables

| File | Status | Reason | Levels | Values | Unit |
| --- | --- | --- | --- | --- | --- |
| cards_common.csv | NOT_PROMOTABLE | missing_level_or_value_column |  |  | unknown |
| cards_epic.csv | NOT_PROMOTABLE | missing_level_or_value_column |  |  | unknown |
| cards_rare.csv | NOT_PROMOTABLE | missing_level_or_value_column |  |  | unknown |
| lab_enemy_attack_level_skip.csv | PROMOTABLE |  | 1..20 | 0.1..2.0 | raw_number |
| lab_enemy_health_level_skip.csv | PROMOTABLE |  | 1..20 | 0.1..2.0 | raw_number |
| lab_health.csv | PROMOTABLE |  | 1..100 | 1.03..4.0 | raw_number |
| lab_health_regen.csv | PROMOTABLE |  | 1..100 | 1.03..4.0 | raw_number |
| lab_recovery_package_chance.csv | PROMOTABLE |  | 1..20 | 0.2..4.0 | percent_string |
| wall_lab_wall_health.csv | PROMOTABLE |  | 1..50 | 2.0..100.0 | percent_string |
| wall_lab_wall_regen.csv | PROMOTABLE |  | 1..30 | 10.0..300.0 | percent_string |

## Details

### cards_common.csv

- Status: NOT_PROMOTABLE
- Reason: missing_level_or_value_column
- Path: /workspace/tower-sim/tower_sim/wiki/cache/cards_common.csv
- SHA256: 2d77c7a714d2eb4762267fdfe5164cdb7cf6908d82eb09d8c886646dffc64b48
- Modified: 2026-01-17T03:57:20.682607+00:00
- Delimiter: ,
- Headers: Rarity, Name, Description, Lv. 1, Lv. 2, Lv. 3, Lv. 4, Lv. 5, Lv. 6, Lv. 7
- Row count: 12
- Level column: None
- Value column: None
- Levels sorted: None
- Level range: 
- Level count: 12
- Contiguous: None
- Gaps: []
- Value range: 
- Unit hint: unknown
- Duplicate levels: []
- Duplicate values: []
- Missing values: 0
- Non-numeric values: 0

### cards_epic.csv

- Status: NOT_PROMOTABLE
- Reason: missing_level_or_value_column
- Path: /workspace/tower-sim/tower_sim/wiki/cache/cards_epic.csv
- SHA256: f39d18bea6f471eecc32518d18412606ae6b851cdb7a73a178e226c55ea259cd
- Modified: 2026-01-17T03:57:20.682607+00:00
- Delimiter: ,
- Headers: Rarity, Name, Description, Lv. 1, Lv. 2, Lv. 3, Lv. 4, Lv. 5, Lv. 6, Lv. 7
- Row count: 11
- Level column: None
- Value column: None
- Levels sorted: None
- Level range: 
- Level count: 11
- Contiguous: None
- Gaps: []
- Value range: 
- Unit hint: unknown
- Duplicate levels: []
- Duplicate values: []
- Missing values: 0
- Non-numeric values: 0

### cards_rare.csv

- Status: NOT_PROMOTABLE
- Reason: missing_level_or_value_column
- Path: /workspace/tower-sim/tower_sim/wiki/cache/cards_rare.csv
- SHA256: 0ca46f871b4282a7a1752f735a1acab46c06e093fa4a44a3d240e94b204bf316
- Modified: 2026-01-17T03:57:20.682607+00:00
- Delimiter: ,
- Headers: Rarity, Name, Description, Lv. 1, Lv. 2, Lv. 3, Lv. 4, Lv. 5, Lv. 6, Lv. 7
- Row count: 8
- Level column: None
- Value column: None
- Levels sorted: None
- Level range: 
- Level count: 8
- Contiguous: None
- Gaps: []
- Value range: 
- Unit hint: unknown
- Duplicate levels: []
- Duplicate values: []
- Missing values: 0
- Non-numeric values: 0

### lab_enemy_attack_level_skip.csv

- Status: PROMOTABLE
- Path: /workspace/tower-sim/tower_sim/wiki/cache/lab_enemy_attack_level_skip.csv
- SHA256: 6f07b2299022c8c970877e59c364f6caccec97ca232c1b34e1d6c96ff7e55d69
- Modified: 2026-01-17T03:57:20.682607+00:00
- Delimiter: ,
- Headers: level, value_percent_points
- Row count: 20
- Level column: level
- Value column: value_percent_points
- Levels sorted: True
- Level range: 1..20
- Level count: 20
- Contiguous: True
- Gaps: []
- Value range: 0.1..2.0
- Unit hint: raw_number
- Duplicate levels: []
- Duplicate values: []
- Missing values: 0
- Non-numeric values: 0

### lab_enemy_health_level_skip.csv

- Status: PROMOTABLE
- Path: /workspace/tower-sim/tower_sim/wiki/cache/lab_enemy_health_level_skip.csv
- SHA256: 6f07b2299022c8c970877e59c364f6caccec97ca232c1b34e1d6c96ff7e55d69
- Modified: 2026-01-17T03:57:20.682607+00:00
- Delimiter: ,
- Headers: level, value_percent_points
- Row count: 20
- Level column: level
- Value column: value_percent_points
- Levels sorted: True
- Level range: 1..20
- Level count: 20
- Contiguous: True
- Gaps: []
- Value range: 0.1..2.0
- Unit hint: raw_number
- Duplicate levels: []
- Duplicate values: []
- Missing values: 0
- Non-numeric values: 0

### lab_health.csv

- Status: PROMOTABLE
- Path: /workspace/tower-sim/tower_sim/wiki/cache/lab_health.csv
- SHA256: cc5075f4bc75d5e6e63963f1c7b45f8d527b0ec7372e1a4469d2bd8df6a95b31
- Modified: 2026-01-17T03:57:20.682607+00:00
- Delimiter: ,
- Headers: Level, Time, Cost, Value
- Row count: 100
- Level column: Level
- Value column: Value
- Levels sorted: True
- Level range: 1..100
- Level count: 100
- Contiguous: True
- Gaps: []
- Value range: 1.03..4.0
- Unit hint: raw_number
- Duplicate levels: []
- Duplicate values: []
- Missing values: 0
- Non-numeric values: 0

### lab_health_regen.csv

- Status: PROMOTABLE
- Path: /workspace/tower-sim/tower_sim/wiki/cache/lab_health_regen.csv
- SHA256: cc5075f4bc75d5e6e63963f1c7b45f8d527b0ec7372e1a4469d2bd8df6a95b31
- Modified: 2026-01-17T03:57:20.682607+00:00
- Delimiter: ,
- Headers: Level, Time, Cost, Value
- Row count: 100
- Level column: Level
- Value column: Value
- Levels sorted: True
- Level range: 1..100
- Level count: 100
- Contiguous: True
- Gaps: []
- Value range: 1.03..4.0
- Unit hint: raw_number
- Duplicate levels: []
- Duplicate values: []
- Missing values: 0
- Non-numeric values: 0

### lab_recovery_package_chance.csv

- Status: PROMOTABLE
- Path: /workspace/tower-sim/tower_sim/wiki/cache/lab_recovery_package_chance.csv
- SHA256: bf473321f32799633733b5ad4a3fec967fab344fa95a8b6cb6d80527e4afeb54
- Modified: 2026-01-17T03:57:20.682607+00:00
- Delimiter: ,
- Headers: Level, Time, Cost, Value
- Row count: 20
- Level column: Level
- Value column: Value
- Levels sorted: True
- Level range: 1..20
- Level count: 20
- Contiguous: True
- Gaps: []
- Value range: 0.2..4.0
- Unit hint: percent_string
- Duplicate levels: []
- Duplicate values: []
- Missing values: 0
- Non-numeric values: 0

### wall_lab_wall_health.csv

- Status: PROMOTABLE
- Path: /workspace/tower-sim/tower_sim/wiki/cache/wall_lab_wall_health.csv
- SHA256: 69667446bb7e12bf534412485af2762fa73396e4b6e14ed7c0df4887a63f13c4
- Modified: 2026-01-17T03:57:20.682607+00:00
- Delimiter: ,
- Headers: Level, Time, Cost, Value
- Row count: 50
- Level column: Level
- Value column: Value
- Levels sorted: True
- Level range: 1..50
- Level count: 50
- Contiguous: True
- Gaps: []
- Value range: 2.0..100.0
- Unit hint: percent_string
- Duplicate levels: []
- Duplicate values: []
- Missing values: 0
- Non-numeric values: 0

### wall_lab_wall_regen.csv

- Status: PROMOTABLE
- Path: /workspace/tower-sim/tower_sim/wiki/cache/wall_lab_wall_regen.csv
- SHA256: d3593d8c27679130d20043388b163648dd0f7bec0b460c8cdd8ec4f92633402f
- Modified: 2026-01-17T03:57:20.682607+00:00
- Delimiter: ,
- Headers: Level, Time, Cost, Value
- Row count: 30
- Level column: Level
- Value column: Value
- Levels sorted: True
- Level range: 1..30
- Level count: 30
- Contiguous: True
- Gaps: []
- Value range: 10.0..300.0
- Unit hint: percent_string
- Duplicate levels: []
- Duplicate values: []
- Missing values: 0
- Non-numeric values: 0
