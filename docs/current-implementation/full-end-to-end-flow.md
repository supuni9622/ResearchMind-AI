# ResearchMind AI Current Implementation: Full End-to-End Flow

**Code snapshot reviewed:** 2026-07-28  
**Scope:** Current executable paths in `apps/web`, `apps/api`, and `apps/worker`.  
**Notation:** Solid arrows are synchronous calls or direct control flow. Dotted arrows are asynchronous, best-effort, external, or event-stream interactions.

This document is code-derived. It describes what the current implementation does, including validation, decisions, retries, approval pauses, bounded loops, persistence, and failure paths. Historical roadmap items and scaffold-only packages are not shown as active runtime behavior.

## 1. Whole-system map

```mermaid
flowchart LR
    user["Authenticated user"]
    web["Next.js web application"]
    api["FastAPI API v1"]
    auth["Cognito OAuth and JWT"]
    chat["Chat orchestration"]
    linear["Linear Research orchestration"]
    deepApi["Deep Research proposal and approval API"]
    ingest["Document upload orchestration"]
    docQueue["Processing queue: Valkey or SQS"]
    docWorker["Document processing worker"]
    deepQueue["Research dispatch outbox"]
    deepWorker["Research Runtime worker"]
    ai["Shared AI platforms"]
    pg[("PostgreSQL")]
    valkey[("Valkey")]
    qdrant[("Qdrant")]
    storage[("S3 or configured document storage")]
    llm["Configured generation providers"]
    voyage["Voyage AI embeddings and reranking"]
    tavily["Tavily web search"]
    mcp["Research Intelligence MCP paper search"]
    langsmith["LangSmith"]
    metrics["Prometheus and Grafana"]

    user --> web
    web -->|"Bearer HTTP or token WebSocket"| api
    api -.->|"OAuth code exchange and JWT verification"| auth
    api --> chat
    api --> linear
    api --> deepApi
    api --> ingest

    ingest --> pg
    ingest --> storage
    ingest -.-> docQueue
    docQueue -.-> docWorker
    docWorker --> ai

    deepApi --> pg
    deepApi -.-> deepQueue
    deepQueue -.-> deepWorker
    deepWorker --> ai

    chat --> ai
    linear --> ai
    ai --> pg
    ai --> valkey
    ai --> qdrant
    ai --> storage
    ai -.-> llm
    ai -.-> voyage
    ai -.-> tavily
    ai -.-> mcp
    ai -.-> langsmith
    ai -.-> metrics
```

## 2. Application startup, request envelope, and authentication

```mermaid
flowchart TD
    start["FastAPI lifespan starts"] --> logging["Configure structured logging"]
    logging --> migrate{"auto_migrate enabled?"}
    migrate -->|Yes| migrations["Run Alembic upgrade in a worker thread"]
    migrate -->|No| clients
    migrations --> clients["Create Valkey and Qdrant clients"]
    clients --> ready["Application ready"]

    ready --> request["HTTP request enters middleware stack"]
    request --> prometheus{"Prometheus HTTP metrics enabled?"}
    prometheus -->|Yes| recordHttp["Start full-request metrics measurement"]
    prometheus -->|No| cors
    recordHttp --> cors["CORS handling"]
    cors --> requestId["Assign or propagate request ID"]
    requestId --> requestLog["Bind request logging context"]
    requestLog --> timing["Measure request duration"]
    timing --> route["Route under /api/v1"]

    route --> protected{"Endpoint protected?"}
    protected -->|No| handler["Execute endpoint"]
    protected -->|Yes| credential{"Bearer credential present?"}
    credential -->|No| unauthorized["Return 401"]
    credential -->|Yes| verify["Verify JWT through Cognito-backed verifier"]
    verify --> verified{"JWT valid?"}
    verified -->|No| unauthorized
    verified -->|Yes| sync["Create or update internal user and last login in PostgreSQL"]
    sync --> bind["Bind user ID to log context"]
    bind --> handler

    handler --> response{"Handler completed?"}
    response -->|Yes| returnResponse["Return JSON, SSE, WebSocket frames, or download"]
    response -->|AppException| mapped["Map to structured application error"]
    response -->|Unexpected error| serverError["Return server error and log exception"]
    returnResponse --> nextRequest["Wait for next request"]
    mapped --> nextRequest
    serverError --> nextRequest

    nextRequest --> shutdown{"Application shutting down?"}
    shutdown -->|No| request
    shutdown -->|Yes| close["Dispose SQLAlchemy engine; close Valkey and Qdrant clients"]
```

The Cognito callback is a separate public flow: the frontend supplies an authorization code and redirect URI, the API validates Cognito configuration, optionally adds PKCE and client-secret authentication, exchanges the code at Cognito `/oauth2/token`, and returns the token response or a mapped authentication error.

## 3. Document ingestion and asynchronous indexing

### 3.1 Upload request

