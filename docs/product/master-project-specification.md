# JARVIS
## Personal Finance Intelligence & Research Operating System

## Master Project Specification & Development Guideline

---

# 0. ROLE

You are the principal software architect and lead engineer responsible for designing and progressively implementing a highly scalable personal AI assistant platform called **JARVIS**.

JARVIS is initially being developed as a **personal finance intelligence and research operating system**, but the architecture must explicitly support expansion into additional domains of the user's life in the future.

The application must NOT be architected as a collection of hard-coded finance pages.

Instead, it must be architected as a **modular, configuration-driven, database-driven platform** in which:

- knowledge is stored as structured data;
- concepts are reusable;
- formulas are reusable;
- analytical workflows are reusable;
- research documents are indexed and linked to concepts;
- data sources are modular;
- users have personalized configurations;
- modules can be added without rewriting the application;
- AI capabilities can be added progressively;
- the same architecture can eventually support non-financial modules.

The initial domain is Finance.

The long-term objective is to create a highly personalized digital assistant that feels like a persistent analytical environment rather than a conventional SaaS dashboard.

---

# 1. CORE VISION

JARVIS should become the user's:

- finance knowledge base;
- CFA knowledge system;
- master's-level finance knowledge system;
- research-paper library;
- quantitative research environment;
- macroeconomic analysis environment;
- equity research environment;
- fixed-income analysis environment;
- alternative-investment analysis environment;
- quantitative-methods laboratory;
- financial-modeling environment;
- research workflow manager;
- personal finance learning environment;
- AI research assistant;
- eventually, broader personal assistant.

The central philosophy is:

> **Do not make the user remember where information lives. Make the system understand how information relates to one another.**

For example:

A user should be able to start from:

**Inflation**

and discover:

- definition;
- formulas;
- CFA concepts;
- master's concepts;
- relevant economic indicators;
- FRED series;
- historical relationships;
- relevant research papers;
- related concepts;
- analytical workflows;
- equity implications;
- fixed-income implications;
- alternative-investment implications;
- quantitative methods that can be applied;
- previous analyses performed by the user.

Likewise, starting from a workflow such as:

**Yield Curve Analysis**

should expose:

- required theoretical concepts;
- formulas;
- required datasets;
- FRED series;
- statistical methods;
- interpretation framework;
- relevant research papers;
- previous analyses;
- outputs;
- conclusions.

This interconnectedness is one of the most important design goals.

---

# 2. PRINCIPLES

The entire project must follow these principles.

## 2.1 Modular

Every major capability must be a module.

Examples:

- Theory
- Research
- Quantitative Methods
- Macro
- Equity Research
- Fixed Income
- Alternative Investments
- Portfolio Management
- Risk
- Data
- Documents
- Settings
- AI Assistant

New modules should be addable without major architectural changes.

---

## 2.2 Database-driven

Do not hard-code:

- CFA topics;
- definitions;
- formulas;
- concepts;
- research-paper metadata;
- workflow definitions;
- analytical methodologies;
- data-source metadata;
- user preferences;
- module structure.

These should live in the database whenever practical.

The frontend should consume structured data.

The goal is to make the application **content-configurable rather than code-configurable**.

---

## 2.3 Configuration-driven

Navigation, modules, subjects, subsections, workflows and capabilities should be represented through configuration/database structures.

For example:

```text
Module
  └── Section
       └── Subsection
            └── Content
```

Rather than:

```text
if page == "CFA Level 2"
    render this hard-coded page
```

The system should instead understand:

```text
module = CFA
level = Level II
topic = Fixed Income
subtopic = Term Structure
```

and render the relevant content dynamically.

---

## 2.4 API-first

Business logic should live in backend services/API layers rather than directly inside frontend components.

The application should eventually be able to support:

- web frontend;
- desktop application;
- mobile application;
- AI agents;
- automated jobs;
- external integrations.

without rewriting the core business logic.

---

## 2.5 AI-ready, but not AI-dependent

Do not build the application around an LLM.

The database and deterministic analytical engines are the source of truth.

AI should enhance:

- search;
- explanation;
- summarization;
- research;
- workflow selection;
- interpretation;
- recommendations;
- natural-language interaction.

AI must not replace:

- deterministic calculations;
- financial formulas;
- data validation;
- auditability;
- reproducibility.

For example:

If calculating WACC, the calculation engine must calculate WACC.

The LLM can explain the result.

---

## 2.6 Reproducible

Every research analysis should be reproducible.

An analysis should record:

- dataset;
- data source;
- data retrieval date;
- parameters;
- methodology;
- transformations;
- assumptions;
- model specification;
- output;
- version;
- user notes.

The user should be able to return months later and understand how an analysis was generated.

---

## 2.7 Auditable

Financial calculations should never become black boxes.

Whenever JARVIS produces a result, the user should be able to inspect:

**Input → Transformation → Formula/Method → Output**

For statistical models:

**Dataset → Cleaning → Specification → Estimation → Diagnostics → Result**

---

## 2.8 Personal

JARVIS should feel like the user's environment.

It should eventually learn:

- preferred terminology;
- preferred analytical approaches;
- current learning objectives;
- frequently used workflows;
- favorite datasets;
- previous research;
- saved concepts;
- notes;
- frequently accessed papers;
- current projects.

However, personal data must be explicitly separated from system-level data.

---

# 3. INITIAL APPLICATION STRUCTURE

The first major version should have the following top-level navigation.

```text
JARVIS
│
├── Dashboard
│
├── Theory
│   ├── Master's
│   ├── CFA
│   │   ├── Level I
│   │   ├── Level II
│   │   └── Level III
│   └── Research Papers
│
├── Research
│   ├── Flows
│   ├── Macro Analysis
│   ├── Equity Research
│   ├── Fixed Income
│   ├── Alternative Investments
│   ├── Portfolio Management
│   ├── Risk Management
│   └── Quantitative Methods
│
├── Data
│   ├── FRED
│   ├── Imported Data
│   ├── Saved Datasets
│   └── Data Dictionary
│
├── Research Library
│   ├── Papers
│   ├── Analyses
│   ├── Models
│   └── Notes
│
├── AI / JARVIS
│
└── Settings
    ├── Profile
    ├── Preferences
    ├── Modules
    ├── Data Sources
    ├── API Keys
    ├── Appearance
    ├── AI Configuration
    └── System Configuration
```

This is the initial information architecture.

It should NOT be treated as permanently fixed.

The architecture must allow future modules such as:

```text
Personal
├── Career
├── Learning
├── Projects
├── Fitness
├── Travel
├── Productivity
└── etc.
```

without changing the fundamental architecture.

---

# 4. DASHBOARD

The dashboard should become the user's command center.

Do not initially overload it with dozens of widgets.

Start with a modular dashboard.

Potential components:

### Quick Actions

- Start Research Flow
- Search Theory
- Upload Research Paper
- Import FRED Data
- Open Recent Analysis
- Ask JARVIS
- Browse CFA
- Browse Master's Theory

### Recent Activity

Show:

- recently viewed concepts;
- recent research papers;
- recent analyses;
- recent datasets;
- recently executed workflows.

### Continue Research

Show incomplete analyses.

### Personal Knowledge

Potential future metrics:

