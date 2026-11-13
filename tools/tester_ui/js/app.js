const form = document.querySelector("#tryon-form");
const personImage = document.querySelector("#person-image");
const fabricImage = document.querySelector("#fabric-image");
const garmentImage = document.querySelector("#garment-image");
const garmentSource = document.querySelector("#garment-source");
const fabricImageField = document.querySelector("#fabric-image-field");
const garmentImageField = document.querySelector("#garment-image-field");
const garmentTypeField = document.querySelector("#garment-type-field");
const generatedPersonOptions = document.querySelector("#generated-person-options");
const generatedPersonHelp = document.querySelector("#generated-person-help");
const gender = document.querySelector("#gender");
const genderRequiredMarker = document.querySelector("#gender-required-marker");
const bodyType = document.querySelector("#body-type");
const faceChoice = document.querySelector("#face-choice");
const faceImage = document.querySelector(
  '#face-image, #face-image-upload, input[name="face_image"]'
);
const clearFaceImage = document.querySelector(
  "#clear-face-image, #clear-face-image-button"
);
const garmentType = document.querySelector("#garment-type");
const garmentStyleField = document.querySelector("#garment-style-field");
const garmentStyle = document.querySelector("#garment-style");
const poseSelect = document.querySelector("#pose");
const garmentDetailsFieldset = document.querySelector("#garment-details-fieldset");
const garmentDetailsHelp = document.querySelector("#garment-details-help");
const garmentDetailsControls = document.querySelector("#garment-details-controls");
const generateButton = document.querySelector("#generate-button");
const statusMessage = document.querySelector("#status-message");
const requestTimer = createRequestTimer(document.querySelector("#request-timer"));
const resultImage = document.querySelector("#result-image");
const imagePlaceholder = document.querySelector("#image-placeholder");
const resultActions = document.querySelector("#result-actions");
const openImage = document.querySelector("#open-image");
const downloadImage = document.querySelector("#download-image");
const errorBox = document.querySelector("#error-box");
const comparisonSection = document.querySelector("#comparison-section");
const comparisonGrid = document.querySelector("#comparison-grid");
const personCard = document.querySelector("#person-card");
const personPreview = document.querySelector("#person-preview");
const fabricPreview = document.querySelector("#fabric-preview");
const outputPreview = document.querySelector("#output-preview");
const fabricCardTitle = document.querySelector("#fabric-card-title");
const outputCardTitle = document.querySelector("#output-card-title");
const personFilename = document.querySelector("#person-filename");
const fabricFilename = document.querySelector("#fabric-filename");
const outputFormat = document.querySelector("#output-format");
const localSaveMessage = document.querySelector("#local-save-message");
const themeToggle = document.querySelector("#theme-toggle");
const feedbackSection = document.querySelector("#feedback-section");
const feedbackForm = document.querySelector("#feedback-form");
const issueNote = document.querySelector("#issue-note");
const saveReportButton = document.querySelector("#save-report-button");
const reportSaveMessage = document.querySelector("#report-save-message");
const generationMode = document.querySelector('#generation-mode');
const readyCatalog = document.querySelector('#ready-catalog');
const fabricType = document.querySelector('#fabric-type');
const cancelButton = document.querySelector('#cancel-generation');
const catalogGrid = document.querySelector('#catalog-grid');
const catalogResults = document.querySelector('#catalog-results');
const catalogSummary = document.querySelector('#catalog-summary');
let requestController = null;

function setGenerationMode() {
  const fabric = garmentSource.value === 'fabric';
  const catalog = generationMode.value === 'catalog';
  const extractFabric = !fabric && catalog && readyCatalog.value.endsWith(':swatch');
  document.querySelector('#ready-catalog-field').classList.toggle('hidden', fabric || !catalog);
  readyCatalog.disabled = fabric || !catalog;
  readyCatalog.required = !readyCatalog.disabled;
  document.querySelectorAll('[data-saree-detail-crop]').forEach(field => {
    const enabled = fabric && catalog && garmentType.value === 'saree';
    field.classList.toggle('hidden', !enabled);
    field.querySelector('input').disabled = !enabled;
  });
  document.querySelector('#fabric-type-field').classList.toggle('hidden', !fabric);
  document.querySelector('#fabric-crop-field').classList.toggle('hidden', !fabric && !extractFabric);
  fabricType.disabled = !fabric;
  document.querySelector('#fabric-crop-box').disabled = !fabric && !extractFabric;
  poseSelect.disabled = catalog;
  document.querySelector('#camera-view').disabled = catalog;
  generateButton.textContent = catalog ? 'Generate Catalog' : 'Generate image';
  document.querySelector('#mode-help').textContent = catalog
    ? (fabric
      ? 'Generate the garment’s catalog views and a finished collage. Plain Kurta, Sherwani, Saree and Kurti + Pant use a 3:4 collage.'
      : 'Choose a Kurta style for reference-based collar, cuff and side slit views.')
    : 'Generate one image with your selected pose and camera view.';
  setReferencePoseAvailability();
}

