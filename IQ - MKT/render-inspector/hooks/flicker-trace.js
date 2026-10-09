(() => {
  if (globalThis.__riFlickerTrace) return;

  const classifications = Object.freeze([
    'POST_RENDER_OVERRIDE',
    'ONE_FRAME_LATE_TRACKING',
    'MUTATION_OBSERVER_DELAY',
    'TIMER_DELAY',
    'RAF_ORDERING_PROBLEM',
    'DOUBLE_RAF_DELAY',
    'WORKER_MAIN_THREAD_DESYNC',
    'CANVAS_REDRAW_OVERWRITES_PATCH',
    'WEBGL_UNIFORM_APPLIED_AFTER_DRAW',
    'WEBGL_TEXTURE_APPLIED_AFTER_DRAW',
    'OVERLAY_COMPOSITION_DELAY',
    'MULTIPLE_CANVAS_LAYER_DESYNC',
    'REFERENCE_TARGET_CLOCK_DESYNC',
    'UNKNOWN'
  ]);
  const state = {
    armed: false,
    label: '',
    frameSequence: 0,
    eventSequence: 0,
    operationSequence: 0,
    maxEvents: 20000,
    maxFrames: 120,
    startFrame: 0,
    startedAt: 0,
    stoppedAt: 0,
    events: [],
    droppedEvents: 0,
    lastRafTimestamp: null,
    rafWrapped: false
  };

  const record = (type, payload = {}) => {
    if (!state.armed) return null;
    if (state.events.length >= state.maxEvents) {
      state.events.shift();
      state.droppedEvents += 1;
    }
    const event = {
      sequence: ++state.eventSequence,
      type,
      timestamp: performance.now(),
      frameSequence: state.frameSequence,
      payload
    };
    state.events.push(event);
    return event;
  };

  const begin = (type, payload = {}) => {
    const operationId = ++state.operationSequence;
    record(`${type}_BEGIN`, {...payload, operationId});
    return operationId;
  };
  const end = (type, operationId, payload = {}) => {
    record(`${type}_END`, {...payload, operationId});
  };

  const wrapRaf = () => {
    if (state.rafWrapped || typeof globalThis.requestAnimationFrame !== 'function') return;
    const original = globalThis.requestAnimationFrame;
    function wrapped(callback) {
      return original.call(this, timestamp => {
        if (timestamp !== state.lastRafTimestamp) {
          state.lastRafTimestamp = timestamp;
          state.frameSequence += 1;
        }
        record('REQUEST_ANIMATION_FRAME_BEGIN', {rafTimestamp: timestamp});
        let result;
        try { result = callback(timestamp); }
        finally {
          record('REQUEST_ANIMATION_FRAME_END', {rafTimestamp: timestamp});
          queueMicrotask(() => record('FRAME_PRESENT_CANDIDATE', {rafTimestamp: timestamp}));
        }
        return result;
      });
    }
    Object.defineProperty(wrapped, '__riWrapped', {value: true});
    try { Object.defineProperty(wrapped, 'name', {value: original.name}); } catch (_) {}
    globalThis.requestAnimationFrame = wrapped;
    state.rafWrapped = true;
  };

  const arm = (options = {}) => {
    state.armed = false;
    state.label = String(options.label || 'flicker-trace');
    state.events = [];
    state.droppedEvents = 0;
    state.eventSequence = 0;
    state.operationSequence = 0;
    state.maxEvents = Math.max(100, Number(options.maxEvents) || 20000);
    state.maxFrames = Math.max(1, Number(options.maxFrames) || 120);
    state.startFrame = state.frameSequence;
    state.startedAt = performance.now();
    state.stoppedAt = 0;
    wrapRaf();
    state.armed = true;
    record('FLICKER_TRACE_ARMED', {label: state.label, maxFrames: state.maxFrames});
    return snapshot();
  };
  const stop = () => {
    record('FLICKER_TRACE_STOPPED', {label: state.label});
    state.stoppedAt = performance.now();
    state.armed = false;
    return snapshot();
  };
  const snapshot = () => ({
    version: 1,
    label: state.label,
    armed: state.armed,
    startedAt: state.startedAt,
    stoppedAt: state.stoppedAt || performance.now(),
    observedFrames: Math.max(0, state.frameSequence - state.startFrame),
    frameSequence: state.frameSequence,
    droppedEvents: state.droppedEvents,
    classifications: Array.from(classifications),
    events: state.events.slice()
  });

  globalThis.__riFlickerTrace = Object.freeze({
    classifications,
    record,
    begin,
    end,
    arm,
    stop,
    snapshot,
    get frameSequence() { return state.frameSequence; },
    get armed() { return state.armed; }
  });
})();