```mermaid
flowchart TD
    upload["POST /documents/upload"] --> filename{"Filename present?"}
    filename -->|No| invalid["Return validation error"]
    filename -->|Yes| size["Measure file size and reset stream"]
    size --> validate["Validate filename, content type, extension, and size"]
    validate --> valid{"Upload valid?"}
    valid -->|No| invalid
    valid -->|Yes| hash["Compute SHA-256"]
    hash --> duplicate["Find same owner and checksum in PostgreSQL"]
    duplicate --> isDuplicate{"Duplicate exists?"}
    isDuplicate -->|Yes| conflict["Return 409 with existing document metadata"]
    isDuplicate -->|No| key["Generate owner/document storage key"]
    key --> store["Upload original file to configured storage"]
    store --> persist["Create COMPLETED upload record in PostgreSQL"]
    persist --> commit["Commit and refresh document"]
    commit --> job["Build processing job"]
    job --> enqueue["Enqueue in configured processing queue"]
    enqueue --> accepted["Return 201 immediately"]

    validate -.->|Exception| rollback["Rollback database transaction"]
    hash -.->|Exception| rollback
    store -.->|Exception| rollback
    persist -.->|Exception| rollback
    enqueue -.->|Exception| rollback
    rollback --> uploaded{"Was object already uploaded?"}
    uploaded -->|Yes| cleanup["Best-effort delete stored object"]
    uploaded -->|No| fail["Propagate upload failure"]
    cleanup --> fail
```

### 3.2 Processing worker, pipeline, retry, and dead-letter behavior

```mermaid
flowchart TD
    worker["Start ProcessingWorker"] --> running{"Worker running?"}
    running -->|No| stopped["Graceful shutdown complete"]
    running -->|Yes| dequeue["Dequeue message"]
    dequeue --> message{"Message available?"}
    message -->|No| sleep["Sleep poll interval"]
    sleep --> running
    message -->|Yes| resolve["Load document from PostgreSQL"]
    resolve --> found{"Document found?"}
    found -->|No| jobFailure["Job failure"]
    found -->|Yes| parseRequest["Build ParseRequest from document metadata"]
    parseRequest --> processing["Set status PROCESSING and commit"]
    processing --> statusOk{"Status commit succeeded?"}
    statusOk -->|No| rollbackStatus["Rollback and fail job"]
    statusOk -->|Yes| parser["Resolve parser for document format"]
    parser --> parserFound{"Parser registered?"}
    parserFound -->|No| pipelineFailure["Pipeline failure"]
    parserFound -->|Yes| download["Download original object"]
    download --> temp["Create managed temporary file"]
    temp --> parse["Parse through Docling adapter"]
    parse --> enrich["Attach canonical document ID and filename"]
    enrich --> metadata["Run metadata enrichers"]
    metadata --> statistics["Run statistics enrichers"]
    statistics --> processArtifacts["Build and persist processed JSON, Markdown, and text artifacts"]
    processArtifacts --> chunk["Chunk with active MARKDOWN strategy"]
    chunk --> chunkArtifact["Build and persist chunks artifact"]
    chunkArtifact --> embed["Embed chunks with active VOYAGE_AI provider"]
    embed --> embeddingArtifact["Build and persist embeddings artifact"]
    embeddingArtifact --> index["Index dense and sparse representations in Qdrant"]
    index --> indexingMetrics["Finish pipeline metrics and optionally persist observability artifact"]
    indexingMetrics --> completeStatus["Set document COMPLETED, processed_at, clear error, commit"]
    completeStatus --> ack["Acknowledge queue message"]
    ack --> metricsCount["Update worker success and duration metrics"]
    metricsCount --> logEveryTwo{"Every second processed job?"}
    logEveryTwo -->|Yes| logMetrics["Log aggregate worker metrics"]
    logEveryTwo -->|No| running
    logMetrics --> running

    download -.->|Exception| pipelineFailure
    temp -.->|Exception| pipelineFailure
    parse -.->|Exception| pipelineFailure
    enrich -.->|Exception| pipelineFailure
    metadata -.->|Exception| pipelineFailure
    statistics -.->|Exception| pipelineFailure
    processArtifacts -.->|Exception| pipelineFailure
    chunk -.->|Exception| pipelineFailure
    embed -.->|Exception| pipelineFailure
    index -.->|Exception| pipelineFailure

    pipelineFailure --> failedStatus["Set document FAILED and truncate processing error to 2000 characters"]
    failedStatus --> failedCommit{"FAILED status commit succeeds?"}
    failedCommit -->|No| rollbackFailed["Rollback; preserve original exception"]
    failedCommit -->|Yes| jobFailure
    rollbackFailed --> jobFailure
    rollbackStatus --> jobFailure
    jobFailure --> increment["Increment attempt and failure metrics"]
    increment --> attempts{"attempt <= queue_max_attempts?"}
    attempts -->|Yes| retry["Requeue job and acknowledge original message"]
    retry --> retryMetric["Increment retry metric"]
    retryMetric --> running
    attempts -->|No| reject["Reject to provider dead-letter behavior"]
    reject --> dlqMetric["Increment dead-letter metric"]
    dlqMetric --> running
```

