
// Symptom options for Cats and Dogs
document.addEventListener("DOMContentLoaded", function () {
	const symptomsContainer = document.getElementById("symptomsContainer");
	const petTypeRadios = document.querySelectorAll('input[name="petType"]');
  
	// Symptom options for Cats and Dogs
	const symptoms = {
		Cat: [
		  "Redness",  "Swelling","Itching",
		  "Excessive Scratching","Hair Loss",
		  "Circular Hair Loss","Scaly Patches",
		  "Crusty Skin","Wounds","Patchy Hair Loss",
		  "Intense Itching","Thickened Skin"
		],
		Dog: [
		  "Cloudy Eyes","Vision Loss","Red Eyes",
		  "Discharge","Swelling","Pus","Wound",
		  "Nasal Discharge","Crusty Nose",
		  "Intense Itching","Scaling","Scabs",
		  "Hair Loss","Inflammation",
	 	  "Constant Scratching","Circular Lesions","Hair Loss",
		  "Crusty Skin",  "Itching","Lesions"
		]
	  };
	  
	
	// Update symptoms based on selected pet type
	petTypeRadios.forEach((radio) => {
	  radio.addEventListener("change", () => {
		const selectedType = radio.value;
		updateSymptoms(selectedType);
	  });
	});
  
	function updateSymptoms(petType) {
	  symptomsContainer.innerHTML = ""; // Clear current symptoms
	  if (symptoms[petType]) {
		symptoms[petType].forEach((symptom) => {
		  const checkbox = document.createElement("input");
		  checkbox.type = "checkbox";
		  checkbox.name = "symptoms";
		  checkbox.value = symptom;
		  checkbox.id = symptom;
  
		  const label = document.createElement("label");
		  label.htmlFor = symptom;
		  label.textContent = symptom;
  
		  const wrapper = document.createElement("div");
		  wrapper.appendChild(checkbox);
		  wrapper.appendChild(label);
  
		  symptomsContainer.appendChild(wrapper);
		});
	  }
	}
  });
  document.getElementById('analysisForm').addEventListener('submit', function(e) {
    const loadingOverlay = document.querySelector('.loading-overlay');
    loadingOverlay.style.display = 'flex';
    
    // Optional: Disable form submission button
    const submitBtn = this.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
});

// Enhanced symptom display
function updateSymptoms(petType) {
    const container = document.getElementById('symptomsContainer');
    container.className = 'symptoms-grid';
    container.innerHTML = '';
    
    if (symptoms[petType]) {
        symptoms[petType].forEach(symptom => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'symptom-item';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.name = 'symptoms';
            checkbox.value = symptom;
            checkbox.id = symptom;
            checkbox.className = 'form-check-input';
            
            const label = document.createElement('label');
            label.htmlFor = symptom;
            label.textContent = symptom;
            label.className = 'form-check-label';
            
            itemDiv.appendChild(checkbox);
            itemDiv.appendChild(label);
            container.appendChild(itemDiv);
        });
    }
}
  