- concepts studied;
- papers read;
- workflows completed;
- analyses performed;
- topics recently explored.

### Watchlist

Eventually:

- macro indicators;
- equities;
- bonds;
- sectors;
- economic variables.

The dashboard must be widget-based so additional dashboard components can be added without restructuring the page.

---

# 5. THEORY MODULE

Theory is the foundational knowledge layer of JARVIS.

It should NOT merely be a document viewer.

It should be a structured knowledge graph.

---

# 5.1 Master's

Structure:

```text
Master's
│
├── Course 1
│   ├── Topic
│   ├── Topic
│   └── Topic
│
├── Course 2
│
├── Course 3
│
└── ...
```

Courses should be database records.

Each course should contain:

- name;
- institution;
- professor;
- semester;
- description;
- topics;
- notes;
- associated documents;
- concepts;
- formulas;
- research papers;
- workflows.

The user must be able to add new courses without modifying source code.

---

# 5.2 CFA

The CFA structure should be hierarchical.

```text
CFA
│
├── Level I
│   ├── Quantitative Methods
│   ├── Economics
│   ├── Financial Statement Analysis
│   ├── Corporate Issuers
│   ├── Equity Investments
│   ├── Fixed Income
│   ├── Derivatives
│   ├── Alternative Investments
│   └── Portfolio Management
│
├── Level II
│   └── ...
│
└── Level III
    └── ...
```

Do not hard-code this hierarchy.

Store:

```text
program
level
subject
topic
subtopic
concept
```

in the database.

This allows curriculum updates without application rewrites.

---

# 5.3 Knowledge Objects

The system should distinguish between different types of theoretical knowledge.

Potential object types:

```text
Concept
Definition
Formula
Framework
Methodology
Example
Assumption
Rule
Accounting Treatment
Statistical Method
Economic Relationship
Model
```

For example:

### Concept

CAPM

### Definition

Structured textual definition.

### Formula

```text
E(Ri) = Rf + βi(E(Rm) - Rf)
```

### Variables

```text
Rf = risk-free rate
β = beta
E(Rm) = expected market return
```

### Related concepts

- systematic risk;
- beta;
- equity risk premium;
- efficient markets.

### Related workflows

- equity valuation;
- portfolio construction;
- cost of equity.

### Related research papers

Papers tagged with CAPM.

This relational architecture is critical.

---

# 6. FORMULA DATABASE

Create a dedicated formula system.

Each formula should have:

- formula name;
- mathematical expression;
- description;
- variables;
- units;
- assumptions;
- applicable asset class;
- applicable methodology;
- CFA references;
- master's references;
- related concepts;
- related workflows;
- examples.

Example:

```text
Formula:
Gordon Growth Model

Expression:
P0 = D1 / (Ke - g)

Variables:
D1
Ke
g

Requirements:
Ke > g
```

The system should eventually support formula rendering using a mathematical renderer such as KaTeX or MathJax.

Do not store formulas only as plain text if structured representations are possible.

---

# 7. DEFINITION DATABASE

Definitions should be independently searchable.

Each definition should contain:

```text
term
definition
domain
difficulty
source
references
related concepts
related formulas
related workflows
user notes
```

Search should support:

- exact search;
- fuzzy search;
- semantic search;
- tags;
- domain;
- CFA level;
- Master's course;
- asset class.

---

# 8. RESEARCH PAPERS

Research Papers should be a first-class entity.

The user should be able to:

- drag and drop PDFs;
- upload papers;
- import papers;
- store metadata;
- search papers;
- tag papers;
- associate papers with concepts;
- associate papers with workflows;
- write notes;
- mark papers as read/unread;
- archive papers;
- delete papers.

---

# 8.1 Paper lifecycle

When a paper is uploaded:

```text
Upload
   ↓
Validate file
   ↓
Store original
   ↓
Extract metadata
   ↓
Extract text
   ↓
Create searchable representation
   ↓
Generate structured summary
   ↓
Identify concepts
   ↓
Identify methodologies
   ↓
Identify datasets
   ↓
Identify relevant workflows
   ↓
Save to Research Library
```

The original PDF should remain available.

The extracted text should be stored/indexed separately.

Do not destroy the original document.

---

# 8.2 Paper interface

Each paper should show:

### Metadata

- title;
- authors;
- year;
- journal;
- DOI;
- keywords.

### Abstract

### AI Summary

### Key Findings

### Methodology

### Data

### Variables

### Main Results

### Limitations

### Related Concepts

### Related Workflows

### User Notes

### PDF Viewer

### Research Connections

For example:

```text
This paper relates to:

CAPM
Business Cycles
Industry Rotation
Transaction Costs
Market Timing
Macroeconomic Regimes
```

---

# 8.3 Upload behavior

The user mentioned wanting uploaded papers to effectively disappear from the upload area after being processed.

Implement this as a proper workflow:

```text
Inbox
   ↓
Processing
   ↓
Processed
   ↓
Research Library
```

The upload inbox should automatically remove successfully processed documents.

However, never delete the actual paper.

The user can manually delete it using an explicit X/delete action.

Use soft deletion where possible.

---

# 9. RESEARCH MODULE

Research is where theory becomes application.

The Research section should be built around **flows**.

A Flow is a structured analytical workflow.

Examples:

```text
Macro Regime Analysis
Equity Valuation
Financial Statement Normalization
Credit Analysis
Yield Curve Analysis
Bond Valuation
Portfolio Optimization
Factor Analysis
Time Series Forecasting
Real Estate Valuation
Hedge Fund Analysis
Risk Analysis
Machine Learning Model Selection
```

---

# 10. FLOW ENGINE

This is one of the most important parts of the architecture.

Do NOT hard-code each workflow as a unique page.

Create a generic **Flow Engine**.

A flow should be represented as a structured object.

Example:

```text
Flow
├── Metadata
├── Objective
├── Required Inputs
├── Optional Inputs
├── Steps
├── Questions
├── Calculations
├── Statistical Methods
├── Validation Rules
├── Outputs
├── Visualizations
├── Interpretation Framework
├── Related Theory
└── Related Research
```

For example:

```text
Yield Curve Analysis
```

could contain:

```text
Step 1
Select yield curve

Step 2
Select maturities

Step 3
Calculate:
- slope
- curvature
- level

Step 4
Analyze:
- PCA
- historical percentiles
- changes
- regime shifts

Step 5
Interpret

Step 6
Generate report
```

The flow engine should execute these steps dynamically.

---

# 11. FLOW BUILDER

Eventually, the application should allow the user to create custom flows.

For example:

```text
Create Flow

Name:
Macro Recession Signal

Inputs:
- unemployment
- CPI
- GDP
- yield curve
- credit spreads

Methods:
- z-score
- rolling average
- PCA
- logistic regression

Output:
- recession probability
- charts
- interpretation
```

This is where the platform becomes much more powerful than a static finance website.

---

# 12. MACROECONOMIC ANALYSIS

Create a dedicated Macro Analysis module.

Initial data provider:

**FRED**

The application should allow the user to configure their FRED API key securely.

Never hard-code API keys.

Never store API keys in frontend code.

Use secure environment variables/secrets management.

---

# 12.1 FRED integration

Build a generic data-provider abstraction.

For example:

```text
DataProvider
    ├── FRED
    ├── CSV
    ├── Excel
    └── Future Providers
```

