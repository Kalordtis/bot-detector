# Bot detetor


## Behavioral Abuse Detection System

EcoSec is a behavioral abuse detection system designed to identify suspicious account activity and surface high-risk accounts for analyst review.

The system analyzes account behavior across transactions, recipients, senders, and sessions to identify patterns that may indicate automated or coordinated abuse.

## Features

* **Account monitoring**: Tracks behavioral activity across monitored accounts
* **Risk scoring**: Identifies accounts exhibiting suspicious behavioral patterns
* **Investigation queue**: Surfaces high-risk accounts for analyst review
* **Behavioral signals**: Uses transaction and session activity to identify anomalous behavior
* **Analyst dashboard**: Provides a centralized interface for reviewing suspicious accounts

## Dashboard

The investigation dashboard provides analysts with an overview of monitored accounts, including:

* Account suspicion score
* First trade
* Total amount sent
* Number of receivers
* Number of senders
* Number of sessions
* Investigation actions

## Tech Stack

* Python
* Flask
* HTML/CSS
* JavaScript
* Git/GitHub

## Project Structure

```text
epic_ecosec_project/
├── app.py
├── templates/
├── static/
├── requirements.txt
├── .gitignore
└── README.md
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Kalordtis/bot-detector.git
cd bot-detector
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python app.py
```

Then open the local URL shown in the terminal.

## Purpose

EcoSec is a prototype focused on using behavioral signals to help analysts prioritize accounts for investigation rather than automatically making enforcement decisions.

## Status

This project is currently a prototype and is intended for experimentation and development.
