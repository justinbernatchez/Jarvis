# JARVIS Numerical Correctness Policy

- Status: Phase 0 baseline
- Date: 2026-08-18
- Applies to: finance engine, statistics engine, transformations, flows,
  analyses, charts, and AI explanations of numerical results

## 1. Objective

JARVIS must prefer a transparent refusal over a plausible but unsupported
number. Every numerical result must make its inputs, conventions, method,
version, validation, and limitations inspectable.

The deterministic finance/statistics engines are authoritative for
calculations. UI code and AI models do not independently calculate or alter
results.

## 2. Classification of numerical output

Every output is classified as one of:

- **Exact calculation**: deterministic arithmetic under declared conventions.
- **Numerical estimate**: solver, optimization, interpolation, or statistical
  estimate subject to tolerance and convergence behavior.
- **Forecast**: model-based future estimate with uncertainty and evaluation
  context.
- **Diagnostic**: test statistic, warning, quality metric, or model check.
- **Visualization transform**: display-oriented aggregation that does not
  replace the underlying result.
- **Interpretation**: prose derived from recorded results; never a new
  calculation.

The classification is persisted with the result.

## 3. Numeric type policy

### Decimal domain

Use Python `Decimal` and PostgreSQL `numeric` for:

- money and accounting values;
- contractual cash flows;
- prices where exact decimal representation is required;
- fee/rate application governed by a rounding rule;
- user-entered financial assumptions;
- formula examples intended to reproduce by hand.

Decimal context and rounding mode are explicit at the engine boundary. Domain
functions do not silently inherit an ambient process-wide context.

### Binary floating-point domain

Use IEEE float64/NumPy arrays for:

- statistical estimation;
- linear algebra;
- optimization;
- time-series transforms;
- machine learning;
- large provider observation arrays where source precision does not justify
  decimal arithmetic.

Float outputs use tolerances and diagnostic checks. They are never compared
for exact equality in tests unless the algorithm guarantees it.

### Integer and rational domain

Use integers for counts, periods, basis points when explicitly modeled as
integral units, and identifiers. Use rational or exact symbolic
representations only where they materially improve formula validation; do not
force statistical workloads into rational arithmetic.

### Boundary conversion

Conversion between Decimal and float is explicit, localized, documented, and
included in provenance. Convert through decimal strings where source intent
matters. A domain object cannot mix Decimal and float implicitly.

### Canonical value encoding and hashing

JARVIS defines a versioned canonical value encoding (JCVE) for idempotency,
semantic hashes, flow inputs/outputs, and reproducibility. Language-default
JSON serialization is not canonical.

JCVE v1 rules:

- objects use Unicode property names sorted by code point;
- arrays preserve declared order;
- UUIDs use lowercase canonical text;
- timestamps normalize to UTC RFC 3339 with a declared precision;
- Decimal uses a tagged canonical string with no exponent/leading plus,
  normalized zero, and insignificant trailing zeros removed;
- float64 uses a tagged IEEE-754 bit representation for semantic hashing;
- negative floating zero normalizes only when the schema declares it
  semantically equivalent to zero;
- NaN and infinities are rejected by default; a domain schema may represent
  missing/non-finite state through explicit tagged values;
- units, currency, frequency, timezone, and convention fields participate in
  the hash;
- maps/sets whose order is not meaningful must declare and apply a canonical
  ordering before encoding;
- the encoding version prefixes every semantic hash.

Tabular data has two hashes:

- **artifact byte hash**: SHA-256 of the exact Parquet/Arrow object;
- **semantic dataset hash**: SHA-256 of canonical schema metadata plus
  canonical column and row order/value encoding.

Parquet writer metadata, compression, or row-group changes may alter the byte
hash without altering the semantic hash. Reordering observations alters the
semantic hash unless the dataset contract first declares and applies a stable
sort. Hash comparison never substitutes for authorization.

## 4. Units, dimensions, and currencies

Every numeric input/output that has physical or financial meaning declares:

- unit;
- scale, such as percent, decimal fraction, basis points, or index points;
- currency where applicable;
- frequency/period;
- price basis or quote convention;
- timezone/calendar when dates matter.

Examples:

- `5%` is not interchangeable with decimal `5`;
- an annualized volatility is not interchangeable with period volatility;
- a clean bond price is not interchangeable with dirty price;
- nominal and real rates are distinct;
- USD and CAD amounts cannot be added without an explicit FX conversion.

The API rejects ambiguous values rather than guessing units.

## 5. Required financial conventions

Functions declare all conventions that can change a result, including:

- compounding frequency and effective/nominal basis;
- day-count convention;
- business-day calendar and adjustment;
- settlement date and ex-coupon behavior;
- clean versus dirty price;
- cash-flow timing;
- currency and rounding;
- tax/accounting framework where relevant;
- annualization factor;
- return convention: simple, log, gross, or excess;
- missing-data and interpolation policy;
- benchmark and risk-free-rate definition.

Defaults are allowed only when:

