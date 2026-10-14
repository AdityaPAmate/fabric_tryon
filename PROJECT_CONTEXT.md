# Fabric Try-on: सद्य Project Context

हा दस्तऐवज सध्याच्या लागू कोडची स्थिती, image-flow आणि अलीकडील मर्यादित बदल नोंदवतो. तो पुढील बदलांसाठी संदर्भ आहे.

**स्थिती-नोंद (2026-10-14):** Saree साठी स्वतंत्र prompt route (`fabricapp/ai/saree/`) तयार करून दिला आहे. तो `prompt_builder.py` मध्ये जोडला की लागू होतो (खाली "Saree: स्वतंत्र route" पहा). जोडणी आणि जुन्या saree कोडची सफाई user ने केली आहे की नाही, हे अजून confirm नाही. confirm झाल्यावर या फाइलमधील "लागू स्थिती" सारणी update करा. कोणतीही output image किंवा API चाचणी अजून झालेली नाही.

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
| `kurta`, `blazer` | छोटा dedicated prompt (`_build_person_pose_spec_prompt`) |
| `saree` (fabric swatch) | **वेगळा package `fabricapp/ai/saree/` (`build_saree_prompt`)** — NEW |
| `pant`, garment_image | जुना shared long prompt (अजून बदललेला नाही) |

## Saree: स्वतंत्र route (NEW, 2026-10-14)

### का केला

Saree चे तीनही मार्ग (person_pose, generated_person/face_photo, pose_reference) kurta/blazer/kurti_pant च्या दुरुस्त्यांपासून वंचित होते. कोड वाचून सापडलेली कारणे (output पाहिलेले नाहीत):

- `saree + person_image + pose` जुन्या ~1000 शब्दांच्या shared prompt ला जात होता; pose त्यात हरवत होता.
- Resolver मध्ये 8 poses ना PALLU ओळ नव्हती, पण `SAREE_BORDER_RULES` "the loose end described in the PALLU line" म्हणत होता. त्यामुळे model स्वतःचा दुसरा pallu बनवत होता.
- `camera_view=front/side` आणि pose एकमेकांना छेद देत होते (उदा. back view + "facing the camera").
- `body_type` फक्त एका शब्दात जात होता; `BODY BUILD` ओळ नव्हती.
- Background मध्यभागी होता; chair/ledge हरवत होता.
- `camera_data.py` चा side `pose_default` "pant legs" म्हणतो, जे saree ला चुकीचे आहे.

### नवीन फाइल्स (प्रत्येकाचे एकच काम)

```
fabricapp/ai/saree/
    __init__.py     # फक्त build_saree_prompt export करतो
    poses.py        # POSE + PALLU data. pose/pallu control साठी फक्त ही फाइल बदला
    texts.py        # सर्व prompt शब्द (एक गरज = एक variable)
    builder.py      # resolve + compose logic (शब्द नाहीत)
check_saree_prompts.py   # project root मध्ये; offline check + preview
```

### Control कसा करायचा

- एका pose चा pallu बदलायचा: `poses.py` मध्ये `SAREE_POSES[pose]["pallu"]` ची value बदला (style नाव).
- एका pallu style चा मजकूर बदलायचा: `poses.py` मधील `PALLU_STYLES` बदला.
- Pallu styles: `nivi_shoulder` (image च्या उजव्या खांद्यावर), `seedha_front` (image च्या डाव्या खांद्यावर, पुढे), `veil_head`, `lap_drape`, `back_fall`.
- सर्व दिशा image च्या बाजूने लिहिल्या आहेत ("the arm on the left of the image"), model च्या डाव्या/उजव्या बाजूने नाही.
- कोणत्याही pose चा final prompt पाहायचा: `python check_saree_prompts.py --show POSE [SCENARIO] [CAMERA_VIEW] [BACKGROUND]`.
- पूर्ण तपासणी: `python check_saree_prompts.py` (pose × scenario × camera × background; sandbox मध्ये stub फाइल्ससह 800 combinations ALL OK आले; खऱ्या प्रोजेक्टमध्ये user ने चालवायचे आहे).

### Route चे नियम

| scenario | कोण handle करतो |
|---|---|
| `generated_person`, `face_photo`, `person_pose` | नवीन saree builder |
| `pose_reference` (saree + pallu_on_head फोटो edit) | नवीन saree builder (जुना मजकूर `REF_*` तसाच, version `saree-ref-v3`) |
| `person_photo` (pose/camera नसलेला साधा edit) | जुना मार्ग (`prompts.py` मधला tested saree prompt), unchanged |
| `garment_image` + saree | जुना मार्ग, unchanged |

