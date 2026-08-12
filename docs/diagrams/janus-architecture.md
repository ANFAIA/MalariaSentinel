# Janus Architecture — Mermaid Diagrams

## 1. High-Level Overview

```mermaid
graph TB
    subgraph User["👤 User"]
        U["User Input"]
    end

    subgraph Janus["🏛️ Janus Orchestrator"]
        direction TB
        Factory["create_orchestrator(mode)"]
        
        subgraph Modes["Dual-Mode"]
            direction LR
            C["🎭 Centinela<br/>(conversational REPL)"]
            D["🎯 Dispatcher<br/>(goal-driven one-shot)"]
        end

        subgraph PromptTemplate["📝 Prompt Engine"]
            TPL["orchestrator.md.j2<br/>(Jinja2 Template)"]
            CSEC["{% if mode == 'centinela' %}<br/>Centinela Protocol"]
            DSEC["{% if mode == 'dispatcher' %}<br/>Dispatcher Protocol"]
        end
    end

    subgraph Specialists["🔧 9 Specialist Subagents"]
        direction LR
        S1["🔬 abm"]
        S2["📊 scoring"]
        S3["📥 ingest"]
        S4["⬇️ download"]
        S5["🔮 prediction"]
        S6["🏋️ training"]
        S7["📂 data"]
        S8["📚 commonlib"]
        S9["🔄 self_improve"]
    end

    subgraph Infrastructure["⚙️ Infrastructure"]
        direction LR
        GAWT["gawt MCP<br/>(session + worktree)"]
        KG["Neo4j<br/>Knowledge Graph"]
        LF["Langfuse<br/>Tracing"]
        Pipeline["mal-core<br/>Pipeline"]
    end

    U -->|"REPL input"| C
    U -->|"--goal flag"| D
    Factory --> C
    Factory --> D
    TPL --> CSEC
    TPL --> DSEC
    C -->|"task() research"| Specialists
    C -->|"delegate_to_dispatcher()"| D
    D -->|"start_session + task()"| Specialists
    Specialists -->|"edit_file / write_file"| GAWT
    C -->|"memory_recall_kg()"| KG
    D -->|"memory_recall_kg()"| KG
    C -->|"traces"| LF
    D -->|"traces"| LF
    D -->|"pipeline_run_calibration()"| Pipeline
```

## 2. Delegation Flow — How Centinela and Dispatcher Cooperate

```mermaid
sequenceDiagram
    actor User
    participant C as 🎭 Centinela<br/>(REPL)
    participant D as 🎯 Dispatcher<br/>(one-shot)
    participant GW as gawt MCP
    participant SP as Specialist<br/>(e.g. scoring)
    participant KG as Neo4j KG
    participant LF as Langfuse

    User->>C: "Fix population extinction bug"

    rect rgb(230, 245, 255)
        Note over C: Phase 1: Investigation
        C->>KG: memory_recall_kg("extinction")
        KG-->>C: related patterns, pitfalls
        C->>SP: task("abm", "[MODE:research]<br/>What causes extinction?")
        SP-->>C: "Adult survival = 0 in D14 scorer"
    end

    rect rgb(255, 245, 230)
        Note over C,D: Phase 2: Delegation
        C->>D: delegate_to_dispatcher(goal="Fix D14 scorer")
        Note over D: Creates new LangGraph stream
        D->>LF: root span (mode:dispatcher)
        D->>GW: start_session(feature="fix-d14")
        GW-->>D: session active
    end

    rect rgb(230, 255, 230)
        Note over D,SP: Phase 3: Implementation
        D->>SP: task("scoring", "[MODE:implementation]<br/>Fix D14 adult survival")
        SP->>GW: register_agent(role="scoring")
        SP->>GW: start_intent("fix D14 scorer")
        SP->>GW: edit_file("scorers/D14_adult_survival.py")
        GW-->>SP: edit accepted
        SP->>GW: check_inbox()
        SP->>SP: abm_test() → pass
        SP->>GW: send_message(to=orchestrator, "done")
        GW-->>D: proposal ready
    end

    rect rgb(245, 230, 255)
        Note over D: Phase 4: Finalization
        D->>GW: finalize_session(message="fix D14 scorer")
        GW-->>D: commit SHA abc123
        D-->>C: summary + commit SHA
    end

    rect rgb(255, 230, 230)
        Note over C,User: Phase 5: Report
        C->>User: "Fixed. D14 scorer now uses <= instead of <.<br/>Commit: abc123"
    end
```

## 3. Tool Matrix — Who Has What

