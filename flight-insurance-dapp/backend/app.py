import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from pydantic import BaseModel
import solcx
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from database import PolicyRecord, engine, create_db_and_tables
from oracle import check_flight_status
from sms_service import send_sms

app = FastAPI(title="Uçuş Gecikme Sigortası API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

w3 = Web3(EthereumTesterProvider())
w3.eth.default_account = w3.eth.accounts[0] # deploy eden yetkili hesap (Backend/Oracle Owner)

contract_interface = None
contract_instance = None

def compile_and_deploy():
    global contract_instance
    print("Solidity Contract derleniyor ve deploy ediliyor...")
    
    solcx.install_solc("0.8.20")
    solcx.set_solc_version("0.8.20")
    
    contract_path = os.path.join(os.path.dirname(__file__), '..', 'contracts', 'FlightInsurance.sol')
    with open(contract_path, "r", encoding="utf-8") as f:
        contract_source = f.read()

    compiled_sol = solcx.compile_source(
        contract_source,
        output_values=['abi', 'bin']
    )
    contract_id, interface = compiled_sol.popitem()
    
    FlightContract = w3.eth.contract(abi=interface['abi'], bytecode=interface['bin'])
    tx_hash = FlightContract.constructor().transact({'from': w3.eth.accounts[0]})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    contract_instance = w3.eth.contract(address=receipt.contractAddress, abi=interface['abi'])
    
    # Akıllı sözleşmeyi müşterilere ödeme yapabilmesi için fonlayalım (100 ETH)
    contract_instance.functions.fundContract().transact({'from': w3.eth.accounts[0], 'value': w3.to_wei(100, 'ether')})
    print(f"Sozlesme Deploy Edildi. Adres: {receipt.contractAddress}")

def get_session():
    with Session(engine) as session:
        yield session

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    compile_and_deploy()

class PurchaseRequest(BaseModel):
    flight_number: str
    coverage_amount: float
    customer_id: str
    phone_number: str
    customer_address: str 

@app.post("/api/buy_insurance")
def buy_insurance(req: PurchaseRequest, session: Session = Depends(get_session)):
    coverage_wei = w3.to_wei(req.coverage_amount, 'ether')
    user_address = w3.to_checksum_address(req.customer_address)
    
    tx_hash = contract_instance.functions.createPolicy(
        req.flight_number,
        coverage_wei,
        req.customer_id,
        req.phone_number,
        user_address
    ).transact({'from': w3.eth.accounts[0]})
    
    w3.eth.wait_for_transaction_receipt(tx_hash)
    
    policy_id = contract_instance.functions.policyCount().call()

    record = PolicyRecord(
        policy_id=policy_id,
        flight_number=req.flight_number,
        coverage_amount=req.coverage_amount,
        customer_id=req.customer_id,
        phone_number=req.phone_number,
        customer_address=user_address,
        status="Satin Alindi - Bekliyor"
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    return {"message": "Poliçe oluşturuldu", "policy": record}

@app.get("/api/policies")
def get_policies(session: Session = Depends(get_session)):
    return session.exec(select(PolicyRecord)).all()

@app.post("/api/oracle/trigger_check")
def trigger_oracle_check(session: Session = Depends(get_session)):
    pending_policies = session.exec(select(PolicyRecord).where(PolicyRecord.status == "Satin Alindi - Bekliyor")).all()
    logs = []
    
    for pol in pending_policies:
        status = check_flight_status(pol.flight_number)
        if status in ["CANCELLED", "DELAYED"]:
            try:
                tx_hash = contract_instance.functions.issuePayout(pol.policy_id).transact({'from': w3.eth.accounts[0]})
                w3.eth.wait_for_transaction_receipt(tx_hash)
                
                sms_message = f"Sayin Musterimiz, {pol.flight_number} ucusunuz {status} statusundedir. {pol.coverage_amount} ETH Teminat tutari hesabiniza yatirilmistir."
                send_sms(pol.phone_number, sms_message)
                
                pol.status = f"Odendi ({status})"
                session.add(pol)
                
                logs.append({"flight": pol.flight_number, "status": "ODENDI", "msg": f"{pol.coverage_amount} ETH yatirildi"})
            except Exception as e:
                logs.append({"flight": pol.flight_number, "status": "HATA", "msg": str(e)})
        else:
            logs.append({"flight": pol.flight_number, "status": "BEKLIYOR", "msg": "Ucus Normal"})
            
    session.commit()
    return {"message": "Oracle kontrolu tamamlandi", "logs": logs}
