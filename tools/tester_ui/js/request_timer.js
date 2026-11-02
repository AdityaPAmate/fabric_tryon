/* Measures the whole API request, excluding later image download/local saving. */
function createRequestTimer(element, clock = performance, scheduler = window) {
  let startedAt = null;
  let intervalId = null;
  let elapsedMs = null;

  function render(running) {
    const duration = running ? clock.now() - startedAt : elapsedMs;
    element.textContent = `${running ? "Request elapsed" : "Total request time"}: ${(duration / 1000).toFixed(1)} s`;
  }

  return {
    start() {
      if (intervalId !== null) scheduler.clearInterval(intervalId);
      startedAt = clock.now();
      elapsedMs = null;
      element.classList.remove("hidden");
      render(true);
      intervalId = scheduler.setInterval(() => render(true), 100);
    },
    stop() {
      if (startedAt === null) return elapsedMs;
      elapsedMs = Math.round(clock.now() - startedAt);
      startedAt = null;
      if (intervalId !== null) scheduler.clearInterval(intervalId);
      intervalId = null;
      render(false);
      return elapsedMs;
    }
  };
}
