**Suggested Data Model**  
Identity of the earnings call and quarter:

* Data Model:  
  * Date  
  * Actual time range that is evaluated in the call  
  * Name of the quarter   
  * Company  
* How can this be retrieved? →  All on first page

Participants of the earnings call

* Data Model:  
  * List of Corporate representatives including Name & Role  
  * List of Other participants including Name, Role and company  
* How can this be retrieved?   
  * → For Nvidia and BAC listed on page 2  
  * → For JPMorgen listed in every subssection  
    → For Microsoft only in text

Management discussion section

* Data Model:  
  * List of text chunks, with following metadata on each chunk: speaker (name, role, company — role/company optional), pages  
* How can this be retrieved: Go through all pages


Q\&A section:

* Data Model:  
  * List of text chunks, with following metadata on each chunk: speaker (name, role, company — role/company optional), pages, \[Optional: Type as ‘question’ or ‘answer’\]  
* How can this be retrieved: Go through all pages

## Refinements / Decisions
- A **turn is the unit of one continuous speaker turn**, not a fixed-size text window. A turn is never split at a page boundary — if it spans multiple pages, the turn stays whole and lists every page it touches.
- A turn's `text` is a **list of per-page chunks** (`page_no` + the portion of the turn's text on that page), not one flat string, so a long turn spanning several pages stays anchored to its exact source page per portion of text — needed for citing a specific page later, not just the set of pages a whole turn touched. `pages` (the flat list of every page a turn touches) is derived from the chunks rather than stored separately, so it can never drift out of sync with `text`. A page number always refers to the **physical PDF page index** (the same numbering used for `docling`'s `page_range`, i.e. what a reader's PDF viewer shows) — never a printed page number that may appear in the document body/footer, since those can diverge (e.g. a cover page shifts them).
- A turn's speaker is a structured name/role/company, not a bare name string. Role and company are extracted from whatever is stated inline next to the speaker label in the source text (e.g. JPM's "Christopher McGratty / Analyst, Keefe, Bruyette & Woods, Inc.", MSFT's "KEITH WEISS, Morgan Stanley:") when available, since for some speakers this inline mention is the only place that information exists.
- Participants are not always listed up front (JPMorgan, Microsoft only reveal external/analyst participants through the Q&A itself). The participants list is therefore reconciled after turn extraction: any speaker found while tagging turns but missing from the upfront roster is added, carrying whatever role/company was recovered from the turn — a union, not a replace, since the upfront roster may list attendees who are present but never speak.
- Grounding-check status (whether text was verified as a near-verbatim match of the independently-extracted raw page text) is checked **per page chunk**, not once per whole turn — checking the whole turn's text against the concatenation of all its pages' raw text could mask a chunk attributed to the wrong page. A turn's own `is_grounded` is derived from its chunks (true only if every chunk is grounded). A failed check flags the chunk; it does not block storage of the document.
- Company/participant identity normalization (e.g. mapping "Bank of America" / "BAC" to one canonical company ID across documents) is required for cross-quarter analysis but left as an implementation detail, not a schema-level decision yet.
- Naming: what the schema calls `Turn` (one continuous speaker turn), `Section` (management-discussion vs. Q&A), and `Chunk` (one page's worth of a turn's text) were originally named `Chunk`, `ChunkSection`, and `ChunkSegment` respectively — renamed for clarity, since "chunk" reads more naturally as the small, page-bounded unit than as the whole multi-page turn.
