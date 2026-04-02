// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract FlightInsurance {
    struct Policy {
        string flightNumber;
        uint256 coverageAmount; // Teminat Tutarı (Wei cinsinden)
        string customerId; // Müşteri Kimlik No
        string phoneNumber; // Telefon Numarası
        bool isActive;
        bool isPayoutIssued;
        address payable customerAddress; // Müşterinin Cüzdan Adresi
    }

    address public owner; // Sözleşme Sahibi / Oracle / Arka Uç sistemi yetkili adresi

    // Policy ID'den Poliçe bilgilerine erişim
    mapping(uint256 => Policy) public policies;
    uint256 public policyCount;

    event PolicyCreated(uint256 policyId, string flightNumber, address customer, uint256 coverageAmount);
    event PayoutIssued(uint256 policyId, string flightNumber, address customer, uint256 amount);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner/oracle can call this method");
        _;
    }

    // Poliçe oluşturma fonksiyonu (Yalnızca owner tarafından çağrılabilir)
    function createPolicy(
        string memory _flightNumber,
        uint256 _coverageAmount,
        string memory _customerId,
        string memory _phoneNumber,
        address payable _customerAddress
    ) public onlyOwner {
        policyCount++;
        policies[policyCount] = Policy({
            flightNumber: _flightNumber,
            coverageAmount: _coverageAmount,
            customerId: _customerId,
            phoneNumber: _phoneNumber,
            isActive: true,
            isPayoutIssued: false,
            customerAddress: _customerAddress
        });

        emit PolicyCreated(policyCount, _flightNumber, _customerAddress, _coverageAmount);
    }

    // Uçuş İptali/Gecikmesi durumunda Oracle tarafından tetiklenecek fonksiyon
    function issuePayout(uint256 _policyId) public onlyOwner {
        Policy storage policy = policies[_policyId];
        require(policy.isActive, "Policy is not active");
        require(!policy.isPayoutIssued, "Payout already issued");
        
        // Akıllı sözleşmede yeterli bakiye olup olmadığını kontrol et
        require(address(this).balance >= policy.coverageAmount, "Insufficient contract balance for coverage");

        policy.isPayoutIssued = true;
        policy.isActive = false;

        // Müşteriye teminat miktarını yatır
        policy.customerAddress.transfer(policy.coverageAmount);

        emit PayoutIssued(_policyId, policy.flightNumber, policy.customerAddress, policy.coverageAmount);
    }

    // Sözleşmenin içine teminatlar için önceden bakiye aktarma fonksiyonu
    function fundContract() public payable {}
}