The application should not depend directly on FRED throughout the codebase.

Instead:

```text
Research Flow
      ↓
Data Service
      ↓
Provider Interface
      ↓
FRED
```

This means another provider can eventually be added without rewriting research flows.

---

# 12.2 FRED functionality

Allow:

- search series;
- retrieve series;
- inspect metadata;
- select date range;
- frequency;
- transformations;
- percentage changes;
- log transformations;
- rolling averages;
- growth rates;
- spreads;
- z-scores;
- normalization;
- resampling.

Users should be able to save frequently used series.

Example:

```text
Saved Macro Dataset

Name:
US Recession Dashboard

Series:
UNRATE
CPIAUCSL
GDP
FEDFUNDS
DGS10
DGS2
BAMLH0A0HYM2
```

---

# 13. DATA PIPELINE

Create a central data layer.

Conceptually:

```text
External Source
      ↓
Connector
      ↓
Raw Data
      ↓
Validation
      ↓
Normalization
      ↓
Processed Dataset
      ↓
Analysis
```

Separate:

### Raw Data

What the provider gave us.

### Processed Data

Cleaned/transformed data.

### Analysis Dataset

The exact dataset used in an analysis.

This separation is essential for reproducibility.

---

# 14. DATASET OBJECT

Every dataset should have metadata:

```text
dataset_id
name
description
provider
source_identifier
frequency
start_date
end_date
units
currency
retrieval_date
last_updated
transformations
version
```

This allows JARVIS to know exactly what data was used.

---

# 15. EQUITY RESEARCH MODULE

The Equity Research module should eventually support a full research workflow.

Potential structure:

```text
Equity Research
│
├── Company Overview
├── Industry Analysis
├── Macro Context
├── Financial Statements
├── Accounting Adjustments
├── Historical Analysis
├── Forecasting
├── Profitability
├── Growth
├── Capital Structure
├── Cost of Capital
├── Valuation
├── Relative Valuation
├── DCF
├── Scenario Analysis
├── Sensitivity Analysis
├── Risk
└── Investment Thesis
```

---

# 15.1 Financial statement normalization

Create a dedicated accounting adjustment engine.

It should distinguish:

```text
GAAP / IFRS reported value
        ↓
Adjustment
        ↓
Normalized value
```

Adjustments should be explicit and auditable.

Each adjustment should record:

- line item;
- original value;
- adjustment;
- adjusted value;
- reason;
- accounting framework;
- source;
- user assumption;
- timestamp.

Do NOT make silent adjustments.

---

# 15.2 Accounting framework

Support:

```text
IFRS
US GAAP
```

as structured configuration/data.

Do not encode every accounting rule directly into UI components.

Use:

```text
Accounting Rule
├── Framework
├── Topic
├── Condition
├── Treatment
├── Exception
├── Source
└── Notes
```

This allows accounting knowledge to evolve.

---

# 16. FIXED INCOME MODULE

Build a Fixed Income analytical framework around:

```text
Bond Mathematics
Yield Measures
Duration
Convexity
Term Structure
Yield Curve
Credit
Spread Analysis
Default Risk
Liquidity
Mortgage-Backed Securities
Structured Products
Portfolio Management
Risk
```

Potential workflows:

- bond pricing;
- yield-to-maturity;
- spot curve;
- forward rates;
- duration;
- modified duration;
- effective duration;
- convexity;
- spread analysis;
- credit analysis;
- scenario analysis;
- curve trades;
- portfolio immunization.

Every workflow should connect back to Theory.

---

# 17. ALTERNATIVE INVESTMENTS

Create modular submodules:

```text
Alternative Investments
├── Real Estate
├── Private Equity
├── Private Debt
├── Hedge Funds
├── Commodities
├── Infrastructure
└── Other
```

---

# 17.1 Real Estate

Potential flows:

- cap rate analysis;
- NOI analysis;
- DCF;
- property valuation;
- leverage;
- mortgage analysis;
- IRR;
- equity multiple;
- sensitivity analysis;
- scenario analysis.

---

# 17.2 Hedge Funds

Potential analysis:

- return analysis;
- volatility;
- Sharpe;
- Sortino;
- alpha;
- beta;
- factor exposure;
- drawdown;
- tail risk;
- liquidity;
- performance attribution.

---

# 18. PORTFOLIO MANAGEMENT

Eventually include:

```text
Portfolio Construction
Asset Allocation
Risk Budgeting
Factor Exposure
Performance Attribution
Optimization
Rebalancing
Scenario Analysis
Stress Testing
```

Potential methods:

- mean-variance optimization;
- Black-Litterman;
- risk parity;
- minimum variance;
- maximum diversification;
- factor models.

---

# 19. QUANTITATIVE METHODS

This should become one of the strongest parts of JARVIS.

The module should not simply provide statistical formulas.

It should help the user answer:

> **Which method should I use for this problem?**

---

# 19.1 Quantitative Method Selector

Create an interactive questionnaire.

Example:

```text
What is your objective?

[Forecast]
[Explain]
[Classify]
[Estimate relationship]
[Detect regime]
[Reduce dimensions]
[Optimize]
[Detect anomaly]
```

Then:

```text
What type of data?

[Time Series]
[Cross Section]
[Panel]
[Text]
[Image]
```

Then:

```text
What is the target variable?

Continuous
Binary
Categorical
Count
Time-to-event
None
```

Then:

```text
How much data do you have?

Small
Medium
Large
```

Then:

```text
Are observations independent?

Yes
No
Unknown
```

Then recommend methods.

Example:

```text
Recommended:
1. OLS
2. Ridge
3. Lasso

Why:
...

Potential problems:
- multicollinearity
- heteroskedasticity

Diagnostics:
...
```

The recommendation engine should be deterministic and explainable where possible.

---

# 19.2 Quantitative Methods Knowledge Base

Create structured entities for:

```text
Method
├── Objective
├── Data Requirements
├── Assumptions
├── Advantages
├── Limitations
├── Diagnostics
├── Hyperparameters
├── Interpretation
├── Related Methods
└── Finance Applications
```

Methods could eventually include:

### Econometrics

- OLS
- GLS
- WLS
- Logistic regression
- Probit
- Panel models
- Fixed effects
- Random effects
- IV
- GMM
- VAR
- VECM

### Time Series

- AR
- MA
- ARMA
- ARIMA
- SARIMA
- VAR
- GARCH
- EGARCH
- regime-switching models

### Machine Learning

- linear regression;
- ridge;
- lasso;
- elastic net;
- decision trees;
- random forest;
- gradient boosting;
- XGBoost;
- SVM;
- k-means;
- PCA;
- neural networks.

The application should not automatically encourage ML when a simpler econometric method is more appropriate.

---

# 20. TIME SERIES ANALYSIS

Create reusable analytical components for:

```text
Stationarity
ADF Test
KPSS
Autocorrelation
Partial Autocorrelation
Differencing
Cointegration
Granger Causality
Rolling Statistics
Structural Breaks
Volatility
Regime Detection
Forecasting
```

Each method should provide:

- theoretical explanation;
- assumptions;
- implementation;
- diagnostics;
- interpretation;
- finance applications.

---

# 21. MACHINE LEARNING WORKFLOW

The user should be able to import a dataset and go through:

