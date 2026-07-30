## System Requirements
- Input: PDF-files of BAC, JPMorgan, Nvidia or Microsoft
- Intermediate output: parsed PDF-files, transformed in a suitable data format (e.g., json) and stored in a suitable system
- Final output: One Report for each of the companies, summarising, how the discussion on AI changed over time, that can be used by Analysts as a basis for decision making.
- **For the each of the statemetns in the report, the statement must be verifiable by providing an excerpt and the page of the original document**. If feasible within the prototype, the author/speaker of the excerpt should be provided, too.
- Separation of concerns: The system should be extensible to earnings-call pdfs of other companies and other reportgenerators, that focus on other topics than AI (e.g. for financial standings) 
- The system should be possible to be run on-prem (except for LLM-calls) but easily extendable to run on the cloud
- Any thrid party services (e.g. Vertex AI for LLM calls) needs to be wrapped, such that the provider can easily be swapped