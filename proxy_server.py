import os 
import json
import numpy as np
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from ultralytics import YOLO
import tensorflow as tf
from tensorflow.keras.preprocessing.image import load_img, img_to_array
import cv2
from PIL import UnidentifiedImageError
import os
import sys
import signal
import multiprocessing
import logging
import sqlite3

# Enhanced Logging Configuration
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/proxy_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
###############################################################################
# Flask App
###############################################################################
proxy_app = Flask(__name__)

###############################################################################
# Paths & Folders
###############################################################################
UPLOAD_FOLDER = 'frontend/static/uploads'
F_UPLOAD_FOLDER = 'frontend/static/f_upload'  # New folder for full animal images
PREDICTIONS_FOLDER = os.path.join(UPLOAD_FOLDER, 'predictions')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(F_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PREDICTIONS_FOLDER, exist_ok=True)

proxy_app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
proxy_app.config['F_UPLOAD_FOLDER'] = F_UPLOAD_FOLDER
proxy_app.config['PREDICTIONS_FOLDER'] = PREDICTIONS_FOLDER

###############################################################################
# Symptom Mappings (From Original app.py)
###############################################################################
cat_classes = [
    "dermatitis", "fine", "flea_allergy", "ringworm", "scabies", 
    "Healthy skin", "Mange", "Ringworm"
]

# ✅ Updated Dog Disease Classes
dog_classes = [
    "Cataratas", "Conjuntivitis", "Infección Bacteriana", "PyodermaNasal", "Sarna",
    "dermatitis", "fine", "flea_allergy", "ringworm", "scabies"
]

# ✅ Similar Class Mapping (Handles Label Differences)
similar_labels = {
    "fine": "Healthy skin",
    "Healthy skin": "Healthy skin", 
    "Ringworm": "ringworm",
    "ringworm": "ringworm"
}
cat_symptom_mapping = {
    "dermatitis": ["Redness", "Swelling", "Itching"],
    "flea_allergy": ["Excessive Scratching", "Hair Loss", "Redness"],
    "ringworm": ["Circular Hair Loss", "Scaly Patches"],
    "Ringworm": ["Circular Hair Loss", "Scaly Patches"],  
    "scabies": ["Intense Itching", "Crusty Skin", "Wounds"],
    "Mange": ["Patchy Hair Loss", "Thickened Skin"]
}

