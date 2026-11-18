# 🏛️ Zero-Cross-Impact Garment Architecture Blueprint
## (एकमेकांवर अजिबात परिणाम न होणारे स्वतंत्र आर्किटेक्चर)

---

## 1. मुख्य समस्या काय आहे? (Root Cause of Cross-Impact)

सध्या सिस्टीममध्ये **"Leaky Abstractions"** आणि **"Tight Coupling"** आहे:
1. **Direct Cross-Import:** `Blazer` थेट `Kurta (Sherwani)` चे मॉड्यूल्स इम्पोर्ट करतो.
2. **Central If-Else Sprawl:** शेअर्ड फाइल्स (`fabric_conditioning.py`, `garment_lighting.py`, `backgrounds.py`) मध्ये `if garment_type == 'shirt'` असे स्पेशल रूल्स आहेत. उद्या तुम्ही साडी किंवा कुर्तीसाठी तिथे नवीन नियम टाकला, तर नकळत तो शर्ट किंवा ब्लेझरवर परिणाम करू शकतो.
3. **Legacy Fallback:** `Pant` कडे स्वतःचा कॅटलॉग नसल्याने तो जुन्या शेअर्ड `legacy.py` वर चालतो.

---

## 2. नवीन आर्किटेक्चर: "Garment Strategy / Plugin Pattern"

या आर्किटेक्चरचा मुख्य नियम आहे:
> **"The Core Engine knows how to run shots, but knows NOTHING about garments. Each Garment owns 100% of its prompts, lighting, backgrounds, and details."**

---

## 3. आर्किटेक्चरचे ४ सुवर्ण नियम (The 4 Golden Rules)

### नियम १: Zero Cross-Garment Imports (कडक बंदी)
`ai/garments/X/` मधील कोणतीही फाईल `ai/garments/Y/` मधून **काहीही इम्पोर्ट करू शकत नाही.**
- उदा. Blazer ने Kurta कडून `SCENERY` किंवा `WHITE_LIGHT` इम्पोर्ट करणे पूर्णपणे बंद.

### नियम २: शेअर्ड कोर इंजिनमध्ये `if garment == '...'` नसावे
- `runner.py`, `renderer.py`, `main.py` या कोर फाइल्समध्ये गार्मेंटच्या नावाचे कोणतेही `if-else` असणार नाही.
- कोर इंजिन फक्त गार्मेंटच्या `definition.build_config(data, shot, seed)` ला कॉल करेल. प्रॉम्प्ट कसा तयार करायचा हे १००% ते गार्मेंट स्वतः ठरवेल.

### नियम ३: शेअर्ड फाइल्स फक्त "Pure Utilities" (Tools) असाव्यात
- शेअर्ड फाइल्समध्ये प्रॉम्प्टचे वाक्य (Strings) नसतील.
- शेअर्ड फाइल्समध्ये फक्त गणिताची आणि इमेज प्रोसेसिंगची टूल्स असतील:
  - `measure_fabric_colours(image)` -> RGB व्हॅल्यू देईल (प्रॉम्प्ट नाही)
  - `crop_identity_reference(image, box)` -> इमेज क्रॉप करेल
  - `detect_face(image)` -> फेस बॉक्स देईल
- त्या RGB व्हॅल्यूचे प्रॉम्प्ट कसे बनवायचे हे प्रत्येक गार्मेंटचे स्वतःचे `prompts.py` ठरवेल.

### नियम ४: स्वयंचलित आर्किटेक्चर चाचणी (CI/Test Guardrail)
- एक ऑटोमॅटिक टेस्ट (`test_garment_isolation.py`) बनवली जाईल जी दर वेळी चालेल.
- जर चुकून कोणी एका गार्मेंटचा कोड दुसऱ्यामध्ये इम्पोर्ट केला, तर टेस्ट लगेच **FAIL** होईल.

---

## 4. अंमलबजावणीचा ४-टप्प्यांचा मास्टर प्लॅन (Implementation Plan)

### 🔹 टप्पा १: Blazer आणि Kurta चे डीकप्लिंग (Immediate Fix)
1. `kurta/catalog/sherwani.py` मधील `SCENERY` आणि `WHITE_LIGHT` कॉन्स्टंट्स कॉपी करून:
   - एकतर `blazer/catalog/lighting.py` मध्ये स्वतंत्र ठेवा.
   - किंवा जेनेरिक सीन असल्यास `ai/scene/scenery.py` मध्ये हलवा.
2. `blazer/catalog/business.py` आणि `casual.py` मधील `from fabricapp.ai.garments.kurta...` इम्पोर्ट्स काढून टाका.

### 🔹 टप्पा २: शेअर्ड `fabric_conditioning.py` मधील शर्टचे लॉजिक वेगळे करणे
1. `fabric_conditioning.py` मधील ५ `if garment_type == "shirt"` ब्लॉक्स काढून टाका.
2. ते सर्व लॉजिक `fabricapp/ai/garments/shirt/catalog/prompts.py` (आणि `shirt/builder.py`) मध्ये हलवा.
3. `fabric_conditioning.py` फक्त जेनेरिक कलर कंडिशनिंग टूल बनेल.

### 🔹 टप्पा ३: पँट (Pant) साठी स्वतंत्र कॅटलॉग बनवणे
1. नवीन डिरेक्टरी: `fabricapp/ai/garments/pant/catalog/`
2. फाइल्स:
   - `definition.py`: 4 किंवा 6 शॉट्स (Front Full, Pocket Detail, Hem Detail, Waistband, Back)
   - `prompts.py`: पँटसाठीचे प्युअर प्रॉम्प्ट्स
   - `layout.py`: पँटचा कॅटलॉग कोलाज लेआउट
3. `catalog_engine/registry.py` मध्ये `('pant', 'classic-v1')` रजिस्टर करा आणि `legacy.py` वरील अवलंबित्व संपवा.

### 🔹 टप्पा ४: ऑटोमॅटिक आयसोलेशन टेस्ट (Guardrail) तयार करणे
एक युनिट टेस्ट तयार करणे जी खालील २ गोष्टी तपासेल:
1. **AST Import Scanner:** कोणत्याही गार्मेंटने दुसऱ्या गार्मेंटला इम्पोर्ट केलेले नाही.
2. **Snapshot Regression Test:** साडीच्या कोडमध्ये बदल केल्यास शर्ट, कुर्ता किंवा ब्लेझरचा प्रॉम्प्ट १ टक्काही बदलत नाही.