## 4. Shared retrieval and context-building pipeline

This pipeline is used by Linear Research, Deep Research task retrieval, citations preview, and the explicit retrieval endpoints. Chat deliberately does not call it.

```mermaid
flowchart TD
    query["Owner-scoped RetrievalQuery"] --> validate["Validate non-empty query, maximum length, and top_k"]
    validate --> valid{"Valid?"}
    valid -->|No| error["Raise retrieval validation error"]
    valid -->|Yes| normalize["Trim and collapse whitespace"]
    normalize --> pool["Expand candidate top_k to min(requested x 5, 50)"]
    pool --> parallel["Run three searches concurrently"]
    parallel --> dense["Dense query embedding and Qdrant dense search"]
    parallel --> sparse["Sparse SPLADE query embedding and Qdrant sparse search"]
    parallel --> metadata["Metadata-filtered search without query embedding"]
    dense --> fusion["Reciprocal Rank Fusion"]
    sparse --> fusion
    metadata --> fusion
    fusion --> fused["Take requested top_k"]
    fused --> rerank{"Reranking enabled, service configured, and chunks exist?"}
    rerank -->|Yes| voyage["Voyage AI rerank and replace ordering"]
    rerank -->|No| retrievalResult["Build HYBRID RetrievalResult and timings"]
    voyage --> retrievalResult

    retrievalResult --> contextChunks["Convert retrieved chunks to ContextChunk"]
    contextChunks --> platformGuard{"Platform retrieval guardrails configured?"}
    platformGuard -->|Yes| evaluateGuard["Evaluate source trust, access, sanitization, and citation checks"]
    platformGuard -->|No| dedup
    evaluateGuard --> blocked{"Guardrails blocked?"}
    blocked -->|Yes| guardError["Raise GuardrailBlockedError"]
    blocked -->|No| dedup["Deduplicate"]
    dedup --> parent["Expand hierarchical parents when referenced"]
    parent --> merge["Merge adjacent chunks"]
    merge --> order["Order context"]
    order --> redundancy["Embedding-redundancy compression"]
    redundancy --> langchain{"LangChain contextual compression enabled and query present?"}
    langchain -->|Yes| contextual["Contextual compression"]
    langchain -->|No| budget
    contextual --> budget["Token-budget compression to 6000 tokens"]
    budget --> chunkGuard["Rule-based chunk guardrails filter suspicious or malicious chunks"]
    chunkGuard --> citations["Build canonical citations"]
    citations --> format["Format prompt context"]
    format --> result["Return ContextResult with chunks, citations, warnings, and statistics"]
```

## 5. Chat end-to-end flow

Chat is conversational and memory-aware. Its `PromptContext.chunks` is always empty, so uploaded documents are not retrieved for this surface. Web and paper searches are independent opt-in external augmentations.

```mermaid
flowchart TD
    input["Chat composer submits message"] --> transport{"Transport?"}
    transport -->|HTTP| bearer["POST /chat/stream with Bearer token"]
    transport -->|WebSocket| ws["Connect /chat/ws?token= then send one JSON payload"]
    bearer --> auth["Authenticate and sync user"]
    ws --> auth
    auth --> limit["Check per-owner Chat rate limit"]
    limit --> limited{"Rate limited?"}
    limited -->|HTTP| http429["Return 429 and Retry-After"]
    limited -->|WebSocket| ws1013["Close with 1013"]
    limited -->|No| conversation["Get existing owner conversation or create one"]
    conversation --> identity["Best-effort persist immutable conversation identity artifact"]
    identity --> compact["Compact older history if prompt budget exceeded"]
    compact --> history["Load summary plus recent messages"]

    history --> webToggle{"Web search enabled and available?"}
    webToggle -->|No| paperToggle
    webToggle -->|Yes| webNeed["Run AUTO web-search necessity decision"]
    webNeed --> webNeeded{"Search needed?"}
    webNeeded -->|No| paperToggle
    webNeeded -->|Yes| webSearch["Emit started event; call Tavily; normalize evidence"]
    webSearch --> webEvidence{"Usable web evidence?"}
    webEvidence -->|Yes| webContext["Emit completed with source metadata; format web context"]
    webEvidence -->|No or error| webSkip["Emit skipped; continue without web context"]
    webContext --> paperToggle
    webSkip --> paperToggle

    paperToggle{"Paper search enabled and MCP available?"}
    paperToggle -->|No| memory
    paperToggle -->|Yes| distill["Distill academic query using prompt and recent conversation context"]
    distill --> paperSearch["Emit started; call MCP search_papers"]
    paperSearch --> papers{"Results exist?"}
    papers -->|Yes| paperContext["Emit completed with papers; format paper context"]
    papers -->|No or error| paperSkip["Emit skipped; continue without paper context"]
    paperContext --> memory
    paperSkip --> memory

    memory["Best-effort retrieve session, semantic, and research memory"] --> request["Build transcript and GenerationRequest"]
    request --> noDocs["Set chunks empty; prepend memory, web, and paper context"]
    noDocs --> generation["Shared streaming generation runtime"]
    generation --> cache{"Runtime cache hit?"}
    cache -->|Yes| replay["Replay cached answer as START, synthetic TOKEN chunks, COMPLETE; record zero-cost usage"]
    cache -->|No| live["Stream provider events as canonical SSE or WebSocket events"]
    replay --> completed
    live --> streamError{"Stream error?"}
    streamError -->|Yes| errorEvent["Emit ERROR; do not persist completed turn"]
    streamError -->|No| completed["Completion event observed"]

    completed --> persistTurn["Append user and assistant messages in PostgreSQL"]
    persistTurn --> memoryWrite["Best-effort update session state or raw turn; extract durable memories"]
    memoryWrite --> titleClaim["Claim one-time title generation"]
    titleClaim --> titleWon{"Claim acquired and first question exists?"}
    titleWon -->|Yes| titleGenerate["Generate short uncached Groq title and persist it"]
    titleWon -->|No| artifact
    titleGenerate --> artifact["Best-effort persist immutable conversation-turn artifact if policy allows"]
    artifact --> render["Frontend renders Markdown and source chips"]
```

