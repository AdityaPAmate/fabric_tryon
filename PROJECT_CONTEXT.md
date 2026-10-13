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

## person_pose साठी सध्याचे prompt routes (`prompt_builder.build_prompt`)

| garment_type | person_pose साठी वापरला जाणारा prompt |
|---|---|
| `kurti_pant` | छोटा dedicated prompt (`_build_person_pose_kurti_prompt`) |
| `shirt` | छोटा dedicated prompt (`_build_person_pose_shirt_prompt`) |
| `kurta`, `blazer` (NEW) | छोटा dedicated prompt (`_build_person_pose_spec_prompt`) |
| `saree`, `pant`, garment_image | जुना shared long prompt (अजून बदललेला नाही) |

## लागू केलेले बदल

### 1. Portrait output आणि fabric quality

`fabricapp/ai/cloudflare_engine.py` मध्ये person-pose generation साठी स्थिर 3:4 portrait canvas आणि output ठेवले आहे. यामुळे पूर्ण body साठी उंच frame मिळतो आणि पूर्वीच्या sharp fabric scale शी सुसंगतता राहते.

### 2. Kurti-pant: फक्त तीन अडचणीच्या poses

`fabricapp/ai/pose_data.py` मध्ये फक्त `kurti_pant` साठी खालील pose overrides आहेत:

- `sleeve_adjust_stand`: right hand ने left wrist जवळ sleeve cuff पकडणे आणि left hand thigh जवळ ठेवणे स्पष्ट केले आहे.
- `three_quarter_hand_adjust`: right forearm, left forearm आणि left hand ने right wrist पकडण्याची जागा स्पष्ट केली आहे.
- `cross_leg_chair_recline`: chair, lap वरचे हात, crossed legs आणि दोन्ही feet स्पष्ट केले आहेत.

### 3. Kurti-pant cross-chair identity protection

`fabricapp/ai/prompt_builder.py` मध्ये `cross_leg_chair_recline` साठीच extra identity lock जोडला आहे. इतर poses वर लागू होत नाही.

### 4. Kurta आणि Blazer (NEW) — test reports वरून

Test reports (`all_reports.json`, 2026-10-09) मधील तक्रारी:

| # | garment | request | तक्रार |
|---|---|---|---|
| 1 | kurta/plain | person image + pose `hands_on_hips_side_look` + background | pose not work |
| 2 | kurta/plain | person image, pose नाही, background | pant must be white |
| 3 | kurta/plain | person image, `with_dupatta` | dupatta plain, fabric pattern नाही |
| 4 | kurta/plain | person image + camera_view `side` | camera view not work |
| 5 | kurta/plain | person image + pose `rail_wide_arm_side_look` | pose not work |
| 6 | blazer/business | person image + pose `hands_on_hips_side_look` + background | poses not work |

कारणे (कोड वाचून; output images पाहिलेल्या नाहीत):

- **#1, #4, #5, #6 (pose / camera_view):** Person image + pose किंवा camera_view दिल्यास request `person_pose` बनते. `kurta` आणि `blazer` साठी तेव्हा जुना shared long prompt वापरला जात होता (SUBJECT, IDENTITY, PERSON_POSE_EXTRA, garment, color_note, FABRIC, BORDER, CLOSING, MODESTY_RULE, PERSON_REFERENCE_LINE, background override, MODESTY_FINAL). इतका मोठा prompt असल्यावर pose चे छोटे spatial details कमी प्राधान्याने पाळले जातात. `kurti_pant` आणि `shirt` साठी हीच समस्या dedicated short prompt ने आधी सोडवली होती; kurta आणि blazer साठी तो route नव्हता.
- **#2 (pant white):** `GARMENT_SPECS[("kurta","plain")]` मध्ये pajama चा रंग "white, off-white, or a solid shade from the kurta's palette" असा मोकळा होता. `prompts.py` मधील kurta/plain edit prompt मध्येही pajama चा रंग "white, off-white, or a solid shade picked from the kurta's own color palette" असा मोकळा आहे, आणि `prompt_builder` मधून pant रंगाची स्पष्ट सूचना जात नव्हती. त्यामुळे model white सोडून दुसरा रंग निवडू शकतो.
- **#3 (dupatta plain):** `DUPATTA_ADD` (kurti_pant सोबत shared) मध्ये "same fabric as image 1" असे एकच वाक्य होते आणि ते शेवटी जोडले जात होते; fabric rules मध्ये target फक्त "kurta" असतो, त्यामुळे dupatta fabric target म्हणून स्पष्ट नव्हता.

