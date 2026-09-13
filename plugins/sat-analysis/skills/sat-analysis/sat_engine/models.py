"""Typed JSON-facing engine records.

These types document the wire contract; :mod:`sat_engine.validators` enforces
the packaged JSON Schemas. Optional values are not silently filled here.
"""

from typing import Literal, Never, NotRequired, TypedDict


type JSONValue = None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]
type Mode = Literal["LIGHT", "FULL"]
type Submode = Literal["BREACH", "CRASH", "FIX", "STATEMENT", "GENERAL"]
type Relationship = Literal["unspecified", "exclusive_exhaustive", "exclusive_nonexhaustive", "overlapping"]
type Reliability = Literal["A", "B", "C", "D", "E", "F", "unknown"]
type Rating = Literal["++", "+", "N", "-", "--"]
type ParseStatus = Literal["parsed", "unparsed", "rejected"]
type AssessmentStatus = Literal["insufficient_evidence", "incomplete", "underdetermined", "differentiated"]
type CalculationOperation = Literal["sum", "difference", "product", "ratio", "reported_interval"]


class TimestampContext(TypedDict, total=False):
    year: int
    timezone: str
    fold: Literal[0, 1]


class Observation(TypedDict):
    schema_version: Literal["1"]
    id: str
    raw: str
    source: str
    parse_status: ParseStatus
    timestamp: NotRequired[str | None]
    host: NotRequired[str | None]
    process: NotRequired[str | None]
    pid: NotRequired[int | None]
    user: NotRequired[str | None]
    src_ip: NotRequired[str | None]
    dst_ip: NotRequired[str | None]
    src_port: NotRequired[int | None]
    dst_port: NotRequired[int | None]
    action: NotRequired[str | None]
    status: NotRequired[str | None]
    message: NotRequired[str | None]
    tags: NotRequired[list[str]]
    source_id: NotRequired[str | None]
    line_number: NotRequired[int | None]
    record_sha256: NotRequired[str | None]
    raw_bytes_base64: NotRequired[str | None]
    parse_error: NotRequired[str | None]
    parser: NotRequired[str]
    address_mentions: NotRequired[list[str]]
    origin_id: NotRequired[str | None]
    dependency_groups: NotRequired[list[str]]
    timestamp_semantics: NotRequired[str]
    clock_domain: NotRequired[str | None]
    timestamp_uncertainty_seconds: NotRequired[float | None]
    timestamp_context: NotRequired[TimestampContext]
    reliability: NotRequired[Reliability]
    reliability_reason: NotRequired[str | None]


class Hypothesis(TypedDict):
    schema_version: Literal["1"]
    id: str
    description: str
    category: NotRequired[str]
    initial_probability: NotRequired[float | None]
    falsifier: NotRequired[str | None]
    posterior_probability: NotRequired[float | None]


class Evidence(TypedDict):
    schema_version: Literal["1"]
    id: str
    observation_id: str
    ratings: dict[str, Rating]
    rationale: NotRequired[str]


class Likelihood(TypedDict):
    proposition: str
    value: float | None
    basis: str
    term: NotRequired[str]
    horizon: NotRequired[str]


class Confidence(TypedDict):
    level: Literal["low", "moderate", "high", "unassessed"]
    reasoning: str


class Judgment(TypedDict):
    summary: str
    selected_hypothesis_ids: NotRequired[list[str]]
    observation_ids: NotRequired[list[str]]
    likelihood: NotRequired[Likelihood]
    confidence: NotRequired[Confidence]
    implications: NotRequired[list[str]]


class Task(TypedDict):
    id: str
    action: str
    owner: NotRequired[str]
    trigger: NotRequired[str]
    observation_ids: NotRequired[list[str]]
    hypothesis_ids: NotRequired[list[str]]


class ArithmeticCalculation(TypedDict):
    id: str
    operation: Literal["sum", "difference", "product", "ratio"]
    operands: list[float]
    unit: NotRequired[str]


class IntervalCalculation(TypedDict):
    id: str
    operation: Literal["reported_interval"]
    start_observation_id: str
    end_observation_id: str
    unit: NotRequired[str]


type Calculation = ArithmeticCalculation | IntervalCalculation


class CalculationResult(TypedDict):
    id: str
    operation: CalculationOperation
    value: float | None
    unit: str | None
    status: Literal["resolved", "unresolved"]
    caveats: list[str]
    physical_latency_established: NotRequired[Literal[False]]


class TimelineOptions(TypedDict, total=False):
    gap_threshold_seconds: float
    rapid_threshold_seconds: float
    default_year: int
    default_timezone: str
    fold: Literal[0, 1]


class AnalysisRequest(TypedDict):
    schema_version: Literal["1"]
    mode: Mode
    submode: Submode
    question: str
    analysis_id: NotRequired[str]
    revision: NotRequired[int]
    observations: NotRequired[list[Observation]]
    hypotheses: NotRequired[list[Hypothesis]]
    evidence: NotRequired[list[Evidence]]
    relationship: NotRequired[Relationship]
    judgment: NotRequired[Judgment | None]
    assumptions: NotRequired[list[str]]
    limitations: NotRequired[list[str]]
    tasks: NotRequired[list[Task]]
    rule_ids: NotRequired[list[str]]
    calculations: NotRequired[list[Calculation]]
    timeline_options: NotRequired[TimelineOptions]


