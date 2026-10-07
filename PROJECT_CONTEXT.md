# Fabric Try-on: सद्य Project Context

हा दस्तऐवज सध्याच्या लागू कोडची स्थिती, image-flow आणि अलीकडील मर्यादित बदल नोंदवतो. तो पुढील बदलांसाठी संदर्भ आहे.

## Image आणि request flow

- `image 1`: fabric swatch. त्यातील रंग, print आणि motif वापरायचे; garment shape कॉपी करायची नाही.
- Person image दिली आणि pose/camera दिला, तर request `person_pose` होते.
  - `image 0` हा रिकामा 3:4 portrait canvas असतो.
  - Person photo `image 2` reference म्हणून जाते.
  - Model नवीन full-body photograph तयार करतो. त्यामुळे pose बदलता येते; पण face आणि body proportions prompt ने जपावे लागतात.
- Person image दिली पण pose/camera दिला नाही, तर request `person_photo` होते आणि मूळ photo edit होतो.
- Pose-reference image फक्त saree `pallu_on_head` साठी वापरली जाते, आणि person image नसल्यावरच वापरली जाते.
- Person image असल्यास कोणत्याही garment साठी pose-reference image पाठवली जात नाही. हा जाणीवपूर्वक ठेवलेला नियम आहे.

## लागू केलेले बदल

### 1. Portrait output आणि fabric quality

`fabricapp/ai/cloudflare_engine.py` मध्ये person-pose generation साठी स्थिर 3:4 portrait canvas आणि output ठेवले आहे. यामुळे पूर्ण body साठी उंच frame मिळतो आणि पूर्वीच्या sharp fabric scale शी सुसंगतता राहते.

### 2. Kurti-pant: फक्त तीन अडचणीच्या poses

`fabricapp/ai/pose_data.py` मध्ये फक्त `kurti_pant` साठी खालील pose overrides आहेत:

- `sleeve_adjust_stand`: right hand ने left wrist जवळ sleeve cuff पकडणे आणि left hand thigh जवळ ठेवणे स्पष्ट केले आहे.
- `three_quarter_hand_adjust`: right forearm, left forearm आणि left hand ने right wrist पकडण्याची जागा स्पष्ट केली आहे.
- `cross_leg_chair_recline`: chair, lap वरचे हात, crossed legs आणि दोन्ही feet स्पष्ट केले आहेत.

इतर kurti-pant poses, saree poses आणि `pallu_on_head` pose-reference path बदललेले नाहीत.

### 3. Kurti-pant cross-chair identity protection

`fabricapp/ai/prompt_builder.py` मध्ये `cross_leg_chair_recline` साठीच extra identity lock जोडला आहे:

- image 2 प्रमाणे facial structure ठेवणे
- seated pose मध्येही slim shoulder, waist आणि hip widths ठेवणे
- arm/leg thickness बदलू न देणे
- source clothes किंवा loose cloth काढणे

हा नियम इतर poses वर लागू होत नाही.

## Saree + person image + pose: सध्याची समस्या

### दिसणारे वर्तन

Person image दिल्यावर saree fabric लागू होतो; मात्र pose मूळ photo सारखाच राहू शकतो किंवा अपेक्षित pose स्पष्ट होत नाही.

### Code मधील कारणे

1. **Saree person-pose request resolver वापरत नाही.**
   Saree resolver फक्त `generated_person` आणि `face_photo` scenarios साठी आहे. Person image + pose request `person_pose` बनते आणि shared older prompt path वापरते.

2. **Final saree person-pose prompt खूप मोठा आहे.**
   तपासलेल्या prompts मध्ये 977 ते 1041 शब्द आहेत. Pose ची सूचना सुरुवातीला असली तरी पुढे identity, background, pallu, blouse, fabric, border, modesty आणि final rules येतात. FLUX model अशा मोठ्या prompt मध्ये fabric instruction जास्त स्थिरपणे पाळतो; pose चे छोटे spatial details कमी प्राधान्याने घेतो.

3. **Saree pose text आणि saree garment text दोन्ही pallu/pleats सांगतात.**
   Pose override मध्ये pallu कुठे आहे, हात कुठे आहेत आणि pleats कुठे आहेत हे येते. Garment text पुन्हा pallu आणि pleats सांगतो. अर्थ थेट विरुद्ध नसला तरी एकाच visual भागासाठी अनेक instructions येतात. Pose मधील हात किंवा body orientation यांचे महत्त्व कमी होऊ शकते.

4. **Person photo edit होत नाही; ती कमी-size reference म्हणून जाते.**
   Person-pose flow मध्ये model रिकाम्या canvas वर पूर्ण नवीन photo तयार करतो. Person image 511 px maximum size पर्यंत resize होते. Saree drape, pallu, full-body pose आणि original identity हे सर्व एकाच वेळी नव्याने तयार करावे लागते.

5. **Person image असताना pose-reference वापरला जात नाही.**
   हा सध्याचा अपेक्षित नियम आहे. त्यामुळे साडीच्या person-image poses मध्ये model कडे text व्यतिरिक्त pose geometry दाखवणारी image नाही.

## Saree issue साठी सध्याचा निष्कर्ष

ही समस्या fabric setting मुळे नाही. Person-image saree flow मधील long shared prompt, pallu instructions ची पुनरावृत्ती आणि blank-canvas reconstruction या तीन गोष्टी pose follow होण्यास कमकुवत करतात.

या दस्तऐवजाच्या वेळी saree code मध्ये कोणताही बदल केलेला नाही. पुढील वेळी बदल करायचा असल्यास तो फक्त `saree + person_pose` route साठी छोटा dedicated prompt बनवून करावा. त्यामुळे saree generated-person, face-photo, `pallu_on_head` reference flow आणि सध्या योग्य असलेले prompts बदलणार नाहीत.
