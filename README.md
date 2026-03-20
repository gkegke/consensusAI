# ConsensusAI 

Live Demo: [live preview on heroku](https://consensusai-2e915a8fa798.herokuapp.com/)

ConsensusAI is a crowdsourced prediction engine that pits Human Sentiment against AI Model Consensus over real-world timelines. Users can vote and aggregate their forecasts alongside major LLMs like Google's Gemini and other models found on OpenRouter's network.

## 🎯 The Core Concept & USP

As AI models become more prevalent, they carry inherent biases, and human sentiment is often siloed away from AI logic. ConsensusAI bridges this gap by creating a unified platform that tracks both human and AI predictions to see who is historically more accurate.

**The "Vote to Reveal" Loop:** 
To prevent bias, users are required to lock in their own prediction or sentiment *before* they are allowed to see the aggregated Crowd Data and the AI Consensus Engine results.

### Supported Question Types
The platform dynamically alters validation logic and UI based on three core question types:

1. **Subjective Slider (0-100)**
   * *Example:* "Should Universal Basic Income (UBI) be implemented globally?"
   * *Logic:* Pure opinion. Cannot be objectively resolved, but tracks sentiment drift.
2. **Predictive Binary (Probability %)**
   * *Example:* "Will SpaceX successfully land an uncrewed Starship on Mars by Dec 31, 2026?"
   * *Logic:* Yes/No probability. Resolves on a specific future date.
3. **Predictive Choice (Categorical Distribution)**
   * *Example:* "Who will win the 2026 FIFA World Cup?"
   * *Logic:* Users assign probability percentages to specific outcomes. The backend enforces that all choices, plus an auto-calculated "Other" category, mathematically sum to exactly 100%.

---

## 🛠️ User CRUD Functionality

The application features full CRUD (Create, Read, Update, Delete) capabilities for standard authenticated users, primarily revolving around the Proposal System and Profile Management:

* **CREATE:** 
  * Users can submit new Question Proposals to the community (`QuestionCreateView`).
  * Users create Human Votes/Predictions on active questions (`VoteSubmitView`).
* **READ:** 
  * Users browse the Trending Proposals feed (`ProposalFeedView`).
  * Users view detailed AI breakdown results and community metrics on questions they have voted on (`QuestionDetailView`).
* **UPDATE:** 
  * Users can edit the text, context, and choices of their pending Question Proposals if they need refinement (`QuestionUpdateView`).
  * Users can update their personal Profile Bio (`ProfileUpdateView`).
* **DELETE:** 
  * Users can permanently delete their own Question Proposals if they change their mind, which cascades and removes all associated upvotes (`QuestionDeleteView`).

---

## 🎓 Fulfillment of Capstone Learning Outcomes (LO)

This project was built to directly fulfill the 8 core learning outcomes of the Capstone:

### LO1: Agile Methodology & Full-Stack Django
The project was planned using the Agile MoSCoW method, dividing work into 8 distinct phases (Foundation -> Authentication -> Question Generation -> AI Orchestration, etc.). It utilizes the complete Django MVT (Model-View-Template) architecture to deliver a functional full-stack web application.

### LO2: Data Modeling & Business Logic
The application manages a complex real-world domain (Predictions & Consensus). Custom business logic is heavily utilized, particularly in `questions/services.py` where the `process_vote` function validates categorical probabilities (ensuring they sum to 100% and auto-calculating the remainder).

### LO3: Authentication, Authorization & Permissions
* **Authentication:** Implemented using `django-allauth` for robust session and user management. 
* **Authorization:** Anonymous users can vote (tracked via IP/Session Key), but only authenticated users get a Dashboard, Profile, and the ability to submit new questions.
* **Permissions:** Custom mixins like `OwnerOnlyProposalMixin` ensure that a user can only *Edit* or *Delete* a question if they are the original author.

### LO4: Automated Testing
Automated tests are written using Django's `TestCase` to battle-test critical business logic. Examples include:
* `VoteServiceTests`: Validates the mathematical logic that blocks users from submitting >100% probability and tests the auto-balancing "Other" logic.
* `QuestionSecurityTests`: Verifies that the "Vote to Reveal" gate properly hides AI results from users who haven't voted yet.

### LO5: Version Control
The project utilizes Git and GitHub for distributed version control, utilizing structured commits and branching to manage the development of discrete epics and features.

### LO6: Cloud Deployment
The application is fully configured for cloud deployment on Heroku. It utilizes `gunicorn` as the web server, `dj-database-url` to connect to a Heroku PostgreSQL database, and `whitenoise` to serve static CSS/JS files reliably in a production environment.

### LO7: Object-Based Software Concepts
Custom Object-Oriented models drive the application. We utilize abstract base classes (like `TimeStampedModel` and `BaseVote`) to enforce DRY principles. Concrete classes inherit from these to create structured relationships (e.g., `ConsensusRun` containing multiple `AIResponse` objects, or `Question` tying to `HumanVote`).

### LO8: AI Orchestration & Tools
AI was leveraged in two ways:
1. **Software Development Process:** AI coding assistants were used to help plan the architecture, generate boilerplate, and refactor complex logic.
2. **App Functionality:** The core application natively orchestrates AI models using the `LiteLLM` and `Instructor` libraries. A background management command (`orchestrate_ai.py`) queries multiple LLMs simultaneously, synthesizes their answers, tracks API costs, and saves structured JSON data back to our Django Postgres database.