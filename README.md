🧠 FacterAI
Fast Evidence. Clear Answers.
FacterAI is an intelligent legal and biomedical research engine that delivers citation-backed answers in real time.
It was built as a scalable version of my SageMind project — focused on summarization, retrieval, and citation tracking for complex legal and medical queries.

🚀 Features
LLM-backed question answering using OpenAI API
Real-time semantic search powered by AWS OpenSearch
Flask API + JavaScript frontend for seamless query experience
Automatic citation generation from verified research sources
Optimized inference pipeline for high recall and clean UI
Modular architecture — easily extendable for domain-specific reasoning (e.g., healthcare, law, finance)

🧩 Tech Stack
Frontend: HTML, CSS, JavaScript
Backend: Python (Flask)
Database / Search: AWS OpenSearch
LLM Integration: OpenAI API
Deployment: AWS App Runner + S3 + CloudFront + Route53

🧰 Setup
Clone this repository:
git clone https://github.com/SamWorley1/FacterAI.git
cd FacterAI

Create and activate a virtual environment:
python3 -m venv venv
source venv/bin/activate

Install dependencies:
pip install -r requirements.txt

Set your environment variables in a .env file:
OPENAI_API_KEY=your_openai_key
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret

Run the app locally:
python app.py
or
flask run

🧠 Future Plans
Add multi-domain model routing (legal vs medical)
Improve retrieval precision with cross-encoder re-ranking
Integrate dynamic citation validation pipeline
Release public-facing dashboard for structured summaries

👤 Author
Sam Worley
Data Scientist & AI Engineer
🌐 LinkedIn
✉️ samueljworley@gmail.com