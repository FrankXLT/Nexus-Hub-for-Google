# Nexus Hub for Google: Technical Architecture & System Lifecycle

## System Overview

Nexus Hub operates on a robust hybrid architecture, bridging the serverless convenience of Google Apps Script with the computational power of a dedicated Python Virtual Machine (VM). Acting as the spiritual successor to "Google Inbox," it utilizes a zero-inbox philosophy to transform unstructured chaos into a highly organized, task-oriented knowledge graph. The Python VM acts as the centralized brain, utilizing a strict, WAL-enabled SQLite database (`nexus.db`) for high-concurrency state management, metadata storage, and immutable audit logging. The Apps Script environment serves as a zero-dependency, Material Design frontend, communicating with the backend VM via a cryptographically secured (HMAC-SHA256), replay-protected webhook bridge. 

---

## 1. The Multi-Dimensional Taxonomy (Three-Tier Hierarchy)

To solve the issue of "directory sprawl," Nexus Hub enforces a strict Three-Tier Relational Hierarchy. Rather than a flat list of hundreds of senders, entities are logically grouped, making both automated routing and manual UI filtering significantly faster.

```mermaid
graph TD
    A[Category: Technology] --> B[Correspondent: Google]
    B --> C[Division: Google Cloud]
    B --> D[Division: Google Store]
    C --> E[Purpose: Invoice]
    D --> F[Purpose: Receipt]
    
    G[Category: Financial] --> H[Correspondent: Chase Bank]
    H --> I[Purpose: Statement]
    H --> J[Purpose: Tax Form]
```

### Zero-Trust Toggles
Every node in this hierarchy contains `is_gmail_enabled` and `is_drive_enabled` booleans. The default state for any new insertion is `FALSE` (Zero-Trust). If both are false, the entity is considered "Quarantined" or "Blacklisted." The AI is physically forbidden from routing documents to disabled paths, ensuring total human control over the taxonomy.

### Entity Profiles
To support robust data extraction, each Correspondent and Purpose is enriched with an Entity Profile. This includes:
- **Sending Subdomains:** JSON arrays of recognized email domains to authenticate senders.
- **Physical Addresses:** JSON arrays of known company addresses to improve document matching.
- **Brand Colors:** JSON arrays of hex pairs to automatically sync visual identity across Google Workspace.
- **Frequency & Confidence Weights:** Integers and floats used to refine the routing algorithm based on historical accuracy.

### Database Schema & Relational Integrity

To ensure high performance, prevent data anomalies, and maintain strict system constraints, the `nexus.db` SQLite index normalizes the taxonomy and isolates system states. 

The `Workspace_Artifacts` table does not redundantly store string names for Categories or Correspondents; it stores a single `purpose_id`. During Python data analysis or API fetching, the backend dynamically joins the `Taxonomy_Purposes`, `Taxonomy_Correspondents`, and `Taxonomy_Categories` tables. This guarantees that if an administrator renames a Correspondent or shifts a Purpose to a different Category in the UI, the change propagates instantly across thousands of artifacts without requiring expensive bulk database updates.

#### Entity Relationship Diagram

