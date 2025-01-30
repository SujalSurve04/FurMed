# 🐾 FurMed: AI-Powered Pet Disease Detection System

FurMed is a sophisticated web application that leverages artificial intelligence to diagnose diseases in both pets and stray animals. The system uses advanced deep learning models including YOLOv8 for object detection and custom CNN architectures for precise disease classification.

## ✨ Key Features

### Core Functionality
- 🔍 **Dual Animal Classification**: Accurately identifies cats and dogs in uploaded images
- 🏥 **Disease Detection**: 
  - Cats: Dermatitis, Flea Allergy, Ringworm, Scabies, Mange
  - Dogs: Cataratas, Conjuntivitis, Infección Bacteriana, PyodermaNasal, Sarna, Dermatitis, Ringworm
- 📋 **Comprehensive Reports**: Detailed disease information, first aid advice, and treatment recommendations

### Technical Architecture
- 🖥️ **Dual-Server System**:
  - Main Server (Port 5000): Handles user interface, database operations, and payment processing
  - Proxy Server (Port 5001): Dedicated to AI model inference and image processing
- 💾 **Hybrid Storage**:
  - Primary: MongoDB for scalable cloud storage
  - Backup: Local SQLite database for reliability
- 💰 **Payment Integration**: Secure PayPal gateway with INR/USD conversion
- 📧 **Communication**: Email feedback system and automated invoice generation

### User Experience
- 📱 **Responsive Design**: Optimized for all device sizes
- 🌐 **Real-time Processing**: Fast disease detection and report generation
- 🔄 **Feedback System**: Users can provide correction feedback for continuous improvement

## 🛠️ Technology Stack

### Backend
- **Framework**: Flask
- **AI/ML**: 
  - TensorFlow/Keras
  - YOLOv8
  - OpenCV
- **Databases**: 
  - MongoDB (primary)
  - SQLite (backup)
- **Payment**: PayPal API
- **Email**: Flask-Mail

### Frontend
- **Framework**: HTML5, CSS3, JavaScript
- **Styling**: Tailwind CSS
- **Visualization**: Chart.js
- **Maps**: Leaflet.js

## 📁 Project Structure

```
FurMed/
├── main_server.py          # Primary application server
├── proxy_server.py         # AI inference server
├── logs/
├── database/
│    
├── models/
│   ├── cat/                    # Cat disease models
│   │   ├── *_keras.h5         # Keras models
│   │   └── *_yolov8.pt        # YOLOv8 models
│   └── dog/                    # Dog disease models
│       ├── *_keras.h5         # Keras models
│       └── *_yolov8.pt        # YOLOv8 models
│
├── frontend/
│   ├── static/                 # Static assets
│   │   ├── css/               # Stylesheets
│   │   ├── js/                # JavaScript files
│   │   ├── images/            # Static images
│   │   ├── uploads/           # Disease images
│   │   ├── f_upload/          # Full animal images
│   │   └── invoices/          # Payment invoices
│   └── templates/              # HTML templates
│
└── database/                   # Local database storage
```

## ⚙️ Installation Guide

### Prerequisites
- Python 3.9+
- MongoDB 5.0+
- Git

### Step 1: Clone & Setup
```bash
# Clone repository
git clone https://github.com/SujalSurve04/FurMed.git
cd FurMed

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Environment Configuration
Create `.env` file in root directory:
```ini
# MongoDB Configuration
MONGO_URI=your_mongodb_uri

# PayPal Settings
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_SECRET=your_paypal_secret
PAYPAL_API_BASE=https://api-m.sandbox.paypal.com

# Email Configuration
MAIL_USERNAME=your_email
MAIL_PASSWORD=your_app_password

# Application Security
SECRET_KEY=your_secure_secret_key
```

### Step 3: Directory Setup
```bash
# Create required directories
mkdir -p frontend/static/{uploads,f_upload,invoices}
mkdir -p database
```

### Step 4: Download Models
Download the pre-trained models from [Google Drive](https://drive.google.com/drive/folders/11dRe0v_fgoGKq8NONxXMy7A7rNuaO6gl?usp=drive_link) and place them in the `models/` directory.

## 🚀 Running the Application

1. Start the AI Inference Server:
```bash
python proxy_server.py  # Runs on port 5001
```

2. Launch the Main Application Server:
```bash
python main_server.py   # Runs on port 5000
```

Access the application at: http://localhost:5000

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|---------|------------|
| `/disease` | POST | Process pet disease detection |
| `/donation` | POST | Handle donations |
| `/feedback` | POST | Process user feedback |
| `/api/get_predictions` | GET | Retrieve prediction history |
| `/api/get_donations` | GET | Access donation records |
| `/convert-inr-to-usd` | POST | Currency conversion |

## 🔒 Security Features

- Secure credential management via environment variables
- File upload validation and sanitization
- PayPal sandbox integration for safe testing
- MongoDB authentication protection
- Cross-Origin Resource Sharing (CORS) protection
- SQL injection prevention
- Rate limiting on sensitive endpoints

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Contact & Support

- **Email**: survesujal04@gmail.com
- **Issues**: Please use the GitHub issues tab
- **Models**: Access pre-trained models [here](https://drive.google.com/drive/folders/11dRe0v_fgoGKq8NONxXMy7A7rNuaO6gl?usp=drive_link)

## 📄 License

This project is licensed under the MIT License. See `LICENSE` file for details.

---

Made with ❤️ by the FurMed Team