function displayOutput(output) {
  resultImage.src = output.url;
  outputPreview.src = output.url;
  outputFormat.textContent = (output.format || 'image').toUpperCase();
  openImage.href = output.url;
  downloadImage.href = output.url;
  downloadImage.download = `fabric-tryon-${output.view || 'image'}.${output.format || 'jpg'}`;
  resultImage.classList.remove('hidden');
  resultActions.classList.remove('hidden');
  comparisonSection.classList.remove('hidden');
  imagePlaceholder.classList.add('hidden');
}

const faceOptions = {
  women: ["anaya", "poonam"],
  men: ["raghav", "vihaan"],
  girl: [],
  boy: []
};

const garmentStyles = {
  kurta: ["plain", "sherwani", "pathani", "jodhpuri"],
  blazer: ["business", "wedding", "casual"]
};

let sourceObjectUrl = null;
let personObjectUrl = null;
let latestGeneration = null;

function setFaces() {
  const previous = faceChoice.value;

  faceChoice.replaceChildren(new Option("Model chooses", ""));

  for (const face of faceOptions[gender.value] || []) {
    faceChoice.add(
      new Option(face[0].toUpperCase() + face.slice(1), face)
    );
  }

  faceChoice.value = Array.from(faceChoice.options).some(
    (option) => option.value === previous
  ) ? previous : "";
}

function addDetailOption({
  label,
  value,
  type = "checkbox",
  group = ""
}) {
  const labelElement = document.createElement("label");
  labelElement.className = "detail-option";

  const input = document.createElement("input");
  input.type = type;
  input.name = type === "radio" ? group : "garment_details";
  input.value = value;

  labelElement.append(input, document.createTextNode(label));
  garmentDetailsControls.append(labelElement);
}

function setGarmentDetails() {
  garmentDetailsControls.replaceChildren();
  garmentDetailsFieldset.classList.add('hidden');
  if (garmentSource.value !== 'fabric') return;
  const slots = new Map();
  for (const rule of TRYON_API_OPTIONS[garmentType.value]?.details || []) {
    if (rule.styles && !rule.styles.includes(garmentStyle.value)) continue;
    const keys = slots.get(rule.slot) || new Set();
    rule.options.forEach(key => keys.add(key));
    slots.set(rule.slot, keys);
  }
  for (const [slot, keys] of slots) {
    if (keys.size > 1) addDetailOption({label: `${slot.replaceAll('_', ' ')}: default`,
      value: '', type: 'radio', group: `detail-${slot}`});
    for (const key of keys) addDetailOption({label: key.replaceAll('_', ' '), value: key,
      type: keys.size > 1 ? 'radio' : 'checkbox', group: `detail-${slot}`});
  }
  garmentDetailsHelp.textContent = 'Optional garment details supported by the current API. Leave unselected to use defaults.';
  garmentDetailsFieldset.classList.toggle('hidden', !garmentDetailsControls.childElementCount);
}

function setReferencePoseAvailability() {
  const previous = poseSelect.value;
  const garment = garmentSource.value === 'fabric' ? garmentType.value : null;
  const poses = garment ? TRYON_API_OPTIONS[garment]?.poses || {} :
    Object.assign({}, ...Object.values(TRYON_API_OPTIONS).map(item => item.poses));
  const face = !personImage.files?.length && (faceChoice.value || faceImage?.files?.length);
  const close = document.querySelector('#camera-view').value === 'close_up';
  poseSelect.replaceChildren(new Option('Keep default pose', ''));
  for (const [key, metadata] of Object.entries(poses)) {
    const option = new Option(key.replaceAll('_', ' '), key);
    option.disabled = Boolean((face && metadata.hides_face) || (close && metadata.requires_full_body) ||
      (metadata.allows_identity_reference === false && (face || personImage.files?.length)));
    if (metadata.allows_identity_reference === false) option.title = 'This pose uses its reference model. Clear face and person uploads to select it.';
    poseSelect.add(option);
  }
  const selected = Array.from(poseSelect.options).find(option => option.value === previous && !option.disabled);
  poseSelect.value = selected ? previous : '';
}

