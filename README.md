<p align="center">
  <img src="https://github.com/user-attachments/assets/ed5b23ba-3e7e-46fd-a18c-8fcc520bee52" alt="kpmg-logo-1" width="200" />
</p>

<h1 align="center">GenAI Developer Assessment Assignment</h1>


You are given 4 days to complete this assessment. For this assignment, you have access to the following Azure OpenAI resources:

- Document Intelligence for Optical Character Recognition (OCR)
- GPT-4o and GPT-4o Mini as Large Language Models (LLMs)
- ADA 002 for text embeddings

All required resources have already been deployed in Azure. There is no need to create additional resources for this assignment.

The necessary Azure credentials have been included in the email containing this assignment. Please refer to these credentials for accessing the pre-deployed resources.

## **IMPORTANT NOTE:** Use only the native Azure OpenAI SDK library, not LangChain or other frameworks.


## Repository Contents

The Git repository for this assignment contains two important folders:

- **phase1_data**: This folder contains:
  - 1 raw PDF file that you can use to create more examples if needed
  - 3 filled documents for testing and development

- **phase2_data**: This folder contains:
  - HTML files that serve as the knowledge base for Part 2 of the home assignment

## Part 1: Field Extraction using Document Intelligence & Azure OpenAI

### Task
Develop a system that extracts information from ביטוח לאומי (National Insurance Institute) forms using OCR and Azure OpenAI.

### Requirements
1. Use Azure Document Intelligence for OCR. [Learn more about Document Intelligence layout](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept-layout?view=doc-intel-4.0.0&tabs=sample-code)
2. Use Azure OpenAI to extract fields and generate JSON output.
3. Create a simple UI to upload a PDF/JPG file and display the resulting JSON. You can use **Streamlit** or **Gradio** for the UI implementation.
4. Handle forms filled in either Hebrew or English.
5. For any fields not present or not extractable, use an empty string in the JSON output.
6. Implement a method to validate the accuracy and completeness of the extracted data.

### Desired Output Format:
```json
{
  "lastName": "",
  "firstName": "",
  "idNumber": "",
  "gender": "",
  "dateOfBirth": {
    "day": "",
    "month": "",
    "year": ""
  },
  "address": {
    "street": "",
    "houseNumber": "",
    "entrance": "",
    "apartment": "",
    "city": "",
    "postalCode": "",
    "poBox": ""
  },
  "landlinePhone": "",
  "mobilePhone": "",
  "jobType": "",
  "dateOfInjury": {
    "day": "",
    "month": "",
    "year": ""
  },
  "timeOfInjury": "",
  "accidentLocation": "",
  "accidentAddress": "",
  "accidentDescription": "",
  "injuredBodyPart": "",
  "signature": "",
  "formFillingDate": {
    "day": "",
    "month": "",
    "year": ""
  },
  "formReceiptDateAtClinic": {
    "day": "",
    "month": "",
    "year": ""
  },
  "medicalInstitutionFields": {
    "healthFundMember": "",
    "natureOfAccident": "",
    "medicalDiagnoses": ""
  }
}
```
Here is a translation of the fields in Hebrew: 
```json
{
  "שם משפחה": "",
  "שם פרטי": "",
  "מספר זהות": "",
  "מין": "",
  "תאריך לידה": {
    "יום": "",
    "חודש": "",
    "שנה": ""
  },
  "כתובת": {
    "רחוב": "",
    "מספר בית": "",
    "כניסה": "",
    "דירה": "",
    "ישוב": "",
    "מיקוד": "",
    "תא דואר": ""
  },
  "טלפון קווי": "",
  "טלפון נייד": "",
  "סוג העבודה": "",
  "תאריך הפגיעה": {
    "יום": "",
    "חודש": "",
    "שנה": ""
  },
  "שעת הפגיעה": "",
  "מקום התאונה": "",
  "כתובת מקום התאונה": "",
  "תיאור התאונה": "",
  "האיבר שנפגע": "",
  "חתימה": "",
  "תאריך מילוי הטופס": {
    "יום": "",
    "חודש": "",
    "שנה": ""
  },
  "תאריך קבלת הטופס בקופה": {
    "יום": "",
    "חודש": "",
    "שנה": ""
  },
  "למילוי ע\"י המוסד הרפואי": {
    "חבר בקופת חולים": "",
    "מהות התאונה": "",
    "אבחנות רפואיות": ""
  }
}
```

## Part 2: Microservice-based ChatBot Q&A on Medical Services


### Task
Develop a microservice-based chatbot system that answers questions about medical services for Israeli health funds (Maccabi, Meuhedet, and Clalit) based on user-specific information. The system should be capable of handling multiple users simultaneously without maintaining server-side user memory.

### Core Requirements

1. **Microservice Architecture**
   - Implement the chatbot as a stateless microservice using FastAPI or Flask.
   - Handle multiple concurrent users efficiently.
   - Manage all user session data and conversation history client-side (frontend).

2. **User Interface**
   - Develop a frontend using **Gradio** or **Streamlit**.
   - Implement two main phases: User Information Collection and Q&A.

3. **Azure OpenAI Integration**
   - Utilize the Azure OpenAI client library for Python.
   - Implement separate prompts for the information collection and Q&A phases.

4. **Data Handling**
   - Use provided HTML files provided in the 'phase2_data' folder as the knowledge base for answering questions.

5. **Multi-language Support**
   - Implement support for Hebrew and English. 

6. **Error Handling and Logging**
   - Implement comprehensive error handling and validation.
   - Create a logging system to track chatbot activities, errors, and interactions.

### Detailed Specifications

#### User Information Collection Phase
Collect the following user information:
- First and last name
- ID number (valid 9-digit number)
- Gender
- Age (between 0 and 120)
- HMO name (מכבי | מאוחדת | כללית)
- HMO card number (9-digit)
- Insurance membership tier (זהב | כסף | ארד)
- Provide a confirmation step for users to review and correct their information.

**Note:** This process should be managed exclusively through the LLM, avoiding any hardcoded question-answer logic or form-based filling in the UI


#### Q&A Phase
- Transition to answering questions based on the user's HMO and membership tier.
- Utilize the knowledge base from provided HTML files.

#### State Management
- Pass all necessary user information and conversation history with each request to maintain statelessness.

### Evaluation Criteria

1. Microservice Architecture Implementation
2. Technical Proficiency (Azure OpenAI usage, data processing)
3. Prompt Engineering and LLM Utilization
4. Code Quality and Organization
5. User Experience
6. Performance and Scalability
7. Documentation
8. Innovation
9. Logging and Monitoring Implementation

### Submission Guidelines
1. Provide source code via GitHub.
2. Include setup and run instructions.

**Good luck! For any questions, feel free to contact me.**

Dor Getter.