- the domain has a documented unambiguous standard for the context;
- the default is stored in the result;
- the UI displays or makes it inspectable;
- a caller can override it when valid.

## 6. Formula registry

Each executable formula release records:

- stable formula key and semantic version;
- human-readable LaTeX;
- validated expression AST or implementation key;
- variable definitions, units, and domains;
- assumptions and preconditions;
- output units;
- expected failure/warning conditions;
- authoritative references and review status;
- test vector set and implementation digest.

Formula text is not executable. Expression evaluation uses an allowlisted AST
or a reviewed engine function. No `eval`, dynamic imports, or arbitrary code.

Changing a formula's mathematical meaning creates a new release. Typographical
display fixes that do not affect execution still preserve an audit trail.

## 7. Validation layers

### Input validation

Reject or flag:

- missing required inputs;
- impossible dates/ranges;
- inconsistent units/currencies;
- denominator or logarithm domain violations;
- invalid probability/rate bounds where mathematically required;
- non-finite values unless a method explicitly supports them;
- insufficient observations;
- inconsistent frequency;
- non-monotonic timestamps when order is required.

### Precondition validation

Examples:

- Gordon growth requires discount rate greater than growth;
- IRR may have no or multiple solutions;
- covariance matrices may not be positive semidefinite;
- duration/convexity require defined cash-flow and yield conventions;
- regression requires sufficient rank/degrees of freedom;
- time-series methods require the expected index/frequency.

Precondition failure is a typed validation error or explicit warning. It is
not converted into an arbitrary fallback result.

### Postcondition validation

Check:

- finite outputs;
- identities and bounds expected by the method;
- solver convergence and residuals;
- matrix conditioning/rank;
- probability sums and value ranges;
- reconciliation totals;
- cash-flow/valuation invariants;
- output schema, units, and dimensions.

## 8. Rounding and presentation

Store and calculate at justified precision. Round only at explicit domain or
presentation boundaries.

- Intermediate values are not rounded merely to match display precision.
- Currency rounding declares currency minor units and rounding mode.
- Basis-point and percentage displays retain their underlying unrounded value.
- Tables/charts may format values, but exported machine-readable results retain
  documented precision.
- A report states material rounding that can affect reconciliation.

The UI does not parse formatted strings back into calculation inputs.

## 9. Tolerance policy

Every floating-point comparison declares:

- absolute tolerance;
- relative tolerance;
- expected scale;
- rationale/source.

Tests prefer:

```text
abs(actual - expected) <= absolute_tolerance
or
abs(actual - expected) <= relative_tolerance * abs(expected)
```

Tolerance must not be widened solely to make a failing test pass. Changes
require explanation of algorithm, conditioning, dependency, or reference
precision.

For iterative methods, record:

- convergence flag;
- stopping criterion and tolerance;
- iterations/evaluations;
- residual/objective;
- warning/failure reason.

Non-convergence is not reported as an ordinary successful estimate.

## 10. Data transformations

Transformations are immutable, versioned operations with:

- input snapshot IDs and hashes;
- operation key/version;
- parameters and order;
- units/frequency before and after;
- missing/infinite/outlier policy;
- output snapshot ID/hash;
- row-count/date-range effects;
- warnings.

No silent:

- dropping of rows;
- forward/back filling;
- resampling;
- winsorization;
- currency conversion;
- seasonal adjustment;
- inflation adjustment;
- revision replacement;
- randomization.

The analysis dataset is an exact immutable snapshot, not a query that may
return different observations later.

## 11. Time-series safeguards

Time-series methods must preserve time order by default.

Required checks and metadata:

- observation timestamp and, where relevant, availability/vintage timestamp;
- frequency and date gaps;
- train/validation/test boundaries;
- no random shuffle unless explicitly justified and recorded;
- transform fit only on training data;
- rolling/expanding window definition;
- lag alignment and target horizon;
- look-ahead and leakage checks;
- revision-aware FRED/ALFRED status;
- transaction-cost/turnover assumptions for strategy-like analysis;
- structural-break and parameter-stability diagnostics where relevant.

A backtest using latest-revised data must be labeled as revised-data research,
not point-in-time evidence.

## 12. Statistical estimation policy

Every statistical result records:

- method and implementation release;
- dataset snapshot and exact sample/filter;
- dependent, independent, grouping, and weighting variables;
- transformations;
- missing-data handling;
- estimator, covariance/error method, and significance level;
- parameters/hyperparameters and random seed;
- coefficient/statistic/diagnostic outputs;
- convergence/rank/conditioning warnings;
- software/dependency environment fingerprint.

Results distinguish descriptive association from causal inference. Causal
language requires an identified design and assumptions; a generic regression
does not establish causality.

### Regression minimum

Where applicable expose:

- coefficients, standard errors, confidence intervals, and sample size;
- fit statistics and residual diagnostics;
- multicollinearity/rank condition;
- heteroskedasticity and autocorrelation handling;
- influential observations;
- formula/design matrix definition.

