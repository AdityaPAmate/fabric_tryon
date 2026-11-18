# 🧵 Fabric Tryon: कॅटलॉग आणि गार्मेंट आर्किटेक्चर विश्लेषण (मराठीत)

---

## 1. सारांश (Executive Summary)

तुमच्या प्रोजेक्टमध्ये **काही गार्मेंट्सचे कॅटलॉग कोड स्वतंत्र आहेत, पण अनेक महत्त्वाच्या ठिकाणी कोड छुपेपणाने एकमेकांवर अवलंबून (tightly coupled) आहे.**

विशेषतः:
1. **धोकादायक क्रॉस-डिपेंडन्सी (Cross-Garment Import):** `Blazer` चा कॅटलॉग कोड `Kurta (Sherwani)` मधून थेट प्रॉम्प्ट आणि लायटिंग इम्पोर्ट करतो!
2. **शेअर्ड कोडमधील हार्डकोडेड If-Else:** `fabric_conditioning.py` आणि `garment_lighting.py` मध्ये `if garment_type == 'shirt'` असे स्पेशल रूल्स आहेत; बाकी सर्व गार्मेंट्स एकच डिफॉल्ट पाथ शेअर करतात. एकाचा बदल दुसऱ्याला लागू होतो.
3. **पँट (Pant) ची स्वतंत्र फाईल नाही:** पँटसाठी कोणताही स्वतंत्र कॅटलॉग नाही, ती जुन्या `legacy.py` वर चालते.

---

## 2. प्रत्येक गार्मेंटचा कोड कुठे आणि कसा आहे?

### A. साडी (Saree) — **80% स्वतंत्र**
- **स्थान:** `fabricapp/ai/garments/saree/`
  - `catalog/definition.py` : मुख्य कॅटलॉग शॉट्सची रचना
  - `catalog/prompts.py` : साडीसाठीचे विशेष प्रॉम्प्ट्स (Pallu, Pleats, Border)
  - `catalog/layout.py` : 6-पॅनेल किंवा 4-पॅनेल लेआउट
  - `catalog/references.py` : पल्लू आणि बॉर्डरचे संदर्भ
- **शेअर्ड अवलंबित्व:** `fabric_conditioning.py` आणि `pose_registry.py` वापरते.

---

### B. कुर्ती-पँट (Kurti-Pant) — **75% स्वतंत्र**
- **स्थान:** `fabricapp/ai/garments/kurti_pant/`
  - `catalog/definition.py` : Editorial-v1 लेआउट आणि शॉट्स
  - `catalog/prompts.py` : नेकलाईन, स्लीव्ह, हेमचे प्रॉम्प्ट्स
  - `builder.py` : ट्रायऑन प्रॉम्प्ट बिल्डर
- **शेअर्ड अवलंबित्व:** `fabric_conditioning.py`, `garment_lighting.py`.

---

### C. शर्ट (Shirt) — **85% स्वतंत्र (पण शेअर्ड कोडवर परिणाम करणारा)**
- **स्थान:** `fabricapp/ai/garments/shirt/`
  - `catalog/definition.py` : Classic-v1 व्याख्या
  - `catalog/layout.py` : कॉलर, कफ, बटन प्लॅकेट लेआउट
  - `catalog/prompts.py` : शर्टचे स्वतःचे प्रॉम्प्ट्स
- **धोका:** शर्टसाठी शेअर्ड फाइल्समध्ये (`fabric_conditioning.py`, `garment_lighting.py`, `backgrounds.py`) भरपूर `if garment_type == 'shirt'` लिहिले आहेत. त्यामुळे शर्ट सुधारताना शेअर्ड फाइल्स बदलल्यास इतर गार्मेंट्सवर नकळत परिणाम होतो.

---

### D. कुर्ता (Kurta) — **प्रकारानुसार विभागलेला (Sub-typed)**
कुर्तामध्ये प्रत्येक प्रकारासाठी वेगळी फाईल आहे:
- `kurta/catalog/plain.py` (Plain Kurta)
- `kurta/catalog/sherwani.py` (Sherwani)
- `kurta/catalog/jodhpuri.py` (Jodhpuri)
- `kurta/catalog/pathani.py` (Pathani)
- प्रत्येकाचे स्वतःचे कलर प्रोफाईल (`sherwani_colour.py`, `jodhpuri_colour.py`) आहेत.

---

