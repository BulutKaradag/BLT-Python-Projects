<div align="center">
  <img src="https://img.icons8.com/color/150/000000/ethereum.png" alt="Ethereum Logo" width="100"/>
  <h1>🛫 Decentralized Flight Insurance dApp</h1>
  <p><strong>A Blockchain-powered Smart Insurance System for Flight Delays and Cancellations</strong></p>

  <p>
    <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
    <img src="https://img.shields.io/badge/Solidity-363636?style=for-the-badge&logo=solidity&logoColor=white" />
    <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
    <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" />
    <img src="https://img.shields.io/badge/Web3.py-F16822?style=for-the-badge&logo=python&logoColor=white" />
  </p>
</div>

---

## 🎯 Overview
This project is a hybrid Web3/Web2 application that allows passengers to purchase decentralized insurance against flight delays and cancellations using **Ethereum** smart contracts. If a flight is delayed or cancelled, the smart contract automatically refunds the policy amount directly to your wallet—without human bureaucracy or approval delays!

---

## ⚙️ System Architecture & Topology

The topology below demonstrates how Web2 interfaces seamlessly communicate with Web3 (Blockchain) and External Services (Oracle):

```mermaid
graph TD
    subgraph Client
        Browser(["🌐 Web Browser"])
        Frontend["🎨 Frontend App (HTML/JS/CSS)"]
    end

    subgraph Backend_Server
        API["⚙️ FastAPI Application (app.py)"]
        ORACLE["📡 Oracle Module (oracle.py)"]
        SMS_SVC["📱 SMS Service (sms_service.py)"]
        DB[("💾 SQLite Database (insurance_db)")]
    end

    subgraph Blockchain_Node
        ETH["⛓️ Local Ethereum Node (EthTester)"]
        SC{{"📜 FlightInsurance.sol"}}
    end

    Browser -->|"Interacts"| Frontend
    Frontend -->|"REST API"| API
    
    API <-->|"Saves/Reads"| DB
    API <-->|"Web3.py (Transact)"| ETH
    ETH <-->|"Executes Logic"| SC
    
    API -->|"Triggers Check"| ORACLE
    API -->|"Triggers Notification"| SMS_SVC
```

---

## 🛠️ How It Works (Workflow)

The system functionality is divided into two primary phases: *Purchasing* and *Payouts*:

```mermaid
flowchart LR
    subgraph Phase 1: Purchase and Wait
    direction LR
        A(["👤 User Purchases Policy"]) --> B["💾 Backend saves to DB"]
        B --> C["📜 Create Smart Contract Record"]
        C --> D(["⏳ Wait for Flight Time"])
    end

    subgraph Phase 2: Oracle Check and Payout
    direction LR
        E["📡 Trigger Oracle Check"] --> F{"✈️ Delayed or Cancelled?"}
        
        F -- "Yes" --> G["💸 Smart Contract Transfers ETH"]
        G --> H["📱 Send SMS Notification"]
        H --> I["🔄 Policy Status set to 'Paid'"]
        
        F -- "No" --> K["✅ Flight is On-Time"]
        K --> L(["⛔ Process Completed (No Action)"])
    end

    D -->|"Time Elapses"| E

    classDef highlight fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px;
    classDef decision fill:#fff3e0,stroke:#ff9800,stroke-width:2px;
    class A,C,D,E,G,H,I highlight;
    class F decision;
```

---

## 🚀 Installation & Usage Guide

### 1️⃣ Starting the Backend
From the project root directory, navigate to the **backend** folder, activate your virtual environment, and start the Uvicorn server:
```bash
# Activate Virtual Environment (Windows)
..\venv\Scripts\activate

# Start the Backend Server
uvicorn app:app --reload
```
> 💡 *The API server will run at `http://localhost:8000`. The **Solidity smart contract will automatically compile** and deploy to the local Ethereum test network (EthTester).*

### 2️⃣ Starting the Frontend
Open a new terminal session, navigate to the **frontend** folder from the root directory:
```bash
cd frontend
python -m http.server 8080
```
> 🌐 *Visit `http://localhost:8080` in your browser to view the dApp User Interface and start purchasing policies.*

---

## 🔒 Security & Optimization Strategy
* Customer data (phone numbers, status, etc.) is kept securely Off-Chain in a **SQLite** database to prevent unnecessary transaction (Gas) costs.
* Financial locks, collateral logic, and fund release mechanisms are strictly maintained on **On-Chain (Ethereum Contracts)** ensuring the policy payout architecture is transparent and robust.