dog_symptom_mapping = {
    "Cataratas": ["Cloudy Eyes", "Vision Loss"],
    "Conjuntivitis": ["Red Eyes", "Discharge", "Swelling"],
    "Infección Bacteriana": ["Pus", "Swelling", "Wound"],
    "PyodermaNasal": ["Nasal Discharge", "Crusty Nose"],
    "Sarna": ["Intense Itching", "Scabs", "Hair Loss"],
    "dermatitis": ["Inflammation", "Redness", "Scaling"],
    "flea_allergy": ["Constant Scratching", "Hair Loss"],
    "ringworm": ["Circular Lesions", "Hair Loss", "Scaling"],
    "Ringworm": ["Circular Lesions", "Hair Loss", "Scaling"],  
    "scabies": ["Crusty Skin", "Itching", "Lesions"]
}

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
    "flea_allergy": {
        "details": "Flea allergy dermatitis occurs when a dog has an allergic reaction to flea saliva. Even a few flea bites can cause intense itching and skin inflammation. Common symptoms include hair loss, red patches, and constant scratching, often around the tail, groin, and belly areas. If untreated, secondary bacterial infections can develop.",
        "first_aid": "Bathe the dog with a vet-approved flea shampoo to eliminate existing fleas. Use flea combs and spot treatments to prevent re-infestation. Wash bedding, carpets, and upholstery to remove flea eggs and larvae. Keep the dog on a strict flea prevention routine year-round.",
        "treatment": "Flea prevention products such as oral medications, flea collars, and topical treatments can help control infestations. Anti-itch medications and antibiotics may be required if secondary infections occur. Addressing environmental flea control is crucial to prevent reinfestation."
    },
    "ringworm": {
        "details": "Ringworm is a fungal infection that causes circular, hairless lesions with scaling and redness. It is highly contagious and can spread to humans and other pets. Affected dogs may show itching, brittle hair, and crusty patches on the skin. Without treatment, the infection can spread to large areas of the body.",
        "first_aid": "Isolate the infected dog to prevent spreading the fungus. Clean and disinfect bedding, brushes, and collars frequently. Wear gloves when handling the affected areas to avoid transmission. Keep the skin dry, as the fungus thrives in moist environments.",
        "treatment": "Antifungal shampoos, oral antifungal medications, and topical creams are commonly used. In severe cases, a vet may prescribe systemic antifungal treatments. Proper hygiene and environmental disinfection are essential for full recovery."
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
# Allowed File Checker
###############################################################################
def allowed_file(filename):
    """Check file extension to ensure it's PNG, JPG, or JPEG."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

###############################################################################
# Load Models
###############################################################################
print("Loading models...")

# Classification Models
CLASSIFICATION_MODEL_1_PATH = 'models/classify_201.keras'
CLASSIFICATION_MODEL_2_PATH = 'models/furmed_classification.keras'
CLASSIFICATION_OVERFIT_PATH = 'models/furmed_classification_model_memorized.keras'

classification_model_1 = tf.keras.models.load_model(CLASSIFICATION_MODEL_1_PATH)
classification_model_2 = tf.keras.models.load_model(CLASSIFICATION_MODEL_2_PATH)
classification_overfit_model = tf.keras.models.load_model(CLASSIFICATION_OVERFIT_PATH)

# YOLO Cat
cat_generalized_model = YOLO('models/cat/catdisease_generalized_finetuned_yolov8.pt')
cat_memorized_model = YOLO('models/cat/catdisease_memorized_finetuned_yolov8.pt')

# YOLO Dog
dog_generalized_model = YOLO('models/dog/dogdisease_generalized_finetuned_yolov8.pt')
dog_memorized_model = YOLO('models/dog/dogdisease_memorized_finetuned_yolov8.pt')
dog_generalized_old_model = YOLO('models/dog/dog_genralized_disease.pt')
dog_memorized_old_model = YOLO('models/dog/dog_memorized.pt')

# Keras Cat
cat_disease_keras_1 = tf.keras.models.load_model('models/cat/cat_disease_model_100percent.keras')
cat_disease_keras_2 = tf.keras.models.load_model('models/cat/cat_disease_model_with_weights.keras')

# Keras Dog
dog_disease_keras_1 = tf.keras.models.load_model('models/dog/dog_disease_model_overfit.keras')
dog_disease_keras_2 = tf.keras.models.load_model('models/dog/dog_disease_model_with_weights (1).keras')

# After loading all models, add:
cat_models = {
    'yolo': [cat_generalized_model, cat_memorized_model],
    'keras': [cat_disease_keras_1, cat_disease_keras_2]
}

dog_models = {
    'yolo': [dog_generalized_model, dog_memorized_model, 
             dog_generalized_old_model, dog_memorized_old_model],
    'keras': [dog_disease_keras_1, dog_disease_keras_2]
}

print("✅ All models loaded successfully.")

###############################################################################
# Classes
###############################################################################
classification_classes = ['Cat', 'Dog', 'Other']

cat_classes = [
    "dermatitis", "fine", "flea_allergy", "ringworm", "scabies",
    "Healthy skin", "Mange", "Ringworm"
]

dog_classes = [
    "Cataratas", "Conjuntivitis", "Infección Bacteriana", "PyodermaNasal", "Sarna",
    "dermatitis", "fine", "flea_allergy", "ringworm", "scabies",
    "Healthy skin"
]

###############################################################################
# Preprocessing Helpers
###############################################################################
# In proxy_server.py
def preprocess_image_classification_gen(image_path, target_size=(224, 224)):
    try:
        img = load_img(image_path, target_size=target_size)
        arr = img_to_array(img) / 255.0
        arr = np.expand_dims(arr, axis=0)
        del img  # Free memory
        return arr
    except Exception as e:
        print(f"Error: {e}")
        return None

def preprocess_image_disease(image_path, target_size=(224, 224)):
    return preprocess_image_classification_gen(image_path, target_size)

def preprocess_image_for_keras(image_path, target_size=(224, 224)):
    return preprocess_image_classification_gen(image_path, target_size)

###############################################################################
# Classification: Cat vs Dog vs Other
###############################################################################
def classify_pet_type(filepath, threshold=0.6):
    img1 = preprocess_image_classification_gen(filepath, (224, 224))
    if img1 is None:
        print("Failed to preprocess image for classification")
        return "Invalid Image", 0.0

    print("Making classification model predictions...")
    try:
        preds1 = classification_model_1.predict(img1)
        preds2 = classification_model_2.predict(img1)
        preds_overfit = classification_overfit_model.predict(img1)
        
        print(f"Classification Model 1 predictions: {preds1}")
        print(f"Classification Model 2 predictions: {preds2}")
        print(f"Classification Overfit Model predictions: {preds_overfit}")

        weighted_preds = (0.4 * preds1 + 0.4 * preds2 + 0.2 * preds_overfit)
        best_idx = np.argmax(weighted_preds)
        best_conf = weighted_preds[0][best_idx]
        
        print(f"Best classification index: {best_idx}, confidence: {best_conf}")
        
        final_label = classification_classes[best_idx]
        if best_conf < threshold or final_label == "Other":
            return "Other", float(best_conf)
            
        return final_label, float(best_conf)
        
    except Exception as e:
        print(f"Error during classification: {e}")
        return "Error", 0.0


# Add error handling in main_server.py's disease route

###############################################################################
# Analyze Disease
###############################################################################
def analyze_disease(filepath, user_symptoms, models, classes, symptom_mapping):
    """
    Analyze the disease image using multiple models and user-provided symptoms.
    This function combines YOLO object detection, Keras classification, and symptom analysis
    to provide a comprehensive disease prediction.
    """
    print("Starting disease analysis...")
    
    # Initialize variables to store model predictions
    yolo_predictions = []
    keras_predictions = []
    
    # Step 1: YOLO Object Detection
    for i, yolo_model in enumerate(models['yolo']):
        results = yolo_model(filepath)
        if results and results[0].boxes:
            boxes = results[0].boxes.data.cpu().numpy()
            for box in boxes:
                x1, y1, x2, y2, conf, class_id = box
                disease = classes[int(class_id)]
                yolo_predictions.append((disease, float(conf), f"YOLO_{i}"))
    
    print(f"YOLO detections: {len(yolo_predictions)}")
    
    # Step 2: Keras Classification
    keras_input = preprocess_image_for_keras(filepath)
    if keras_input is not None:
        for i, keras_model in enumerate(models['keras']):
            preds = keras_model.predict(keras_input)
            disease_index = np.argmax(preds)
            confidence = preds[0][disease_index]
            disease = classes[disease_index]
            keras_predictions.append((disease, float(confidence), f"Keras_{i}"))
    
    print(f"Keras predictions: {len(keras_predictions)}")
    
    # Step 3: Combine predictions and calculate scores
    disease_scores = {}
    for disease, conf, model_type in yolo_predictions + keras_predictions:
        if disease not in disease_scores:
            disease_scores[disease] = {
                'score': 0,
                'detections': [],
                'max_conf': 0
            }
        
        # Add detection with model type and confidence
        disease_scores[disease]['detections'].append((model_type, conf))
        
        # Update max confidence
        disease_scores[disease]['max_conf'] = max(disease_scores[disease]['max_conf'], conf)
        
        # Calculate score based on model type
        if model_type.startswith('YOLO'):
            disease_scores[disease]['score'] += conf * 0.6  # Higher weight for YOLO
        else:  # Keras
            disease_scores[disease]['score'] += conf * 0.4  # Lower weight for Keras
    
    # Step 4: Incorporate user symptoms
    for disease in classes:
        symptom_score = sum(1 for s in user_symptoms if s in symptom_mapping.get(disease, [])) * 0.2
        if disease in disease_scores:
            disease_scores[disease]['score'] += symptom_score
        else:
            disease_scores[disease] = {
                'score': symptom_score,
                'detections': [],
                'max_conf': 0
            }
    
    # Step 5: Determine the best disease prediction
    if disease_scores:
        best_disease = max(disease_scores, key=lambda x: disease_scores[x]['score'])
        confidence = disease_scores[best_disease]['score']  # Use the score as confidence
        detections = disease_scores[best_disease]['detections']
    else:
        best_disease = "No disease detected"
        confidence = 0
        detections = []
    
    # Step 6: Generate detailed report
    report = {
        'best_disease': best_disease,
        'confidence': confidence,
        'detections': detections,
        'all_scores': {d: s['score'] for d, s in disease_scores.items()},
        'symptom_match': {d: sum(1 for s in user_symptoms if s in symptom_mapping.get(d, [])) for d in classes}
    }
    
    print(f"Disease prediction: {best_disease}")
    print(f"Confidence: {confidence}")
    print(f"All scores: {report['all_scores']}")
    
    # Step 7: Save detected image
    detected_image_path = save_detected_image(models['yolo'][0](filepath), filepath)
    
    return best_disease, detected_image_path, report

###############################################################################
# Prediction for Cats
###############################################################################
def predict_cat_disease(filepath, user_symptoms):
    print("Processing cat disease prediction")
    return analyze_disease(filepath, user_symptoms, cat_models, cat_classes, cat_symptom_mapping)

def predict_dog_disease(filepath, user_symptoms):
    print("Processing dog disease prediction")
    return analyze_disease(filepath, user_symptoms, dog_models, dog_classes, dog_symptom_mapping)

###############################################################################
# Drawing Bounding Boxes
###############################################################################
def save_detected_image(results, original_path):
    """
    Saves YOLO-predicted image with bounding boxes from the first result set,
    using thicker lines, a background behind the label text, and a larger font.
    """
    image = cv2.imread(original_path)
    if image is None:
        print("Error: Could not read the original image.")
        return None

    # Resize for consistency
    image = cv2.resize(image, (600, 600))

    if results and results[0].boxes:
        # Get YOLO detection boxes
        boxes = results[0].boxes.data.cpu().numpy()

        for det in boxes:
            x1, y1, x2, y2, conf, class_id = det
            x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])

            # Bright green for high confidence; else red
            color = (0, 255, 0) if conf >= 0.7 else (0, 0, 255)

            # Thicker box outline
            box_thickness = 3
            cv2.rectangle(image, (x1, y1), (x2, y2), color, box_thickness)

            # Larger/confident text label
            label_text = f"{conf:.2f}"
            font_scale = 1.0
            text_thickness = 2

            # Calculate text size for the background rectangle
            (text_width, text_height), baseline = cv2.getTextSize(
                label_text,
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                text_thickness
            )

            # Make sure the text background is above the top box edge
            text_y = max(y1, text_height + 10)

            # Draw filled rectangle behind text for better visibility
            cv2.rectangle(
                image,
                (x1, text_y - text_height - 5),
                (x1 + text_width, text_y),
                color,
                -1
            )

            # Put text in white on top of the colored rectangle
            cv2.putText(
                image,
                label_text,
                (x1, text_y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (255, 255, 255),  # White text
                text_thickness
            )
    else:
        # If no detections, add text indicating this
        cv2.putText(
            image,
            "No detections",
            (50, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),  # Red text
            2
        )

    # Save to predictions folder
    base_filename = os.path.basename(original_path)
    predicted_filename = "predicted_" + base_filename
    output_path = os.path.join(PREDICTIONS_FOLDER, predicted_filename)
    cv2.imwrite(output_path, image)

    return f"/static/uploads/predictions/{predicted_filename}"
###############################################################################
# Prediction Endpoint
###############################################################################
@proxy_app.route('/predict_disease', methods=['POST'])
def predict_disease_route():
    try:
        logger.info("Received prediction request")
        
        # Enhanced logging for debugging
        for key, value in request.form.items():
            logger.info(f"Form data - {key}: {value}")
        
        # Validate required form data
        required_fields = ['petType', 'ownerName', 'petName', 'petGender', 'symptoms']
        for field in required_fields:
            if field not in request.form:
                logger.error(f"Missing required field: {field}")
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400

        # Validate file uploads
        if 'full_animal_image' not in request.files or 'disease_image' not in request.files:
            logger.error("Missing image files")
            return jsonify({
                "success": False,
                "error": "Both full animal and disease images are required"
            }), 400

        # Extract data from request
        user_selected_type = request.form.get("petType", "Unknown").lower()
        owner_name = request.form.get("ownerName", "Unknown")
        pet_name = request.form.get("petName", "Unknown")
        pet_gender = request.form.get("petGender", "Unknown")
        user_symptoms = request.form.getlist("symptoms")

        # Save uploaded files
        full_animal_file = request.files['full_animal_image']
        disease_file = request.files['disease_image']

        full_animal_filename = secure_filename(full_animal_file.filename)
        full_animal_filepath = os.path.join(proxy_app.config['F_UPLOAD_FOLDER'], full_animal_filename)
        full_animal_file.save(full_animal_filepath)

        disease_filename = secure_filename(disease_file.filename)
        disease_filepath = os.path.join(proxy_app.config['UPLOAD_FOLDER'], disease_filename)
        disease_file.save(disease_filepath)

        # Classify animal type
        classified_type, classification_confidence = classify_pet_type(full_animal_filepath)
        
        if classified_type == "Other" or classification_confidence < 0.5:
            return jsonify({
                "success": False,
                "error": "Could not detect a clear cat or dog in the image. Please upload a clearer photo."
            }), 400

        # Predict disease
        if user_selected_type not in ["cat", "dog"]:
            return jsonify({"error": "Please select either 'cat' or 'dog'"}), 400

        # Get disease prediction
        predict_func = predict_cat_disease if user_selected_type == "cat" else predict_dog_disease
        final_disease, detected_image_url, report = predict_func(disease_filepath, user_symptoms)
        
        # Prepare prediction data
        prediction_data = {
            "success": True,
            "pet_type": user_selected_type,
            "pet_name": pet_name,
            "owner_name": owner_name,
            "pet_gender": pet_gender,
            "disease": final_disease,
            "detected_image_path": detected_image_url or "/static/images/no_prediction.png",
            "confidence": report['confidence'],
            "symptoms": user_symptoms,
            "full_animal_image_path": full_animal_filepath,
            "disease_image_path": disease_filepath
        }

        # Try saving to local database
        local_prediction_id = save_prediction_to_local_db(prediction_data)

        # Prepare final response
        response_data = {
            "success": True,
            "pet_type": user_selected_type,
            "disease": final_disease,
            "detected_image_url": detected_image_url or "/static/images/no_prediction.png",
            "local_prediction_id": local_prediction_id,
            "confidence": report['confidence'],
            "symptom_match": report['symptom_match'].get(final_disease, 0),
            "all_scores": report['all_scores'],
            "metadata": {
                "pet_name": pet_name,
                "owner_name": owner_name,
                "pet_gender": pet_gender
            }
        }

        # Add confidence warning if needed
        if report['confidence'] < 0.6:
            response_data["warning"] = "Low confidence prediction. Please consult with a veterinarian."

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Unexpected error in prediction route: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Unexpected server error: {str(e)}"
        }), 500
    
DATABASE_DIR = 'database'
os.makedirs(DATABASE_DIR, exist_ok=True)





def save_prediction_to_local_db(prediction_data):
    """Save prediction results to local SQLite database."""
    try:
        with sqlite3.connect(os.path.join(DATABASE_DIR, 'local_predictions.db')) as conn:
            cursor = conn.cursor()
            
            # Prepare data for insertion
            insert_data = (
                prediction_data.get('pet_type', 'Unknown'),
                prediction_data.get('disease', 'Unknown'),
                prediction_data.get('confidence', 0.0),
                json.dumps(prediction_data.get('symptoms', [])),
                prediction_data.get('full_animal_image_path', ''),
                prediction_data.get('disease_image_path', ''),
                prediction_data.get('detected_image_path', ''),
            )
            
            cursor.execute('''
                INSERT INTO predictions (
                    pet_type, disease, confidence, symptoms, 
                    full_animal_image_path, disease_image_path, detected_image_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', insert_data)
            
            conn.commit()
            logger.info(f"Prediction saved to local database with ID: {cursor.lastrowid}")
            return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Error saving prediction to local database: {e}")
        return None
###############################################################################
# Run the Proxy Server
###############################################################################
if __name__ == '__main__':
    try:
        print("Starting AI analysis server on port 5001...")
        proxy_app.run(host='127.0.0.1', port=5001, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\nShutting down AI server...")
        sys.exit(0)
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)