## 6. Linear Research end-to-end flow

```mermaid
flowchart TD
    query["Research UI submits Linear query"] --> endpoint{"Endpoint?"}
    endpoint -->|POST /research| sync["Synchronous answer"]
    endpoint -->|POST /research/stream| stream["SSE answer"]
    endpoint -->|POST /research/citations| citationsOnly["Citation preview only"]
    sync --> auth["Authenticate and check Linear Research rate limit"]
    stream --> auth
    citationsOnly --> auth
    auth --> conversation["Get or create shared research conversation; title from first query"]
    conversation --> history["Load conversation history"]
    history --> memory["Best-effort retrieve memory using query and transcript"]
    memory --> retrieve["Run owner-scoped hybrid retrieval"]
    retrieve --> context["Run full context pipeline"]
    context --> preview{"Citation-only request?"}
    preview -->|Yes| returnCitations["Return citations; no generation or persistence"]
    preview -->|No| request["Build transcript-aware RESEARCH GenerationRequest with memory plus document context"]
    request --> mode{"Synchronous or streaming?"}
    mode -->|Synchronous| runtime["GenerationRuntime.execute"]
    mode -->|Streaming| streamingRuntime["StreamingService.stream_generate and forward events"]
    runtime --> answer["Collect GenerationResult"]
    streamingRuntime --> answer["Collect tokens on completion"]
    answer --> persistSession["Persist ResearchSession with query, answer, citations, sources, and runtime metadata"]
    persistSession --> artifact["Best-effort persist Research artifact if policy permits"]
    artifact --> memories["Best-effort update session state or raw turn and extract durable memories"]
    memories --> response["Return answer or finish SSE; frontend renders Markdown and citations"]

    retrieve -.->|Failure| failed["Record failure metrics and return mapped error"]
    context -.->|Guardrail block or failure| failed
    runtime -.->|Generation failure| failed
    streamingRuntime -.->|ERROR event| failedStream["End stream without successful post-completion persistence"]
```

## 7. Shared generation runtime

### 7.1 Non-streaming generation

```mermaid
flowchart TD
    execute["GenerationRuntime.execute"] --> context["Create execution context and trace ID"]
    context --> validate["Validate GenerationRequest"]
    validate --> inputValidation["Run fail-fast input validation"]
    inputValidation --> inputGuard["Run input guardrails"]
    inputGuard --> inputBlocked{"Blocked or fail-fast rejected?"}
    inputBlocked -->|Yes| fail["Record failure and raise"]
    inputBlocked -->|No| explicit{"Explicit provider supplied?"}
    explicit -->|Yes| providerPath["Use explicit provider"]
    explicit -->|No| route["Resolve routing strategy, score candidates, build fallback chain"]
    route --> providerPath

    providerPath --> cache{"Cache policy allows lookup and cache hit exists?"}
    cache -->|Yes| cached["Apply cached GenerationResult"]
    cache -->|No| capability["Validate provider capabilities"]
    capability --> invoke["Build messages and invoke provider under trace"]
    invoke --> parsed{"Structured or registry-parsed output requested?"}
    parsed -->|Yes| parse["Parse native structured, JSON, Pydantic, Markdown, or XML output"]
    parsed -->|No| guard
    parse --> parseOk{"Parse and schema valid?"}
    parseOk -->|No| regenDecision
    parseOk -->|Yes| guard["Run generation guardrails"]
    guard --> outputValidation["Run output, hallucination, and runtime validation"]
    outputValidation --> regenDecision{"Acceptance requires regeneration?"}
    regenDecision -->|Yes, attempts remain| correction["Build correction prompt; double max_tokens on truncation up to 32000"]
    correction --> invoke
    regenDecision -->|Yes, no attempts remain| providerFail["Provider attempt fails"]
    providerFail --> fallback{"Another routed fallback exists?"}
    fallback -->|Yes| capability
    fallback -->|No| fail
    regenDecision -->|No| storeCache["Store eligible result in runtime cache"]
    cached --> metrics
    storeCache --> metrics["Record latency, tokens, cost, validation, guardrail, and cache metrics"]
    metrics --> artifacts["Policy-gated generation artifact"]
    artifacts --> observability["Optional observability report and LangSmith trace output"]
    observability --> usage["Persist generation usage and estimated cost"]
    usage --> done["Finalize execution context and return result"]
```

