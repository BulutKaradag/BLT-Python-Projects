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

## 🎯 Projenin Amacı (Overview)
Bu proje, yolcuların uçuş gecikmelerine veya iptallerine karşı **Ethereum** (Kripto para) teminatlı akıllı sözleşmeler aracılığıyla sigorta alabilmelerini sağlayan hibrit bir Web3/Web2 uygulamasıdır. Uçuşunuz rötar yaparsa, akıllı sözleşme insani onaya (ve bürokrasiye) gerek kalmadan poliçe bedelini anında cüzdanınıza iade eder!

---

## ⚙️ Sistem Mimarisi & Topoloji

Aşağıdaki topoloji, Web2 arayüzleriyle Web3 (Blockchain) ve Dış Servis (Oracle) bileşenlerinin nasıl uçtan uca haberleştiğini gösterir:

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

## 🛠️ Nasıl Çalışır? (İş Akışı)

Sistem mimarisi, *satın alma* ve *tazminat ödeme* olmak üzere iki ana faza ayrılmıştır:

```mermaid
flowchart LR
    subgraph Faz 1: Satın Alma ve Bekleme
    direction LR
        A(["👤 Müşteri Poliçe Alır"]) --> B["💾 DB'ye Kaydedilir"]
        B --> C["📜 Blockchain'de Sözleşme Açılır"]
        C --> D(["⏳ Uçuş Saati Beklenir"])
    end

    subgraph Faz 2: Oracle Kontrolü ve Ödeme
    direction LR
        E["📡 Oracle Tetiklenir"] --> F{"✈️ Rötar veya İptal mi?"}
        
        F -- "Evet" --> G["💸 Akıllı Sözleşme ETH Gönderir"]
        G --> H["📱 Müşteriye SMS Gider"]
        H --> I["🔄 Poliçe 'Ödendi' Olur"]
        
        F -- "Hayır" --> K["✅ Uçuş Zamanında"]
        K --> L(["⛔ İşlem Tamam (Aksiyon Yok)"])
    end

    D -->|"Zamanı Gelince"| E

    classDef highlight fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px;
    classDef decision fill:#fff3e0,stroke:#ff9800,stroke-width:2px;
    class A,C,D,E,G,H,I highlight;
    class F decision;
```

---

## 🚀 Kurulum & Çalıştırma Yönergesi

### 1️⃣ Backend'i Başlatmak
Terminalden proje dizinindeki **backend** klasörüne geçin ve sanal ortamı aktif ettikten sonra Uvicorn'u başlatın:
```bash
# Sanal Ortam Aktifleştirme (Windows)
..\venv\Scripts\activate

# Backend sunucusunu başlatma
uvicorn app:app --reload
```
> 💡 API sunucusu `http://localhost:8000` adresinde ayağa kalkacak ve **Solidity akıllı sözleşmesi otomatik olarak derlenip** yerel ağda (EthTester) oluşturulacaktır.

### 2️⃣ Frontend'i Çalıştırmak
Yeni bir terminal açın ve genel kök dizinden **frontend** klasörüne geçin:
```bash
cd frontend
python -m http.server 8080
```
> 🌐 Tarayıcınızdan `http://localhost:8080` adresine giderek dApp (Kullanıcı Paneli) arayüzünü görüntüleyebilir ve hemen poliçe satın alabilirsiniz.

---

## 🔒 Güvenlik & İşlem Maliyeti Mimarisi
* Müşteriye ait veriler (telefon, işlem durumu vb.) işlem maliyetini artırmamak için **SQLite** veritabanında Off-Chain olarak tutulur.
* Finansal kilit işlemleri, teminat tutarları ve parayı serbest bırakma mantığı ise sadece manipüle edilemeyen **On-Chain (Ethereum Sözleşmesi)** üzerinde şeffaf bir şekilde gerçekleşir. 