class NormalizedAnalysisRequest(TypedDict):
    schema_version: Literal["1"]
    mode: Mode
    submode: Submode
    question: str
    analysis_id: str
    revision: int
    observations: list[Observation]
    hypotheses: list[Hypothesis]
    evidence: list[Evidence]
    relationship: Relationship
    judgment: Judgment | None
    assumptions: list[str]
    limitations: list[str]
    tasks: list[Task]
    rule_ids: list[str]
    calculations: list[Calculation]
    timeline_options: TimelineOptions


class TimelineEvent(TypedDict):
    id: str
    timestamp: str | None
    description: str
    source: str
    actor: str | None
    target: str | None
    tags: list[str]
    timestamp_context: TimestampContext
    timestamp_resolution_error: str | None
    timestamp_semantics: str
    clock_domain: str | None
    timestamp_uncertainty_seconds: float | None
    parse_status: ParseStatus
    raw: str
    source_id: str | None
    line_number: int | None
    record_sha256: str | None
    origin_id: str | None
    dependency_groups: list[str]
    parse_error: str | None
    raw_bytes_base64: str | None
    parser: str
    address_mentions: list[str]
    timestamp_utc: str | None
    reliability: Reliability
    reliability_reason: str | None


class ReportedInterval(TypedDict):
    event1: str
    event2: str
    delta_seconds: float
    kind: Literal["reported_clock_interval"]
    same_known_clock_domain: bool
    combined_timestamp_uncertainty_seconds: float | None
    physical_latency_established: Literal[False]


class ParseCounts(TypedDict):
    parsed: int
    unparsed: int
    rejected: int


class TimeRange(TypedDict):
    first: str | None
    last: str | None


class ActorSequence(TypedDict):
    count: int
    first: str | None
    last: str | None
    unresolved: int


class TimelineAnalysis(TypedDict):
    total_events: int
    resolved_events: int
    unresolved_events: int
    parse_counts: ParseCounts
    time_range: TimeRange
    actors: dict[str, ActorSequence]
    tag_sequences: list[Never]
    rapid_succession: list[ReportedInterval]
    gaps: list[ReportedInterval]
    caveats: list[str]


class Timeline(TypedDict):
    schema_version: Literal["1"]
    events: list[TimelineEvent]
    analysis: TimelineAnalysis
    gap_threshold_seconds: float
    rapid_threshold_seconds: float


class MissingRating(TypedDict):
    evidence_id: str
    hypothesis_id: str


class Contradiction(TypedDict):
    evidence_ids: list[str]
    origin_id: str | None
    description: str
    rating: Literal["-", "--"]


class Assessment(TypedDict):
    status: AssessmentStatus
    heuristic_leaders: list[str]
    winner: None
    missing_ratings: list[MissingRating]
    caveats: list[str]
    scores: dict[str, int]
    contradictions: dict[str, list[Contradiction]]
    contributing_record_count: int


class RemovalImpact(TypedDict):
    removed_evidence_ids: list[str]
    status: AssessmentStatus
    heuristic_leaders: list[str]
    winner: None
    scores_without: dict[str, int]
    changes_assessment: bool


class GroupImpact(RemovalImpact):
    kind: Literal["source", "origin", "dependency"]
    id: str


class Sensitivity(TypedDict):
    base_assessment: Assessment
    base_scores: dict[str, int]
    base_winner: None
    evidence_impact: dict[str, RemovalImpact]
    group_impact: dict[str, GroupImpact]
    heuristic_stable: bool | None
    caveat: str


class ACHMatrix(TypedDict):
    schema_version: Literal["1"]
    title: str
    relationship: Relationship
    hypotheses: list[Hypothesis]
    evidence: list[Evidence]
    assessment: Assessment
    sensitivity: Sensitivity
    diagnosticity: dict[str, float | None]


class Diagnostic(TypedDict):
    code: str
    path: str
    message: str
    severity: Literal["warning", "error"]
    remediation: str


class SnapshotIdentity(TypedDict):
    schema_version: Literal["1"]
    analysis_id: str
    revision: int
    content_hash: str


class DecisionCard(SnapshotIdentity):
    question: str
    summary: str
    likelihood: Likelihood | None
    confidence: Confidence | None
    implications: list[str]
    assessment_status: AssessmentStatus | Literal["not_evaluated"]
    limitations: list[str]
    calculations: list[CalculationResult]


class AnalyticTrace(SnapshotIdentity):
    engine_version: Literal["1.0.0"]
    request: NormalizedAnalysisRequest
    ach_matrix: ACHMatrix | None
    timeline: Timeline
    calculations: list[CalculationResult]
    diagnostics: list[Diagnostic]


class TaskingView(SnapshotIdentity):
    tasks: list[Task]
    limitations: list[str]


class Artifacts(TypedDict):
    decision_card: DecisionCard
    analytic_trace: AnalyticTrace
    tasking_view: TaskingView | None


class EngineResult(TypedDict):
    schema_version: Literal["1"]
    engine_version: Literal["1.0.0"]
    status: Literal["ok", "invalid"]
    diagnostics: list[Diagnostic]
    artifacts: Artifacts | None


class DoctrineRule(TypedDict):
    rule_id: str
    title: str
    summary: str
    standard: str
    section: str
    citation: str
    url: str
    severity: Literal["BLOCKING", "WARNING", "NOTE"]
    implementation_policy: bool


class DoctrineCatalog(TypedDict):
    schema_version: Literal["1"]
    catalog_version: str
    rules: list[DoctrineRule]
