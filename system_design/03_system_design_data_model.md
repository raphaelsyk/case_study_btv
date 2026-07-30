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
  * List of text chunks, with following metadata on each chunk: speaker, page  
* How can this be retrieved: Go through all pages


Q\&A section:

* Data Model:  
  * List of text chunks, with following metadata on each chunk: speaker, page, \[Optional: Type as ‘question’ or ‘answer’\]  
* How can this be retrieved: Go through all pages
