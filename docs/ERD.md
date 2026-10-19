# Entity-relationship diagram

```mermaid
erDiagram
    USERS ||--o{ FABRIC_ANALYSES : owns
    USERS ||--o{ WASHING_HISTORY : records
    FABRIC_ANALYSES ||--o{ WASHING_HISTORY : "mode chosen for"
    USERS ||--o{ AUDIT_LOGS : "generates (nullable FK)"
    FABRIC_KNOWLEDGE ||--o{ FABRIC_ANALYSES : "describes (by fabric_type key)"

    USERS {
        int id PK
        string name
        string email UK
        string password_hash
        datetime created_at
        datetime last_login
        bool notifications_enabled
        string theme
        bool is_demo
    }
    FABRIC_ANALYSES {
        int id PK
        int user_id FK
        string image_path
        string predicted_fabric
        float confidence
        string washing_temperature
        string washing_mode
        string drying_method
        string ironing_temperature
        text special_care
        bool low_confidence
        text probabilities
        text note_encrypted
        string model_version
        bool is_synthetic
        datetime created_at
    }
    FABRIC_KNOWLEDGE {
        int id PK
        string fabric_type UK
        text property
        string washing_method
        string temperature
        string drying_method
        string ironing_method
        text special_care
        string detergent
        string bleaching
    }
    WASHING_HISTORY {
        int id PK
        int user_id FK
        int fabric_analysis_id FK
        string selected_washing_mode
        datetime created_at
    }
    AUDIT_LOGS {
        int id PK
        int user_id FK
        string action
        datetime timestamp
        string ip_address
        string status
        string detail
    }
    ETL_RUNS {
        int id PK
        string source
        string status
        datetime started_at
        text report_json
    }
```

Notes:

- `fabric_analyses.user_id` and `washing_history.*` use `ON DELETE CASCADE`; `audit_logs.user_id` uses `ON DELETE SET NULL`, so the audit trail survives user deletion.
- `fabric_knowledge` is linked to analyses by the shared `fabric_type` key (not a hard foreign key, so rules can evolve without breaking history).
- `etl_runs` stores one JSON quality report per pipeline run.
- `note_encrypted` holds Fernet ciphertext. `is_synthetic` marks Synthetic Demo Data.
