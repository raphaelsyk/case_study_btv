## Suggested System design
- Separation of concerns: The system has three core components, that should be decoupled: 1. A Data transformation pipeline taking the PDFs and transforming it into structured data model (e.g. json), 2. a data storage system for storing that data (e.g. a folder or a document database), 3. An Analyzer module performing that performs the AI trend/sentiment analysis
- For the design of the data model, see the file  '03_system_design_data_model.md'


## System design Decisions
### Core Components
1. **Data Transformation Pipeline**: converts a raw earnings-call PDF into the structured data model (see `03_system_design_data_model.md`). Fully topic-agnostic — it extracts the complete transcript (call identity, participants, all speaker-tagged turns) independent of any downstream analysis topic (AI or otherwise), so the same pipeline serves future report generators beyond the AI use case.
2. **Data Storage**: persists the structured transcripts produced by the pipeline and is read by the Analyzer. Decoupled behind a storage interface so the backing technology can change without touching the other components.
3. **Analyzer Module**: consumes structured transcripts from storage to produce topic-specific reports (e.g. the AI-discussion-over-time report). Owns topic filtering, cross-quarter synthesis, and citation verification (checking that generated statements are grounded in the stored source text) — none of this lives in the transformation pipeline. See "Analyzer Module" below for the detailed design.

### Data Transformation Pipeline
- **Extraction**: `docling`, run **per page**, so every text block carries an unambiguous page number (whole-document conversion can merge pages, even speakers, on some sources). PDFs are digitally native, so extraction fidelity isn't the bottleneck — turn/page segmentation is.
- **Structuring**: an LLM (Gemini) turns page-tagged raw text into the structured schema (identity, participants, turns), with pages delimited inline (`<page N>...</page N>`). Chosen over per-vendor deterministic parsers, since layouts vary too much across sources to hand-write a parser per template. Dispatched by detected document structure, not company identity.
- **Two structuring calls**: (a) identity + participants, over the first page(s); (b) full turn segmentation over the whole document — keeps each call's output bounded and simple. Participant detection in (a) is optional, since some sources only reveal participants via the Q&A; (b)'s speaker tag also captures role/company when stated inline. Participants are reconciled afterward as a union of (a) and (b), not a replace.
- A failing or invalid Gemini call skips and logs that document; it doesn't halt the rest of the batch.
- **Build order**: the general LLM-based path first; a deterministic fast-path for the more regular templates is a possible later optimization, not a prerequisite.
- **Grounding check**: each structured chunk is verified as a near-verbatim match of the independently-extracted raw page text, catching LLM hallucination without a human reviewer. Raw text is persisted alongside the structured output. A failed check flags the chunk; it doesn't block storage.
- **Validation**: reusable plausibility assertions (e.g. non-empty participants, turn count vs. page count), enforced both as pytest regression tests and as pydantic validators at runtime — an implausible transcript fails to construct.

### Storage
- Prototype storage: pydantic-validated JSON files on disk, one per transcript, behind a thin storage interface. On-prem by default (no external dependency), trivially swappable for a real document database later without touching the pipeline or analyzer.

### Analyzer Module
- **Two-stage "distill → synthesize" pipeline**, not a single mega-call and not a retrieval/agentic-search system — unnecessary at this corpus size (~19 documents, single-digit quarters per company; see "Tech stack"), kept as a future extension if that changes. Stage 1 distills each quarter's transcript into a structured, per-quarter AI analysis; stage 2 synthesizes a cross-quarter trend report from a company's stage-1 outputs.
- **Stage 1 (distill)**: one structured-output call per quarter, reusing the existing per-quarter AI-analysis prompts (bank/tech variant, dispatched by company sector). Each of the four sections carries a narrative plus a list of `Evidence` items (verbatim excerpt, page, speaker, quarter — always one page and one speaker per excerpt). Cached to disk per quarter, so a new quarter only requires distilling that quarter. The prompt uses only a transcript's `identity`, `participants`, and `turns` — never `raw_pages`, which stays reserved as ground truth for a deterministic grounding check run after stage 1.
- **Citeability**: every stage-1 `Evidence` item gets a deterministic ID (from quarter, section, position — never LLM-assigned). Stage 2 may only cite evidence by ID, never retype quote text; rendering resolves each ID via lookup, and an ID a model invents simply fails to resolve and is dropped.
- **Stage 2 (synthesize)**: one call per company over all cached stage-1 quarters, producing per-section trend claims that cite evidence IDs. Stage 1's filtering keeps this input small regardless of quarter count.
- **Storage** gains a `list_quarters(company)` method, so the Analyzer can discover a company's stored quarters without reading the filesystem directly.
- **Deployment**: a CLI command producing a markdown (+ PDF) report per company, matching the stated deliverable.

### Tech stack
- For required cloud services (e.g. Calling an LLM), we use Google Cloud Platform
- For the validation of data models and llm responses, we use pydantic
- Default LLM: Gemini via Vertex AI, called through a swappable wrapper (per the third-party-service requirement) — concrete model choice is a config detail, not a hard dependency of the design
- No retrieval/RAG for the prototype analyzer: the corpus is small (~19 documents, single-digit quarters per company) and each transcript fits comfortably in a long-context LLM call, so whole-transcript prompting is used directly. Flagged as a possible future extension if corpus size grows.