```text
Dataset
   ↓
Data Audit
   ↓
Target Selection
   ↓
Feature Selection
   ↓
Missing Data
   ↓
Outlier Analysis
   ↓
Train/Test Split
   ↓
Time-Series Split if necessary
   ↓
Baseline Model
   ↓
Candidate Models
   ↓
Cross Validation
   ↓
Hyperparameter Tuning
   ↓
Evaluation
   ↓
Interpretation
   ↓
Model Comparison
```

Finance-specific safeguards are critical.

Never randomly shuffle time-series data unless explicitly justified.

The system should detect potential:

- look-ahead bias;
- survivorship bias;
- leakage;
- overfitting;
- data snooping.

---

# 22. RESEARCH PROJECT OBJECT

Every substantial analysis should become a Research Project.

Example:

```text
Research Project

Title:
Macroeconomic Regime-Based Industry Rotation

Objective:
...

Data:
...

Theory:
...

Methods:
...

Results:
...

Files:
...

Notes:
...

Conclusions:
...

Status:
Draft / Active / Complete / Archived
```

This allows JARVIS to become a persistent research environment.

---

# 23. RESEARCH ANALYSIS OBJECT

Every analysis should be saved.

Example:

```text
Analysis
├── Project
├── Dataset
├── Method
├── Parameters
├── Code/Execution
├── Results
├── Charts
├── Interpretation
└── Notes
```

This allows:

```text
"Show me everything I did on yield curves last year."
```

to become possible.

---

# 24. KNOWLEDGE GRAPH

One of the most important long-term features should be a relationship layer.

Entities:

```text
Concept
Formula
Paper
Course
CFA Topic
Dataset
Variable
Method
Workflow
Research Project
Analysis
```

Relationships:

```text
Concept → related_to → Concept
Concept → explained_by → Paper
Concept → used_in → Workflow
Workflow → requires → Dataset
Workflow → uses → Method
Method → related_to → Concept
Paper → studies → Concept
Analysis → uses → Workflow
Analysis → uses → Dataset
Course → teaches → Concept
CFA Topic → contains → Concept
```

This should eventually allow graph-based exploration.

For example:

```text
Macroeconomic Regimes
       ↓
Business Cycle
       ↓
Industry Cash Flow
       ↓
Industry Returns
       ↓
Sector Rotation
       ↓
Transaction Costs
       ↓
Portfolio Construction
```

---

# 25. SEARCH

Search should become a core feature.

Create one global search interface.

Search should cover:

```text
Theory
Concepts
Definitions
Formulas
Papers
Datasets
Variables
Flows
Methods
Research Projects
Analyses
Notes
```

Eventually support semantic search.

For example:

> "How can I estimate whether the yield curve predicts recessions?"

could return:

- relevant concepts;
- formulas;
- FRED variables;
- statistical methods;
- research papers;
- available workflows.

---

# 26. JARVIS AI ASSISTANT

JARVIS should sit on top of the structured system.

The assistant should have tools such as:

```text
search_knowledge
get_concept
get_formula
search_papers
search_workflows
search_methods
retrieve_dataset
run_analysis
create_analysis
save_note
create_research_project
```

The AI should use these tools instead of hallucinating information.

---

# 26.1 Contextual AI

The AI should know what page the user is currently on.

For example, if the user is viewing:

```text
CFA → Fixed Income → Duration
```

and asks:

> "How would I use this in practice?"

JARVIS should understand the context.

It can answer using:

- duration theory;
- related formulas;
- fixed-income workflows;
- saved analyses;
- relevant papers.

---

# 26.2 Research AI

If the user is inside a research flow, the AI should have access to:

- selected dataset;
- selected variables;
- workflow steps;
- current results;
- relevant theory.

But the AI must distinguish:

```text
FACT
CALCULATION
INFERENCE
INTERPRETATION
OPINION
```

This distinction is especially important in finance.

---

# 27. PERSONALIZATION

Create a proper user configuration layer.

Potential settings:

```text
User
├── Profile
├── Finance Preferences
├── Learning Preferences
├── Research Preferences
├── UI Preferences
├── AI Preferences
└── Data Preferences
```

Examples:

### Finance preferences

- preferred currency;
- preferred accounting framework;
- preferred market;
- preferred terminology.

### Research preferences

- preferred significance level;
- default confidence interval;
- default estimation window;
- default chart style;
- default benchmark;
- preferred statistical methods.

### AI preferences

- response depth;
- technicality;
- explanation style;
- citation preference;
- aggressiveness of recommendations.

---

# 28. MULTI-USER ARCHITECTURE

Even if this starts as a single-user application, design it as multi-user.

Every user-owned object should eventually be associated with:

```text
user_id
```

Examples:

- notes;
- papers;
- datasets;
- analyses;
- research projects;
- preferences;
- API credentials.

System-wide knowledge can be shared.

User-specific knowledge remains private.

This enables a future:

```text
System Knowledge
       +
User Knowledge
```

architecture.

---

# 29. CONFIGURATION EXPORT / IMPORT

A major requirement is portability.

Create a configuration system that can export/import user configuration.

Example:

```text
jarvis-config.json
```

containing:

- enabled modules;
- navigation;
- preferences;
- default settings;
- workflow preferences;
- personal categories.

Do NOT export secrets such as API keys in plaintext.

A future user should be able to configure JARVIS without modifying source code.

---

# 30. MODULE REGISTRY

Create a module registry.

Conceptually:

```text
Module
├── id
├── name
├── description
├── icon
├── route
├── enabled
├── version
├── dependencies
├── permissions
└── configuration
```

This should allow:

```text
enable_module("fixed_income")
disable_module("alternative_investments")
```

without changing core application architecture.

---

# 31. DATABASE ARCHITECTURE

Use a relational SQL database as the primary source of structured truth.

PostgreSQL is strongly preferred for the initial architecture.

Potential core entities:

```text
users

modules
module_sections
module_items

courses
course_topics

programs
program_levels
subjects
topics
subtopics

concepts
definitions
formulas
formula_variables
methods
frameworks
rules

documents
research_papers
document_chunks
paper_authors
paper_tags

datasets
data_sources
data_series
dataset_series
data_observations

flows
flow_steps
flow_inputs
flow_outputs
flow_methods

research_projects
analyses
analysis_inputs
analysis_results
analysis_runs

notes
tags
entity_tags
entity_relationships

user_preferences
user_module_settings
api_credentials

audit_logs
```

Do not implement all tables immediately.

Design the schema first.

---

# 32. DATABASE DESIGN RULES

Use:

- UUIDs for primary keys;
- foreign keys;
- indexes;
- unique constraints;
- created_at;
- updated_at;
- soft deletion where appropriate;
- versioning where necessary.

Avoid:

- duplicated data;
- hard-coded IDs;
- giant JSON blobs containing the entire application state;
- business logic embedded inside database-specific hacks.

JSON/JSONB may be used where flexibility is valuable, especially for configurable workflow definitions, but should not become an excuse to avoid relational modeling.

---

# 33. SEARCH ARCHITECTURE

Start with PostgreSQL full-text search where appropriate.

Later consider:

```text
PostgreSQL
+
pgvector
```

for semantic search.

Do not introduce a separate vector database unless scale actually requires it.