### 7.2 Streaming generation

```mermaid
flowchart TD
    request["StreamingService.stream_generate"] --> resolve["Resolve explicit provider or top routed provider"]
    resolve --> lookup{"Caching service configured?"}
    lookup -->|Yes| cacheLookup["Lookup exact, semantic, and session cache per policy"]
    lookup -->|No| live
    cacheLookup --> hit{"Cache hit?"}
    hit -->|Yes| usageHit["Record zero-cost cache-hit usage"]
    usageHit --> replay["Emit START; replay content in 12-character TOKEN chunks; emit COMPLETE"]
    hit -->|No| live["Start live trace and GenerationService.stream_generate"]
    live --> preflight["Validate request, fail-fast input validation, input guardrails, capabilities"]
    preflight --> provider["Stream from one provider; no mid-stream fallback or regeneration"]
    provider --> adapt["Convert provider chunks to canonical StreamEvents"]
    adapt --> providerDone{"Provider completed?"}
    providerDone -->|No, more chunks| provider
    providerDone -->|GenerationError| error["Emit ERROR with provider failure"]
    providerDone -->|Unexpected error| genericError["Emit generic ERROR"]
    providerDone -->|Yes| result["Assemble GenerationResult and token counts"]
    result --> score["Best-effort post-stream output guardrail and validation scoring"]
    score --> cacheStore["Store completed stream if eligible"]
    cacheStore --> streamArtifact["Policy-gated stream artifact"]
    streamArtifact --> metrics["Record metrics and observability artifact"]
    metrics --> usage["Persist usage and cost"]
```

## 8. Deep Research end-to-end flow

### 8.1 Proposal, explicit approval, queue admission, and worker dispatch

```mermaid
flowchart TD
    deep["User selects Deep Research or receives escalation suggestion"] --> path{"Action?"}
    path -->|Escalation check| check["Check proposal rate limit; retrieve memory; run uncached planner"]
    check --> complexity{"Plan complexity SIMPLE?"}
    complexity -->|Yes| noProposal["Suggest Linear Research; persist no proposal"]
    complexity -->|No| saveSuggested["Persist immediately approvable proposal"]
    path -->|Create proposal| propose["Check proposal rate limit"]
    propose --> proposalRow["Persist PROPOSING proposal"]
    proposalRow --> memory["Best-effort retrieve memory"]
    memory --> planner["Generate schema-valid plan with bounded tasks and dependencies"]
    planner --> awaiting["Persist plan and AWAITING_APPROVAL"]
    saveSuggested --> proposalReview
    awaiting --> proposalReview["Frontend shows plan proposal"]
    proposalReview --> approve{"User approves proposal?"}
    approve -->|No| idle["No run is authorized"]
    approve -->|Yes| approvalLimit["Check approval rate limit"]
    approvalLimit --> already{"Proposal already linked to a run?"}
    already -->|Yes| returnRun["Return existing idempotent run"]
    already -->|No| status{"Proposal is AWAITING_APPROVAL?"}
    status -->|No| conflict["Return 409"]
    status -->|Yes| capacity["Count active dispatches"]
    capacity --> full{"At deep_research_max_queued_runs?"}
    full -->|Yes| unavailable["Return 503 with retry hint"]
    full -->|No| run["Create or get run by fingerprint and idempotency key"]
    run --> dispatch["Set awaiting_runtime_dispatch; create transactional dispatch record; commit"]
    dispatch --> returnRun

    returnRun --> workerLoop["Research worker poll loop"]
    workerLoop --> expiry{"Expiry sweep due?"}
    expiry -->|Yes| expire["Expire stale approval-paused runs; rollback sweep failure"]
    expiry -->|No| claim
    expire --> claim["Claim next dispatch with lease"]
    claim --> found{"Dispatch found?"}
    found -->|No| sleep["Sleep poll interval and loop"]
    sleep --> workerLoop
    found -->|Yes| commitClaim["Commit claim and execute run"]
    commitClaim --> runtime["ResearchRuntimeExecutionService"]
    runtime --> dispatchDone["Complete dispatch record and commit in finally"]
    dispatchDone --> workerLoop
    runtime -.->|Exception| rollback["Rollback long-lived worker session; execution service records terminal failure when possible"]
    rollback --> dispatchDone
```