function setGarmentStyles() {
  const styles = garmentStyles[garmentType.value] || [];
  const needsStyle =
    garmentSource.value === "fabric" && styles.length > 0;

  garmentStyleField.classList.toggle("hidden", !needsStyle);
  garmentStyle.required = needsStyle;
  garmentStyle.replaceChildren();

  for (const style of styles) {
    garmentStyle.add(
      new Option(style[0].toUpperCase() + style.slice(1), style)
    );
  }

  setGarmentDetails();
  setReferencePoseAvailability();
}

function setGarmentSourceMode() {
  const usesFabric = garmentSource.value === "fabric";

  fabricImageField.classList.toggle("hidden", !usesFabric);
  garmentImageField.classList.toggle("hidden", usesFabric);
  garmentTypeField.classList.toggle("hidden", !usesFabric);

  fabricImage.required = usesFabric;
  fabricImage.disabled = !usesFabric;

  garmentImage.required = !usesFabric;
  garmentImage.disabled = usesFabric;

  setGarmentStyles();
  setGenerationMode();
}

function setPersonMode() {
  const hasPersonImage = Boolean(personImage.files?.length);
  const hasFaceImage = Boolean(faceImage?.files?.length);

  // Keep model settings visible, but lock them when a person image is supplied.
  // Without a person image, the API can generate a model and use either:
  // 1) a selected face_choice, or 2) an uploaded face_image, or 3) its default face.
  [gender, bodyType, faceChoice, faceImage].forEach((control) => {
    if (control) control.disabled = hasPersonImage;
  });

  if (clearFaceImage) {
    clearFaceImage.disabled = hasPersonImage;
    clearFaceImage.classList.toggle("hidden", !hasFaceImage);
  }

  generatedPersonOptions.classList.toggle("is-disabled", hasPersonImage);
  generatedPersonHelp.textContent = hasPersonImage
    ? "Person image selected: model settings are visible but disabled because the supplied person image is used."
    : "No person image selected: a model will be generated. Choose a Face choice, upload a Face image, or leave both empty to use the model's default face.";

  setReferencePoseAvailability();
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;

  themeToggle.textContent =
    theme === "dark" ? "Light mode" : "Dark mode";

  themeToggle.setAttribute(
    "aria-label",
    `Switch to ${theme === "dark" ? "light" : "dark"} mode`
  );

  localStorage.setItem("fabric-tryon-theme", theme);
}

function currentSourceFile() {
  return garmentSource.value === "fabric"
    ? fabricImage.files[0]
    : garmentImage.files[0];
}

function currentSourceLabel() {
  return garmentSource.value === "fabric"
    ? "Fabric image"
    : "Garment image";
}

function previewInputImages() {
  if (personObjectUrl) URL.revokeObjectURL(personObjectUrl);
  if (sourceObjectUrl) URL.revokeObjectURL(sourceObjectUrl);

  personObjectUrl = personImage.files[0]
    ? URL.createObjectURL(personImage.files[0])
    : null;

  sourceObjectUrl = currentSourceFile()
    ? URL.createObjectURL(currentSourceFile())
    : null;

  personPreview.src = personObjectUrl || "";
  fabricPreview.src = sourceObjectUrl || "";

  personFilename.textContent = personImage.files[0]?.name || "";
  fabricFilename.textContent = currentSourceFile()?.name || "";

  personCard.classList.toggle("hidden", !personObjectUrl);
  comparisonGrid.classList.toggle("two-cards", !personObjectUrl);

  fabricCardTitle.textContent =
    `${personObjectUrl ? "2" : "1"}. ${currentSourceLabel()}`;

  outputCardTitle.textContent =
    `${personObjectUrl ? "3" : "2"}. Generated output`;
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function clearError() {
  errorBox.textContent = "";
  errorBox.classList.add("hidden");
}

function selectedGarmentDetails() {
  return Array.from(
    document.querySelectorAll("#garment-details-controls input:checked")
  ).map((input) => input.value).filter(Boolean);
}

function readFileAsDataUrl(file) {
  if (!file) return Promise.resolve(null);

  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = () => resolve({
      name: file.name,
      type: file.type,
      data_url: reader.result
    });

    reader.onerror = () => reject(
      new Error(`Could not read ${file.name}.`)
    );

    reader.readAsDataURL(file);
  });
}

