/* Vastra TryOn Video Client: Manages asynchronous video try-on job lifecycle. */
(function (root) {
  function resolveBaseUrl(apiUrl) {
    try {
      const url = new URL(apiUrl);
      return url.origin;
    } catch {
      return 'http://127.0.0.1:8000';
    }
  }

  function resolveEndpoint(apiUrl, mode) {
    const url = new URL(apiUrl);
    if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Enter an HTTP or HTTPS backend API URL.');
    const target = mode === 'video'
      ? 'generate-tryon-video/'
      : (mode === 'catalog' ? 'generate-catalog/' : 'replace-fabric/');

    if (/\/(replace-fabric|generate-catalog|generate-tryon-video)\/?$/.test(url.pathname)) {
      url.pathname = url.pathname.replace(/(replace-fabric|generate-catalog|generate-tryon-video)\/?$/, target);
    } else {
      url.pathname = '/api/' + target;
    }
    return url.href;
  }

  async function createVideoJob(endpointUrl, formData, bearerToken, signal) {
    const headers = {};
    if (bearerToken) {
      headers['Authorization'] = bearerToken.startsWith('Bearer ') ? bearerToken : `Bearer ${bearerToken}`;
    }

    const response = await fetch(endpointUrl, {
      method: 'POST',
      headers,
      body: formData,
      signal
    });

    const data = await response.json().catch(() => ({}));
    if (response.status === 202) {
      return data;
    }

    if (response.status === 401) {
      throw new Error('Video Bearer Token required or invalid (HTTP 401). Check the Video API Token setting.');
    }
    if (response.status === 503) {
      throw new Error('Video API is not configured on the backend (HTTP 503). Ensure VIDEO_API_TOKEN and GIMMECLIP_API_KEY are configured.');
    }

    const errorMsg = data.error || (data.detail) || (typeof data === 'object' ? JSON.stringify(data) : `HTTP ${response.status}`);
    throw new Error(`Video submission failed: ${errorMsg}`);
  }

  async function getVideoJob(baseUrl, jobId, bearerToken, signal) {
    const origin = resolveBaseUrl(baseUrl);
    const statusUrl = `${origin}/api/video-jobs/${jobId}/`;
    const headers = {};
    if (bearerToken) {
      headers['Authorization'] = bearerToken.startsWith('Bearer ') ? bearerToken : `Bearer ${bearerToken}`;
    }

    const response = await fetch(statusUrl, {
      method: 'GET',
      headers,
      signal
    });

    if (response.status === 404) {
      throw new Error(`Video job ${jobId} not found (HTTP 404).`);
    }
    if (response.status === 401) {
      throw new Error('Video Bearer Token required or invalid (HTTP 401).');
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Status check failed with HTTP ${response.status}`);
    }

    return await response.json();
  }

  async function retryVideoJob(baseUrl, jobId, bearerToken, signal) {
    const origin = resolveBaseUrl(baseUrl);
    const retryUrl = `${origin}/api/video-jobs/${jobId}/retry/`;
    const headers = {};
    if (bearerToken) {
      headers['Authorization'] = bearerToken.startsWith('Bearer ') ? bearerToken : `Bearer ${bearerToken}`;
    }

    const response = await fetch(retryUrl, {
      method: 'POST',
      headers,
      signal
    });

    const data = await response.json().catch(() => ({}));
    if (response.status === 202) {
      return data;
    }
    if (response.status === 409) {
      throw new Error(data.detail || 'This job cannot be retried (either not in failed state or not retryable).');
    }
    throw new Error(data.detail || data.error || `Retry failed with HTTP ${response.status}`);
  }

  async function pollJobUntilFinished(baseUrl, jobId, bearerToken, {
    onUpdate,
    signal,
    intervalMs = 3000,
    timeoutMs = 1800000
  } = {}) {
    const start = performance.now();
    let pollCount = 0;

    while (true) {
      if (signal?.aborted) {
        throw new DOMException('Video polling aborted by user', 'AbortError');
      }

      if (performance.now() - start > timeoutMs) {
        throw new Error(`Stopped waiting after ${Math.round(timeoutMs / 1000)} seconds. The server job may still be running; inspect the saved job ID.`);
      }

      pollCount++;
      const job = await getVideoJob(baseUrl, jobId, bearerToken, signal);
      if (onUpdate) {
        onUpdate(job, pollCount);
      }

      if (job.status === 'completed' || job.status === 'failed') {
        return job;
      }

      await new Promise((resolve, reject) => {
        const onAbort = () => {
          clearTimeout(timeout);
          reject(new DOMException('Video polling aborted by user', 'AbortError'));
        };
        const timeout = setTimeout(() => {
          signal?.removeEventListener('abort', onAbort);
          resolve();
        }, intervalMs);
        signal?.addEventListener('abort', onAbort, { once: true });
        if (signal?.aborted) onAbort();
      });
    }
  }

  root.VideoClient = {
    resolveBaseUrl,
    resolveEndpoint,
    createVideoJob,
    getVideoJob,
    retryVideoJob,
    pollJobUntilFinished
  };

  if (typeof module !== 'undefined') {
    module.exports = root.VideoClient;
  }
})(globalThis);