### 8.2 Multi-wave graph with decisions, approvals, and bounded loops

```mermaid
flowchart TD
    begin["Load approved proposal and refresh durable run"] --> terminal{"Run already COMPLETED?"}
    terminal -->|Yes| replay["Replay persisted outcome"]
    terminal -->|No| resume{"Paused status?"}
    resume -->|Report approval| resumeReport["Read recorded report decision and resume checkpoint"]
    resume -->|Plan approval| resumePlan["Read recorded plan decision and resume checkpoint"]
    resume -->|Web-search approval| resumeWeb["Read recorded web decision and resume checkpoint"]
    resume -->|Fresh run| checkCancel["Check cancellation; mark IN_PROGRESS; publish start events"]
    resumeReport --> reportDecision
    resumePlan --> planDecision
    resumeWeb --> webApproved
    resumeWeb --> postApproved
    checkCancel --> cancelled{"Cancellation requested?"}
    cancelled -->|Yes| cancel["Mark CANCELLED and publish event"]
    cancelled -->|No| waves["Validate dependency DAG and calculate topological task waves"]

    waves --> prepare["Prepare current wave"]
    prepare --> fanout["Fan out all ready tasks concurrently"]
    fanout --> taskRetrieve["Each task runs owner-scoped hybrid retrieval and context building"]
    taskRetrieve --> taskResult["Return completed or failed task result with compact evidence"]
    taskResult --> advance["Fan in and advance wave index"]
    advance --> moreWaves{"More dependency waves?"}
    moreWaves -->|Yes| prepare
    moreWaves -->|No| aggregate["Aggregate task results; build and persist immutable evidence artifact"]

    aggregate --> webMode{"Web search mode enabled and service available?"}
    webMode -->|No| planApproval
    webMode -->|Yes| webNeed["Evaluate evidence relevance and web-search necessity"]
    webNeed --> needsWeb{"Usable suggestion and budget remains?"}
    needsWeb -->|No| planApproval
    needsWeb -->|Yes| webAuthorization{"REQUIRED or auto-approved?"}
    webAuthorization -->|Yes| webSearch
    webAuthorization -->|No| webApproval["Interrupt: await human web-search approval"]
    webApproval --> webApproved{"Approved?"}
    webApproved -->|Yes| webSearch["Call Tavily; normalize evidence; record success or failed synthetic task"]
    webApproved -->|No| planApproval["Interrupt: await human plan approval"]
    webSearch --> reaggregate["Merge web task into evidence and persist revised evidence artifact"]
    reaggregate --> planApproval

    planApproval --> planDecision{"Approved?"}
    planDecision -->|No| endNoDraft["End without synthesis; mark terminal"]
    planDecision -->|Yes, optional edited goal| synthesize["Generate schema-bound research draft from evidence"]
    synthesize --> synthesisOk{"Synthesis succeeded?"}
    synthesisOk -->|No, retry budget remains| retrySynthesis["Retry once through bounded regeneration path with correction"]
    retrySynthesis --> synthesize
    synthesisOk -->|No, budget exhausted| failed["Mark FAILED and publish event"]
    synthesisOk -->|Yes| review["Deterministic citation/completeness review plus optional bounded model review"]
    review --> verdict{"Review decision"}

    verdict -->|FAIL| failed
    verdict -->|PASS| reportApproval
    verdict -->|FINALIZE_WITH_LIMITATIONS| reportApproval
    verdict -->|REVISE_SYNTHESIS| repairBudget{"Iteration and estimated-cost budgets remain?"}
    repairBudget -->|Yes| revision["Set revision instructions and increment synthesis revision count"]
    revision --> synthesize
    repairBudget -->|No| limitations["Convert to FINALIZE_WITH_LIMITATIONS"]
    limitations --> reportApproval

    verdict -->|RESEARCH_GAPS| gapBudget{"Iteration and estimated-cost budgets remain?"}
    gapBudget -->|No| limitations
    gapBudget -->|Yes, web enabled| postWebNeed["Evaluate targeted web-search need"]
    gapBudget -->|Yes, web disabled| docGap["Create one targeted gap task and increment plan version"]
    postWebNeed --> postSuggestion{"Web suggestion produced?"}
    postSuggestion -->|No| docGap
    postSuggestion -->|Yes, authorized| postWebSearch["Search web and add synthetic gap task"]
    postSuggestion -->|Yes, approval required| postWebApproval["Interrupt: await human web-search approval"]
    postWebApproval --> postApproved{"Approved?"}
    postApproved -->|Yes| postWebSearch
    postApproved -->|No| docGap
    docGap --> gapRetrieve["Run document retrieval for targeted gap"]
    postWebSearch --> gapAggregate
    gapRetrieve --> gapAggregate["Merge gap evidence and persist revised evidence artifact"]
    gapAggregate --> synthesize

    reportApproval["Interrupt: show editable draft and await report approval"] --> reportDecision{"Approved?"}
    reportDecision -->|No| publishPlain["Skip PDF but publish synthesized draft as plain answer"]
    reportDecision -->|Yes, optional edited draft| report["Persist Markdown report and PDF"]
    report --> papers{"Related-paper suggestions enabled and MCP available?"}
    papers -->|Yes| paperQuery["Distill query and call MCP with timeout"]
    papers -->|No| publish
    paperQuery --> paperResult{"Results returned?"}
    paperResult -->|Yes| paperEvent["Publish related-paper completion event"]
    paperResult -->|No or error| paperSkip["Publish skipped event; never fail report"]
    paperEvent --> publish["Publish reviewed report into shared conversation"]
    paperSkip --> publish
    publishPlain --> publish
    publish --> memoryWrite["Best-effort session-state update and memory extraction"]
    memoryWrite --> complete["Mark run COMPLETED and publish completion event"]

    prepare -.->|Cancellation observed| cancel
    synthesize -.->|Cancellation observed| cancel
    runtimeBudget["Duration or execution budget exceeded"] -.-> failed
```

