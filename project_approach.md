
### Goal

The main goal of this project is to develop the *Earnings-call-analyzer*, an application that supports analysts in their decision-making by extracting and evaluating a companies’ operational and financial standings, their risks & opportunities, and the commitment made by the management using earnings-call transcripts

### Objectives

* Develop a Data Pipeline extracting key information from unstructured earnings-calls and storing it into a suitable storage system  
* Develop 

### Approach

* Read paper ✅  
* Exploration of raw PDFs & identification of key data fields to extract ✅  
* System Design:  
  * Design of a suitable Data Model for storage of raw unstructured data and processed structured data that enables upstream evaluation use cases  
  * Design of a Data Extraction Pipeline  
  * Design of an upstream decision-support app analyzing the companies’ views on AI  over time, separately for each company
* Implementation of the Data Transformation Pipeline  
* Setup of the data storage system  
* Evaluation of the data transformation pipeline  
* Implementation of the decision-support app  
* Evaluation of the decision support app  
* Presentation of results (slides)

### Deliverables

* **End-to-end Data Extraction Pipeline** that is extracting key information (Summary of operations and financial standings, commitments of management, risks & opportunities) from raw earnings calls PDFs in a structured manner (code)  
* **Database** containing raw and processed earnings calls (TBD)  
* **Evaluation Pipeline** summarising how the companies’ views on AI changed over time, providing citations (code)  
* **Summaries for Nvidia, Microsoft, JPM and Bank of America (PDF)**

### Key Considerations

* For this prood-of-concept, the decision-support app shall evaluate how the companies’ discuss AI over time
* The PoC 

### Expected Challenges
* PDF parsing  
* Developing system for assessing the discussion on AI for each of the companies  
* Make the documents citable 


### Timeline
This system needs to be implemented within two working days. This means, we want to build a prototype that provides reasonable results but can have clear limitations (e.g. parsing of pdfs needs improvement), that can be addressed easily through extending/refining the system