```mermaid
erDiagram
    Taxonomy_Categories ||--o{ Taxonomy_Correspondents : "contains"
    Taxonomy_Correspondents ||--o{ Taxonomy_Purposes : "defines"
    Taxonomy_Purposes ||--o{ Workspace_Artifacts : "categorizes"
    Workspace_Artifacts ||--o{ Artifact_History : "logs"
    Workspace_Artifacts ||--o{ Error_Logs : "tracks"

    Config_System {
        string key PK "Global variables"
        string value
    }
    Sync_State {
        string app_name PK "Gmail or Drive"
        string sync_token "Delta page tokens"
    }
    Config_Prompts {
        string target_app PK
        string prompt_text "Dynamic LLM instructions"
    }
    Taxonomy_Categories {
        int id PK
        string name
        int is_gmail_enabled "Zero-Trust Toggle"
        int is_drive_enabled "Zero-Trust Toggle"
    }
    Taxonomy_Correspondents {
        int id PK
        int category_id FK
        string name
        string division
        json sending_subdomains
        json physical_addresses
        json brand_colors
        int operation_cost "Quota tracking weight"
        int is_gmail_enabled
        int is_drive_enabled
    }
    Taxonomy_Purposes {
        int id PK
        int correspondent_id FK
        string name
        json custom_field_schema
        int frequency_weight
        float confidence_weight
        int operation_cost "Quota tracking weight"
        int is_gmail_enabled
        int is_drive_enabled
    }
    Workspace_Artifacts {
        string artifact_id PK
        int purpose_id FK
        string raw_text
        string summary
        json custom_data
        string status
        int locked_by_system "Prevents race conditions"
    }
    Artifact_History {
        int log_id PK
        string artifact_id FK
        int timestamp
        string actor
        string action_type
        json previous_state
        json new_state
    }
    Error_Logs {
        int log_id PK
        int timestamp
        string module_name
        string artifact_id FK
        string error_message
        json stack_trace "DLQ payload"
    }
```

#### Core Data Structures

* **The Taxonomy Core (`Taxonomy_*`):** Divides the hierarchy into three distinct tiers. The `Taxonomy_Correspondents` table utilizes native `JSON` columns to hold multi-dimensional profiles (`sending_subdomains`, `physical_addresses`, `brand_colors`), while `Taxonomy_Purposes` stores the `custom_field_schema`. Both tables track `operation_cost` to feed the API Quota Governor.
* **The Master Index (`Workspace_Artifacts`):** The central truth for all indexed documents and emails. It includes a `locked_by_system` boolean that acts as a mutex, preventing the UI from pushing manual overrides while the background synchronization engine is actively modifying the file.
* **The Dynamic AI Core (`Config_Prompts`):** Isolates the system role, extraction parameters, and AI instructions from the Python logic. This allows the Tuning Loop and UI to mutate AI behavior on the fly without restarting the Docker container.
* **The Telemetry Core (`Artifact_History` & `Error_Logs`):** Strict append-only ledgers. The History table records immutable JSON diffs of metadata overrides, while the Error Logs function as a Dead-Letter Queue (DLQ), catching API timeouts and Python stack traces for automated background retries.

## 2. Intelligent Quota Governor

Google API quotas and Apps Script execution timeouts are the silent killers of enterprise automation. Nexus Hub implements a "Priority Lane" Governor (`QuotaGovernor` class) directly within `sync_engine.py` to actively monitor and throttle API usage.

### The 72-Hour Priority Lane Logic

For every artifact fetched during a delta sync, `process_file_with_governor()` evaluates the item's age. It physically reserves a portion of the daily API quota (e.g., 30%) exclusively for real-time items.

```mermaid
flowchart TD
    classDef check fill:#e8f0fe,stroke:#1a73e8,stroke-width:2px;
    classDef pass fill:#e6f4ea,stroke:#1e8e3e,stroke-width:2px;
    classDef fail fill:#fce8e6,stroke:#d93025,stroke-width:2px;
    classDef db fill:#fef7e0,stroke:#f9ab00,stroke-width:2px;

    Start((Fetch Artifact)) --> Age{Calculate Age}:::check
    Age -- "< 72 Hours" --> Pass[Priority Lane: Allowed]:::pass
    Age -- "> 72 Hours" --> Hist{can_process_historical?}:::check

    Hist -- "Calls < 70% Limit" --> Pass
    Hist -- "Calls >= 70% Limit" --> Throttle[Governor: Throttled]:::fail

    Pass --> Process[Process Artifact]:::check
    Process --> Record[Governor.record_api_call]:::db
    Record --> UpdateDB[(Update Config_System Daily Count)]:::db
    Record --> UpdateCost[(Update Taxonomy operation_cost)]:::db
```

### Entity Cost Tracking
Every time an API call is made, record_api_call() updates the global counter in the Config_System table. Furthermore, if the call was associated with a specific entity, it increments the operation_cost integer column in either Taxonomy_Correspondents or Taxonomy_Purposes. This allows the UI to forecast exactly how much quota a bulk-edit operation will consume based on historical data.