- Prompt क्रम: TASK, IMAGES, **POSE, PALLU, LIMBS**, SUBJECT, BODY BUILD, GARMENT, FABRIC, BORDER, CAMERA, BACKGROUND, LIGHTING, REALISM, STYLE NOTE, FINAL RULE (modesty, नेहमी शेवटी).
- PALLU ओळ आता प्रत्येक pose ला नेहमी असते (मूळ गफलत #1 दुरुस्त).
- Pose दिल्यावर `camera_view` `front`/`side` दुर्लक्षित होतो (pose दिशा ठरवतो); `close_up` लागू राहतो आणि garment/modesty/pallu चे "ankles/knee" शब्द काढले जातात.
- Chair/ledge लागणाऱ्या poses (`cross_leg_chair_recline`, `rail_wide_arm_side_look`) साठी background बदलला तरी chair/ledge राहतो (`prop`). Seated pose साठी "one person" नियम.
- Lighting: person photo चा background राखला असेल तर photo च्या lighting शी जुळवतो; नवीन background किंवा studio असेल तर neutral white.
- `gender=men/boy` saree साठी `None` परत करतो (engine 502 देईल). Serializer मध्ये स्पष्ट 400 देणे हा सुचवलेला पुढचा बदल आहे (अजून केलेला नाही).
- `pose_reference` route वर `gender`/`body_type` लागू होत नाहीत (व्यक्ती फोटोतली आहे); log मध्ये warning येते. `pallu_on_head` साठी prompt-only मार्ग हवा असेल तर `pose_reference.py` मधून `("saree","pallu_on_head")` ही जोडी काढा. नवीन route मध्ये `veil_head` data तयार आहे, कोड बदल लागत नाही.

### `prompt_builder.py` मध्ये जोडणी (लागू करायचा बाकी / confirm नाही)

1. Import: `from .saree import build_saree_prompt`
2. `build_prompt()` च्या सुरुवातीला, `if scenario == SCENARIO_POSE_REFERENCE:` च्या आधी: `garment_type == "saree" and not use_garment_image` असल्यास `build_saree_prompt(...)` बोलवा; `None` आला नाही तर तो परत करा.

### जुन्या saree कोडची सफाई (optional, जोडणी तपासल्यावरच)

- `fabricapp/ai/prompt_parts.py` पूर्ण फाइल (आधी `grep -rn prompt_parts` ने इतर कुणी import करत नाही हे तपासा).
- `prompt_builder.py`: `from . import prompt_parts as P`, `SAREE_RESOLVER_SCENARIOS`, `_uses_saree_resolver`, `_resolve_saree_instructions`, `SAREE_PROMPT_ORDER`, `_compose_saree_prompt`, `_build_saree_resolved`, `_resolve_pose_reference_instructions`, `POSE_REFERENCE_PROMPT_ORDER`, `_compose_pose_reference_prompt`, `_build_pose_reference_prompt`, `build_prompt` मधील दोन संबंधित branches, `GARMENT_SPECS` मधील saree entry, `SAREE_BORDER_RULES`, `CLOSING_SAREE` चा वापर, `get_saree_pose_parts` import. `SCENARIO_POSE_REFERENCE` constant ठेवा (engine वापरतो).
- `pose_data.py`: `POSE_OVERRIDES` मधील `("saree", ...)` entries, `SAREE_DEFAULT_PALLU`, `SAREE_POSE_PARTS` + त्याचा validation loop, `get_saree_pose_parts`.
- सफाईनंतर `check_pose_prompts.py` आणि `verify_kurti_fixes.py` चालवा. ते काढलेली नावे import करत असतील तर तेच सांगतील (त्या फाइल्स मी पाहिलेल्या नाहीत).
- `garment_details.py` मी पाहिलेली नाही. नवीन saree route `garment_details` वापरत नाही; saree साठी details keys असतील तर ते आता लागू होणार नाहीत.

### मर्यादा

- Person_pose saree prompt सुमारे 850 शब्दांचा आहे (जुना ~1000). Pose आधी आहे, पण kurta च्या ~380 शब्दांइतका छोटा नाही; FABRIC + BORDER मिळून सुमारे 230 शब्द. तरी pose हरवला तर FABRIC/BORDER एकत्र करून लहान करणे हा पुढचा पर्याय.
- Pose reference फोटो `fabricapp/ai/poses/saree/` मध्ये आहेत: `back_pallu_on_shoulder.jpg`, `back_showing_pallu.jpg`, `pallu_on_head.jpg`, `pallu_shawl_wrap.jpg`, `seated_look_down.png`. फक्त `pallu_on_head` registered आहे. बाकीच्यांची नावे `POSE_OPTIONS` मध्ये नाहीत आणि extension `.png` असलेली `pose_reference.py` च्या `.jpg` नियमाशी जुळणार नाहीत. `three_quarter_hand_adjust.png` `poses/` मध्येच आहे, `poses/saree/` मध्ये नाही. हे सध्या वापरले जात नाहीत.

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

### 4. Kurta आणि Blazer — test reports वरून

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
- **#2 (pant white):** `GARMENT_SPECS[("kurta","plain")]` मध्ये pajama चा रंग "white, off-white, or a solid shade from the kurta's palette" असा मोकळा होता. `prompts.py` मधील kurta/plain edit prompt मध्येही तोच मोकळा phrase आहे, आणि `prompt_builder` मधून pant रंगाची स्पष्ट सूचना जात नव्हती.
- **#3 (dupatta plain):** `DUPATTA_ADD` (kurti_pant सोबत shared) मध्ये "same fabric as image 1" असे एकच वाक्य होते आणि ते शेवटी जोडले जात होते; fabric rules मध्ये target फक्त "kurta" असतो, त्यामुळे dupatta fabric target म्हणून स्पष्ट नव्हता.

केलेले बदल (फक्त kurta आणि blazer):

- `prompt_builder.py`: `person_pose` + `kurta`/`blazer` (fabric swatch वापरून) साठी नवीन छोटा dedicated prompt `_build_person_pose_spec_prompt`. त्यात pose सुरुवातीला, नंतर limbs/identity, outfit (`GARMENT_SPECS` मधूनच), fabric, border, closing. Garment details (sleeves, dupatta) जुन्याच anchors ने लागतात.
- `prompt_builder.py`: `GARMENT_SPECS[("kurta","plain")]` मध्ये pajama आता plain solid WHITE. `person_photo` edit path मध्ये kurta/plain साठी `prompts.py` मधील तो मोकळा phrase in-memory "plain solid WHITE" ने बदलला (`prompts.py` फाइल तशीच) आणि एक छोटी "TROUSER COLOUR" ओळ जोडली (`KURTA_WHITE_PANT_STYLES` मध्ये style बदलून इतर styles साठी वाढवता येते).
- `garment_details.py`: kurta साठी स्वतंत्र `KURTA_DUPATTA_ADD` (dupatta वर image 1 चे रंग/pattern स्पष्ट). `DUPATTA_ADD` (kurti_pant) बदललेला नाही.

`kurti_pant`, `shirt`, `pant` चे prompts या बदलात बदललेले नाहीत.

पुढील तपास: `check_pose_prompts.py` मधील Check 1 (जुन्या builder शी तुलना) आता kurta/plain साठी फरक दाखवेल; कारण pajama white झाला आहे. हा अपेक्षित फरक आहे.

### 5. Blazer: reference image प्रमाणे बदल (अजून test केलेले नाहीत)

Reference image (Casual / Business / Wedding blazer) शी prompts तपासले. फरक आणि बदल:

- **Length:** Blazer खूप खाली जात होता, कारण prompts मध्ये फक्त "hip length" असे मोकळे लिहिले होते. आता `BLAZER_LENGTH_DETAIL` (एकाच ठिकाणी): hem seat च्या तळाशी, लटकलेल्या हातांच्या मनगटाच्या पातळीवर, mid-thigh पर्यंत कधीही नाही. तिन्ही styles साठी लागू.
- **Pant (Business, Wedding):** Blazer fabric च्या main रंगाचा plain solid pant, pattern नाही. Casual बदललेला नाही.
- **Wedding:** आतला शर्ट mandarin band-collar (लहान बटणांची रांग), bow tie नाही. छातीच्या खिशात puff-flower आकाराचा pocket square. Jacket shawl lapel.
- **Edit route (`person_photo`):** `prompts.py` ला हात न लावता `BLAZER_EDIT_REPLACEMENTS` ने exact phrases in-memory बदलले; business/wedding साठी `TROUSERS` ओळ जोडली. Phrase न सापडल्यास log मध्ये warning.
- **Own-model / person_pose routes:** `GARMENT_SPECS` मधील blazer entries बदलल्या; `trouser_colour_from_fabric` flag ने pant ला फक्त रंग घेण्याची परवानगी.

Reference मधील पण अजून न बदललेले फरक: Casual मध्ये white T-shirt आणि jeans आहेत (आपल्या prompt मध्ये collared shirt आणि dark trousers); Business jacket ला दोन बटणे आहेत (आपल्या prompt मध्ये single front button).

### 6. Kurti-pant: 2026-10-09 Test Reports बदल

Kurti-pant test reports मधील तक्रारी आणि केलेले बदल:

1. **Side view मधील पाय (Report 1):** `camera_data.py` मध्ये side framing च्या `pose_default` मध्ये पाय सरळ आणि नैसर्गिकरित्या वेगळे असणे स्पष्ट केले, ज्यामुळे profile view मध्ये दोन्ही पाय आणि पावले स्पष्ट राहतात.
2. **Side view + pocket_walk धावल्यासारखे दिसणे (Report 2 & 5):** `prompt_builder.py` मधील `_own_model_pose_text` मध्ये `pocket_walk` आणि `camera_view="side"` एकत्र आल्यास चालण्याचा वेग मंद व पावले जवळ (not a wide stride, not running) आणि दोनच हात राहतील असा side walking prompt दिला.
3. **वाकलेला पाय (Report 3):** `pose_data.py` मध्ये `("kurti_pant", None, "rail_wide_arm_side_look")` साठी स्वतंत्र override जोडला, ज्यामध्ये पाय नैसर्गिक रित्या थोडे मागे आणि गुडघ्यामध्ये जास्त वाक नसणे स्पष्ट केले.
4. **मुलीचे वय मोठे दिसणे आणि चेहरा बदलणे (Report 4 & 6):** `_build_person_pose_kurti_prompt` मध्ये hardcoded "woman" काढून "person" केले आणि चेहऱ्याची रचना जपणे तसेच मूळ फोटो जर लहान मुलीचा/मुलाचा असेल तर प्रौढ न करता तिचे मूळ वय राखणे स्पष्ट केले.
5. **Gender girl साठी body_type "plus" लागू न होणे (Report 7 & 8):** `_is_child` मुळे मुलांसाठी `body_type` वगळला जात होता. आता `_person_description`, `_build_own_model_prompt` आणि `_build_own_model_spec_prompt` मध्ये लहान मुलांसाठी `body_type="plus"` दिल्यास स्पष्ट chubby/plus-size build सूचना जोडली जाते.
6. **हात 3 येणे (Report 9 & 10):** `pose_data.py` मधील `sleeve_adjust_stand` आणि `three_quarter_hand_adjust` मध्ये "exactly two arms and two hands in total, never a third hand" स्पष्ट केले आणि `_build_own_model_prompt` मध्ये kurti_pant साठी `OWN_MODEL_LIMBS_LINE` जोडली.

### 7. Kurti-pant: 2026-10-13 Test Reports बदल (Reports #11–#17)

| # | Report | तक्रार | कारण | बदल |
|---|---|---|---|---|
| 11 | cross_leg + riverside_ghat | fabric applied नाही kurti ला | `_append_overrides` ने 120-word background block शेवटी जोडला; तो fabric instructions पेक्षा नंतर येतो | `_build_person_pose_kurti_prompt` मध्येच `_short_background` embed केला; `_append_overrides(background=None)` |
| 12 | sleeve_adjust_stand | तीन हात | override मध्ये per-hand role अस्पष्ट | "no other hand is visible anywhere, no extra arm" असे explicit पर टाकले |
| 13 | three_quarter_hand_adjust | तीन हात | override मध्ये hanging hand साठी explicit नकार नव्हता | "no other hand hangs at the side or appears anywhere, no extra arm" जोडले |
| 14 | pocket_walk + white_marble_terrace | pose lost | `kurti_pant` generated_person/face_photo साठी 950-word long prompt वापरला जात होता; background शेवटी जोडल्याने model ने त्याकडे दुर्लक्ष केले | `OWN_MODEL_SPEC_GARMENTS = ("kurta", "blazer", "kurti_pant")` — spec routing मध्ये kurti_pant समाविष्ट |
| 15 | pocket_walk + riverside_ghat | pose lost | वरीलप्रमाणे (generated_person) | वरीलप्रमाणे + `OWN_MODEL_SPEC_SCENARIOS = (SCENARIO_FACE_PHOTO, SCENARIO_GENERATED_PERSON)` |
| 16 | cross_leg + white_marble_terrace | chair missing | `_short_background` ने फक्त scene बदलला, chair retention सांगितले नाही | `_short_background(description, pose=None)` — `cross_leg_chair_recline` साठी "armchair must be present" note जोडला |
| 17 | rail_wide_arm_side_look | तीन हात | override मध्ये "never a third hand" नव्हते | "never a third hand: exactly two hands... one on each side, no extra or hanging hand anywhere" जोडले |

**face_choice + background + pose (only fabric as output):**

- कारण: `kurti_pant` `OWN_MODEL_SPEC_GARMENTS` मध्ये नव्हता; त्यामुळे face_photo/generated_person साठी ~950-word `_build_own_model_prompt` वापरला जात होता. Text encoder attention decays; model ने background + face reference नंतर fabric swatch (image 1) alone render केले.
- बदल: `OWN_MODEL_SPEC_GARMENTS = ("kurta", "blazer", "kurti_pant")` आणि `OWN_MODEL_SPEC_SCENARIOS = (SCENARIO_FACE_PHOTO, SCENARIO_GENERATED_PERSON)` — kurti_pant आता ~380-word `_build_own_model_spec_prompt` वापरतो (pose पहिला, शेवटी fabric).

**केलेले code बदल (2026-10-13):**

- `fabricapp/ai/prompt_builder.py`:
  - `OWN_MODEL_SPEC_SCENARIOS` → `(SCENARIO_FACE_PHOTO, SCENARIO_GENERATED_PERSON)`
  - `OWN_MODEL_SPEC_GARMENTS = ("kurta", "blazer", "kurti_pant")` नवीन constant
  - routing gate: `PERSON_POSE_SPEC_GARMENTS` → `OWN_MODEL_SPEC_GARMENTS`
  - `_short_background(description, pose=None)` — cross_leg_chair_recline साठी chair note
  - `_build_own_model_spec_prompt` generated_person branch: child + plus → explicit BODY BUILD line
  - `_build_person_pose_spec_prompt`: `_short_background(..., pose=pose)` call
  - `_build_own_model_spec_prompt`: `_short_background(description, pose=pose)` call
  - `_build_person_pose_kurti_prompt`: background embed + FABRIC PRIORITY note for seated
  - `build_prompt` kurti SCENARIO_PERSON_POSE: `_append_overrides(prompt, None, ...)` (background=None)
  - `_spec_person_pose_text`: `pallu_on_head` conversion only for `KURTA_BLAZER`, not kurti_pant
- `fabricapp/ai/pose_data.py`:
  - `sleeve_adjust_stand` kurti_pant: "no other hand is visible anywhere, no extra arm"
  - `three_quarter_hand_adjust` kurti_pant: "no other hand hangs at the side, no extra arm"
  - `rail_wide_arm_side_look` kurti_pant: "never a third hand: exactly two hands... no extra or hanging hand"
- `check_pose_prompts.py`:
  - `PALLU_HEAD_SKIP_GARMENTS = {"kurta", "blazer", "shirt"}` — Check 2 आणि Check 3 मध्ये pallu_on_head false positives skip

**Verification (त्या वेळी):** `check_pose_prompts.py` → ALL OK (Check 2: 0, Check 3: 0, Check 4: 0); `verify_kurti_fixes.py` → 13/13 PASSED

## Project folder (संदर्भ)

```
fabric_tryon/
    fabricapp/
        ai/
            faces/ (anaya, poonam, raghav, vihaan .png)
            poses/ (_guides/, saree/*.jpg|png, three_quarter_hand_adjust.png)
            saree/ (NEW: __init__, poses, texts, builder)
            camera_data.py, cloudflare_engine.py, debug_utils.py,
            garment_details.py, image_utils.py, pose_data.py,
            pose_reference.py, prompt_builder.py, prompt_parts.py,
            prompts.py
        services/cloudinary_service.py
        check_garment_details.py, serializers.py, views.py, urls.py ...
    tryon/ (settings, urls, wsgi, asgi)
    check_pose_prompts.py, check_saree_prompts.py (NEW), verify_kurti_fixes.py
    PROJECT_CONTEXT.md, render.yaml, Dockerfile, requirements.txt
```

## पुढील पायऱ्या

1. Saree package ची जोडणी (`prompt_builder.py` मध्ये import + early branch) आणि `python check_saree_prompts.py` चालवणे.
2. खरे API test: saree + person_image + pose, आणि saree + generated_person + pose (body_type, face_choice, background सह). Log मधली `FINAL PROMPT:` ओळ आणि output सोबत तपासा.
3. निकाल चांगला आला की जुन्या saree कोडची सफाई, आणि `gender=men/boy` साठी serializer मध्ये स्पष्ट 400.
4. Pallu अपेक्षेप्रमाणे नसेल तर फक्त `fabricapp/ai/saree/poses.py` मध्ये बदल करा.