The initial architecture should avoid unnecessary infrastructure.

---

# 34. DOCUMENT STORAGE

Do not store large PDFs directly inside relational tables unless there is a compelling reason.

Use:

```text
Database
→ metadata

Object storage/filesystem
→ original document
```

The database should store the document location and metadata.

---

# 35. DOCUMENT PROCESSING PIPELINE

Research-paper ingestion should eventually support:

```text
PDF
 ↓
Text Extraction
 ↓
Page Detection
 ↓
Metadata Extraction
 ↓
Section Detection
 ↓
Chunking
 ↓
Embedding
 ↓
Database Index
```

Preserve page numbers so the AI can cite the original paper accurately.

---

# 36. CITATIONS

Research answers should eventually support citations back to:

- page;
- section;
- paragraph;
- research paper;
- dataset;
- source.

For uploaded research papers, JARVIS should be able to say:

```text
According to the paper...
[Paper, p. 7]
```

rather than simply providing unsupported AI summaries.

---

# 37. SECURITY

Treat API keys and credentials as sensitive.

Never:

- expose API keys in frontend code;
- commit API keys;
- place secrets in Git;
- return secrets through ordinary API responses;
- log credentials.

Use:

```text
.env
secret manager
encrypted credentials
```

depending on deployment environment.

---

# 38. OBSERVABILITY

The application should eventually include:

- structured logging;
- error tracking;
- API request logging;
- analysis execution logs;
- database migration tracking;
- background-job monitoring.

Do not build excessive infrastructure during the MVP.

Create interfaces that allow observability to scale later.

---

# 39. BACKGROUND JOBS

Some operations should not block the UI.

Examples:

- PDF processing;
- embeddings;
- FRED data imports;
- large statistical analyses;
- ML training;
- report generation.

Use a background-job architecture when necessary.

The user should see:

```text
Processing...
```

and eventually:

```text
Completed
```

with errors surfaced clearly.

---

# 40. FRONTEND DESIGN

The interface should feel like a serious research workstation.

Avoid:

- excessive cards;
- meaningless dashboards;
- flashy animations;
- generic SaaS aesthetics;
- excessive gradients;
- unnecessary gamification.

Prioritize:

- information density;
- hierarchy;
- keyboard accessibility;
- fast navigation;
- clean typography;
- tables;
- charts;
- expandable panels;
- command palette;
- contextual navigation.

---

# 41. COMMAND PALETTE

Eventually support something similar to:

```text
Ctrl/Cmd + K
```

Commands:

```text
Search Theory
Search Papers
Open Flow
Import Data
Start Analysis
Open Dataset
Ask JARVIS
Create Note
Create Research Project
```

This should become one of the fastest ways to interact with the application.

---

# 42. THREE-PANEL RESEARCH INTERFACE

For complex workflows, consider:

```text
LEFT
Navigation / Flow Steps

CENTER
Main Analysis

RIGHT
JARVIS / Theory / Context
```

For example:

```text
┌──────────────┬──────────────────────────┬────────────────────┐
│ Flow         │ Analysis                 │ JARVIS             │
│              │                          │                    │
│ 1. Dataset   │ Chart                    │ Relevant Theory    │
│ 2. Clean     │                          │                    │
│ 3. Model     │ Results                  │ Formula            │
│ 4. Diagnose  │                          │                    │
│ 5. Interpret │                          │ Research Papers    │
└──────────────┴──────────────────────────┴────────────────────┘
```

This would make JARVIS feel substantially more integrated than a chatbot bolted onto the side.

---

# 43. THEORY ↔ RESEARCH CONNECTION

This connection is fundamental.

Every research flow should be able to expose:

```text
Relevant Theory
```

For example:

### DCF Flow

Show:

- time value of money;
- WACC;
- FCFF;
- FCFE;
- terminal value;
- growth;
- capital structure.

### Yield Curve Flow

Show:

- spot rates;
- forward rates;
- duration;
- convexity;
- term structure;
- expectations hypothesis.

### Regression Flow

Show:

- OLS;
- assumptions;
- heteroskedasticity;
- autocorrelation;
- multicollinearity;
- statistical inference.

The user should never have to manually search the Theory section to understand a workflow.

---

# 44. THEORY → RESEARCH

The reverse connection should also work.

If the user is reading:

```text
CAPM
```

JARVIS should show:

```text
Used in:
- Cost of Equity
- Portfolio Analysis
- Performance Attribution
- Factor Analysis
```

and allow the user to launch those flows.

---

# 45. RESEARCH PAPER → THEORY

If a paper references:

```text
Fama-French
```

the paper should connect to:

```text
Fama-French Model
```

in the Theory database.

This allows knowledge to accumulate over time.

---

# 46. DATA → THEORY

Variables should also be connected to concepts.

For example:

```text
UNRATE
```

could connect to:

```text
Unemployment
Labor Market
Business Cycle
Phillips Curve
Recession Analysis
```

This creates a powerful bridge between abstract knowledge and real-world data.

---

# 47. ANALYSIS REPORT GENERATION

Eventually allow the user to generate a research report from an analysis.

Example:

```text
Research Report

1. Objective
2. Data
3. Methodology
4. Theoretical Motivation
5. Results
6. Diagnostics
7. Interpretation
8. Limitations
9. Conclusion
```

The report should be generated from structured analysis objects rather than simply asking an LLM to write a report from scratch.

---

# 48. VERSIONING

Important research objects should support versions.

For example:

```text
Analysis v1
Analysis v2
Analysis v3
```

If the user changes:

- dataset;
- methodology;
- sample;
- parameters;

the system should be able to preserve previous versions.

---

# 49. EXPERIMENT TRACKING

For quantitative research, support experiment tracking.

Example:

```text
Experiment 001
Model: OLS
Variables: X1 X2 X3
Sample: 2000-2025
R²: ...
AIC: ...
BIC: ...

Experiment 002
Model: Ridge
...
```

This becomes extremely valuable once ML and quantitative research expand.

---

# 50. TESTING

Do not build the application without tests.

At minimum:

### Unit tests

- formulas;
- transformations;
- validation;
- calculations.

### Integration tests

- database;
- API;
- FRED;
- document ingestion.

### End-to-end tests

Critical user workflows.

Financial calculations should have especially strong test coverage.

For example:

```text
Given:
Face Value = 1000
Coupon = 5%
Yield = 4%

Expected:
Price = ...
```

---

# 51. FINANCIAL CALCULATION ENGINE

Create a reusable calculation engine.

Do not duplicate financial mathematics throughout workflows.

For example:

```text
FinancialMath
├── TVM
├── Bond Pricing
├── Duration
├── Convexity
├── NPV
├── IRR
├── WACC
├── DCF
├── Portfolio Statistics
└── Risk Metrics
```

Flows call these functions.

This ensures consistency.

---

# 52. STATISTICAL ENGINE

Similarly create:

```text
StatisticsEngine
├── Descriptive Statistics
├── Regression
├── Correlation
├── Time Series
├── Hypothesis Testing
├── PCA
├── Optimization
└── ML
```

Do not bury statistical calculations inside frontend components.

---

# 53. PYTHON ANALYTICS SERVICE

Python is strongly preferred for sophisticated quantitative analysis.

Potential architecture:

```text
Frontend
   ↓
Backend API
   ↓
Analysis Service
   ↓
Python Quant Engine
   ↓
Results
```

The Python engine should return structured results rather than only rendered plots.

For example:

```json
{
  "model": "OLS",
  "coefficients": {},
  "statistics": {},
  "diagnostics": {},
  "predictions": {}
}
```

Charts can then be rendered by the frontend.

---

# 54. TECHNOLOGY DIRECTION

Choose technologies based on maintainability rather than trendiness.

A reasonable architecture could be:

### Frontend

React + TypeScript

Potential framework:

Next.js

### Backend

Python-based API

Potential:

FastAPI

### Database

PostgreSQL

### Analytics

Python

Potential libraries:

- pandas;
- NumPy;
- SciPy;
- statsmodels;
- scikit-learn.

### Charts

A mature interactive charting library.

### Formula rendering

KaTeX or MathJax.

### Search

PostgreSQL FTS initially.

Potential pgvector later.

### Background jobs

Introduce only when required.

### Deployment

Containerized architecture.

Use Docker.

The exact technology choices should be validated before implementation, but the architecture must maintain these separation principles regardless of the final stack.

---

# 55. API STRUCTURE

Organize APIs by domain rather than by frontend page.

Example:

```text
/api/v1/users
/api/v1/modules
/api/v1/theory
/api/v1/concepts
/api/v1/formulas
/api/v1/methods
/api/v1/papers
/api/v1/datasets
/api/v1/data-sources
/api/v1/flows
/api/v1/analyses
/api/v1/research-projects
/api/v1/search
/api/v1/ai
```

Use versioned APIs.

---

# 56. PROJECT DIRECTORY STRUCTURE

Use a clean monorepo or equivalent architecture.

Potential structure:

```text
jarvis/
│
├── apps/
│   ├── web/
│   └── api/
│
├── packages/
│   ├── shared-types/
│   ├── finance-engine/
│   ├── statistics-engine/
│   ├── flow-engine/
│   └── ui/
│
├── services/
│   ├── document-processing/
│   ├── analytics/
│   └── background-jobs/
│
├── database/
│   ├── migrations/
│   ├── seeds/
│   └── schemas/
│
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── workflows/
│   └── decisions/
│
├── tests/
│
└── infrastructure/
```

The exact structure can change after architectural review.

---

# 57. DATABASE MIGRATIONS

All schema changes must be migration-based.

Never manually modify production databases.

Every schema change should have:

```text
migration
↓
test
↓
deployment
```

Seed data should be separate from migrations.

---

# 58. SEED DATA

The application should include initial seed data for:

- modules;
- CFA structure;
- initial concepts;
- formulas;
- quantitative methods;
- workflows.

However, seed data should be treated as data.

It should be possible to update it without rewriting the application.

---

# 59. ADMIN / CONTENT MANAGEMENT

Eventually create an internal admin interface.

The user should be able to:

```text
Create Concept
Edit Concept
Create Formula
Edit Formula
Create Workflow
Edit Workflow
Create Method
Edit Method
Create Module
Edit Module
```

This is important because the user should not need to ask Claude Code to modify the code every time they want to add a concept or workflow.

---

# 60. FLOW DEFINITION FORMAT

Create a structured flow definition.

Example conceptually:

```json
{
  "id": "yield_curve_analysis",
  "name": "Yield Curve Analysis",
  "inputs": [],
  "steps": [
    {
      "type": "dataset_selector"
    },
    {
      "type": "transformation"
    },
    {
      "type": "calculation"
    },
    {
      "type": "statistical_test"
    },
    {
      "type": "visualization"
    },
    {
      "type": "interpretation"
    }
  ]
}
```

The flow engine should interpret this configuration.

Do not create a unique React page for every flow.

---

# 61. COMPONENT LIBRARY

Create reusable components:

```text
ConceptCard
FormulaCard
MethodCard
PaperCard
DatasetCard
FlowCard
AnalysisCard
Chart
DataTable
Metric
SearchBar
CommandPalette
UploadZone
ResearchSidebar
TheorySidebar
JarvisPanel
```

These should be reusable across modules.

---

# 62. USER EXPERIENCE PRINCIPLE

The user should always know:

```text
Where am I?
What am I looking at?
Why is it relevant?
What can I do next?
```

For example:

```text
Theory
→ CFA
→ Level II
→ Fixed Income
→ Term Structure
```

At the bottom:

```text
Related Research Flows
[Yield Curve Analysis]
[Forward Rate Analysis]
[Credit Spread Analysis]
```

And:

```text
Related Papers
...
```

This creates a continuous navigation loop.

---

# 63. "ASK JARVIS" EVERYWHERE

Eventually every major page should have contextual access to JARVIS.

Examples:

On a formula:

> "Explain this intuitively."

On a dataset:

> "What economic relationships should I investigate?"

On a paper:

> "How does this relate to my industry rotation research?"

On a regression:

> "Are these diagnostics sufficient?"

On an equity:

> "What accounting adjustments should I consider?"

The AI should receive page-specific context automatically.

---

# 64. KNOWLEDGE MATURITY

Do not assume all information has the same authority.

Each knowledge object should potentially have:

```text
Source
Confidence
Status
Last Reviewed
Author
Version
```

Possible statuses:

```text
Draft
Verified
System
User
Imported
AI-generated
```

AI-generated knowledge should never silently become authoritative knowledge.

---

# 65. SOURCE HIERARCHY

For finance, the system should distinguish between:

```text
Primary Sources
Academic Research
Professional Standards
CFA Material
University Material
Secondary Sources
AI-generated explanations
User Notes
```

The user should be able to see where a piece of knowledge came from.

---

# 66. NO HALLUCINATION POLICY

JARVIS must not invent:

- formulas;
- citations;
- research findings;
- accounting rules;
- data;
- statistical results.

If the system does not know, it should say:

```text
Insufficient information.
```

and explain what is missing.

---

# 67. DATA QUALITY

Every imported dataset should have a quality layer.

Potential checks:

- missing observations;
- duplicates;
- frequency consistency;
- outliers;
- date gaps;
- unit mismatches;
- currency mismatches;
- revisions;
- stale observations.

The user should be able to inspect data-quality warnings before running an analysis.

---

# 68. FINANCE-SPECIFIC WARNINGS

Because this is a research system, JARVIS should eventually identify common analytical problems.

Examples:

```text
Potential Look-Ahead Bias
Potential Survivorship Bias
Potential Data Leakage
Small Sample
Multiple Testing
Multicollinearity
Heteroskedasticity
Autocorrelation
Non-Stationarity
Overfitting
Parameter Instability
Structural Break
```

These warnings should be informative rather than obstructive.

---

# 69. PERSONAL RESEARCH MEMORY

JARVIS should eventually remember the user's research history.

For example:

```text
You previously analyzed:
US recession indicators
using:
UNRATE, T10Y2Y, HY spreads
```

Then, when starting another macro analysis, JARVIS could suggest:

```text
You have previously used these variables.
Reuse previous dataset?
```

This should be based on stored research objects, not vague AI memory.

---

# 70. PROJECT GRAPH

Eventually create a visual relationship graph.

Example:

```text
Research Project
       │
       ├── Theory
       │    ├── Concept
       │    └── Formula
       │
       ├── Data
       │    ├── FRED
       │    └── Dataset
       │
       ├── Methods
       │
       ├── Papers
       │
       └── Analyses
```

This could become a very powerful interface for long-term research.

---

# 71. IMPLEMENTATION PHILOSOPHY

Do NOT build everything at once.

The project must be implemented incrementally.

The first objective is to establish the architecture.

---

# 72. PHASE 0 — ARCHITECTURE

Before writing significant application code:

1. Inspect the repository.
2. Determine existing project state.
3. Propose final architecture.
4. Identify technology choices.
5. Design database schema.
6. Define module architecture.
7. Define API architecture.
8. Define flow architecture.
9. Define authentication strategy.
10. Define storage strategy.
11. Define testing strategy.
12. Identify risks.

Create documentation before large implementation.

Do NOT blindly start generating dozens of files.

---

# 73. PHASE 1 — FOUNDATION

Build:

- application shell;
- authentication;
- database;
- migrations;
- module registry;
- user configuration;
- navigation;
- theme;
- command palette;
- global search skeleton.

At the end of Phase 1, the application should feel like a real platform even though functionality is limited.

---

# 74. PHASE 2 — THEORY

Build:

- Master's hierarchy;
- CFA hierarchy;
- concepts;
- definitions;
- formulas;
- methods;
- theory search;
- relationships.

This establishes the knowledge layer.

---

# 75. PHASE 3 — RESEARCH PAPERS

Build:

- drag-and-drop upload;
- document storage;
- PDF processing;
- metadata;
- paper library;
- search;
- tags;
- notes;
- related concepts.

This establishes the research library.

---

# 76. PHASE 4 — DATA

Build:

- FRED connector;
- API-key configuration;
- dataset management;
- data-series search;
- data import;
- transformations;
- data quality;
- saved datasets.

---

# 77. PHASE 5 — FLOW ENGINE

Build the generic flow engine before building dozens of finance flows.

Create 2–3 high-quality flows first.

Recommended initial flows:

1. Macro Time-Series Analysis
2. Equity DCF
3. Yield Curve Analysis

These should be used to prove that the flow architecture is genuinely reusable.

---

# 78. PHASE 6 — QUANTITATIVE ENGINE

Build:

- descriptive statistics;
- regression;
- time-series analysis;
- diagnostics;
- visualization;
- model comparison;
- ML foundations.

Then create the Method Selector.

---

# 79. PHASE 7 — FINANCE MODULES

Expand:

- Equity Research;
- Fixed Income;
- Alternative Investments;
- Portfolio Management;
- Risk.

Each module should reuse:

- theory;
- formulas;
- datasets;
- flow engine;
- calculation engine;
- quantitative engine.

---

# 80. PHASE 8 — JARVIS AI

Only after the structured system is functioning should the AI layer become deeply integrated.

JARVIS should gain tools for:

- search;
- retrieval;
- research;
- calculations;
- workflow execution;
- document analysis;
- report generation.

---

# 81. PHASE 9 — PERSONAL INTELLIGENCE

Eventually add:

- personal research history;
- recommendations;
- learning paths;
- personalized workflow suggestions;
- knowledge gaps;
- frequently used concepts;
- research continuity.

---

# 82. PHASE 10 — EXPANSION BEYOND FINANCE

Once the finance architecture is mature, additional personal modules should be possible.

Examples:

```text
Career
Learning
Projects
Productivity
Travel
Personal Knowledge
```

These should reuse the same platform concepts:

```text
Module
Knowledge
Documents
Flows
Projects
AI
Personalization
```

---

# 83. DEVELOPMENT RULE

At every implementation stage ask:

> "If this application had 100,000 users and 1,000 modules, would this architectural decision still make sense?"

Do not actually optimize prematurely for 100,000 users.

Instead, avoid architectural decisions that would make scaling painful later.

---

# 84. AVOID OVERENGINEERING

Scalability does NOT mean:

- microservices everywhere;
- Kubernetes immediately;
- five databases;
- complicated event buses;
- distributed systems;
- unnecessary cloud infrastructure.

Start with a modular monolith if appropriate.

A strong modular monolith with:

```text
PostgreSQL
Backend API
Frontend
Python analytics service
Object storage
```

is preferable to a premature distributed architecture.

The architecture should make future extraction into services possible.

---

# 85. DOCUMENT ARCHITECTURAL DECISIONS

Maintain:

```text
docs/architecture/decisions/
```

Each major decision should be recorded.

Example:

```text
ADR-001:
Why PostgreSQL?

ADR-002:
Why modular monolith?

ADR-003:
Why configurable flows?

ADR-004:
Why separate raw and processed data?

ADR-005:
Why PostgreSQL + pgvector instead of a separate vector database?
```

This prevents architectural drift.

---

# 86. CODING STANDARDS

Use:

- strict typing;
- clear naming;
- small modules;
- reusable functions;
- domain separation;
- documentation;
- tests;
- validation.

Avoid:

- massive components;
- duplicated logic;
- magic numbers;
- hard-coded financial rules;
- hidden state;
- frontend business logic;
- unnecessary dependencies.

---

# 87. ERROR HANDLING

Errors must be understandable.

Bad:

```text
500 Internal Server Error
```

Better:

```text
FRED data retrieval failed.

Reason:
Invalid API key.

Action:
Check Settings → Data Sources → FRED.
```

For research workflows, distinguish:

```text
Data Error
Calculation Error
Validation Error
Model Error
Configuration Error
System Error
```

---

# 88. LOADING STATES

Every asynchronous process needs clear states.

Example:

```text
Idle
Loading
Processing
Success
Warning
Error
```

Do not leave users wondering whether the application is doing something.

---

# 89. PERFORMANCE

Prioritize:

- lazy loading;
- pagination;
- database indexes;
- caching where appropriate;
- background processing;
- efficient queries;
- avoiding unnecessary API calls.

Do not load the entire Theory database into the browser.

---

# 90. ACCESSIBILITY

Build with accessibility from the beginning.

Support:

- keyboard navigation;
- semantic HTML;
- screen readers;
- focus states;
- accessible charts where possible;
- sufficient contrast;
- scalable typography.

---

# 91. RESPONSIVE DESIGN

Desktop is the primary environment because this is a research workstation.

However, the architecture should remain responsive.

Mobile can eventually focus on:

- search;
- notes;
- reading;
- AI;
- quick research.

Complex quantitative workflows can remain desktop-first.

---

# 92. FUTURE PLUGIN ARCHITECTURE

Eventually modules may become installable packages.

Conceptually:

```text
JARVIS Core
     │
     ├── Finance
     ├── Career
     ├── Learning
     └── Other
```

A module should define:

```text
manifest
routes
database entities
permissions
flows
UI components
AI tools
```

Do not implement a complete plugin marketplace now.

But do not architect the system so that plugins become impossible later.

---

# 93. PERMISSIONS

Even as a personal application, establish permission concepts.

Potential future roles:

```text
Owner
Admin
Editor
Viewer
```

Potential resource permissions:

```text
read
write
execute
delete
share
```

This becomes important if the application eventually supports collaborators.

---

# 94. BACKUPS

The application should eventually support:

- database backups;
- document backups;
- configuration export;
- research project export.

The user's research should never be trapped inside the application.

---

# 95. EXPORT