केलेले बदल (फक्त kurta आणि blazer):

- `prompt_builder.py`: `person_pose` + `kurta`/`blazer` (fabric swatch वापरून) साठी नवीन छोटा dedicated prompt `_build_person_pose_spec_prompt`. त्यात pose सुरुवातीला, नंतर limbs/identity, outfit (`GARMENT_SPECS` मधूनच), fabric, border, closing. Garment details (sleeves, dupatta) जुन्याच anchors ने लागतात.
- `prompt_builder.py`: `GARMENT_SPECS[("kurta","plain")]` मध्ये pajama आता plain solid WHITE. `person_photo` edit path मध्ये kurta/plain साठी `prompts.py` मधील तो मोकळा phrase in-memory "plain solid WHITE" ने बदलला (`prompts.py` फाइल तशीच) आणि एक छोटी "TROUSER COLOUR" ओळ जोडली (`KURTA_WHITE_PANT_STYLES` मध्ये style बदलून इतर styles साठी वाढवता येते).
- `garment_details.py`: kurta साठी स्वतंत्र `KURTA_DUPATTA_ADD` (dupatta वर image 1 चे रंग/pattern स्पष्ट). `DUPATTA_ADD` (kurti_pant) बदललेला नाही.

`kurti_pant`, `shirt`, `pant`, `saree` चे prompts बदललेले नाहीत.

पुढील तपास: `check_pose_prompts.py` मधील Check 1 (जुन्या builder शी तुलना) आता kurta/plain साठी फरक दाखवेल; कारण pajama white झाला आहे. हा अपेक्षित फरक आहे.

### 5. Blazer: reference image प्रमाणे बदल (NEW, अजून test केलेले नाहीत)

Reference image (Casual / Business / Wedding blazer) शी prompts तपासले. फरक आणि बदल:

- **Length:** Blazer खूप खाली जात होता, कारण prompts मध्ये फक्त "hip length" असे मोकळे लिहिले होते. आता `BLAZER_LENGTH_DETAIL` (एकाच ठिकाणी): hem seat च्या तळाशी, लटकलेल्या हातांच्या मनगटाच्या पातळीवर, mid-thigh पर्यंत कधीही नाही. तिन्ही styles साठी लागू.
- **Pant (Business, Wedding):** Blazer fabric च्या main रंगाचा plain solid pant, pattern नाही. Casual बदललेला नाही.
- **Wedding:** आतला शर्ट mandarin band-collar (लहान बटणांची रांग), bow tie नाही. छातीच्या खिशात puff-flower आकाराचा pocket square. Jacket shawl lapel.
- **Edit route (`person_photo`):** `prompts.py` ला हात न लावता `BLAZER_EDIT_REPLACEMENTS` ने exact phrases in-memory बदलले; business/wedding साठी `TROUSERS` ओळ जोडली. Phrase न सापडल्यास log मध्ये warning.
- **Own-model / person_pose routes:** `GARMENT_SPECS` मधील blazer entries बदलल्या; `trouser_colour_from_fabric` flag ने pant ला फक्त रंग घेण्याची परवानगी.

Reference मधील पण अजून न बदललेले फरक: Casual मध्ये white T-shirt आणि jeans आहेत (आपल्या prompt मध्ये collared shirt आणि dark trousers); Business jacket ला दोन बटणे आहेत (आपल्या prompt मध्ये single front button).

## Saree issue (अजून बदललेले नाही)

Saree + person image + pose: long shared prompt, pallu instructions ची पुनरावृत्ती आणि blank-canvas reconstruction यामुळे pose कमकुवत. Saree code मध्ये कोणताही बदल केलेला नाही. पुढील वेळी बदल करायचा असल्यास फक्त `saree + person_pose` route साठी छोटा dedicated prompt बनवावा.