### Hypothesis tests

Store null/alternative, test statistic, distribution/approximation, p-value,
significance level, sample, and assumptions. Do not translate p-values into
probability that a hypothesis is true.

## 13. Machine-learning safeguards

Before ML is enabled:

- establish a simple baseline;
- separate training, validation, and test data appropriately;
- use time-aware splits for time series;
- fit preprocessing inside the training pipeline;
- detect feature/target leakage;
- record search space and tuning budget;
- keep the final test set untouched until final evaluation;
- report uncertainty and out-of-sample metrics;
- record random seeds and non-deterministic library limitations;
- compare complexity against simpler econometric alternatives.

Model artifacts pin training snapshot, code/image/dependency hashes, feature
schema, hyperparameters, metrics, and evaluation data.

## 14. Optimization safeguards

Optimization output includes:

- objective and units;
- constraints and bounds;
- solver/version;
- initialization and seed;
- convergence/status;
- objective value and residual/constraint violations;
- sensitivity to inputs where material.

Portfolio optimizers must disclose assumptions, turnover/cost constraints, and
input-estimation instability. An infeasible or non-converged solution is not
presented as an allocation recommendation.

## 15. Reproducibility fingerprint

Every completed analysis execution records:

- analysis and flow version;
- handler and engine versions/code digests;
- Git commit and container image digest;
- dependency lock hash;
- operating/runtime and relevant BLAS/solver metadata;
- input resource revisions;
- dataset snapshot/artifact hashes;
- parameters, assumptions, units, and conventions;
- random seed;
- execution timestamps;
- output/artifact hashes;
- warning and diagnostic set.

Exact bit-for-bit reproduction may be impossible across different hardware or
non-deterministic libraries. In that case JARVIS declares the reproducibility
level:

- `exact`
- `numerically_equivalent_within_tolerance`
- `methodologically_reproducible`
- `not_reproducible`

Execution modes are also explicit:

- `replay_stored_evidence`: render/inspect the original immutable outputs;
- `rerun_retained_bundle`: execute the pinned image/handler digest;
- `rerun_current_method`: execute a current compatible release and compare.

The second mode is available only while a retained bundle remains runnable and
approved. The system never labels a current-method rerun as the original run.

## 16. Numerical test requirements

### Golden vectors

Use authoritative examples for:

- time value of money;
- bond pricing, accrued interest, yields, duration, and convexity;
- spot/forward rates and curve factors;
- NPV, IRR, WACC, and DCF;
- portfolio return/risk metrics;
- regression and time-series diagnostics.

Each vector records source, conventions, expected value, and tolerance.

### Independent cross-checks

Critical formulas require either:

- an independently implemented reference path;
- comparison with a trusted external library/tool;
- reconciliation to a primary/professional published example.

The cross-check must not simply call the same internal function through
another wrapper.

### Property tests

Use Hypothesis for valid domains and invariants, such as:

- zero-coupon price monotonicity with yield;
- present-value linearity in cash flows;
- duration/convexity finite-difference consistency;
- normalized weight sums;
- transformation shape/date invariants;
- idempotent deterministic handler output hashes.

### Edge cases

Include zero/negative rates where permitted, near-zero denominators, leap
years, irregular coupons, short samples, singular matrices, missing dates,
large/small magnitudes, non-finite provider values, and multiple/no-root IRR.

## 17. Review and change control

A critical numerical feature is not complete until:

- formula/method source and assumptions are documented;
- inputs/outputs have types and units;
- validations and warnings are defined;
- golden, property, and edge tests pass;
- an independent reviewer checks the method and test sources;
- API and UI expose conventions and diagnostics;
- execution provenance is persisted.

Dependency upgrades affecting NumPy, SciPy, pandas, statsmodels,
scikit-learn, BLAS, solvers, or date/calendar behavior trigger the relevant
golden and reproducibility suite.

Before implementing each high-risk analytical family, add a feature-specific
numerical specification. At minimum:

- yield curves: instrument conventions, interpolation/extrapolation,
  no-arbitrage checks, maturity alignment, and source vintages;
- DCF: accounting normalization, forecast/terminal conventions, WACC,
  currency, share count, scenarios, and sensitivity bounds;
- backtests: point-in-time availability, survivorship, transaction costs,
  multiple testing, model-selection bias, and benchmark definition;
- portfolio optimization: input estimation, constraints, costs, feasibility,
  and allocation stability.

## 18. AI boundary

AI may:

- explain recorded inputs, methods, diagnostics, and outputs;
- summarize uncertainty and limitations;
- suggest an appropriate deterministic workflow;
- format a report from structured evidence.

AI may not:

- invent or silently modify a formula;
- calculate an authoritative value independently;
- claim a model ran when no run record exists;
- create a citation or statistic without tool evidence;
- suppress engine warnings;
- convert interpretation into fact.

If required inputs, conventions, or evidence are absent, the correct output is
“Insufficient information” plus the missing requirements.