### Seed Ingestion & Zero-Trust Defaults

Before the standard delta syncs occur, `sync_engine.py` executes `ingest_taxonomy_seed()`. This function acts as a passive ingestion bridge, allowing external scrapers (like the standalone Nexus for Gmail worker) to securely feed new entities into the system without requiring open webhook endpoints.

```mermaid
sequenceDiagram
    autonumber
    participant Cron as run_sync()
    participant SE as Sync Engine
    participant Drive as Google Drive API
    participant DB as SQLite (nexus.db)

    Cron->>SE: Initialize Sync Cycle
    SE->>Drive: Query: name='taxonomy_seed.json'
    alt File Found
        Drive-->>SE: Download JSON Payload
        SE->>SE: Parse Categories, Correspondents, Purposes
        SE->>DB: INSERT OR IGNORE Categories (is_gmail=0, is_drive=0)
        SE->>DB: INSERT OR IGNORE Correspondents (is_gmail=0, is_drive=0)
        SE->>DB: INSERT OR IGNORE Purposes (is_gmail=0, is_drive=0)
        Note over SE,DB: Frequency weights & Schemas merged
    else Not Found
        SE->>SE: Bypass Ingestion
    end
    SE->>SE: Proceed to Delta Syncs (Drive/Gmail)
```

To protect the system against malicious, hallucinated, or misconfigured routing paths from the seed file, the engine forces the is_gmail_enabled and is_drive_enabled booleans to 0 (FALSE) during the INSERT commands. These Zero-Trust toggles quarantine the newly discovered taxonomy nodes until a human administrator explicitly reviews and enables them in the frontend UI.

### Google Contacts Entity Bootstrapping
In addition to passive Drive ingestion, Nexus Hub actively bootstraps its `Taxonomy_Correspondents` table using the user's verified Google Contacts via the Google People API. 

This converts a user's personal address book into a deterministic routing engine.

```mermaid
sequenceDiagram
    autonumber
    participant Cron as run_sync()
    participant SE as Sync Engine
    participant People as Google People API
    participant DB as SQLite (nexus.db)

    Cron->>SE: Initialize Sync Cycle
    SE->>People: GET /v1/people/me/connections
    People-->>SE: Return Contacts (Names, Emails, Addresses)
    
    loop For Each Contact
        SE->>SE: Assign to 'Personal Network' Category
        SE->>SE: Map Emails -> sending_subdomains JSON
        SE->>SE: Map Addresses -> physical_addresses JSON
        SE->>DB: INSERT OR UPDATE Taxonomy_Correspondents
        Note over SE,DB: Enforce: is_gmail_enabled = 0<br/>Enforce: is_drive_enabled = 0
    end
```
### Data Mapping & Zero-Trust:
When `sync_contacts()` executes, it aggregates all known email addresses and physical addresses for a single person into the native JSON arrays designed in Phase 24. To prevent flooding the active taxonomy with hundreds of personal contacts, every ingested contact is forced into the Zero-Trust Quarantine. This allows the user to selectively enable only the contacts they actively wish to track for document routing.

## 3. The Google Drive Pipeline (Deep Dive)

The Google Drive ingestion pipeline is designed to efficiently process complex, unstructured documents through a rigorous, Two-Stage Triage system powered by Gemini AI.

