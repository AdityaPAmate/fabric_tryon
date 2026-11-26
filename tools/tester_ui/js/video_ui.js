/* Optional video stage; the existing image/catalog form keeps all its controls. */
function createVideoUI(h) {
  const el = id => document.getElementById(id);
  const token = el('video-token');
  const lookup = el('video-job-id');
  const progress = el('video-progress');
  const stageTime = el('video-generation-time');
  const player = el('result-video');
  const actions = el('video-actions');
  const retry = el('retry-video');
  const animate = el('animate-result');
  const motion = el('video-motion');
  const garmentChoice = el('video-garment-type');
  const garmentField = el('video-garment-field');
  let options = null;
  let optionsKey = '';
  let loadingKey = '';
  let optionsSequence = 0;
  motion.addEventListener('change',()=>{
    showMotionHelp();
  });
  let current = null;
  let image = null;
  let stageInterval = null;
  const labels = {queued:'Queued', image_generating:'Preparing try-on image',
    video_submitting:'Submitting video', video_generating:'Generating video',
    video_storing:'Saving video', completed:'Video ready', failed:'Video failed'};

  try { const savedApi = localStorage.getItem('fabric-api-url'); if (savedApi) h.api.value=savedApi; } catch {}
  h.api.addEventListener('change',()=>localStorage.setItem('fabric-api-url',h.api.value.trim()));
  try { lookup.value = JSON.parse(localStorage.getItem('fabric-video-job') || 'null')?.id || ''; } catch {}

  function getToken() {
    if (!token.value.trim()) throw new Error('Enter your backend VIDEO_API_TOKEN in Video options. Do not enter the Gimmeclip key.');
    return token.value.trim();
  }

  function savedGarment() {
    const type = h.getRecord()?.request?.garment_type;
    return ['garment_image','garment','ready_made'].includes(type) ? null : type;
  }

  function selectedGarment() {
    // A saved image uses its own context, never a subsequently changed form value.
    if (image && h.mode.value !== 'video') return savedGarment() || garmentChoice.value;
    return el('garment-source').value === 'fabric' ? el('garment-type').value : garmentChoice.value;
  }

  function showMotionHelp() {
    const style = options?.styles.find(s=>s.id === motion.value);
    el('video-motion-help').textContent = style
      ? `${style.help} ${options.source_hint}` : 'Choose the garment to see its video styles.';
  }

  async function getOptions(apiUrl, garment, signal) {
    if (!garment) throw new Error('Choose the garment shown in the image in Video options.');
    const url = new URL('/api/video-options/',apiUrl || h.api.value);
    url.searchParams.set('garment_type',garment);
    const response = await fetch(url,{signal});
    if (response.status === 404) throw new Error('Video options need the latest backend deployment. Deploy the update, then try again.');
    const data = await response.json();
    if (!response.ok || data.garment_type !== garment || !Array.isArray(data.styles) || !data.styles.length) {
      throw new Error(data.garment_type || 'Could not load video styles for this garment.');
    }
    return data;
  }

  function displayOptions(data) {
    const previous = options?.garment_type === data.garment_type ? motion.value : null;
    options = data;
    motion.replaceChildren(...data.styles.map(style=>{
      const option = document.createElement('option');
      option.value = style.id; option.textContent = style.label;
      return option;
    }));
    motion.value = data.styles.some(s=>s.id === previous) ? previous : data.default_style;
    showMotionHelp();
  }

  async function refreshOptions() {
    const garment = selectedGarment();
    garmentField.classList.toggle('hidden', Boolean(
      image && h.mode.value !== 'video' ? savedGarment() : el('garment-source').value === 'fabric'));
    if (!garment) {
      ++optionsSequence;
      options = null; optionsKey = ''; loadingKey = '';
      motion.replaceChildren(); showMotionHelp(); return;
    }
    const key = `${h.api.value}|${garment}`;
    if ((options && optionsKey === key) || loadingKey === key) return;
    const sequence = ++optionsSequence;
    loadingKey = key;
    try {
      const data = await getOptions(h.api.value,garment);
      if (sequence === optionsSequence) { optionsKey = key; displayOptions(data); }
    } catch (error) {
      if (sequence === optionsSequence) {
        options = null;
        el('video-motion-help').textContent = error.message;
      }
    } finally { if (sequence === optionsSequence && loadingKey === key) loadingKey = ''; }
  }

  async function checkMotionSupport(apiUrl, garment, signal) {
    // Revalidate on submission, even when the UI previously loaded options.
    const requested = motion.value;
    const data = await getOptions(apiUrl,garment,signal);
    const choice = requested || data.default_style;
    if (!data.styles.some(s=>s.id === choice)) {
      throw new Error('This video style is unavailable for this garment or needs the latest backend deployment. Select one of its current options.');
    }
    return choice;
  }
  garmentChoice.addEventListener('change',refreshOptions);
  el('garment-type').addEventListener('change',()=>{if(h.mode.value === 'video') refreshOptions();});
  el('garment-source').addEventListener('change',()=>{if(h.mode.value === 'video') refreshOptions();});
  h.api.addEventListener('change',()=>{if(h.mode.value === 'video' || image) refreshOptions();});

  function stopClock() {
    if (stageInterval !== null) clearInterval(stageInterval);
    stageInterval = null;
  }

  function update(job) {
    current = job;
    lookup.value = job.job_id;
    localStorage.setItem('fabric-video-job', JSON.stringify({id:job.job_id, origin:VideoClient.resolveBaseUrl(h.api.value)}));
    progress.classList.remove('hidden');
    progress.textContent = `${labels[job.status] || job.status} | Job: ${job.job_id}`;
    h.status.textContent = labels[job.status] || job.status;
    if (job.status !== 'completed') {
      player.classList.add('hidden');
      actions.classList.add('hidden');
    }
    if (job.image?.url) h.displayOutput(job.image);
    retry.classList.toggle('hidden', !(job.status === 'failed' && job.error?.retryable));
    stopClock();
    const seconds = job.timing?.video_generation_seconds;
    stageTime.classList.toggle('hidden', seconds == null);
    if (seconds != null) {
      const start = performance.now();
      const running = ['video_submitting','video_generating'].includes(job.status);
      const render = () => {
        const elapsed = seconds + (running ? (performance.now()-start)/1000 : 0);
        stageTime.textContent = `Video generation ${running ? 'elapsed' : 'time'}: ${elapsed.toFixed(1)} s`;
      };
      render();
      if (!running && job.status === 'completed') {
        const parts = [['download_seconds','Download'],['render_seconds','Render'],['final_upload_seconds','Upload']]
          .filter(([key])=>job.timing?.[key] != null)
          .map(([key,label])=>`${label}: ${job.timing[key].toFixed(1)} s`);
        if (parts.length) stageTime.textContent += ` | ${parts.join(' | ')}`;
      }
      if (running) stageInterval = setInterval(render, 100);
    }
    if (job.status === 'failed') h.showError(job.error?.message || 'Video generation failed. The generated image is retained.');
    if (job.status === 'completed' && job.video?.url) {
      player.src = job.video.url;
      player.classList.remove('hidden');
      actions.classList.remove('hidden');
      el('open-video').href = job.video.url;
      el('download-video').href = job.video.url;
      el('download-video').download = `fabric-tryon-${job.job_id}.mp4`;
      if (job.quality_status === 'needs_review' || job.video.continuity?.status === 'review_required') {
        h.status.textContent = 'Video ready — visual review needed';
        progress.textContent = `Video ready — visual review needed | Job: ${job.job_id}`;
        h.showError('Review needed: possible background or lighting change. The video is available below; visual consistency is not verified.');
      } else if (job.quality_status === 'not_verified' || job.video.continuity?.status === 'not_applicable') {
        h.status.textContent = 'Video generated — visual consistency not verified';
        progress.textContent = `Video generated — check fabric, background, lighting and accessories before use | Job: ${job.job_id}`;
      }
    }
  }

  async function finish(job, context = {}) {
    update(job);
    const duration = h.timer.stop();
    const record = {...context, request:context.request || {generation_mode:'video',garment_type:job.garment_type || 'garment'},
      output:job.image || null, video:job.video || null, video_job:job,
      request_duration_ms:duration, generation_error:job.error?.message || null};
    h.setRecord(record);
    h.feedback.classList.remove('hidden');
    if (job.status === 'completed') {
      const savedImage = job.image?.url ? await h.save(job.image.url, job.image.format || 'png') : null;
      const savedVideo = await h.save(job.video.url, job.video.format || 'mp4', 'video');
      record.local_output_path = savedImage?.filename || null;
      record.local_video_path = savedVideo?.filename || null;
      if (savedVideo?.filename) el('download-video').href=savedVideo.filename;
    }
    return record;
  }

  async function poll(job, signal, context, resume = false) {
    if (resume && job.timing?.elapsed_seconds != null) h.timer.start(job.timing.elapsed_seconds * 1000);
    update(job);
    if (!['completed','failed'].includes(job.status)) {
      job = await VideoClient.pollJobUntilFinished(h.api.value, job.job_id, getToken(), {signal,onUpdate:update});
    }
    return finish(job, context);
  }

  async function busy(action) {
    if (h.isBusy()) return;
    h.clearError();
    const states = [...h.form.elements].map(control=>[control,control.disabled]);
    states.forEach(([control])=>{control.disabled=true;});
    animate.disabled=true;
    h.cancel.disabled=false;
    h.cancel.classList.remove('hidden');
    const controller = new AbortController();
    h.setController(controller);
    h.timer.start();
    try { await action(controller.signal); }
    catch (error) {
      h.status.textContent = error.name === 'AbortError' ? 'Stopped waiting; the server job continues.' : 'Video request failed.';
      h.showError(error.name === 'AbortError' ? 'Inspect the saved job ID to resume checking it.' : error.message);
    } finally {
      stopClock();
      h.timer.stop();
      states.forEach(([control,disabled])=>{control.disabled=disabled;});
      animate.disabled=false;
      h.cancel.classList.add('hidden');
      h.setController(null);
      h.refreshMode();
    }
  }

  el('lookup-video').onclick = () => busy(async signal => {
    const id = lookup.value.trim();
    if (!/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i.test(id)) throw new Error('Enter a valid saved job UUID.');
    const job = await VideoClient.getVideoJob(h.api.value,id,getToken(),signal);
    await poll(job,signal,undefined,true);
  });
  retry.onclick = () => busy(async signal => {
    if (!current?.error?.retryable) return;
    const job = await VideoClient.retryVideoJob(h.api.value,current.job_id,getToken(),signal);
    await poll(job,signal,h.getRecord() || {},true);
  });
  animate.onclick = () => busy(async signal => {
    if (!image?.url || image.view === 'catalog') return;
    const auth = getToken();
    const previous = h.getRecord() || {};
    const garment = savedGarment() || garmentChoice.value;
    const selectedMotion = await checkMotionSupport(h.api.value,garment,signal);
    const response = await fetch(image.url,{signal});
    if (!response.ok) throw new Error('Could not read the generated photo for animation.');
    const form = new FormData();
    form.append('source_image',await response.blob(),'generated.png');
    form.set('video_motion',selectedMotion);
    form.append('garment_type',garment);
    const view = previous.request?.camera_view;
    if (['front','side','close_up'].includes(view)) form.append('camera_view',view);
    else if (image.view && !['front','side','back','default'].includes(image.view)) form.append('camera_view','close_up');
    if (previous.request?.pose) form.append('pose',previous.request.pose);
    const endpoint = new URL('/api/animate-image/',h.api.value).href;
    const job = await VideoClient.createVideoJob(endpoint,form,auth,signal);
    await poll(job,signal,{...previous,request:{...previous.request,garment_type:garment,
      video_motion:selectedMotion,generation_mode:'video_from_image'}});
  });

  return {
    setMode(video) {
      el('video-settings').classList.toggle('hidden',!(video || image));
      animate.classList.toggle('hidden',!image || image.view === 'catalog' || video);
      if (!video && !current) { player.classList.add('hidden'); actions.classList.add('hidden'); }
      if (video || (image && image.view !== 'catalog')) refreshOptions();
    },
    onImage(output) { image=output; this.setMode(h.mode.value === 'video'); },
    reset() { stopClock(); ++optionsSequence; options=null; optionsKey=''; loadingKey='';
      current=null; image=null; player.removeAttribute('src'); player.classList.add('hidden');
      actions.classList.add('hidden'); retry.classList.add('hidden'); progress.classList.add('hidden'); stageTime.classList.add('hidden'); animate.classList.add('hidden'); },
    stop:stopClock,
    currentJob:()=>current,
    async generate(apiUrl,payload,signal,context) {
      const garment = payload.get('garment_type') || garmentChoice.value;
      const selectedMotion = await checkMotionSupport(apiUrl,garment,signal);
      payload.set('garment_type',garment);
      payload.set('video_motion',selectedMotion);
      const job = await VideoClient.createVideoJob(apiUrl,payload,getToken(),signal);
      return poll(job,signal,{...context,request:{...context?.request,garment_type:garment,video_motion:selectedMotion}});
    }
  };
}