async function saveOutputLocally(url, format) {
  localSaveMessage.textContent = "Saving output locally...";

  try {
    const response = await fetch("/save-output", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, format })
    });

    const saved = await response.json();

    if (!response.ok) {
      throw new Error(saved.error || "Local save failed.");
    }

    localSaveMessage.textContent =
      `Saved locally: ${saved.filename}`;

    return saved;

  } catch (error) {
    localSaveMessage.textContent =
      `Image is visible above, but local save failed: ${error.message}`;

    return null;
  }
}

gender.addEventListener("change", setFaces);
garmentType.addEventListener("change", () => { setGarmentStyles(); setGenerationMode(); });
garmentStyle.addEventListener("change", setGarmentDetails);
garmentSource.addEventListener("change", setGarmentSourceMode);
personImage.addEventListener("change", setPersonMode);

// Face choice and uploaded face image are alternatives.
// Choosing one clears the other so the intended face source is unambiguous.
faceChoice.addEventListener("change", () => {
  if (faceChoice.value && faceImage) faceImage.value = "";
  setPersonMode();
});

if (faceImage) {
  faceImage.addEventListener("change", () => {
    if (faceImage.files?.length) faceChoice.value = "";
    setPersonMode();
  });
}

clearFaceImage?.addEventListener("click", () => {
  if (faceImage) faceImage.value = "";
  setPersonMode();
});

themeToggle.addEventListener("click", () => {
  setTheme(
    document.documentElement.dataset.theme === "dark"
      ? "light"
      : "dark"
  );
});