Users should eventually be able to export:

```text
PDF
CSV
Excel
JSON
Markdown
```

depending on the object.

For example:

```text
Analysis → PDF
Dataset → CSV
Research Project → JSON/Markdown
Notes → Markdown
```

---

# 96. INITIAL SUCCESS CRITERIA

The first meaningful milestone is NOT:

> "The app has 100 finance features."

It is:

> "I can open JARVIS and move naturally from theory to research to data to analysis without feeling like I am using separate applications."

For example:

```text
CFA → Fixed Income → Yield Curve
       ↓
Related Concepts
       ↓
Yield Curve Analysis Flow
       ↓
Select FRED Data
       ↓
Run Analysis
       ↓
Visualize Results
       ↓
Ask JARVIS
       ↓
Save Analysis
       ↓
Link Research Papers
```

If this works beautifully, the architecture is working.

---

# 97. FIRST MVP

The first MVP should contain only:

### Core

- authentication;
- PostgreSQL;
- module registry;
- settings;
- navigation;
- search.

### Theory

- concepts;
- definitions;
- formulas;
- CFA hierarchy;
- Master's hierarchy.

### Research

- research paper upload;
- paper library;
- basic metadata;
- notes.

### Data

- FRED integration;
- saved datasets.

### Flows

- generic flow engine;
- one macro flow;
- one equity flow;
- one fixed-income flow.

### AI

- contextual search/explanation;
- basic JARVIS assistant.

Do NOT build every CFA topic or every finance workflow before proving the architecture.

---

# 98. WHAT NOT TO DO

Do NOT:

1. hard-code CFA pages;
2. hard-code workflows into individual React pages;
3. put financial calculations inside UI components;
4. expose API keys;
5. make the LLM the source of truth;
6. create a separate database for every module;
7. create microservices prematurely;
8. build 50 flows before testing the Flow Engine;
9. duplicate formulas;
10. store all knowledge in giant JSON files;
11. create a separate implementation for every data provider;
12. mix user data and system knowledge;
13. destroy original research papers after processing;
14. silently modify financial statements;
15. silently transform datasets;
16. perform ML without leakage checks;
17. randomly split time-series data by default;
18. make AI-generated research indistinguishable from verified knowledge;
19. optimize infrastructure before validating the product;
20. make architectural decisions that require rewriting the application every time a module is added.

---

# 99. DEFINITION OF DONE

A feature is not considered complete simply because the UI works.

A feature is complete when:

```text
Database
+
Backend
+
Frontend
+
Validation
+
Error Handling
+
Tests
+
Documentation
```

are appropriately implemented.

For analytical features also require:

```text
Reproducibility
+
Auditability
+
Numerical Tests
```

---

# 100. HOW YOU SHOULD WORK WITH ME

Treat me as the product owner.

Do not make major architectural decisions silently.

When a decision has meaningful long-term consequences:

1. identify the decision;
2. explain the tradeoffs;
3. recommend an approach;
4. wait for approval when appropriate.

For small implementation decisions, use engineering judgment.

Do not constantly ask for permission for trivial implementation details.

---

# 101. DEVELOPMENT PROTOCOL

Before each major phase:

### Step 1
Explain what will be built.

### Step 2
Identify dependencies.

### Step 3
Show the database changes.

### Step 4
Show the architecture changes.

### Step 5
Implement.

### Step 6
Run tests.

### Step 7
Review for architectural debt.

### Step 8
Document the changes.

### Step 9
Report:

```text
Implemented
Tested
Known Issues
Technical Debt
Next Recommended Step
```

---

# 102. ARCHITECTURAL REVIEW QUESTIONS

Before implementing a feature, ask:

### Data

Does this belong in the database?

### Reuse

Could another module use this?

### Configuration

Should this be configurable?

### Scalability

Will adding 100 similar entities require code changes?

### AI

Does this need AI or should it be deterministic?

### Research

Can the result be reproduced?

### Security

Does this involve sensitive information?

### Personalization

Should this be user-specific or system-wide?

### Versioning

Could the underlying information change over time?

### Dependencies

Does this introduce an unnecessary external dependency?

---

# 103. LONG-TERM JARVIS ARCHITECTURE

The ultimate architecture should look conceptually like this:

```text
                         ┌──────────────────────┐
                         │       JARVIS         │
                         │     AI INTERFACE     │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │   KNOWLEDGE LAYER    │
                         │                      │
                         │ Concepts             │
                         │ Definitions          │
                         │ Formulas             │
                         │ Methods              │
                         │ Papers               │
                         │ Relationships        │
                         └──────────┬───────────┘
                                    │
          ┌─────────────────────────┼────────────────────────┐
          │                         │                        │
┌─────────▼─────────┐    ┌──────────▼─────────┐   ┌─────────▼─────────┐
│     THEORY        │    │     RESEARCH       │   │       DATA        │
│                   │    │                    │   │                   │
│ Master's          │    │ Flows              │   │ FRED              │
│ CFA               │    │ Equity             │   │ Imported Data     │
│ Papers            │    │ Fixed Income       │   │ Saved Datasets    │
│ Concepts          │    │ Alternatives       │   │ Data Dictionary   │
│ Formulas          │    │ Quant              │   │                   │
└─────────┬─────────┘    └──────────┬─────────┘   └─────────┬─────────┘
          │                         │                        │
          └─────────────────────────┼────────────────────────┘
                                    │
                         ┌──────────▼───────────┐
                         │   ANALYTICS ENGINE   │
                         │                      │
                         │ Finance Mathematics  │
                         │ Statistics           │
                         │ Econometrics         │
                         │ Time Series          │
                         │ Machine Learning     │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │  RESEARCH MEMORY     │
                         │                      │
                         │ Projects             │
                         │ Analyses             │
                         │ Experiments          │
                         │ Notes                │
                         │ History              │
                         └──────────────────────┘
```

---

# 104. THE MOST IMPORTANT ARCHITECTURAL IDEA

JARVIS should not think in terms of pages.

It should think in terms of:

```text
ENTITIES
RELATIONSHIPS
KNOWLEDGE
DATA
METHODS
FLOWS
ANALYSES
USERS
CONTEXT
```

The interface is simply one way of interacting with these objects.

This is what will allow the system to grow.

---

# 105. FINAL INSTRUCTION TO CURSOR

Before writing significant code, inspect the current repository and produce a concise but technically detailed **Architecture Proposal** containing:

1. recommended technology stack;
2. application architecture;
3. database ERD;
4. core entities;
5. relationships;
6. module system;
7. flow engine architecture;
8. data-provider architecture;
9. document-processing architecture;
10. AI/tool architecture;
11. authentication architecture;
12. security model;
13. folder structure;
14. testing strategy;
15. migration strategy;
16. deployment strategy;
17. MVP scope;
18. future scalability considerations;
19. major architectural risks;
20. recommended implementation sequence.

Do not start by implementing the entire application.

First establish the foundation.

After the architecture is approved, implement the system incrementally.

The guiding principle for every decision should be:

> **Build JARVIS as a platform, not as a collection of pages.**

The finance module is the first domain.

It is not the final architecture.

The ultimate objective is a persistent, intelligent, personalized operating system for the user's knowledge, research, analysis and eventually broader life.

Build the foundation accordingly.