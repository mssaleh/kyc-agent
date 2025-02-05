# KYC Agent

## Business Overview
The KYC Agent is an advanced automated solution designed to streamline customer onboarding by replicating the decision-making of a human compliance officer. It processes identity documents (e.g., passport, national ID), performs multi-API compliance and risk checks (including sanctions, AML/CFT), and leverages AI-powered reasoning to produce comprehensive KYC reports. This automation reduces manual effort, minimizes risks, and improves overall efficiency in customer due diligence.

## Technical Overview
The project is built in Python 3.12 using FastAPI, employing asynchronous processing to handle concurrent tasks efficiently. Key technical features include:
- **Document Processing:** Extracts identity information using external APIs.
- **Multi-API Compliance Checks:** Integrates with various services (e.g., IDCHECK, WATCHMAN, DILISENSE, OPENSANCTIONS) for risk and compliance screening.
- **AI-Powered Analysis:** Utilizes the OpenAI Assistant API for intelligent reasoning and risk assessment based on aggregated data.
- **Report Generation:** Produces structured KYC reports in both JSON and PDF formats using FPDF.
- **Robust Logging & Error Handling:** Implements comprehensive logging to aid in tracing and debugging.
- **Containerization:** Deployable via Docker and managed with Docker Compose for simplified scaling and deployment.

## Developer Instructions
1. **Installation:**
   - Clone the repository.
   - Copy `.env.example` to `.env` and update the necessary API keys and settings.
   - Install dependencies using Poetry:
     ```
     poetry install
     ```
2. **Local Development:**
   - Run the service using Uvicorn:
     ```
     uvicorn kyc_service:app --host 0.0.0.0 --port 8000 --reload
     ```
3. **Containerized Deployment:**
   - Build the Docker image:
     ```
     docker build -t kyc-agent .
     ```
   - Run the container:
     ```
     docker run -p 8000:8000 kyc-agent
     ```
   - Alternatively, use Docker Compose:
     ```
     docker compose up --build
     ```
     When using local environment for development, you can stop and remove the running containers with
     ```
     docker compose down
     ```
     No need to prune to update the container, simply use this command for rebuild
     ```
     docker compose up --build --always-recreate-deps --force-recreate
     ```
     Please note that all of the above commands will run docker interactively, so you can stop it with CTRL+C in the terminal.
     If you want docker to release the terminal, you can add `-d` to `docker` or `docker compose` commands.

4. **Testing & Debugging:**
   - Ensure proper configuration of environment variables in `.env`.
   - Monitor log outputs for detailed error handling and debugging messages.

## API Endpoints

### POST /analyze_document
- **Purpose:** Initiates the KYC analysis process by accepting an image of an ID document and an optional callback URL.
- **Parameters:** 
  - `document`: File (image)
  - `callback_url` (optional): URL for job status updates.
- **Example:**
  ```bash
  curl -X POST -F "document=@/path/to/document.jpg" -F "callback_url=https://your.callback.url" http://localhost:8000/analyze_document
  ```
- **Response:** Returns a job object containing a unique `job_id` and status such as `submitted`.

### GET /get_job_status
- **Purpose:** Retrieves the current status of a KYC job.
- **Parameters:**
  - `job_id`: Unique identifier for the job.
- **Example:**
  ```bash
  curl "http://localhost:8000/get_job_status?job_id=<job_id>"
  ```
- **Response:** A JSON object with detailed job status, progress, and any error messages.

### GET /get_report
- **Purpose:** Provides the final KYC report in either JSON or PDF format.
- **Parameters:**
  - `job_id`: Unique identifier for the job.
  - `format`: Either `json` or `pdf`.
- **Example:**
  ```bash
  curl "http://localhost:8000/get_report?job_id=<job_id>&format=pdf" -o report.pdf
  ```
- **Response:** Downloads the report in the requested format.

### GET /health
- **Purpose:** Health check endpoint to confirm the service is running.
- **Example:**
  ```bash
  curl http://localhost:8000/health
  ```
- **Response:** A simple status message indicating service availability.
