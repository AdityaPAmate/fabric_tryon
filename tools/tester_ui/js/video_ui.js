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

  async function checkMotionSupport(apiUrl, signal) {
    if (motion.value !== 'walking') return;
    const response = await fetch(new URL('/api/health/',apiUrl),{signal});
    const info = await response.json();
    if (!response.ok || !info.video_motions?.includes('walking')) {
      throw new Error('Walking needs the latest backend deployment. Deploy the update, then try again.');
    }
  }

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
      if (job.video.continuity?.status === 'review_required') {
        h.status.textContent = 'Video ready — visual review needed';
        progress.textContent = `Video ready — visual review needed | Job: ${job.job_id}`;
        h.showError('Review needed: possible background or lighting change. The video is available below; visual consistency is not verified.');
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
    await checkMotionSupport(h.api.value,signal);
    const response = await fetch(image.url,{signal});
    if (!response.ok) throw new Error('Could not read the generated photo for animation.');
    const form = new FormData();
    form.append('source_image',await response.blob(),'generated.png');
    form.set('video_motion',motion.value || 'mirror_check');
    const garment = previous.request?.garment_type;
    if (['shirt','saree','kurta','kurti_pant','pant','blazer'].includes(garment)) form.append('garment_type',garment);
    const view = previous.request?.camera_view;
    if (['front','side','close_up'].includes(view)) form.append('camera_view',view);
    else if (image.view && !['front','side','back','default'].includes(image.view)) form.append('camera_view','close_up');
    if (previous.request?.pose) form.append('pose',previous.request.pose);
    const endpoint = new URL('/api/animate-image/',h.api.value).href;
    const job = await VideoClient.createVideoJob(endpoint,form,auth,signal);
    await poll(job,signal,{...previous,request:{...previous.request,generation_mode:'video_from_image'}});
  });

  return {
    setMode(video) {
      el('video-settings').classList.toggle('hidden',!(video || image));
      animate.classList.toggle('hidden',!image || image.view === 'catalog' || video);
      if (!video && !current) { player.classList.add('hidden'); actions.classList.add('hidden'); }
    },
    onImage(output) { image=output; this.setMode(h.mode.value === 'video'); },
    reset() { stopClock(); current=null; image=null; player.removeAttribute('src'); player.classList.add('hidden');
      actions.classList.add('hidden'); retry.classList.add('hidden'); progress.classList.add('hidden'); stageTime.classList.add('hidden'); animate.classList.add('hidden'); },
    stop:stopClock,
    currentJob:()=>current,
    async generate(apiUrl,payload,signal,context) {
      await checkMotionSupport(apiUrl,signal);
      payload.set('video_motion',motion.value || 'mirror_check');
      const job = await VideoClient.createVideoJob(apiUrl,payload,getToken(),signal);
      return poll(job,signal,context);
    }
  };
}
