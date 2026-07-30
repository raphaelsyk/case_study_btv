## Suggested System design
- Separation of concerns: The system has three core components, that should be decoupled: 1. A Data transformation pipeline taking the PDFs and transforming it into structured data model (e.g. json), 2. a data storage system for storing that data (e.g. a folder or a document database), 3. An Analyzer module performing that performs the AI trend/sentiment analysis
- For the design of the data model, see the file  '03_system_design_data_model.md'


## System design Decisions
### Core Components
TODO

### Tech stack
- For required cloud services (e.g. Calling an LLM), we use Google Cloud Platform
- For the validation of data models and llm responses, we use pydantic