```mermaid  
sequenceDiagram  
    autonumber
    participant D as Google Drive API  
    participant SE as Sync Engine (Python)  
    participant DocAI as Document AI  
    participant LLM as Gemini AI  
    participant DB as SQLite (nexus.db)

    rect rgb(240, 248, 255)  
    Note right of D: Phase 1: Ingestion & OCR  
    D->>SE: Delta Push / Changes API (pageToken)  
    SE->>D: Download Raw PDF/Image File  
    SE->>DocAI: Transmit Payload for OCR  
    DocAI-->>SE: Return Full JSON (Text + hOCR bounding boxes)  
    Note over SE: Optimization: Strip out heavy hOCR data<br/>Retain only UTF-8 Raw Text  
    end

    rect rgb(255, 245, 238)  
    Note right of D: Phase 2: Triage & Routing  
    SE->>LLM: Send Text to Triage Prompt  
    LLM-->>SE: Return Correspondent String (e.g., 'AWS')  
    SE->>DB: Insert to Holding Queue (Status: PENDING_BATCH)  
    end

    rect rgb(245, 255, 250)  
    Note right of D: Phase 3: Threshold Execution & Extraction  
    Note over SE: Cron triggers batch execution  
    SE->>DB: Select batched artifacts  
    SE->>LLM: Send batched text + 'AWS' Purpose Whitelist + Schema  
    LLM-->>SE: Return Structured JSON (Purpose, Custom Fields, Summary)  
    end

    rect rgb(253, 245, 230)  
    Note right of D: Phase 4: Archival & Exception Handling  
    alt JSON Valid & Strict Match  
        SE->>DB: Update Artifact (Status: PROCESSED)  
        SE->>DB: Insert Artifact_History  
        SE->>D: Apply nested folderColorRgb  
        SE->>D: Inject Custom AppProperties Metadata  
    else Ambiguous Intent OR Normalization Failure  
        SE->>DB: Route to Exception Queue (Tag: Purpose/Review)  
    else LLM JSON Malformed / 500 Error  
        SE->>DB: Route to Error_Logs (Dead-Letter Queue)  
    end  
    end
```

### **Phase 1: Ingestion & OCR Strip-down**

1. **Delta Synchronization:** To avoid the prohibitive latency of full polling, the sync_engine.py process maintains a persistent pageToken in the Sync_State table. It queries the Google Drive API (changes().list) to fetch only files modified since the last check.  
2. **Payload Optimization:** For scanned documents, the engine leverages Document AI for OCR. Because raw hOCR output is massive and token-heavy, the engine strips down this payload, retaining only the UTF-8 text to minimize latency before passing it to the LLM.

### **Phase 2 & 3: Two-Stage Triage & Logical Routing**

Because Drive documents are unstructured, `llm_engine.py` employs a Two-Stage verification process (`process_drive_document`). It strictly enforces whitelists via the `normalize_taxonomy()` function while gracefully capturing "Discovery" suggestions from the LLM if a vendor is unknown.

```mermaid
flowchart TD
    classDef ai fill:#fce8e6,stroke:#d93025,stroke-width:2px;
    classDef processing fill:#e8f0fe,stroke:#1a73e8,stroke-width:2px;
    classDef queue fill:#fff7d0,stroke:#f29900,stroke-width:2px;
    classDef final fill:#e6f4ea,stroke:#1e8e3e,stroke-width:2px;

    Start((Start Drive Sync)) --> Fetch1[Fetch 'DRIVE_STAGE_1' Prompt]:::processing
    Fetch1 --> Gemini1[Gemini API: Identify Correspondent]:::ai
    Gemini1 --> Norm1{Normalize Correspondent}:::processing

    Norm1 -- Valid Match --> Fetch2[Fetch Correspondent-Specific Prompt]:::processing
    Norm1 -- 'UNKNOWN' or Failed Match --> Disc1{Has 'discovered_correspondent'?}:::processing

    Disc1 -- Yes --> RouteCR[Status: Correspondent/Review<br>Data: pending_discovery]:::queue
    Disc1 -- No --> RouteUnk[Status: UNKNOWN_CORRESPONDENT]:::queue

    Fetch2 --> Gemini2[Gemini API: Extract Purpose & Fields]:::ai
    Gemini2 --> Norm2{Normalize Purpose}:::processing

    Norm2 -- Valid Match --> RouteProc[Status: PROCESSED]:::final
    Norm2 -- 'Purpose/Review' --> Disc2{Has 'discovered_purpose'?}:::processing

    Disc2 -- Yes --> RoutePR1[Status: Purpose/Review<br>Data: pending_discovery]:::queue
    Disc2 -- No --> RoutePR2[Status: Purpose/Review]:::queue
```

