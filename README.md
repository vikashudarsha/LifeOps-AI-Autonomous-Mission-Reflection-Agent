# 🧠 LifeOps AI – Autonomous Mission Reflection Agent

LifeOps AI is an autonomous mission management system powered by **Google Gemini 3**.
It helps users plan long-term goals, execute daily tasks, reflect on performance, and
adapt strategies intelligently over time.

This project was built for the **Gemini 3 Hackathon** and demonstrates how Gemini 3 can
be used as a reasoning engine for planning, reflection, and adaptation workflows.

---

## 🚀 What is LifeOps AI?

LifeOps AI acts like a **personal mission operator**.

Instead of just generating tasks, it:
- Plans structured missions
- Observes execution behavior
- Reflects on outcomes
- Adapts future strategies automatically

All intelligence is driven by **Gemini 3**.

---

## 🤖 Gemini 3 Integration (Core of the Project)

This project is built using the **Google Gemini 3 API**.

Gemini 3 is used to:
- Generate mission plans from high-level goals
- Analyze execution logs and user behavior
- Detect patterns, root causes, and planning mistakes
- Adapt future plans based on reflection insights

### 🧠 Gemini Model Used
- **Gemini 3 Flash** (via Google AI Studio)

Gemini 3 acts as the **Planner Agent**, **Reflector Agent**, and **Adaptation Engine**
inside the backend.

---

## ✨ Key Features

- 🧩 **Mission Planning**
  - Convert a goal into structured phases and tasks using Gemini 3

- 📅 **Daily Execution Planning**
  - Generate realistic daily task plans based on time availability

- 🧠 **Reflection & Adaptation**
  - Analyze execution history
  - Detect behavior trends and planning mistakes
  - Adapt strategy automatically

- 📊 **Reflection Dashboard (UI)**
  - Visualizes patterns, root causes, confidence level, and strategy updates

---

## 🛠️ Built With

### Backend
- **Python**
- **FastAPI**
- **Google Gemini 3 API**
- Uvicorn

### Frontend
- **React**
- Vite
- JavaScript (ES6)

### AI / Platform
- **Google AI Studio**
- **Gemini 3 Flash**

---

## 🧪 How It Works (High-Level Flow)

1. User creates a mission (goal, days, time, constraints)
2. Gemini 3 generates a structured mission plan
3. User logs daily execution results
4. Gemini 3 reflects on behavior and outcomes
5. Strategy is adapted automatically
6. UI displays reflection and adaptation insights

---

## 📂 Project Structure

LifeOps-AI/
│
├── backend/
│ ├── app.py
│ ├── agents/
│ │ ├── planner.py
│ │ ├── executor.py
│ │ └── reflector.py
│ ├── gemini/
│ │ └── client.py
│ ├── routes/
│ │ └── mission.py
│ ├── memory/
│ │ └── state.json
│ └── requirements.txt
│
├── frontend/
│ └── lifeops-ui/
│ ├── index.html
│ ├── src/
│ │ ├── App.jsx
│ │ ├── api.js
│ │ ├── main.jsx
│ │ ├── index.css
│ │ └── screens/
│ │ └── ReflectionScreen.jsx
│ └── package.json
│
└── README.md

---

## ▶️ How to Run the Project

### 🔹 Backend Setup

```bash
cd backend
pip install -r requirements.txt
Create a .env file inside backend/:

GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=models/gemini-3-flash

Run the backend:

uvicorn app:app --reload --port 8000


Backend will be available at:

http://127.0.0.1:8000

http://127.0.0.1:8000/docs

🔹 Frontend Setup
cd frontend/lifeops-ui
npm install
npm run dev


Frontend will be available at:

http://localhost:5173

🧪 Testing Instructions (for Judges)

Start the backend and frontend

Open the frontend UI

Click Start Demo Mission

Log sample execution data

Click Run Reflection

Observe reflection insights and adaptation output

All reasoning, reflection, and adaptation are generated using Google Gemini 3.

🎥 Demo Video

▶️ YouTube Demo:
https://youtu.be/yGGkw9c1oJ0

🏆 Hackathon Note

This project was created from scratch for the Gemini 3 Hackathon.
It demonstrates a real-world application of Gemini 3 beyond simple chat use cases,
showing how Gemini can operate as an autonomous reasoning agent.

📌 Future Improvements

User authentication & profiles

Multi-mission support

Timeline visualization

Advanced adaptation strategies

Mobile-friendly UI

❤️ Final Note

LifeOps AI explores how Gemini 3 can think beyond prompts —
acting as a planner, analyst, and adaptive strategist.
