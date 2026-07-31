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
- A **chunk is the unit of one continuous speaker turn**, not a fixed-size text window. A chunk is never split at a page boundary — if a turn spans multiple pages, the chunk stays whole and lists every page it touches.
- A chunk's `text` is a **list of per-page segments** (`page_no` + the portion of the turn's text on that page), not one flat string, so a long turn spanning several pages stays anchored to its exact source page per portion of text — needed for citing a specific page later, not just the set of pages a whole turn touched. `pages` (the flat list of every page a chunk touches) is derived from the segments rather than stored separately, so it can never drift out of sync with `text`. A page number always refers to the **physical PDF page index** (the same numbering used for `docling`'s `page_range`, i.e. what a reader's PDF viewer shows) — never a printed page number that may appear in the document body/footer, since those can diverge (e.g. a cover page shifts them).
- A chunk's speaker is a structured name/role/company, not a bare name string. Role and company are extracted from whatever is stated inline next to the speaker label in the source text (e.g. JPM's "Christopher McGratty / Analyst, Keefe, Bruyette & Woods, Inc.", MSFT's "KEITH WEISS, Morgan Stanley:") when available, since for some speakers this inline mention is the only place that information exists.
- Participants are not always listed up front (JPMorgan, Microsoft only reveal external/analyst participants through the Q&A itself). The participants list is therefore reconciled after chunk extraction: any speaker found while tagging chunks but missing from the upfront roster is added, carrying whatever role/company was recovered from the chunk — a union, not a replace, since the upfront roster may list attendees who are present but never speak.
- Grounding-check status (whether text was verified as a near-verbatim match of the independently-extracted raw page text) is checked **per page segment**, not once per whole chunk — checking the whole chunk's text against the concatenation of all its pages' raw text could mask a segment attributed to the wrong page. A chunk's own `is_grounded` is derived from its segments (true only if every segment is grounded). A failed check flags the segment; it does not block storage of the document.
- Company/participant identity normalization (e.g. mapping "Bank of America" / "BAC" to one canonical company ID across documents) is required for cross-quarter analysis but left as an implementation detail, not a schema-level decision yet.
