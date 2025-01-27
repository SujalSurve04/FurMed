import os
import sys
import subprocess
import json
import requests
import numpy as np
from datetime import datetime, timedelta, timezone
from flask import Flask, request, render_template, redirect, url_for, jsonify, session
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from pymongo import MongoClient
from fpdf import FPDF
from ultralytics import YOLO
import tensorflow as tf
import flask_mail
from flask_mail import Mail, Message
import sys
import signal
import multiprocessing
import time

###############################################################################
# Load Environment Variables
###############################################################################
load_dotenv()  # Load .env file

MONGO_URI = os.environ.get("MONGO_URI")
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.environ.get("PAYPAL_SECRET")
PAYPAL_API_BASE = "https://api-m.sandbox.paypal.com"  # Use live URL for production

###############################################################################
# Flask Configuration
###############################################################################
app = Flask(
    __name__,
    template_folder='frontend/templates',  # Where .html templates reside
    static_folder='frontend/static'        # Where static files reside
)

app.secret_key = os.environ.get("SECRET_KEY", "your-strong-secret-key")

# Define separate upload folders
FULL_ANIMAL_UPLOAD_FOLDER = 'frontend/static/f_upload'
DISEASE_UPLOAD_FOLDER = 'frontend/static/uploads'


# Create directories if they don't exist
for folder in [FULL_ANIMAL_UPLOAD_FOLDER, DISEASE_UPLOAD_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['FULL_ANIMAL_UPLOAD_FOLDER'] = FULL_ANIMAL_UPLOAD_FOLDER
app.config['DISEASE_UPLOAD_FOLDER'] = DISEASE_UPLOAD_FOLDER

###############################################################################
# (Optional) Auto-Start the Proxy Server on port 5001
###############################################################################
# If you prefer to start proxy_server.py manually (or via Docker), remove this.
if __name__ == '__main__':
    ai_process = subprocess.Popen([sys.executable, 'proxy_server.py'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.STDOUT)
    # This will run `proxy_server.py` in the background. 
    # Make sure your `proxy_server.py` has `app.run(port=5001)` inside.

###############################################################################
# Connect to MongoDB
###############################################################################
client = MongoClient(MONGO_URI)
db = client["fur-med"]

# Collections
predictions_coll = db["predictions"]  
donations_coll = db["donations"]     

###############################################################################
# Allowed File Checker
###############################################################################
def allowed_file(filename):
    """Check file extension to ensure it's PNG, JPG, or JPEG."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

###############################################################################
# Currency Conversion Helper
###############################################################################
def get_usd_to_inr():
    """
    Fetch USD to INR rate from a free API or fallback to 83 if fails.
    """
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD")
        if response.status_code == 200:
            return response.json().get("rates", {}).get("INR", 83.0)
    except Exception as e:
        print(f"⚠️ Exchange rate API failed: {e}")
    return 83.0  # fallback rate

###############################################################################
# Invoice Generator (Same as in your app.py)
###############################################################################
def generate_invoice(transaction_id, donor_name, email, phone, address, amount, currency, date):
    invoice_dir = os.path.join("frontend", "static", "invoices")
    if not os.path.exists(invoice_dir):
        os.makedirs(invoice_dir)

    invoice_path = os.path.join(invoice_dir, f"invoice_{transaction_id}.pdf")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # FurMed Logo
    logo_path = os.path.join("frontend", "static", "images", "logo.png")
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=10, w=30)

    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "FurMed - Donation Invoice", ln=True, align="C")
    pdf.ln(10)

    # Receipt Info
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, "RECEIPT INFORMATION", 1, 1, "L", True)

    pdf.set_font("Arial", "", 11)
    pdf.cell(100, 8, f"Transaction ID: {transaction_id}", ln=True)
    pdf.cell(100, 8, f"Date: {date}", ln=True)
    pdf.ln(5)

    # Donor Info
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "DONOR INFORMATION", 1, 1, "L", True)

    pdf.set_font("Arial", "", 11)
    pdf.cell(100, 8, f"Name: {donor_name}", ln=True)
    pdf.cell(100, 8, f"Email: {email}", ln=True)
    pdf.cell(100, 8, f"Phone: {phone}", ln=True)
    pdf.cell(100, 8, f"Address: {address}", ln=True)
    pdf.ln(5)

    # Donation Summary
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "DONATION SUMMARY", 1, 1, "L", True)

    pdf.set_font("Arial", "", 11)
    pdf.cell(130, 8, "Description", 1, 0, "C")
    pdf.cell(60, 8, "Amount", 1, 1, "C")

    pdf.cell(130, 8, "Charitable Donation to FurMed", 1, 0, "L")
    pdf.cell(60, 8, f"INR {amount:,.2f}", 1, 1, "R")

    pdf.set_font("Arial", "B", 11)
    pdf.cell(130, 8, "Total Amount Donated", 1, 0, "L")
    pdf.cell(60, 8, f"INR {amount:,.2f}", 1, 1, "R")

    # Thank You
    pdf.ln(10)
    pdf.set_font("Arial", "I", 11)
    pdf.set_text_color(0, 100, 255)
    pdf.multi_cell(0, 8, 
        "Thank you for your generous donation! Your support helps us provide medical care to animals in need.", 
        align="C"
    )

    # Footer
    pdf.ln(10)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(128)
    pdf.cell(0, 5, 
        "This is a computer-generated invoice. For any queries, contact support@furmed.com", 
        ln=True, align="C"
    )

    pdf.output(invoice_path)
    return f"/static/invoices/invoice_{transaction_id}.pdf"

###############################################################################
# Disease Info (for display on result page)
###############################################################################

dog_disease_info = {
    "Cataratas": {
        "details": "Cataracts cause clouding of the eye lens, leading to partial or total blindness. It commonly affects older dogs or those with diabetes. Symptoms include a bluish-gray film over the eyes, difficulty seeing in low light, and increased clumsiness. If left untreated, it can lead to complete blindness or secondary issues like glaucoma.",
        "first_aid": "Ensure the dog's environment remains familiar to prevent disorientation. Avoid rearranging furniture and use scent cues or verbal commands to help them navigate. Provide well-lit spaces to improve visibility and keep water and food bowls in a fixed location. A prompt vet visit is crucial for early diagnosis and treatment options.",
        "treatment": "The most effective treatment is surgical lens removal, which can restore vision in many cases. If surgery isn’t an option, managing underlying conditions like diabetes and using antioxidant supplements can slow progression. Anti-inflammatory eye drops may also be prescribed to reduce discomfort and prevent complications."
    },
    "Conjuntivitis": {
        "details": "Conjunctivitis is an eye infection that causes redness, swelling, and excessive discharge. It can be triggered by allergens, bacteria, viruses, or environmental irritants. Affected dogs may blink frequently, rub their eyes, or have a green or yellow discharge. If untreated, it can worsen and lead to corneal ulcers or chronic eye problems.",
        "first_aid": "Gently clean the eyes with a vet-approved saline solution or warm water on a cotton pad. Avoid using human eye drops unless prescribed by a veterinarian. Prevent the dog from scratching or rubbing its eyes to avoid further irritation. Limit exposure to dust, smoke, or strong chemicals that could worsen symptoms.",
        "treatment": "Treatment depends on the cause—bacterial infections require antibiotic eye drops, while allergic conjunctivitis may need antihistamines. If viral, supportive care such as artificial tears and anti-inflammatory medications can help. In severe cases, a vet may recommend further diagnostics like eye swabs or blood tests."
    },
    "Infección Bacteriana": {
        "details": "A bacterial skin infection, also known as pyoderma, can develop due to wounds, allergies, or excessive licking. Symptoms include red, inflamed skin, pus-filled sores, crusting, and an unpleasant odor. It is often secondary to conditions like flea allergies or hormonal imbalances. If left untreated, the infection can spread, causing severe discomfort.",
        "first_aid": "Gently clean affected areas with a mild antiseptic solution to prevent further infection. Avoid letting the dog lick or scratch the wounds by using an Elizabethan collar. Ensure the dog stays in a dry and clean environment to reduce bacterial growth. Contact a vet immediately if swelling, pain, or fever develops.",
        "treatment": "A vet may prescribe systemic antibiotics, anti-inflammatory drugs, or medicated shampoos. In chronic cases, long-term management with supplements or immune support may be needed. Regular grooming and skin care routines can help prevent future infections and promote overall skin health."
    },
    "PyodermaNasal": {
        "details": "PyodermaNasal is a bacterial infection affecting the nasal area, causing crusting, swelling, and discharge. It often occurs due to excessive moisture, allergies, or immune deficiencies. Symptoms include redness, constant nose licking, and the presence of scabs or sores around the nostrils. The condition can worsen if bacteria spread deeper into the tissues.",
        "first_aid": "Keep the dog's nose clean by gently wiping away any discharge with a damp cloth. Avoid harsh soaps or chemicals that could further irritate the skin. Discourage excessive nose rubbing on surfaces, as it can lead to worsening lesions. Provide a well-ventilated, stress-free environment to aid healing.",
        "treatment": "Antibiotic ointments and oral medications may be necessary to eliminate the infection. If allergies are a contributing factor, antihistamines or dietary changes may be required. Regular nasal care and hygiene maintenance can help prevent recurrence and improve overall nose health."
    },
    "Sarna": {
        "details": "Sarna (mange) is caused by microscopic mites that burrow into the skin, leading to intense itching and hair loss. The condition can be sarcoptic mange (highly contagious) or demodectic mange (affecting immunocompromised dogs). Symptoms include red, scaly skin, open sores, and a foul smell due to secondary infections. If left untreated, it can lead to severe skin damage.",
        "first_aid": "Isolate the affected dog to prevent spreading mites to other pets. Clean and disinfect bedding, collars, and grooming tools frequently. Use gloves when handling the dog to avoid transmission, as sarcoptic mange can be passed to humans. Keep the dog's immune system strong with a balanced diet and supplements.",
        "treatment": "Treatment involves medicated baths, oral or injectable anti-mite medications, and antibiotics if secondary infections develop. A vet may also recommend anti-inflammatory drugs to relieve itching and discomfort. Long-term management includes flea control, proper hygiene, and routine skin checkups."
    },
    "dermatitis": {
        "details": "Dermatitis in dogs results in itchy, red, and inflamed skin that may lead to chronic scratching. It can be caused by food allergies, flea bites, fungal infections, or environmental irritants. The condition may worsen if the dog licks or bites at the affected areas. Left untreated, it can result in thickened skin, sores, and bacterial infections.",
        "first_aid": "Keep the dog's skin dry and avoid known allergens, such as certain foods, dust, or strong detergents. Use vet-recommended anti-itch shampoos or soothing sprays to relieve irritation. Monitor the dog closely to prevent excessive scratching that could worsen the condition. Provide a comfortable, stress-free environment to aid healing.",
        "treatment": "Corticosteroids, antihistamines, or medicated shampoos may be prescribed depending on the severity. In cases of bacterial or fungal infections, antibiotics or antifungals are needed. Long-term management includes dietary adjustments, regular flea prevention, and proper grooming to maintain healthy skin."
    },
    "Healthy skin": {
        "details": "A healthy dog's skin is free from redness, dryness, or excessive shedding. Regular grooming, a nutritious diet, and good hygiene play crucial roles in skin maintenance. Healthy skin also indicates strong immunity, reducing the likelihood of infections. Monitoring changes in skin or coat texture can help detect early signs of health issues.",
        "first_aid": "Ensure the dog follows a balanced diet rich in omega-3 and omega-6 fatty acids for optimal skin health. Regular brushing removes dirt, dead hair, and potential allergens from the coat. Provide a flea and tick prevention routine to keep the skin free from external parasites. Keep an eye out for any unusual lumps, rashes, or dry patches.",
        "treatment": "No medical treatment is necessary for a dog with healthy skin, but routine checkups can help detect potential problems early. Maintaining hydration, using gentle shampoos, and avoiding harsh chemicals will help preserve skin health. If minor skin irritation occurs, natural remedies like aloe vera or coconut oil can provide relief."
    }
}

cat_disease_info = {
    "dermatitis": {
        "details": "Dermatitis in cats is an inflammatory skin condition that causes redness, itching, and discomfort. It can be triggered by allergies, parasites, fungal infections, or exposure to harsh chemicals. Affected cats may excessively groom, scratch, or develop bald patches. If left untreated, secondary bacterial infections may develop, worsening the condition.",
        "first_aid": "Gently clean the affected area with a mild antiseptic to reduce irritation. Avoid exposing the cat to potential allergens such as certain foods, pollen, or household cleaning products. Provide a cool and stress-free environment to prevent excessive grooming. Use an Elizabethan collar if the cat is scratching excessively to prevent further damage.",
        "treatment": "A vet may prescribe antihistamines, corticosteroids, or topical ointments to reduce inflammation and itching. If the dermatitis is caused by a bacterial or fungal infection, antibiotics or antifungal medications will be necessary. Regular grooming, proper flea control, and dietary adjustments can help manage and prevent flare-ups."
    },
    "flea_allergy": {
        "details": "Flea allergy dermatitis (FAD) is a severe allergic reaction to flea saliva that causes intense itching and skin irritation. Even a single flea bite can trigger extreme discomfort in sensitive cats. Symptoms include excessive scratching, red or inflamed skin, hair loss (especially on the lower back and tail), and small scabs known as 'flea dirt.'",
        "first_aid": "Use a flea comb to remove fleas and bathe the cat with a vet-approved anti-flea shampoo. Wash bedding, carpets, and furniture thoroughly to eliminate flea eggs and larvae. Keep the cat indoors as much as possible to prevent reinfestation. Apply a vet-approved flea treatment to all household pets to break the flea life cycle.",
        "treatment": "Monthly flea prevention treatments such as spot-on solutions, flea collars, or oral medications are essential. Anti-inflammatory medications may be prescribed to relieve itching and discomfort. If secondary bacterial infections develop due to excessive scratching, antibiotics or medicated shampoos may be required."
    },
    "ringworm": {
        "details": "Ringworm is a highly contagious fungal infection that affects the skin, nails, and fur of cats. It appears as circular, scaly patches of hair loss, often accompanied by redness and crusting. It can spread to humans and other animals through direct contact or contaminated objects. Kittens and cats with weakened immune systems are more susceptible.",
        "first_aid": "Wear gloves when handling an infected cat to prevent transmission to humans. Isolate the affected cat from other pets and disinfect bedding, furniture, and grooming tools frequently. Keep the cat’s environment dry and well-ventilated, as fungi thrive in warm and humid conditions. Avoid using shared items like litter boxes and food bowls until treatment is complete.",
        "treatment": "Topical antifungal creams or shampoos containing miconazole or chlorhexidine are commonly used. For severe cases, oral antifungal medications such as itraconazole or terbinafine may be required. Treatment can take several weeks, and follow-up tests may be needed to confirm the infection has cleared."
    },
    "scabies": {
        "details": "Scabies, also known as feline sarcoptic mange, is caused by microscopic mites that burrow into the skin. It leads to extreme itching, crusty skin lesions, redness, and hair loss. It is highly contagious among cats and can even cause mild itching in humans. If left untreated, it can lead to open sores, bacterial infections, and severe discomfort.",
        "first_aid": "Isolate the affected cat to prevent the spread of mites to other pets. Clean the cat’s bedding, furniture, and grooming tools thoroughly to eliminate mites and eggs. Wear gloves when handling the cat and avoid close contact until treatment begins. Keep the cat’s skin moisturized with soothing sprays or vet-approved lotions to relieve irritation.",
        "treatment": "Vet-prescribed medicated dips, topical treatments, or oral medications like ivermectin are required to eliminate mites. If secondary bacterial infections occur, antibiotics may be needed. Regular checkups and maintaining a clean living environment are essential to prevent reinfection."
    },
    "Healthy skin": {
        "details": "A cat with healthy skin has a smooth, shiny coat with no signs of redness, dryness, or excessive shedding. Proper grooming, a balanced diet, and routine veterinary checkups contribute to overall skin health. Healthy skin also reflects a strong immune system, reducing the likelihood of infections or skin conditions. Monitoring for changes in coat texture or excessive scratching can help detect early issues.",
        "first_aid": "Ensure your cat consumes a high-quality diet rich in essential fatty acids like omega-3 and omega-6. Regular grooming helps remove dirt, loose fur, and allergens that may irritate the skin. Provide fresh water and maintain a clean living space to prevent skin infections. Keep an eye on any unusual lumps, scabs, or rashes that may require veterinary attention.",
        "treatment": "No treatment is needed for a cat with healthy skin, but preventive care is crucial. Regular flea control, proper hydration, and avoiding exposure to harsh chemicals help maintain optimal skin condition. If minor irritation occurs, natural remedies such as coconut oil or aloe vera may help soothe the skin."
    },
    "Mange": {
        "details": "Mange is a severe skin disease caused by mite infestations, leading to relentless scratching, hair loss, and thickened, crusty skin. It is highly contagious and spreads quickly among cats and other animals. Symptoms include patches of raw, inflamed skin, foul odor, and restlessness due to constant itching. If untreated, mange can lead to severe skin damage and infections.",
        "first_aid": "Bathe the cat with medicated shampoos designed to eliminate mites and soothe irritated skin. Isolate the affected cat and disinfect bedding, food bowls, and grooming tools frequently. Avoid direct contact with other pets until the infection is treated. Provide a stress-free environment to boost the cat’s immune system and aid recovery.",
        "treatment": "Oral or topical anti-parasitic treatments prescribed by a vet are essential to eradicate mites. Medicated dips or injections may be required for severe cases. If secondary infections develop, antibiotics or anti-inflammatory drugs may be necessary. Long-term skin health maintenance includes regular flea prevention and maintaining a clean environment."
    }
}

###############################################################################
# mail logic
###############################################################################
# After app initialization
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'furmed.19@gmail.com'  # Your Gmail
app.config['MAIL_PASSWORD'] = 'mqalxlffxthhmmwo'    # Your Gmail App Password

mail = Mail(app)

@app.route('/send_feedback', methods=['POST'])
def send_feedback():
    try:
        data = request.get_json()
        email = data.get('email')
        message = data.get('message')
        
        if not email or not message:
            return jsonify({
                'status': 'error',
                'message': 'Email and message are required'
            }), 400

        msg = Message('Feedback from FurMed Website',
                     sender=email,
                     recipients=['furmed.19@gmail.com'])  # Your receiving email

        msg.body = f"""
        Feedback from: {email}
        Message: {message}
        """

        mail.send(msg)
        return jsonify({
            'status': 'success',
            'message': 'Feedback sent successfully!'
        }), 200
        
    except Exception as e:
        print(f"Error sending feedback: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
###############################################################################
# Flask Routes
###############################################################################
@app.route('/')
def route_home():
    """Home page (Landing)."""
    return render_template('home.html')

###############################################################################
# Admin Login Route with Authentication
###############################################################################
@app.route('/login', methods=['GET', 'POST'])
def route_login():
    if request.method == 'POST':
        data = request.json
        username = data.get("username")
        password = data.get("password")

        # Hardcoded admin credentials (replace with DB check in production)
        ADMIN_USERNAME = "admin"
        ADMIN_PASSWORD = "admin123"

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return jsonify({"success": True, "redirect_url": url_for('admin_dashboard')}), 200
        else:
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

    return render_template('login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('route_login'))  
    return render_template("admin_dashboard.html")

@app.route('/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('route_home'))

@app.route('/api/get_donations', methods=['GET'])
def get_donations():
    if not session.get('admin_logged_in'):
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        total_donations = donations_coll.count_documents({})
        all_donations = donations_coll.find({}, {"_id": 0, "amount_inr": 1})

        grand_total_donations = sum(d.get('amount_inr', 0) for d in all_donations)
        
        donations = list(
            donations_coll.find({}, {"_id": 0})
            .sort("date", -1)
            .skip((page - 1) * per_page)
            .limit(per_page)
        )

        return jsonify({
            "status": "success",
            "donations": donations,
            "total_pages": (total_donations + per_page - 1) // per_page,
            "current_page": page,
            "grand_total_donations": grand_total_donations
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

###############################################################################
# Server-Side Pagination for Predictions API
###############################################################################
@app.route('/api/get_predictions', methods=['GET'])
def get_predictions():
    if not session.get('admin_logged_in'):
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        total_predictions = predictions_coll.count_documents({})
        predictions = list(
            predictions_coll.find({}, {"_id": 0})
            .sort("timestamp", -1)
            .skip((page - 1) * per_page)
            .limit(per_page)
        )

        for p in predictions:
            if "is_correct" not in p:
                p["is_correct"] = True
            if "correct_label" not in p:
                p["correct_label"] = None

        return jsonify({
            "status": "success",
            "predictions": predictions,
            "total_pages": (total_predictions + per_page - 1) // per_page,
            "current_page": page
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

###############################################################################
# Disease Route (Refactored to use Proxy Server)
###############################################################################
@app.route('/disease', methods=['GET', 'POST'])
def route_disease():
    if request.method == 'POST':
        try:
            owner_name = request.form.get('ownerName', 'Unknown')
            pet_name = request.form.get('petName', 'Unknown')
            pet_gender = request.form.get('petGender', 'Unknown')
            selected_pet_type = request.form.get('petType', 'Unknown')
            user_symptoms = request.form.getlist('symptoms')

            # Handle Full Animal Image
            full_animal_file = request.files.get('full_animal_image')
            if not full_animal_file or not allowed_file(full_animal_file.filename):
                return render_template('disease.html', error="Invalid full animal image format.")

            full_animal_filename = secure_filename(full_animal_file.filename)
            full_animal_filepath = os.path.join(app.config['FULL_ANIMAL_UPLOAD_FOLDER'], full_animal_filename)
            full_animal_file.save(full_animal_filepath)

            # Handle Disease Image
            disease_file = request.files.get('disease_image')
            if not disease_file or not allowed_file(disease_file.filename):
                return render_template('disease.html', error="Invalid disease image format.")

            disease_filename = secure_filename(disease_file.filename)
            disease_filepath = os.path.join(app.config['DISEASE_UPLOAD_FOLDER'], disease_filename)
            disease_file.save(disease_filepath)

            # POST to proxy server
            proxy_url = "http://localhost:5001/predict_disease"
            with open(full_animal_filepath, 'rb') as fa, open(disease_filepath, 'rb') as da:
                files_data = {
                    "full_animal_image": (full_animal_filename, fa, full_animal_file.content_type),
                    "disease_image": (disease_filename, da, disease_file.content_type)
                }
                form_data = {
                    "ownerName": owner_name,
                    "petName": pet_name,
                    "petGender": pet_gender,
                    "petType": selected_pet_type,
                    "symptoms": user_symptoms
                }
                response = requests.post(proxy_url, data=form_data, files=files_data)

            if response.status_code != 200:
                error_msg = response.json().get("error", "Error from AI Server.")
                return render_template('disease.html', error=error_msg)

            ai_result = response.json()
            predicted_type = ai_result.get("pet_type", "Other")
            final_disease = ai_result.get("disease", "No disease detected")
            detected_image_url = ai_result.get("detected_image_url", None)

            if predicted_type == "Other":
                return render_template('disease.html', error="Please upload a valid cat or dog image.")

            if not detected_image_url:
                detected_image_url = url_for('static', filename='images/no_prediction.png')

            disease_info = cat_disease_info.get(final_disease, {}) if predicted_type.lower() == "cat" else dog_disease_info.get(final_disease, {})

                        # Create record WITHOUT inserting yet
            record = {
                "owner_name": owner_name,
                "pet_name": pet_name,
                "pet_gender": pet_gender,
                "pet_type": predicted_type,
                "disease": final_disease,
                "full_animal_image_path": url_for('static', filename=f'f_upload/{full_animal_filename}'),
                "disease_image_path": url_for('static', filename=f'uploads/{disease_filename}'),
                "predicted_image_path": detected_image_url,
                "timestamp": datetime.now(timezone.utc)
            }

            # Single insert - remove the duplicate insert
            result = predictions_coll.insert_one(record)
            record_id = str(result.inserted_id)

            # Rest of template rendering with record_id
            return render_template(
                'result.html',
                prediction_id=record_id,
                owner_name=owner_name,
                pet_name=pet_name,
                pet_gender=pet_gender,
                pet_type=predicted_type,
                disease_name=final_disease,
                details=disease_info.get("details", "No information available."),
                first_aid=disease_info.get("first_aid", "No first aid available."),
                treatment=disease_info.get("treatment", "No treatment info available."),
                image_path=url_for('static', filename=f'uploads/{disease_filename}'),
                predicted_image_path=detected_image_url
            )

        except Exception as ex:
            print(f"Error during disease analysis: {ex}")
            return render_template('disease.html', error="An unexpected error occurred.")

    return render_template('disease.html')
###############################################################################
# Leaflet Map Integration for Nearby Veterinary Clinics
###############################################################################
@app.route('/get_nearby_vets', methods=['GET'])
def get_nearby_vets():
    try:
        latitude = float(request.args.get('lat', 0))
        longitude = float(request.args.get('lng', 0))

        # Generate mock or real vet clinic data
        vet_clinics = [
            {
                "name": f"Vet Clinic {i+1}",
                "lat": latitude + (np.random.rand() - 0.5) * 0.02,
                "lng": longitude + (np.random.rand() - 0.5) * 0.02,
                "contact": "1234567890"
            }
            for i in range(5)
        ]

        return jsonify({"status": "success", "clinics": vet_clinics}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/result')
def route_result():
    return redirect(url_for('route_disease'))

###############################################################################
# Feedback for Incorrect Predictions
###############################################################################
@app.route('/feedback', methods=['POST'])
def save_incorrect_prediction():
    try:
        data = request.json
        prediction_id = data.get("prediction_id")
        correct_label = data.get("correct_label")

        if not prediction_id or not correct_label:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        # Find the prediction record
        pred_rec = predictions_coll.find_one({"_id": ObjectId(prediction_id)})
        if not pred_rec:
            return jsonify({"status": "error", "message": "Prediction not found"}), 404

        # Create incorrect_predictions directory if it doesn't exist
        incorrect_folder = os.path.join(app.config['DISEASE_UPLOAD_FOLDER'], 'incorrect_predictions')
        os.makedirs(incorrect_folder, exist_ok=True)

        # Get original image path
        original_image_path = pred_rec.get("disease_image_path")
        if not original_image_path:
            return jsonify({"status": "error", "message": "Original image not found"}), 404

        # Create new filename with correct label
        new_filename = f"{correct_label}_{os.path.basename(original_image_path)}"
        new_filepath = os.path.join(incorrect_folder, new_filename)

        # Move and rename the file
        try:
            source_path = os.path.join(app.root_path, 'frontend/static', original_image_path.lstrip('/static/'))
            if os.path.exists(source_path):
                os.rename(source_path, new_filepath)
            else:
                return jsonify({"status": "error", "message": "Source image not found"}), 404
        except Exception as e:
            return jsonify({"status": "error", "message": f"File operation failed: {str(e)}"}), 500

        # Update database record
        try:
            predictions_coll.update_one(
                {"_id": ObjectId(prediction_id)},
                {
                    "$set": {
                        "is_correct": False,
                        "correct_label": correct_label,
                        "corrected_image_path": f"/static/uploads/incorrect_predictions/{new_filename}"
                    }
                }
            )
        except Exception as e:
            return jsonify({"status": "error", "message": f"Database update failed: {str(e)}"}), 500

        return jsonify({
            "status": "success",
            "message": "Feedback saved successfully"
        }), 200

    except Exception as e:
        print(f"Error in save_incorrect_prediction: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

###############################################################################
# Services Page
###############################################################################
@app.route('/services')
def route_services():
    return render_template('services.html')

###############################################################################
# Donation Route
###############################################################################
@app.route('/donation', methods=['GET', 'POST'])
def route_donation():
    if request.method == 'POST':
        try:
            donor_name = request.form.get('name', '').strip()
            donor_email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()
            amount_inr = request.form.get('amount', '').strip()

            # Validate
            if not donor_name or not donor_email or not phone or not address or not amount_inr:
                return render_template("donation.html", 
                                       error="All fields are required.",
                                       paypal_client_id=PAYPAL_CLIENT_ID)

            if not phone.isdigit() or len(phone) != 10:
                return render_template("donation.html", 
                                       error="Phone must be 10 digits.",
                                       paypal_client_id=PAYPAL_CLIENT_ID)

            if '@' not in donor_email or '.' not in donor_email.split('@')[-1]:
                return render_template("donation.html", 
                                       error="Invalid email address.",
                                       paypal_client_id=PAYPAL_CLIENT_ID)

            try:
                amount_inr = float(amount_inr)
                if amount_inr <= 0:
                    return render_template("donation.html", 
                                           error="Amount must be > 0.",
                                           paypal_client_id=PAYPAL_CLIENT_ID)
            except ValueError:
                return render_template("donation.html", 
                                       error="Invalid amount.",
                                       paypal_client_id=PAYPAL_CLIENT_ID)

            # Convert INR to USD
            usd_rate = get_usd_to_inr()
            amount_usd = round(amount_inr / usd_rate, 2)

            session["donation_email"] = donor_email

            donation_data = {
                "donor_name": donor_name,
                "donation_email": donor_email,
                "phone": phone,
                "address": address,
                "amount_inr": amount_inr,
                "amount_usd": amount_usd,
                "currency": "INR",
                "status": "Pending",
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            }
            inserted = donations_coll.insert_one(donation_data)
            donation_id = str(inserted.inserted_id)

            return render_template("donation.html",
                                   thank_you=f"Thank you, {donor_name}, for your donation!",
                                   donation_id=donation_id,
                                   paypal_client_id=PAYPAL_CLIENT_ID)

        except Exception as e:
            print(f"Error while processing donation: {e}")
            return render_template("donation.html",
                                   error="An unexpected error occurred.",
                                   paypal_client_id=PAYPAL_CLIENT_ID)

    return render_template("donation.html", paypal_client_id=PAYPAL_CLIENT_ID)

###############################################################################
# About Page
###############################################################################
@app.route('/about')
def route_about():
    return render_template('about.html')

###############################################################################
# PayPal Success Callback
###############################################################################
@app.route('/paypal-success', methods=['POST'])
def paypal_success():
    """Handle successful PayPal payment and generate invoice."""
    try:
        # Extract data from request
        data = request.json
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data received"
            }), 400

        # Extract required fields
        order_id = data.get("orderID")
        phone = data.get("phone", "").strip()
        address = data.get("address", "").strip()

        # Validate required fields
        if not order_id:
            return jsonify({
                "status": "error",
                "message": "Missing order ID"
            }), 400

        if not phone:
            return jsonify({
                "status": "error",
                "message": "Phone number is required"
            }), 400

        if not address:
            return jsonify({
                "status": "error",
                "message": "Address is required"
            }), 400

        # Check for duplicate transaction
        existing_transaction = donations_coll.find_one({"transaction_id": order_id})
        if existing_transaction:
            return jsonify({
                "status": "error",
                "message": "Duplicate transaction detected.",
                "transaction_id": order_id,
                "invoice_url": existing_transaction.get("invoice_path")
            }), 409

        # Verify with PayPal API
        try:
            auth = (PAYPAL_CLIENT_ID, PAYPAL_SECRET)
            headers = {"Content-Type": "application/json"}
            paypal_response = requests.get(
                f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}",
                auth=auth,
                headers=headers,
                timeout=10  # Add timeout
            )
            
            if paypal_response.status_code != 200:
                return jsonify({
                    "status": "error",
                    "message": f"PayPal API Error: {paypal_response.text}"
                }), 400

            payment_data = paypal_response.json()
            
            if payment_data.get("status") != "COMPLETED":
                return jsonify({
                    "status": "error",
                    "message": "Transaction not completed"
                }), 400

        except requests.exceptions.RequestException as e:
            return jsonify({
                "status": "error",
                "message": f"Failed to verify with PayPal: {str(e)}"
            }), 500

        # Extract PayPal payment details
        payer = payment_data["payer"]
        amount_usd = float(payment_data["purchase_units"][0]["amount"]["value"])
        paypal_email = payer["email_address"]
        donor_name = f"{payer['name']['given_name']} {payer['name']['surname']}"

        # Get donor email from session or use PayPal email
        donor_email = session.pop("donation_email", paypal_email)

        # Convert USD to INR
        exchange_rate = get_usd_to_inr()
        amount_inr = round(amount_usd * exchange_rate, 2)

        # Generate timestamp in IST
        utc_now = datetime.now(timezone.utc)
        ist_now = utc_now + timedelta(hours=5, minutes=30)
        ist_time_str = ist_now.strftime("%Y-%m-%d %H:%M:%S")

        # Generate invoice
        try:
            invoice_path = generate_invoice(
                order_id, donor_name, donor_email,
                phone, address, amount_inr, "INR", ist_time_str
            )
            invoice_url = url_for('static', 
                                filename=f'invoices/invoice_{order_id}.pdf',
                                _external=True)
        except Exception as e:
            print(f"Error generating invoice: {e}")
            # Continue even if invoice generation fails
            invoice_path = None
            invoice_url = None

        # Create donation record
        donation_record = {
            "donor_name": donor_name,
            "donation_email": donor_email,
            "paypal_email": paypal_email,
            "phone": phone,
            "address": address,
            "amount_usd": amount_usd,
            "amount_inr": amount_inr,
            "currency": "INR",
            "exchange_rate": exchange_rate,
            "status": "Completed",
            "transaction_id": order_id,
            "date": ist_time_str,
            "invoice_path": invoice_url
        }

        # Save to database
        try:
            donations_coll.insert_one(donation_record)
        except Exception as e:
            print(f"Database error: {e}")
            return jsonify({
                "status": "error",
                "message": "Failed to save donation record"
            }), 500

        # Return success response
        return jsonify({
            "status": "success",
            "message": "Donation recorded successfully.",
            "transaction_id": order_id,
            "invoice_url": invoice_url
        }), 200

    except Exception as e:
        print(f"❌ Error processing PayPal transaction: {e}")
        return jsonify({
            "status": "error",
            "message": f"Server Error: {str(e)}"
        }), 500
###############################################################################
# Convert INR to USD

###############################################################################
@app.route('/convert-inr-to-usd', methods=['POST'])
def convert_inr_to_usd():
    data = request.json
    amount_inr = float(data.get("amount_inr", 0))

    usd_rate = get_usd_to_inr()
    amount_usd = round(amount_inr / usd_rate, 2)

    return jsonify({"amount_usd": amount_usd})

###############################################################################
# Run
###############################################################################
# In main_server.py
if __name__ == '__main__':
    try:
        app.run(debug=True, port=5000)
    finally:
        # If we started the proxy server above, you can optionally kill it here.
        pass