```mermaid
graph LR
    subgraph CentinelaTools["🎭 Centinela Tools"]
        CT1["onboard_run_abm"]
        CT2["onboard_run_stage"]
        CT3["onboard_run_pipeline"]
        CT4["onboard_status"]
        CT5["onboard_diagnose"]
        CT6["onboard_list_components"]
        CT7["delegate_to_dispatcher"]
        CT8["onboard_ask_subagent"]
        CT9["memory_recall_kg"]
        CT10["ask_user"]
    end

    subgraph DispatcherTools["🎯 Dispatcher Tools"]
        DT1["pipeline_run_calibration"]
        DT2["pipeline_compare_scorecards"]
        DT3["abm_run"]
        DT4["abm_test"]
        DT5["abm_score"]
        DT6["web_search"]
        DT7["memory_recall_kg"]
        DT8["ask_user"]
        DT9["gawt_mcp_*<br/>(12 tools)"]
    end

    subgraph SpecialistTools["🔧 Specialist Tools"]
        ST1["gawt_mcp_*<br/>(edit/write/read)"]
        ST2["ask_user"]
        ST3["resolve_conflict"]
    end

    subgraph Shared["🤝 Shared"]
        SH1["memory_recall_kg"]
        SH2["ask_user"]
    end

    CT9 -.-> Shared
    DT7 -.-> Shared
    CT10 -.-> Shared
    DT8 -.-> Shared
```

## 4. Specialist Subagent Lifecycle (gawt workflow)

```mermaid
stateDiagram-v2
    [*] --> Registered: register_agent(role=)

    state "🟢 Active" as Active {
        Registered --> IntentSet: start_intent(intent=)
        IntentSet --> InboxChecked: check_inbox()
        InboxChecked --> Editing: edit_file() / write_file()
        Editing --> InboxChecked2: check_inbox()
        InboxChecked2 --> Testing: abm_test() / abm_score()
        Testing --> Editing: test fails → iterate
        Testing --> Done: test passes ✅
    }

    Done --> MessageSent: send_message(to=orchestrator)
    MessageSent --> Unregistered: unregister_agent()
    Unregistered --> [*]

    state "🔴 Conflict" as Conflict {
        InboxChecked --> ConflictDetected: peer edited same file
        ConflictDetected --> ConflictResolved: resolve_conflict()
        ConflictResolved --> InboxChecked
    }
```

## 5. Middleware Pipeline

```mermaid
graph TB
    subgraph Input["📨 Incoming Request"]
        REQ["User message / tool call"]
    end

    subgraph Middlewares["🔧 Middleware Stack"]
        direction TB
        OM["ObservabilityMiddleware<br/>• Langfuse spans<br/>• SessionLogger JSONL<br/>• mode: tag"]
        SVM["ScopeValidationMiddleware<br/>• edits_allow globs<br/>• file scope check"]
        ICM["InboxCheckMiddleware<br/>• peer conflict detection<br/>• check_inbox()"]
        SAOM["SubAgentObservabilityMiddleware<br/>• dispatch spans per specialist<br/>• agent:<role> tag"]
    end

    subgraph Execution["⚡ Execution"]
        LLM["LLM Call"]
        TOOL["Tool Execution"]
    end

    REQ --> OM
    OM --> SVM
    SVM --> ICM
    ICM --> SAOM
    SAOM --> LLM
    LLM --> TOOL
    TOOL --> OM
```

## 6. Session Lifecycle — JSONL Logging

```mermaid
graph LR
    A["session_start"] --> B["tool_call: gitagent_init"]
    B --> C["decision: session_start"]
    C --> D["tool_call: gitagent_spawn"]
    D --> E["dispatch: scoring"]
    E --> F["tool_call: task(scoring, ...)"]
    F --> G["proposal: edit D14"]
    G --> H["tool_call: gitagent_finalize"]
    H --> I["summary: composite 0.65→0.72"]
    I --> J["session_end"]

    style A fill:#e8f5e9
    style J fill:#ffebee
    style E fill:#e3f2fd
    style I fill:#fff3e0
```

## 7. Prompt Rendering — Dual-Mode Template

```mermaid
graph TB
    subgraph Template["📝 orchestrator.md.j2"]
        P["Preamble<br/>(shared)"]
        CU["{% if mode == 'centinela' %}<br/>Centinela Protocol<br/>• conversational REPL<br/>• explain-then-delegate<br/>• onboard tools"]
        DU["{% if mode == 'dispatcher' %}<br/>Dispatcher Protocol<br/>• decompose goal<br/>• start gawt session<br/>• dispatch specialists<br/>• monitor + finalize"]
        SA["Subagent Access<br/>(shared)"]
        KG["Knowledge Graph<br/>(shared)"]
    end

    C_OUT["🎭 Centinela Prompt"] 
    D_OUT["🎯 Dispatcher Prompt"]

    P --> CU
    P --> DU
    CU --> C_OUT
    DU --> D_OUT
    SA --> C_OUT
    SA --> D_OUT
    KG --> C_OUT
    KG --> D_OUT
```

## 8. gawt MCP — Session Isolation