### **Phase 3 & 4: Threshold Batching, Extraction, and Archival**

Once a batch threshold is met for a specific Correspondent, the documents undergo deep extraction for Custom Fields. Successful extractions are written to the database and native Drive metadata. Ambiguous documents are forcefully routed to the Purpose/Review Exception Queue.

## **4. The Gmail Pipeline (Deep Dive)**

Unlike Drive documents, emails arrive with structured metadata, allowing for a highly efficient, single-pass extraction.

```mermaid  
sequenceDiagram
    autonumber
    participant Gmail as Gmail API
    participant PubSub as GCP Pub/Sub
    participant WH as Webhook (FastAPI)
    participant Sync as Sync Engine (Python)
    participant LLM as Gemini API
    participant DB as nexus.db

    Gmail->>PubSub: Push Notification (New Email)
    PubSub->>WH: POST /api/pubsub
    WH->>Sync: Trigger Delta Sync
    Sync->>Gmail: history().list() fetch modified threads
    Note over Sync: Groups threads by Sender Domain
    Sync->>LLM: Single-Pass Extraction
    LLM-->>Sync: Returns Taxonomy, Summary, Action_State, Fields
    alt Successful Parse
        Sync->>DB: INSERT Artifact & History Log
        Sync->>Gmail: Apply Nested Labels & Brand Colors
    else JSON Parse Error
        Sync->>DB: Flag ERROR_LLM_PARSE
    end
```

1. **Trigger Mechanisms:** A Cloud Pub/Sub push notification serves as the primary trigger, firing a webhook to initiate the sync. A cron-based polling fallback queries users().history().list.  
2. **Single-Pass Extraction:** The payload is evaluated by Gemini in a single pass to determine the taxonomy path, generate a summary, assess actionability, and extract custom fields simultaneously.

### **The Single-Pass Logical Flow**

Because emails provide rich context (Sender, Subject), `llm_engine.py` executes `process_gmail_thread()` in a single step, injecting the schema and whitelists directly into the unified prompt.

```mermaid
flowchart TD
    classDef ai fill:#fce8e6,stroke:#d93025,stroke-width:2px;
    classDef processing fill:#e8f0fe,stroke:#1a73e8,stroke-width:2px;
    classDef queue fill:#fff7d0,stroke:#f29900,stroke-width:2px;
    classDef final fill:#e6f4ea,stroke:#1e8e3e,stroke-width:2px;
    classDef error fill:#fce8e6,stroke:#d93025,stroke-width:2px;

    Start((Start Gmail Sync)) --> Fetch[Fetch 'GMAIL' Prompt]:::processing
    Fetch --> Context[Inject Dynamic Array & Whitelist]:::processing
    Context --> Gemini[Gemini API: Single-Pass Extraction]:::ai

    Gemini -- Valid JSON --> Norm{Normalize Taxonomy Path}:::processing
    Gemini -- JSONDecodeError --> RouteErr[Status: ERROR_LLM_PARSE]:::error

    Norm -- Valid Match --> Save[persist_llm_results]:::processing
    Norm -- Failed Match --> SaveRev[persist_llm_results]:::processing
    
    Save --> RouteProc[Status: PROCESSED]:::final
    SaveRev --> RouteRev[Status: Purpose/Review]:::queue    
```

## **5. The Exception Queue & Manual UI Overrides**

When an artifact fails strict normalization or Gemini returns an ambiguous result, it is flagged as Purpose/Review. These items await human verification in the Apps Script frontend. When a user provides a manual correction, the system secures the transmission via a cryptographic handshake.

