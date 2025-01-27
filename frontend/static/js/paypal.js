document.addEventListener("DOMContentLoaded", function () {
    // Ensure PayPal SDK is loaded
    if (typeof paypal === "undefined") {
        console.error("🚨 PayPal SDK failed to load.");
        alert("PayPal is not available. Please refresh the page.");
        return;
    }

    paypal.Buttons({
        // Enable sandbox mode
        fundingSource: paypal.FUNDING.PAYPAL,

        createOrder: function (data, actions) {
            // Get form data
            let donorName = document.getElementById("name").value.trim();
            let email = document.getElementById("email").value.trim();
            let phone = document.getElementById("phone").value.trim();
            let address = document.getElementById("address").value.trim();
            let amount = parseFloat(document.getElementById("amount").value.trim());

            // Enhanced form validation
            if (!donorName || !email || !phone || !address) {
                alert("⚠ Please fill in all required fields.");
                return actions.reject();
            }

            if (isNaN(amount) || amount <= 0) {
                alert("⚠ Please enter a valid donation amount.");
                return actions.reject();
            }

            // Create PayPal order
            return actions.order.create({
                intent: "CAPTURE",
                purchase_units: [{
                    amount: { 
                        currency_code: "USD",  // Changed to USD for wider compatibility
                        value: amount.toFixed(2)
                    },
                    description: `Donation to FurMed by ${donorName}`,
                }],
                application_context: {
                    shipping_preference: 'NO_SHIPPING'
                }
            });
        },

        onApprove: function (data, actions) {
            // Show processing message
            alert("Processing your donation...");

            return actions.order.capture()
                .then(function (details) {
                    console.log("✅ Transaction Completed:", details);

                    // Prepare donation data
                    let donationData = {
                        orderID: details.id,
                        donor_name: document.getElementById("name").value.trim(),
                        email: document.getElementById("email").value.trim(),
                        phone: document.getElementById("phone").value.trim(),
                        address: document.getElementById("address").value.trim(),
                        amount: document.getElementById("amount").value.trim(),
                        status: "Completed",
                        currency: "USD"
                    };

                    // Send to backend
                    return fetch("/paypal-success", {
                        method: "POST",
                        headers: { 
                            "Content-Type": "application/json",
                            "Accept": "application/json"
                        },
                        body: JSON.stringify(donationData)
                    });
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.status === "success") {
                        alert("🎉 Thank you for your generous donation!");
                        if (data.invoice_url) {
                            downloadInvoice(data.invoice_url);
                        }
                        // Optional: Clear form
                        document.getElementById("donation-form").reset();
                    } else {
                        throw new Error(data.message || "Failed to record donation");
                    }
                })
                .catch(error => {
                    console.error("🚨 Error:", error);
                    alert("An error occurred while processing your donation. Please try again or contact support.");
                });
        },

        onError: function (err) {
            console.error("🚨 PayPal Checkout Error:", err);
            alert("❌ Payment failed. Please check your payment details and try again.");
        },

        onCancel: function (data) {
            console.log("💡 Payment cancelled by user");
            alert("Payment cancelled. Feel free to try again when you're ready.");
        }
    }).render("#paypal-button");
});

// 📜 Auto-Download Invoice (From Flask Server)
function downloadInvoice(invoiceUrl) {
    try {
        let invoiceLink = document.createElement("a");
        invoiceLink.href = invoiceUrl;
        invoiceLink.target = "_blank";
        invoiceLink.download = `FurMed_Donation_Invoice.pdf`;
        document.body.appendChild(invoiceLink);
        invoiceLink.click();
        document.body.removeChild(invoiceLink);
    } catch (error) {
        console.error("🚨 Error downloading invoice:", error);
        alert("Your donation was successful, but there was an error downloading the invoice. Please check your email for the receipt.");
    }
}