```mermaid
graph TB
    subgraph gawtServer["🔧 gawt MCP Server (stdio)"]
        SS["start_session"]
        FA["finalize_session"]
        RA["register_agent"]
        EF["edit_file"]
        WF["write_file"]
        RF["read_file"]
        CI["check_inbox"]
        SM["send_message"]
        LA["list_agents"]
        LE["list_edits"]
    end

    subgraph Worktree["📂 Shared Worktree"]
        WT[".gitagent/worktree/"]
        DB[".gitagent/state.db<br/>(SQLite)"]
    end

    subgraph Agents["👥 Active Agents"]
        ORCH["🎭 Orchestrator<br/>(read-only)"]
        SP1["🔬 abm"]
        SP2["📊 scoring"]
        SP3["📥 ingest"]
    end

    SS --> WT
    FA --> WT
    RA --> DB
    EF --> WT
    WF --> WT
    RF --> WT
    CI --> DB
    SM --> DB
    LA --> DB

    ORCH -->|"read_file only"| RF
    SP1 -->|"edit_file"| EF
    SP2 -->|"edit_file"| EF
    SP3 -->|"write_file"| WF
```

## 9. Complete Component Map

```mermaid
graph TB
    classDef orch fill:#1565c0,color:#fff,stroke:#0d47a1
    classDef mode fill:#2e7d32,color:#fff,stroke:#1b5e20
    classDef spec fill:#e65100,color:#fff,stroke:#bf360c
    classDef tool fill:#6a1b9a,color:#fff,stroke:#4a148c
    classDef infra fill:#00695c,color:#fff,stroke:#004d40
    classDef mw fill:#ad1457,color:#fff,stroke:#880e4f

    User["👤 User"]:::orch

    subgraph Janus["Janus Orchestrator System"]
        Factory["create_orchestrator(mode)"]:::orch

        C["🎭 Centinela<br/>REPL + user interaction"]:::mode
        D["🎯 Dispatcher<br/>goal-driven one-shot"]:::mode

        TPL["📝 orchestrator.md.j2<br/>Jinja2 dual-mode template"]:::tool

        subgraph ToolSets["Tool Sets"]
            CTOOLS["Centinela Tools:<br/>onboard_*, delegate_to_dispatcher"]:::tool
            DTOOLS["Dispatcher Tools:<br/>pipeline_*, abm_*, gawt_mcp_*"]:::tool
        end

        subgraph MWSpec["Middleware"]
            OBS["ObservabilityMiddleware<br/>• Langfuse spans<br/>• mode: tag<br/>• SessionLogger"]:::mw
            SCOPE["ScopeValidationMiddleware<br/>• edits_allow globs"]:::mw
            INBOX["InboxCheckMiddleware<br/>• peer conflicts"]:::mw
            SAOBS["SubAgentObservabilityMiddleware<br/>• dispatch spans"]:::mw
        end

        subgraph Specialists["9 Specialist Subagents"]
            direction LR
            SP1["🔬 abm<br/>C++ engine, params"]:::spec
            SP2["📊 scoring<br/>D1-D17 scorers"]:::spec
            SP3["📥 ingest<br/>data pipelines"]:::spec
            SP4["⬇️ download<br/>dataset fetch"]:::spec
            SP5["🔮 prediction<br/>U-Net surrogate"]:::spec
            SP6["🏋️ training<br/>model training"]:::spec
            SP7["📂 data<br/>data exploration"]:::spec
            SP8["📚 commonlib<br/>shared utils"]:::spec
            SP9["🔄 self_improve<br/>meta-system edits"]:::spec
        end
    end

    subgraph External["External Services"]
        LLM["🧠 LLM Provider<br/>(OpenRouter / Anthropic / OpenAI)"]:::infra
        KG["🗂️ Neo4j<br/>Knowledge Graph"]:::infra
        LF["📈 Langfuse<br/>Tracing Dashboard"]:::infra
        GAWT["🔧 gawt MCP<br/>Session + Worktree Isolation"]:::infra
        PIPE["⚙️ mal-core Pipeline<br/>ABM, Scorers, Calibration"]:::infra
    end

    User -->|"REPL input"| C
    User -->|"--goal flag"| D
    Factory --> C
    Factory --> D
    TPL --> C
    TPL --> D
    C --> CTOOLS
    D --> DTOOLS
    CTOOLS --> C
    DTOOLS --> D

    C -->|"task() research"| Specialists
    C -->|"delegate_to_dispatcher()"| D
    D -->|"start_session + task()"| Specialists

    Specialists -->|"edit_file / write_file"| GAWT
    Specialists -->|"abm_run / test / score"| PIPE

    C -->|"memory_recall_kg()"| KG
    D -->|"memory_recall_kg()"| KG
    C -->|"Langfuse trace"| LF
    D -->|"Langfuse trace"| LF
    C -.->|"LLM calls"| LLM
    D -.->|"LLM calls"| LLM

    OBS -.-> C
    OBS -.-> D
    SCOPE -.-> Specialists
    INBOX -.-> Specialists
    SAOBS -.-> Specialists
```

---

## How to Use

Paste any of the Mermaid blocks into:
- GitHub markdown (renders automatically)
- [mermaid.live](https://mermaid.live) for interactive viewing
- Obsidian with the Mermaid plugin
- Any markdown renderer that supports Mermaid
