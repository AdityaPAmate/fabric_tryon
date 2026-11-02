/* Streaming protocol helpers shared by the tester and its contract tests. */
(function (root) {
  function endpoint(value, catalog) {
    const url = new URL(value);
    if (!/^https?:$/.test(url.protocol) || !/\/(replace-fabric|generate-catalog)\/?$/.test(url.pathname)) {
      throw new Error('Enter an API URL ending in /api/replace-fabric/ or /api/generate-catalog/.');
    }
    url.pathname = url.pathname.replace(/(replace-fabric|generate-catalog)\/?$/, catalog ? 'generate-catalog/' : 'replace-fabric/');
    return url.href;
  }

  async function readEvents(response, onEvent) {
    if (!response.body) throw new Error('This browser does not support streaming responses.');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    async function line(value) {
      if (!value.trim()) return;
      let event;
      try { event = JSON.parse(value); }
      catch { throw new Error('The catalog API returned an invalid stream. Check the API URL and deployment.'); }
      await onEvent(event);
    }
    try {
      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
        let end;
        while ((end = buffer.indexOf('\n')) !== -1) {
          await line(buffer.slice(0, end));
          buffer = buffer.slice(end + 1);
        }
        if (done) { await line(buffer); break; }
      }
    } finally {
      await reader.cancel().catch(() => {});
      reader.releaseLock();
    }
  }

  root.CatalogClient = { endpoint, readEvents };
  if (typeof module !== 'undefined') module.exports = root.CatalogClient;
})(globalThis);