```mermaid  
sequenceDiagram
    autonumber
    actor User
    participant UI as Apps Script UI (Browser)
    participant GS as Apps Script Backend (Code.gs)
    participant VM as Python VM (main.py)
    participant DB as SQLite (nexus.db)

    User->>UI: Corrects Taxonomy (Manual Override)
    UI->>GS: google.script.run.updateArtifact(payload)
    Note over GS: Retrieves HMAC Secret from PropertiesService
    GS->>GS: Generates HMAC-SHA256 Hash<br/>Appends UNIX Timestamp
    GS->>VM: UrlFetchApp POST to /api/update<br/>Header: X-Nexus-Signature
    Note over VM: Validates Timestamp (< 5 mins)<br/>Recalculates HMAC Hash
    alt Signature Valid
        VM->>DB: UPDATE Workspace_Artifacts
        VM->>DB: INSERT Artifact_History (Actor: USER)
        VM-->>GS: 200 OK
        GS-->>UI: Success Notification
    else Signature Invalid / Expired
        VM-->>GS: 401 Unauthorized
        GS-->>UI: Error: Security Handshake Failed
    end
```

## **6. RAG Knowledge Retrieval Pipeline**

Nexus Hub includes a natural language querying engine (`ask_rag()`). To protect system memory, eliminate context-window limits, and reduce API costs, it implements a strict Two-Step "Text-to-SQL" pipeline rather than blindly feeding semantic vector databases.

```mermaid
flowchart TD
    classDef ai fill:#fce8e6,stroke:#d93025,stroke-width:2px;
    classDef db fill:#fef7e0,stroke:#f9ab00,stroke-width:2px;
    classDef processing fill:#e8f0fe,stroke:#1a73e8,stroke-width:2px;

    Input[User Natural Language Question] --> Prompt1[Prompt 1: Text-to-SQL Translation]:::processing
    Prompt1 --> Gemini1[Gemini API: Generate SQL String]:::ai
    Gemini1 --> Query[(SQLite: Execute Read-Only SQL)]:::db
    
    Query -- Returns up to 10 Rows --> Prompt2[Prompt 2: Summarize Rows]:::processing
    Query -- SQLite Error / Empty --> Fail[Return Error Message to UI]:::processing
    
    Prompt2 --> Gemini2[Gemini API: Natural Language Synthesis]:::ai
    Gemini2 --> Output[Return Answer to Chat UI]:::processing
```

## **7. The Tuning Loop (AI Self-Correction)**

Nexus Hub does not simply log user corrections; it learns from them. The system employs an asynchronous background loop to dynamically tune its own extraction prompts based on human feedback.

```mermaid  
flowchart TD  
    UI[User Corrects Label in UI] --> WH[FastAPI Webhook: /api/update]  
      
    WH -- "Immediate Response" --> UI_Success[Returns 200 OK to UI]  
    WH -- "Background Task" --> Fetch[Fetch Raw Text & Previous State]  
      
    Fetch --> LLM{Gemini Tuning Prompt}  
      
    LLM -.- PromptNote["You made a mistake.<br/>Analyze the text and the user's correction.<br/>Write a 1-sentence rule to never do this again."]  
      
    LLM --> Rule[Generate New Routing Rule]  
    Rule --> DB[(Config_Prompts Table)]  
    DB --> Update[Append Rule to Correspondent Prompt]  
      
    style LLM fill:#fce8e6,stroke:#d93025  
    style DB fill:#fef7e0,stroke:#f9ab00  
    style UI_Success fill:#e6f4ea,stroke:#1e8e3e
    style PromptNote fill:#f9f9f9,stroke:#333,stroke-dasharray: 5 5
```

When a manual override occurs, the webhook immediately returns a 200 OK so the UI remains snappy. In the background, the Python engine queries Gemini with the AI's original mistake and the user's correction, generating a new persistent routing rule to prevent future recurrences.

**Technical Implementation:** This asynchronous behavior is achieved using FastAPI's `BackgroundTasks`. During the `POST /api/update` webhook execution, the server attaches the `generate_tuning_rule` function to the background task queue. This guarantees the 200 OK response is dispatched to the Google Apps Script frontend instantaneously, preventing any blocking UI freeze while the Gemini AI API generates and saves the tuning rule.


## **8. Programmatic Color Management**

To maintain visual cohesion across the Google Workspace ecosystem, Nexus Hub employs programmatic visual branding.

