## Trajectory — Architecture and Local Development Environment

### Objective
Develop the FloodSentry implementation and architecture using a reproducible local development stack.

### Initial planning / prompt source
The initial project prompt and planning conversation was created using Gemini.

Conversation:
https://share.gemini.google/Z4y0PTByIk1y

### Development agent
GLM 5.3 Flash

### Human context provided to the agent
The developer already had PostgreSQL installed locally and experience using Django for web development.

Rather than allowing the coding agent to choose an arbitrary stack, the developer instructed the agent to build around the existing local environment:

- Django for the web application
- PostgreSQL/PostGIS for spatial data
- Python for the backend and modelling workflow

### Agent task
The coding agent was asked to continue implementation of the FloodSentry project using the existing architecture and the selected Django/PostgreSQL environment.

### Human engineering decision
The use of Django and PostgreSQL was not simply an autonomous agent decision.

The developer deliberately selected these technologies because:

1. PostgreSQL was already available in the local environment.
2. Django was familiar to the developer.
3. GeoDjango/PostGIS suited the spatial nature of flood modelling.
4. The stack allowed the project to be run and inspected locally.
5. Keeping the environment familiar reduced setup complexity during the hackathon.

### Output
The agent assisted with development of the project code and architecture, including the Django-based application structure and PostgreSQL/PostGIS-backed spatial workflow.

### Evidence
- Gemini planning/prompt conversation
- GitHub commit history
- ARCHITECTURE.md
- Django application code
- PostgreSQL/PostGIS configuration
- management commands and tests
