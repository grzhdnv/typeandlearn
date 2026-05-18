# TODO

## Text input

- [ ] **Create backend with database connection**
  - [ ] Or could just store files for now

- [ ] **Upload text**
  - [ ] Support `.txt` or `.md`
  - [ ] Support `.pdf` (Gemini can read PDFs and transcribe them into text format)
  - [ ] Handle inappropriate file extensions
  - [ ] Store text in database

- [ ] **Process text**
  - [ ] Analyze text for word frequency  
    - [ ] Lemma analysis with Python and NLTK
  - [ ] Send text to LLM (Gemini for now)
    - [ ] Produce practice sentences
      - [ ] Store practice sentences in database
    - [ ] Analyze text difficulty
  - [ ] Prepare word translations and store them in DB (for translation hints)

- [ ] **Print text sentence by sentence**
  - [ ] Decide storage strategy:
    - [ ] Store sentences individually
    - [ ] Or extract sentences dynamically from full text (for original text)