### 8.3 Approval resume and event delivery

```mermaid
flowchart TD
    pause["LangGraph interrupt reached"] --> checkpoint["Persist checkpoint in PostgreSQL"]
    checkpoint --> status{"Interrupt kind"}
    status -->|plan_approval| planStatus["Set AWAITING_PLAN_APPROVAL"]
    status -->|web_search_approval| webStatus["Set AWAITING_WEB_SEARCH_APPROVAL"]
    status -->|report_approval| reportStatus["Set AWAITING_APPROVAL"]
    planStatus --> sse["Event journal persists progress; SSE endpoint replays then tails events"]
    webStatus --> sse
    reportStatus --> sse
    sse --> frontend["Frontend renders progress and the appropriate review editor"]
    frontend --> decision["User submits approve, reject, reason, and optional safe edits"]
    decision --> record["Validate ownership and current state; record decision in run budget_usage"]
    record --> reopen["Reopen transactional dispatch"]
    reopen --> worker["Worker claims fresh dispatch"]
    worker --> refresh["Refresh run to avoid stale long-lived SQLAlchemy identity state"]
    refresh --> command["Resume graph checkpoint with LangGraph Command"]
    command --> pausedAgain{"Another interrupt reached?"}
    pausedAgain -->|Yes| checkpoint
    pausedAgain -->|No| terminal["Complete, cancel, or fail run"]

    reportStatus --> expiry["Periodic worker sweep"]
    planStatus --> expiry
    webStatus --> expiry
    expiry --> stale{"Older than approval expiry?"}
    stale -->|Yes| expired["Mark stale run expired or terminal per lifecycle"]
    stale -->|No| sse
```

## 9. Memory read/write lifecycle

```mermaid
flowchart TD
    turn["Chat, Linear Research, or Deep Research turn"] --> readConfigured{"Memory service configured?"}
    readConfigured -->|No| generation["Continue without memory"]
    readConfigured -->|Yes| read["Load session memory, semantic memory, research memory, and applicable profile context"]
    read --> readOk{"Read succeeded?"}
    readOk -->|No| failOpen["Log warning and continue without memory"]
    readOk -->|Yes| format["Format Memory Context and prepend to prompt context"]
    failOpen --> generation
    format --> generation["Generate or research"]
    generation --> successful{"Turn completed successfully?"}
    successful -->|No| stop["Do not run normal post-completion memory persistence"]
    successful -->|Yes| rawMode{"Raw session-turn storage enabled?"}
    rawMode -->|Yes| raw["Store Q and A as SESSION memory"]
    rawMode -->|No| stateMode{"Session-state storage enabled and updater available?"}
    stateMode -->|Yes| distill["Distill and upsert one evolving session summary"]
    stateMode -->|No| durable
    raw --> durable{"Memory extraction service configured?"}
    distill --> durable
    durable -->|No| done["Finish"]
    durable -->|Yes| extract["Extract candidate USER and RESEARCH memories"]
    extract --> policy["Apply availability, importance, and memory policies"]
    policy --> store["Persist accepted memories in PostgreSQL, Valkey, or Qdrant-backed stores"]
    store --> done

    raw -.->|Failure| bestEffort["Log warning; do not fail completed user request"]
    distill -.->|Failure| bestEffort
    extract -.->|Failure| bestEffort
    store -.->|Failure| bestEffort
    bestEffort --> done
```

The explicit `/memory` API additionally supports remember, search, context retrieval, recall by ID, update, and forget, with authenticated owner scoping.

## 10. Persistence, cache, artifacts, and observability fan-out

