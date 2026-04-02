const API_URL = "http://localhost:8000/api";

document.addEventListener("DOMContentLoaded", () => {
    loadPolicies();

    const form = document.getElementById("insuranceForm");
    const triggerOracleBtn = document.getElementById("triggerOracleBtn");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const submitBtn = document.getElementById("submitBtn");
        submitBtn.disabled = true;
        submitBtn.innerText = "Processing...";

        const data = {
            flight_number: document.getElementById("flightNumber").value,
            customer_id: document.getElementById("customerId").value,
            phone_number: document.getElementById("phoneNumber").value,
            coverage_amount: parseFloat(document.getElementById("coverageAmount").value),
            customer_address: document.getElementById("walletAddress").value
        };

        try {
            const res = await fetch(`${API_URL}/buy_insurance`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });

            const result = await res.json();
            if (res.ok) {
                showMessage("Policy successfully created and saved on the smart contract!", "success");
                form.reset();
                loadPolicies();
            } else {
                showMessage("An error occurred: " + result.detail, "error");
            }
        } catch (error) {
            showMessage("Could not connect to the server. Is backend running?", "error");
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerText = "Purchase Insurance";
        }
    });

    triggerOracleBtn.addEventListener("click", async () => {
        triggerOracleBtn.disabled = true;
        triggerOracleBtn.innerText = "Checking...";

        try {
            const res = await fetch(`${API_URL}/oracle/trigger_check`, {
                method: "POST"
            });
            const result = await res.json();
            
            if(res.ok) {
                console.log("Oracle Logs:", result.logs);
                loadPolicies();
            } else {
                alert("An error occurred");
            }
        } catch(error) {
            alert("Could not trigger Oracle. Is backend running?");
        } finally {
            triggerOracleBtn.disabled = false;
            triggerOracleBtn.innerText = "🔄 Trigger Oracle Check";
        }
    });
});

async function loadPolicies() {
    try {
        const res = await fetch(`${API_URL}/policies`);
        const policies = await res.json();
        const tbody = document.querySelector("#policiesTable tbody");
        tbody.innerHTML = "";

        policies.forEach(p => {
            const tr = document.createElement("tr");
            let statusClass = p.status.includes("Odendi") ? "status-paid" : "status-waiting";
            
            // Map Turkish backend status strings to English for UI
            let displayStatus = p.status;
            if(p.status === "Satin Alindi - Bekliyor") displayStatus = "Purchased (Waiting)";
            if(p.status.startsWith("Odendi")) displayStatus = p.status.replace("Odendi", "Paid Payout");
            if(p.status === "Iptal") displayStatus = "Cancelled";
            
            tr.innerHTML = `
                <td>#${p.policy_id}</td>
                <td><strong>${p.flight_number}</strong></td>
                <td>${p.customer_id}</td>
                <td>${p.coverage_amount} ETH</td>
                <td><span class="status-badge ${statusClass}">${displayStatus}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch(err) {
        console.error("Failed to load policies", err);
    }
}

function showMessage(text, type) {
    const msgDiv = document.getElementById("formMessage");
    msgDiv.innerText = text;
    msgDiv.className = `message ${type}`;
    
    setTimeout(() => {
        msgDiv.className = "message hidden";
    }, 5000);
}