### E. ब्लेझर (Blazer) — **⚠️ उच्च धोका (High Risk - Tightly Coupled)**
ब्लेझरचे प्रकार:
- `blazer/catalog/business.py`
- `blazer/catalog/casual.py`
- `blazer/catalog/wedding.py`
- **🚨 सर्वात मोठी गडबड:**
  `business.py` मध्ये ही ओळ आहे:
  ```python
  from fabricapp.ai.garments.kurta.catalog.sherwani import SCENERY, WHITE_LIGHT
  ```
  आणि `casual.py` मध्ये:
  ```python
  from fabricapp.ai.garments.kurta.catalog.sherwani import SCENERY
  ```
  **याचा अर्थ:** उद्या जर तुम्ही **शेरवानी कुर्ताचा** बॅकग्राउंड (`SCENERY`) किंवा लायटिंग (`WHITE_LIGHT`) चा प्रॉम्प्ट बदलला, तर **ब्लेझरचे आउटपुट आपोआप बिघडेल!**

---

### F. पँट (Pant) — **⚠️ स्वतंत्र कॅटलॉग नाही**
- `ai/garments/pant/` मध्ये फक्त `builder.py`, `details.py`, `poses.py`, `prompts.py` आहेत.
- **कॅटलॉग फोल्डरच अस्तित्वात नाही!**
- पँटचा कॅटलॉग `catalog_engine/legacy.py` मधून 6-शॉट जेनेरिक पद्धतीने चालतो.

---

## 3. शेअर्ड कोडमधील "धोकादायक क्षेत्रे" (Danger Zones)

खालील शेअर्ड फाइल्समध्ये गार्मेंट्सचे लॉजिक मिसळलेले आहे:

| शेअर्ड फाईल | काय प्रॉब्लेम आहे? | धोका |
|---|---|---|
| `fabric_conditioning.py` | `if garment_type == 'shirt'` चे 5 वेगळे ब्लॉक्स आहेत. फॅब्रिक कलर आणि पॅलेट प्रिजर्व्हेशनचे नियम शर्टसाठी वेगळे आणि इतरांसाठी वेगळे आहेत. | शर्टचा कोड बदलताना साडी किंवा कुर्ताचे कलर आउटपुट बदलू शकते. |
| `garment_lighting.py` | `SHIRT_LIGHTING` वेगळा आहे, आणि उर्वरित सर्व गार्मेंट्ससाठी एकच कॉमन लायटिंग आहे (`-lighting-v1`). | जर तुम्ही ब्लेझरची लायटिंग सुधारण्यासाठी शेअर्ड फाईल बदलली, तर साडी आणि कुर्तीची लायटिंगसुद्धा बदलेल! |
| `backgrounds.py` | शर्टसाठी वेगळा बॅकग्राउंड पाथ आणि इतरांसाठी कॉमन पाथ. | इतर गार्मेंट्सचे बॅकग्राउंड एकमेकांशी बांधलेले आहेत. |
| `legacy.py` | पँट आणि जुन्या गार्मेंट्ससाठी एकच हार्डकोडेड प्रॉम्प्ट टेम्पलेट वापरले जाते. | पँटच्या प्रॉम्प्टमध्ये बदल केल्यास इतर लेगसी गार्मेंट्सवर परिणाम होतो. |

---

## 4. भविष्यातील आर्किटेक्चर दुरुस्तीसाठी कृती आराखडा (Remediation Roadmap)

तुम्हाला हवे असलेले आयसोलेटेड आर्किटेक्चर बनवण्यासाठी हे 4 टप्पे करा:

### टप्पा 1: क्रॉस-गार्मेंट इम्पोर्ट तोडणे (तात्काळ)
- `kurta/catalog/sherwani.py` मधील `SCENERY` आणि `WHITE_LIGHT` हे कॉन्स्टंट्स काढून एकतर `ai/scene/` मध्ये न्यावेत किंवा `blazer/catalog/` मध्ये त्यांची स्वतःची कॉपी करावी.
- नियम: **कोणताही गार्मेंट दुसऱ्या गार्मेंटच्या फोल्डरमधून काहीही इम्पोर्ट करणार नाही.**

### टप्पा 2: लायटिंग आणि बॅकग्राउंडचे डिसेन्ट्रलायझेशन
- सध्या `garment_lighting.py` मध्ये एकच कॉमन लायटिंग स्ट्रिंग सर्वांना जाते.
- त्याऐवजी प्रत्येक गार्मेंटच्या `catalog/` फोल्डरमध्ये स्वतःचे `lighting.py` असावे.

### टप्पा 3: पँटसाठी स्वतंत्र कॅटलॉग बनवणे
- `ai/garments/pant/catalog/definition.py` तयार करून पँटला `legacy.py` मधून बाहेर काढणे.

### टप्पा 4: शेअर्ड फॅब्रिक कंडिशनिंगचे नियम
- `fabric_conditioning.py` मधील `if garment_type == 'shirt'` सारखे हार्डकोडेड नियम काढून, ते नियम संबंधित गार्मेंटच्या स्वतःच्या `settings.py` किंवा `builder.py` मध्ये हलवणे.