1. **The Constraints:** The Gmail API strictly limits label colors to 35 specific background/text hex code combinations.  
2. **Dual-Snapping Algorithm:** The branding_engine.py calculates the Euclidean distance in the RGB color space between a user's requested brand color and the allowed Gmail palette, snapping to the closest WCAG contrast-compliant pair.  
3. **Synchronization:** That precise hex code pair is subsequently applied to both the Gmail nested labels and the corresponding Google Drive folders.

## **9. UI Data Retrieval & Presentation**

The frontend relies on a decoupled, asynchronous data retrieval model to ensure a highly responsive user experience without page reloads.

```mermaid  
sequenceDiagram
    autonumber
    actor User
    participant UI as Browser (Index.html / JS_Actions)
    participant GAS as Apps Script Backend (Code.gs)
    participant VM as Nginx & FastAPI (GCP)
    participant DB as SQLite (nexus.db)

    User->>UI: Opens Dashboard or Modifies Filters
    UI->>GAS: google.script.run.fetchArtifacts(filters)
    Note over GAS: Retrieves HMAC Secret
    GAS->>GAS: Generate HMAC Signature + Timestamp
    GAS->>VM: GET /api/artifacts (with Auth Headers)
    
    Note over VM: Validate HMAC & Timestamp
    VM->>DB: Execute Indexed SQL Query
    DB-->>VM: Return List of sqlite3.Row dictionaries
    VM-->>GAS: Return JSON Payload (HTTP 200)
    GAS-->>UI: Pass JSON via Async Promise
    
    Note over UI: JS_State memory is updated.<br/>Material Data Grid renders rows.<br/>Split-Pane listener is attached.
    User->>UI: Clicks specific table row
    UI->>UI: Render Native Drive Iframe (Left Pane)<br/>Render Editable Custom Fields (Right Pane)
```

1. **Secure Proxy:** Apps Script fetches the HMAC secret, generates a timestamped signature, and proxies the GET request to the Python VM.  
2. **Database Fetch:** The Python engine validates the signature, queries the SQLite index, and returns standard JSON array payloads utilizing sqlite3.Row dictionary mappings.  
3. **State Management:** The UI receives the payload, stores it in JS_State.html (acting as client-side memory), and immediately renders the split-pane data grid dynamically.

## **10. Error Routing & Dead-Letter Queue**

To ensure the automated ingestion pipeline never crashes or loses data, Nexus Hub employs a robust Dead-Letter Queue (DLQ).

1. **Race Conditions:** If a user modifies a file in Drive while the Python engine is processing it, the locked_by_system boolean in the Workspace_Artifacts table prevents the UI from causing a data collision.  
2. **API Timeouts:** If a 500 error occurs when calling Gemini or Google APIs, the artifact is logged into the Error_Logs table alongside its full stack trace.  
3. **Auto-Retry:** The background sync job periodically polls the Error_Logs table. Failed artifacts are automatically re-queued for processing up to a maximum of 3 attempts before requiring manual admin intervention.

## 11. Automated Health Checks & Diagnostics

To instantly isolate points of failure across the hybrid architecture, Nexus Hub features a decoupled diagnostic suite (`diagnostics.py`). This suite can be triggered manually via the Apps Script UI or invoked via the command line on the host VM. 

Crucially, the diagnostic suite operates under a strict "Isolated Logging" paradigm. If the SQLite database experiences a fatal lock, it cannot log its own failure. Therefore, the diagnostic suite bypasses the internal `Error_Logs` table and uploads its health reports directly to an isolated folder in Google Drive.

The Automated Watchdog: The host VM utilizes a cron job to execute the diagnostic suite every 15 minutes. If any test (Database integrity, OAuth validity, or API health) fails, the suite bypasses standard logging and utilizes the NexusNotifier to push a critical failure alert directly to the user's mobile device via Pushover.

### Diagnostic Watchdog & Communication Flow