console.log("[DEBUG] Fabric Try-on JavaScript loaded");

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (generateButton.disabled) return;

  const isCatalog = generationMode.value === 'catalog';
  const usesFabric = garmentSource.value === 'fabric';
  if (isCatalog && !usesFabric && !readyCatalog.value) {
    readyCatalog.reportValidity();
    return;
  }

  const sourceFile = currentSourceFile();

  if (!sourceFile) {
    showError(`Choose a ${currentSourceLabel().toLowerCase()} first.`);
    return;
  }

  clearError();

  comparisonSection.classList.add("hidden");
  feedbackSection.classList.add("hidden");

  latestGeneration = null;
  issueNote.value = "";
  reportSaveMessage.textContent = "";
  localSaveMessage.textContent = "";

  resultImage.classList.add("hidden");
  resultActions.classList.add("hidden");

  imagePlaceholder.classList.remove("hidden");
  imagePlaceholder.textContent =
    "Sending request and generating image. This can take a few minutes...";

  statusMessage.textContent = "Generation in progress...";
  generateButton.disabled = true;
  generateButton.textContent = "Generating...";

  let apiUrl;
  try {
    apiUrl = CatalogClient.endpoint(document.querySelector('#api-url').value.trim(), isCatalog);
  } catch (error) {
    showError(error.message);
    statusMessage.textContent = 'Request failed.';
    generateButton.disabled = false;
    setGenerationMode();
    return;
  }
  catalogGrid.replaceChildren();
  catalogSummary.textContent = '';
  catalogResults.classList.toggle('hidden', !isCatalog);
  const payload = new FormData();

  const personFile = personImage.files[0];
  const selectedFaceFile = faceImage?.files?.[0] || null;
  const readySelection = isCatalog && !usesFabric ? readyCatalog.value : null;
  const [catalogGarment, catalogStyle, catalogSource] = readySelection?.includes(':') ? readySelection.split(':') : [];
  const extractFabric = catalogSource === 'swatch';

  if (usesFabric) {
    payload.append("fabric_image", sourceFile);
    payload.append("garment_type", garmentType.value);
    payload.append("fabric_type", fabricType.value);

    if (garmentStyle.value) {
      payload.append("garment_style", garmentStyle.value);
    }

    selectedGarmentDetails().forEach((detail) => {
      payload.append("garment_details", detail);
    });

  } else {
    payload.append("garment_image", sourceFile);
    if (extractFabric) payload.append('garment_as_swatch', 'true');
    if (catalogGarment) {
      payload.append('garment_type', catalogGarment);
      payload.append('garment_style', catalogStyle);
    }
  }

  // Person image is sent independently; it does not control model settings.
  if (personFile) {
    payload.append("person_image", personFile, personFile.name);
  }

  // Generated-model settings are relevant only when no person image is supplied.
  // If both face sources are empty, omit both fields so the backend uses its default face.
  if (!personFile) {
    payload.append("gender", gender.value);

    if (bodyType.value) {
      payload.append("body_type", bodyType.value);
    }

    if (selectedFaceFile) {
      // A real File object is appended as multipart/form-data.
      payload.append("face_image", selectedFaceFile, selectedFaceFile.name);
    } else if (faceChoice.value) {
      payload.append("face_choice", faceChoice.value);
    }
  }

  // Diagnostic: inspect the exact fields/files prepared for the API request.
  console.info("[Fabric Try-on] Request model/face fields:", {
    personImageSelected: Boolean(personFile),
    gender: personFile ? null : gender.value,
    bodyType: personFile ? null : (bodyType.value || null),
    faceImageInputFound: Boolean(faceImage),
    faceImageSelected: Boolean(selectedFaceFile),
    faceImageName: selectedFaceFile?.name || null,
    faceChoice: personFile ? null : (faceChoice.value || null),
    formDataHasPersonImage: payload.has("person_image"),
    formDataHasFaceImage: payload.has("face_image"),
    formDataHasFaceChoice: payload.has("face_choice"),
    faceImageValueIsFile: payload.get("face_image") instanceof File
  });

  if (!personFile && selectedFaceFile &&
      (!payload.has("face_image") || !(payload.get("face_image") instanceof File))) {
    showError("The selected face image could not be added as a file to the API request.");
    statusMessage.textContent = "Request failed.";
    generateButton.disabled = false;
    generateButton.textContent = "Generate image";
    return;
  }

  for (const fieldId of [
    "pose",
    "camera-view",
    "background",
    "style-note"
  ]) {
    const field = document.querySelector(`#${fieldId}`);

    if (isCatalog && ['pose', 'camera-view'].includes(fieldId)) continue;
    if (field.value.trim()) {
      payload.append(field.name, field.value.trim());
    }
  }

  const seedValue = document.querySelector("#seed").value.trim();
  const guidanceValue = document.querySelector("#guidance").value.trim();

  if (seedValue !== "") payload.append("seed", seedValue);
  if (guidanceValue !== "") payload.append("guidance", guidanceValue);
  const options = { draft_mode: document.querySelector('#draft-mode').value === 'true' };
  const crop = usesFabric || extractFabric ? document.querySelector('#fabric-crop-box').value.trim() : '';
  if (crop) {
    const box = crop.split(',').map(value => Number(value.trim()));
    if (crop.split(',').some(value => !value.trim()) || box.length !== 4 ||
        !box.every(Number.isInteger) || box[0] < 0 || box[1] < 0 || box[2] <= box[0] || box[3] <= box[1]) {
      showError('Fabric crop must be four integers: left, upper, right, lower; right/lower must be greater than left/upper.');
      statusMessage.textContent = 'Request failed.';
      generateButton.disabled = false;
      setGenerationMode();
      return;
    }
    options.fabric_crop_box = box;
  }
  if (usesFabric && isCatalog && garmentType.value === 'saree') {
    for (const region of ['body', 'border']) {
      const raw = document.querySelector(`#fabric-${region}-crop-box`).value.trim();
      if (!raw) continue;
      const values = raw.split(',');
      const box = values.map(value => Number(value.trim()));
      if (values.some(value => !value.trim()) || box.length !== 4 || !box.every(Number.isInteger) ||
          box[0] < 0 || box[1] < 0 || box[2] <= box[0] || box[3] <= box[1]) {
        showError(`${region} crop must be left, upper, right, lower in original fabric pixels.`);
        statusMessage.textContent = 'Request failed.';
        generateButton.disabled = false;
        setGenerationMode();
        return;
      }
      options[`fabric_${region}_crop_box`] = box;
    }
  }
  payload.append('options', JSON.stringify(options));

  const catalogProduct = usesFabric && isCatalog && garmentType.value === 'saree' ? Object.fromEntries(
    [...document.querySelectorAll('[data-catalog-product]')].filter(input => input.value.trim())
      .map(input => [input.dataset.catalogProduct, input.value.trim()])) : {};
  if (Object.keys(catalogProduct).length) payload.append('catalog_product', JSON.stringify(catalogProduct));

  const reportRequest = {
    api_url: apiUrl,
    generation_mode: isCatalog ? 'catalog' : 'single',
    ...(isCatalog ? {catalog_product: catalogProduct} : {}),
    fabric_type: usesFabric ? fabricType.value : 'unspecified',
    options,
    garment_source: usesFabric ? "fabric_image" : "garment_image",
    ...(readySelection ? {ready_garment_catalog: readySelection} : {}),
    ...(extractFabric ? {garment_as_swatch: true} : {}),
    garment_type: usesFabric
      ? garmentType.value
      : (catalogGarment || "garment_image"),
    garment_style: usesFabric ? (garmentStyle.value || null) : (catalogStyle || null),
    seed: seedValue === "" ? null : Number(seedValue),
    guidance: guidanceValue === "" ? null : Number(guidanceValue),
    pose: payload.get('pose') || null,
    camera_view: payload.get('camera_view') || null,
    background: document.querySelector("#background").value || null,
    garment_details: usesFabric ? selectedGarmentDetails() : [],
    additional_style_note:
      document.querySelector("#style-note").value.trim() || null,
    draft_mode: document.querySelector("#draft-mode").value === "true",
    person_image_used: Boolean(personFile),
    generated_person: {
      gender: payload.get('gender') || null,
      body_type: payload.get('body_type') || null,
      face_choice: payload.get('face_choice') || null,
      face_image: payload.get('face_image')?.name || null
    }
  };
  const reportFiles = {
    source_file: sourceFile,
    person_file: personFile || null,
    face_file: personFile ? null : selectedFaceFile || null
  };
  let apiResponded = false;
  let apiResponseMetadata = {};

  requestController = new AbortController();
  const states = Array.from(form.elements).map(control => [control, control.disabled]);
  states.forEach(([control]) => { control.disabled = true; });
  cancelButton.disabled = false;
  cancelButton.classList.remove('hidden');
  let catalogCount = 0;
  let saveChain = Promise.resolve();
  const catalogRecords = [];
  const catalogReport = isCatalog ? {
    catalog_id: null, status: 'in_progress', total: null, images: [], failed_views: []
  } : null;
  requestTimer.start();
  try {
    const response = await fetch(apiUrl, {
      method: "POST",
      body: payload,
      signal: requestController.signal
    });
    apiResponded = true;

    if (isCatalog) {
      if (!response.ok) {
        const failure = await response.json().catch(() => ({}));
        throw new Error(failure.error || JSON.stringify(failure) || `HTTP ${response.status}`);
      }
      let finalEvent = null;
      const failedViews = [];
      previewInputImages();
      await CatalogClient.readEvents(response, event => {
        if (event.event === 'started') {
          catalogReport.catalog_id = event.catalog_id || null;
          catalogReport.total = event.total;
          catalogReport.catalog_edition = event.catalog_edition || null;
          catalogReport.layout = event.layout || null;
          catalogReport.requested_views = event.views;
        }
        if (event.event === 'generating') statusMessage.textContent =
          `Generating ${event.view.replaceAll('_', ' ')} (${event.index}/${event.total})…`;
        if (event.event === 'image_ready') {
          const output = event.image;
          if (!output?.url) throw new Error('Catalog image URL is missing.');
          catalogCount++;
          const record = {request: {...reportRequest, catalog_view: output.view}, output,
            local_output_path: null, generation_error: null, http_status: response.status,
            generation_seed: output.generation_seed ?? null, generation: output.generation ?? null,
            catalog: catalogReport, ...reportFiles};
          const catalogImage = { ...output, local_output_path: null };
          catalogReport.images.push(catalogImage);
          catalogRecords.push(record);
          if (!latestGeneration) { latestGeneration = record; displayOutput(output); }
          const card = document.createElement('article');
          card.className = 'comparison-card';
          const heading = document.createElement('h4');
          heading.textContent = output.view.replaceAll('_', ' ');
          const image = document.createElement('img');
          image.src = output.url; image.alt = heading.textContent;
          const open = document.createElement('a');
          open.href = output.url; open.target = '_blank'; open.rel = 'noopener';
          open.className = 'secondary-button'; open.textContent = 'Open / Save image';
          const select = document.createElement('button');
          select.type = 'button'; select.className = 'secondary-button'; select.textContent = 'Inspect / Report';
          select.onclick = () => { latestGeneration = record; displayOutput(output);
            reportSaveMessage.textContent = `Selected catalog view: ${output.view}`; };
          const savedLabel = document.createElement('p');
          savedLabel.textContent = 'Waiting for local save…';
          card.append(heading, image, open, select, savedLabel); catalogGrid.append(card);
          catalogSummary.textContent = `${catalogCount}/${catalogReport.total} images ready. Preparing the portrait catalog.`;
          saveChain = saveChain.then(async () => {
            const saved = await saveOutputLocally(output.url, output.format || 'jpg');
            record.local_output_path = saved?.filename || null;
            catalogImage.local_output_path = record.local_output_path;
            savedLabel.textContent = saved ? `Saved: ${saved.filename}` : 'Local save failed; use Open / Save image.';
          });
        }
        if (event.event === 'composing') statusMessage.textContent = 'Assembling portrait catalog…';
        if (event.event === 'collage_ready') {
          const output = event.image;
          catalogReport.collage = {...output, local_output_path: null};
          const record = {request: {...reportRequest, catalog_view: 'catalog'}, output,
            local_output_path: null, generation_error: null, http_status: response.status,
            catalog: catalogReport, ...reportFiles};
          catalogRecords.push(record);
          latestGeneration = record;
          displayOutput(output);
          const card = document.createElement('article');
          card.className = 'comparison-card';
          card.style.gridColumn = '1 / -1';
          const title = document.createElement('h4'); title.textContent = `Final portrait catalog${output.aspect_ratio ? ' (' + output.aspect_ratio + ')' : ''}`;
          const image = document.createElement('img'); image.src = output.url; image.alt = title.textContent;
          const link = document.createElement('a'); link.href = output.url;
          link.target = '_blank'; link.rel = 'noopener'; link.textContent = 'Open / Download Catalog';
          card.append(title, image, link); catalogGrid.prepend(card);
          saveChain = saveChain.then(async () => {
            const saved = await saveOutputLocally(output.url, output.format || 'png');
            record.local_output_path = saved?.filename || null;
            catalogReport.collage.local_output_path = record.local_output_path;
          });
        }
        if (event.event === 'image_failed') {
          failedViews.push(event.view);
          catalogReport.failed_views.push({view: event.view, error: event.error,
            provider_code: event.provider_code ?? null, generation: event.generation ?? null});
          const failure = document.createElement('p');
          failure.className = 'error-box';
          failure.textContent = `${event.view}: ${event.error}`;
          const inspect = document.createElement('button');
          inspect.type = 'button'; inspect.className = 'secondary-button'; inspect.textContent = 'Report failed view';
          const record = {request: {...reportRequest, catalog_view: event.view}, output: null,
            generation_error: event.error, provider_code: event.provider_code ?? null,
            generation: event.generation ?? null, http_status: response.status,
            catalog: catalogReport, ...reportFiles};
          catalogRecords.push(record);
          inspect.onclick = () => { latestGeneration = record;
            reportSaveMessage.textContent = `Selected failed catalog view: ${event.view}`;
            feedbackSection.classList.remove('hidden'); };
          catalogGrid.append(failure, inspect);
        }
        if (event.event === 'error') throw new Error(event.error || 'Catalog failed.');
        if (event.event === 'complete') {
          finalEvent = event;
          catalogReport.status = event.status;
          catalogReport.collage_error = event.collage_error || null;
        }
      });
      const duration = requestTimer.stop();
      catalogRecords.forEach(record => { record.request_duration_ms = duration; });
      if (!finalEvent) throw new Error('Connection ended before the catalog completed. Images already displayed remain available.');
      statusMessage.textContent = `Catalog ${finalEvent.status}: ${catalogCount}/${finalEvent.total} images ready.`;
      statusMessage.textContent += finalEvent.collage ? ' Portrait catalog ready.' : ' Final collage unavailable: ' + (finalEvent.collage_error || 'server update required') + '.';
      catalogSummary.textContent = statusMessage.textContent + (failedViews.length ? ` Failed views: ${failedViews.join(', ')}.` : '');
      if (catalogCount) feedbackSection.classList.remove('hidden');
      else throw new Error('No catalog images were generated. See the failed views.');
      return;
    }
    const data = await response.json().catch(() => ({}));
    apiResponseMetadata = {
      generation_seed: data.generation_seed ?? data.generation?.effective_seed ?? null,
      generation: data.generation ?? null,
      provider_code: data.provider_code ?? null,
      failure_type: data.failure_type ?? null,
      http_status: response.status,
      request_duration_ms: requestTimer.stop()
    };

    if (!response.ok || !data.success) {
      throw new Error(
        data.error ||
        JSON.stringify(data) ||
        `Request failed with HTTP ${response.status}`
      );
    }

    const output = data.images?.[0];

    if (!output?.url) {
      throw new Error(
        "The API response did not include an image URL."
      );
    }

    previewInputImages();

    displayOutput(output);

    statusMessage.textContent =
      `Generated ${output.width || ""} × ${output.height || ""} ${output.format || "image"}.`;

    const savedOutput = await saveOutputLocally(
      output.url,
      output.format || "jpg"
    );

    latestGeneration = {
      request: { ...reportRequest, garment_type: data.garment_type || reportRequest.garment_type },
      output,
      local_output_path: savedOutput?.filename || null,
      generation_error: null,
      ...apiResponseMetadata,
      ...reportFiles
    };

    feedbackSection.classList.remove("hidden");

  } catch (error) {
    apiResponseMetadata.request_duration_ms = requestTimer.stop();
    const stopped = error.name === 'AbortError';
    if (catalogReport) {
      if (catalogReport.status === 'in_progress') catalogReport.status = stopped ? 'cancelled' : 'interrupted';
      catalogReport.stream_error = error.message;
    }
    imagePlaceholder.textContent = 'No image was generated.';
    statusMessage.textContent = catalogCount
      ? `Catalog ${stopped ? 'stopped' : 'interrupted'}: ${catalogCount} images remain available.`
      : (stopped ? 'Generation stopped.' : 'Request failed.');
    if (catalogCount) {
      catalogSummary.textContent = statusMessage.textContent;
      feedbackSection.classList.remove('hidden');
      showError(stopped ? 'Stopped. An active provider call may still finish on the backend.' : error.message);
      return;
    }

    latestGeneration = {
      request: reportRequest,
      output: null,
      local_output_path: null,
      generation_error: error.message || "Unknown generation error",
      catalog: catalogReport,
      ...apiResponseMetadata,
      ...reportFiles
    };
    issueNote.value = `Generation failed: ${latestGeneration.generation_error}`;
    feedbackSection.classList.remove("hidden");

    const networkHint = !apiResponded && error instanceof TypeError
      ? " Check the API URL, network connection, and CORS configuration."
      : "";
    showError(`${latestGeneration.generation_error}${networkHint}`);

  } finally {
    const duration = requestTimer.stop();
    catalogRecords.forEach(record => { record.request_duration_ms = duration; });
    if (catalogReport) catalogReport.request_duration_ms = duration;
    statusMessage.textContent += isCatalog && catalogCount ? ' Finishing local saves…' : '';
    await saveChain;
    statusMessage.textContent = statusMessage.textContent.replace(' Finishing local saves…', '');
    states.forEach(([control, disabled]) => { control.disabled = disabled; });
    requestController = null;
    cancelButton.classList.add('hidden');
    generateButton.disabled = false;
    setGenerationMode();
  }
});

feedbackForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!latestGeneration) return;

  saveReportButton.disabled = true;
  saveReportButton.textContent = "Saving report...";
  reportSaveMessage.textContent =
    "Copying images and report data...";

  try {
    const [source, person, face] = await Promise.all([
      readFileAsDataUrl(latestGeneration.source_file),
      readFileAsDataUrl(latestGeneration.person_file),
      readFileAsDataUrl(latestGeneration.face_file)
    ]);

    const response = await fetch("/save-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        issue_text: issueNote.value.trim(),
        request: latestGeneration.request,
        output: latestGeneration.output,
        local_output_path: latestGeneration.local_output_path,
        generation_error: latestGeneration.generation_error,
        generation_seed: latestGeneration.generation_seed ?? null,
        generation: latestGeneration.generation ?? null,
        provider_code: latestGeneration.provider_code ?? null,
        failure_type: latestGeneration.failure_type ?? null,
        http_status: latestGeneration.http_status ?? null,
        request_duration_ms: latestGeneration.request_duration_ms ?? null,
        catalog: latestGeneration.catalog ?? null,
        source,
        person,
        face
      })
    });

    const report = await response.json();

    if (!response.ok) {
      throw new Error(report.error || "Could not save report.");
    }

    reportSaveMessage.textContent =
      `Report saved: ${report.report_path}. Aggregate JSON updated: ${report.aggregate_path}` +
      (report.warning ? ` Warning: ${report.warning}` : "");

    issueNote.value = "";

  } catch (error) {
    reportSaveMessage.textContent =
      `Report was not saved: ${error.message}`;

  } finally {
    saveReportButton.disabled = false;
    saveReportButton.textContent = "Save testing report";
  }
});

setTheme(localStorage.getItem("fabric-tryon-theme") || "light");
setFaces();
setGarmentSourceMode();
setPersonMode();

generationMode.addEventListener('change', setGenerationMode);
readyCatalog.addEventListener('change', setGenerationMode);
document.querySelector('#camera-view').addEventListener('change', setReferencePoseAvailability);
cancelButton.addEventListener('click', () => {
  requestController?.abort();
  cancelButton.disabled = true;
});
setGenerationMode();