```mermaid
flowchart LR
    operation["Completed operation"] --> postgres["PostgreSQL: users, documents, conversations, messages, research sessions, proposals, runs, dispatches, events, usage, memory"]
    operation --> valkey["Valkey: rate limits, configured queues, runtime caches, memory/cache support"]
    operation --> qdrant["Qdrant: document vectors, sparse vectors, semantic retrieval, semantic memory"]
    operation --> storage["S3 or configured storage: originals, processing/chunk/embedding/indexing artifacts, generation/stream/research artifacts, reports, PDFs"]
    operation -.-> langsmith["LangSmith: generation traces when configured"]
    operation -.-> prometheus["Prometheus: HTTP, generation, retrieval, research, tool, upload, guardrail, cache, and worker metrics"]
    prometheus -.-> grafana["Grafana dashboards and alerts"]

    operation --> artifactPolicy{"Artifact writer configured and policy permits category/runtime?"}
    artifactPolicy -->|Yes| immutable["Write immutable versioned artifact"]
    artifactPolicy -->|No| skip["Skip artifact"]
    immutable --> artifactError{"Write succeeds?"}
    artifactError -->|Yes| done["Finish"]
    artifactError -->|No, best-effort path| warn["Log warning and preserve primary result"]
    warn --> done
    skip --> done
```

## 11. User-facing API surface represented in the flows

| Area | Current active endpoints |
|---|---|
| Authentication | `POST /auth/callback`, `GET /auth/me` |
| Documents | `GET /documents`, `GET /documents/knowledge-stats`, `POST /documents/upload` |
| Retrieval | `POST /retrieval`, `POST /retrieval/sparse`, `POST /retrieval/hybrid` |
| Chat | conversation list/detail, `POST /chat/stream`, `WS /chat/ws` |
| Linear Research | `POST /research`, `POST /research/stream`, `POST /research/citations`, conversation list/detail/cost, research result lookup |
| Deep Research | proposal, escalation check, proposal approval, run lookup/cancel, plan inspection/decision, web-search inspection/decision, draft inspection/report decision, run SSE events, report download |
| Memory | remember, search, context, recall, update, forget |
| Usage | generation usage summary |
| Operations | health endpoints, OpenAPI, Prometheus metrics when enabled |

## 12. Important implementation boundaries

- Chat is not document-grounded. It uses conversation history, memory, and optional external web/paper context, but sets `PromptContext.chunks` to an empty list.
- Linear Research and Deep Research are document-grounded through the shared Qdrant hybrid retrieval and context pipeline.
- Deep Research never starts from proposal creation alone. A user must explicitly approve a persisted proposal before a run and dispatch are created.
- Deep Research has three possible in-run human pauses: plan approval, conditional web-search approval, and report approval.
- Plan rejection ends before synthesis. Report rejection retains and publishes the already-created draft as a plain answer but skips PDF generation.
- Web search failures and related-paper MCP failures are non-fatal. Document retrieval, synthesis, lifecycle, and checkpoint failures can fail the run.
- Streaming generation cannot switch provider or regenerate after tokens have begun. Non-streaming generation can use routed fallbacks and bounded regeneration.
- Document processing retries at the queue-job level. After `queue_max_attempts`, the message is rejected to the configured provider's dead-letter behavior.
- Artifact and memory post-processing are generally best-effort so they do not invalidate an already successful user response.

## 13. Principal code references

- API assembly and lifecycle: `apps/api/app/main.py`, `apps/api/app/core/lifespan.py`, `apps/api/app/core/setup.py`
- Authentication: `apps/api/app/api/v1/auth.py`, `apps/api/app/auth/dependencies.py`, `apps/api/app/services/auth.py`
- Document upload and worker: `apps/api/app/api/v1/documents.py`, `apps/api/app/ai/knowledge/upload/service.py`, `apps/worker/processing_worker.py`
- Processing pipeline: `apps/api/app/services/document_processing_service.py`, `apps/api/app/ai/knowledge/processing/service.py`
- Retrieval and context: `apps/api/app/ai/knowledge/retrieval/service.py`, `apps/api/app/ai/knowledge/context/service.py`
- Chat: `apps/api/app/api/v1/chat.py`, `apps/api/app/ai/runtime/chat/web_search.py`, `apps/api/app/ai/runtime/chat/paper_search.py`
- Linear Research: `apps/api/app/api/v1/research.py`, `apps/api/app/ai/research/service.py`
- Generation runtime: `apps/api/app/ai/runtime/generation/service.py`, `apps/api/app/ai/runtime/generation/streaming/service.py`, `apps/api/app/ai/runtime/generation/orchestration/orchestrator.py`
- Deep Research: `apps/api/app/ai/runtime/research/proposal_service.py`, `apps/api/app/ai/runtime/research/execution.py`, `apps/api/app/ai/runtime/research/workflows/multi_wave_research.py`
- Research worker: `apps/worker/research_runtime_worker.py`, `apps/worker/research_runtime_main.py`
- Memory: `apps/api/app/ai/memory/`, plus Chat and Research post-completion helpers
- Frontend consumers: `apps/web/src/features/chat/use-chat.ts`, `apps/web/src/features/research/use-research.ts`, `apps/web/src/features/research/use-deep-research.ts`