```mermaid
flowchart TB
    classDef appsScript fill:#e8f0fe,stroke:#1a73e8,stroke-width:2px;
    classDef gcp fill:#e6f4ea,stroke:#1e8e3e,stroke-width:2px;
    classDef database fill:#fef7e0,stroke:#f9ab00,stroke-width:2px;
    classDef googleApi fill:#e8eaed,stroke:#5f6368,stroke-width:2px;
    classDef external fill:#fce8e6,stroke:#d93025,stroke-width:2px;

    subgraph Execution Triggers
        Cron[Host VM: 15-Min Cron Job]
        UI[Apps Script UI: Manual Run]
    end
    class Cron,UI appsScript

    subgraph GCP Compute Engine (Local VM)
        WH[nexus-api: FastAPI]
        Diag[nexus-sync-engine: diagnostics.py]
        DB[(nexus.db SQLite)]
        Notif[notifier.py]

        UI -- "HMAC Webhook" --> WH
        WH -- "Triggers" --> Diag
        Cron -- "docker run" --> Diag

        Diag -- "1. Test R/W Lock" --> DB
        Diag -- "2. Ping /api/health" --> WH
        Diag -- "If Any Check Fails" --> Notif
    end
    class WH,Diag,Notif gcp
    class DB database

    subgraph External Ecosystem
        Auth[Google OAuth]
        Drive[Google Drive]
        Push[Pushover API]

        Diag -- "3. Verify token.json" --> Auth
        Diag -- "4. Upload JSON Report" --> Drive
        Notif -- "Send CRITICAL Mobile Alert" --> Push
    end
    class Auth,Drive googleApi
    class Push external
```

### The Four-Phase Verification Check

1. **Database R/W Integrity:** The script connects to `nexus.db`, enforces `PRAGMA journal_mode=WAL;`, creates a temporary table `_Diagnostic_Test`, inserts a timestamp, reads it back, and drops the table. This confirms the VM filesystem permissions are intact and the database is not locked by a hung background process.
2. **OAuth Authorization Ping:** The script authenticates using the VM's headless `token.json` and performs a lightweight read-only request (`about().get`) against the Google Drive API. This verifies the token has not expired or lost its requested scopes.
3. **Decentralized Log Upload:** The results of the database and OAuth checks are compiled into a JSON payload. The script locates (or creates) a `Nexus Diagnostics` folder in the user's Google Drive and uploads the JSON file, providing an immutable, timestamped record of system health independent of the VM's local storage.
4. **Telemetry & Log Upload:** If all checks pass, a JSON report is uploaded to the 'Nexus Diagnostics' folder in Google Drive. If any check fails, the script immediately leverages 'notifier.py' to push a CRITICAL alert to the user's mobile device via Pushover, bypassing the internal database entirely.

## **12. Dynamic Prompt Architecture**

Nexus Hub employs a fully database-driven prompt architecture, eliminating hardcoded instructions from the execution environment. This allows administrators to modify AI behavior on-the-fly without needing to restart the Docker container or redeploy the Python VM.

1. **Initialization:** On first boot, the system seeds the default master prompts (Gmail Single-Pass, Drive Stage 1, and Drive Stage 2) into the `Config_Prompts` SQLite table.
2. **Real-time Injection:** Immediately before triggering an external call to the Gemini API, the LLM extraction engine queries the database in real-time to fetch the active instructions.
3. **Frontend Modification:** The backend exposes secured `GET /api/prompts` and `POST /api/prompts` endpoints, allowing the Google Apps Script frontend to seamlessly read and apply updates to these core instructions.

## **13. Telemetry & Alerting Matrix**

Because the engine runs headlessly, Nexus Hub employs a robust notification matrix to alert the user of critical failures via Pushover, and emails daily digests of quarantined items.

```mermaid
flowchart TD
    A[System Event] --> B{Severity Check}
    B -- "CRITICAL (e.g., DB Lock, OAuth Expired)" --> C[Pushover Webhook API]
    C --> D[Mobile Push Notification]
    B -- "WARNING (e.g., Quarantine, 85% Quota)" --> E[Daily Digest Queue]
    B -- "INFO (e.g., Sync Complete)" --> F[Apps Script UI Badge]
    E --> G[8:00 AM Cron Task]
    G --> H[Gmail API -> Send Summary Email]
```
