// One edit script drives both the text and the physical keyboard illustrations.
(() => {
  if (!("IntersectionObserver" in window)) return;
  const template = document.getElementById("edit-demo-template");
  const figure = template.content.firstElementChild.cloneNode(true);
  const methods = [...figure.querySelectorAll(".demo-method")];
  const playButton = figure.querySelector(".demo-play");
  const compareButton = figure.querySelector(".demo-compare");
  const paper = figure.querySelector(".demo-text");
  const chord = figure.querySelector(".demo-step kbd");
  const caption = figure.querySelector(".demo-step span");
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const ns = "http://www.w3.org/2000/svg";

  function shape(tag, attrs, parent) {
    const element = document.createElementNS(ns, tag);
    for (const [name, value] of Object.entries(attrs)) element.setAttribute(name, value);
    parent.append(element);
    return element;
  }

  function drawKeyboard(method) {
    const svg = method.querySelector("svg");
    svg.setAttribute("aria-hidden", "true");
    const tray = svg.querySelector(".demo-keys");
    const keys = new Map();
    function key(name, x, y, width = 44) {
      const element = shape("g", {}, tray);
      shape("rect", {x, y: y + 3, width, height: 34, rx: 5, fill: "#0e1727"}, element);
      shape("rect", {x, y, width, height: 33, rx: 5, class: "key-face"}, element);
      const label = shape("text", {x: x + width / 2, y: y + 21, "text-anchor": "middle"}, element);
      label.textContent = name;
      keys.set(name, {element, x: x + width / 2, y: y + 16, width});
    }
    function row(start, y, letters, last, units) {
      let x = start * 48 - 250;
      for (const letter of letters) {
        key(letter, x, y);
        x += 48;
      }
      key(last, x, y, units * 48 - 4);
    }
    row(5, 16, "567890-=", "Backspace", 2);
    row(5.5, 56, "TYUIOP[]", "\\", 1.5);
    row(5.75, 96, "GHJKL;'", "Enter", 2.25);
    row(5.25, 136, "VBNM,./", "Shift", 2.75);
    key("Space", -70, 176, 296);
    key("Alt", 230, 176, 56);
    key("Super", 290, 176, 56);
    key("Menu", 350, 176, 56);
    key("Ctrl", 410, 176, 56);
    for (const [index, name] of ["Ins", "Home", "PgUp", "Del", "End", "PgDn"].entries()) {
      key(name, 502 + index % 3 * 48, 16 + Math.floor(index / 3) * 40);
    }
    key("↑", 550, 136);
    for (const [index, name] of ["←", "↓", "→"].entries()) key(name, 502 + index * 48, 176);
    const nails = Array.from({length: 4}, () => shape("path", {}, svg.querySelector(".hand-nails")));
    return {keys, nails, hand: svg.querySelector(".demo-hand"), outline: svg.querySelector(".hand-outline"),
            travel: svg.querySelector(".demo-travel"), strike: svg.querySelector(".demo-strike"),
            status: method.querySelector(".demo-status"), activeKey: null};
  }
  const boards = methods.map(drawKeyboard);
  const keys = boards[0].keys;
  const home = keys.get("J");
  const fingerOffsets = [[0, 0], [48, -4], [96, 0], [144, 7]];
  const widths = [12, 13, 12, 10];
  const fingerKeys = ["YUHJNM", "IK,", "OL.", "P;'/"];
  function rest() {
    return {x: home.x, y: home.y, tips: fingerOffsets.map(([x, y]) => [x, y])};
  }

  function pose(name) {
    const hand = rest();
    const target = keys.get(name);
    if (!target) return hand;
    let finger;
    if (name === "←" || name === "↑") {
      finger = name === "←" ? 0 : 1;
      hand.x = target.x - fingerOffsets[finger][0];
      hand.y = target.y + 8;
    } else if (name === "Backspace" || name === "Enter") {
      finger = 3;
      hand.x += name === "Backspace" ? 107 : 70;
      hand.y -= name === "Backspace" ? 42 : 8;
    } else {
      finger = fingerKeys.findIndex(letters => name.length === 1 && letters.includes(name));
      if (finger < 0) return hand;
    }
    hand.tips[finger] = [target.x - hand.x, target.y - hand.y];
    return hand;
  }

  function paintHand(board, from, to, amount) {
    const mix = (a, b) => a + (b - a) * amount;
    board.hand.setAttribute("transform", "translate(" + mix(from.x, to.x) + " " + mix(from.y, to.y) + ")");
    // The webbing and wrist follow the palm. Fingertips can reach adjacent keys independently.
    let outline = "M23 193 Q18 158 -17 126 L-62 90 Q-84 73 -76 63 Q-69 54 -55 63 L-24 83 Q-12 91 -13 72";
    for (let i = 0; i < to.tips.length; i++) {
      const x = mix(from.tips[i][0], to.tips[i][0]);
      const y = mix(from.tips[i][1], to.tips[i][1]);
      const w = widths[i];
      const webX = i * 48 + 24;
      const webY = i === 2 ? 78 : 65;
      outline += ` Q${x-w} ${y+44} ${x-w} ${y+8} C${x-w} ${y-9} ${x+w} ${y-11} ${x+w} ${y+8}`;
      if (i < 3) outline += ` Q${x+w+2} ${y+43} ${webX-3} ${webY} Q${webX} ${webY+6} ${webX+4} ${webY-1}`;
      board.nails[i].setAttribute("d", `M${x-6} ${y+8}q0 -11 6 -11t6 11q-5 4 -12 0Z`);
    }
    board.outline.setAttribute("d", outline + " Q164 84 147 135 Q132 162 138 193 Q82 206 23 193Z");
  }

  const actions = [];
  let text = "", cursor = 0, anchor = 0;
  function snapshot() { return {text, cursor, anchor}; }
  function action(kind, name, instruction, edit) {
    const before = snapshot();
    edit();
    actions.push({kind, name, instruction, before, after: snapshot()});
  }
  function type(letters, instruction) {
    for (const c of letters) {
      const key = c === "\n" ? "Enter" : c === " " ? "Space" : c.toUpperCase();
      action("type", key, instruction, () => {
        const start = Math.min(anchor, cursor);
        text = text.slice(0, start) + c + text.slice(Math.max(anchor, cursor));
        cursor = anchor = start + 1;
      });
    }
  }
  const note = "Meet at six.\nBring notess.";
  type(note, "Type a two-line note.");
  action("rest", "", "Check the draft.", () => {});
  action("left", "", "Move before the period.", () => { anchor = --cursor; });
  action("erase", "", "Delete the extra s.", () => {
    text = text.slice(0, cursor - 1) + text.slice(cursor);
    anchor = --cursor;
  });
  action("up", "", "Move up to the meeting time.", () => {
    const lineBreak = text.indexOf("\n");
    cursor = anchor = Math.min(lineBreak, cursor - lineBreak - 1);
  });
  for (let i = 0; i < 3; i++) action("select", "", "Select the word “six”.", () => { cursor--; });
  type("ten", "Replace “six” with “ten”.");
  action("finish", "", "The corrected note.", () => {});

  const bindings = JSON.parse(document.getElementById("keys").textContent);
  function binding(actionName) {
    return Object.values(bindings).find(key => key.action === actionName).label;
  }
  const editing = {
    left: ["←", binding("Move left")], erase: ["Backspace", binding("Backspace")],
    up: ["↑", binding("Move up")], select: ["←", binding("Move left")]
  };

  // The typing cadence and keypress dwell are identical for both methods.
  // Time spent moving the illustrated palm is proportional to the distance.
  function sequence(mode) {
    let elapsed = 0;
    let previous = rest();
    const steps = actions.map(event => {
      const edit = editing[event.kind];
      const key = edit ? edit[mode] : event.name;
      const target = pose(key);
      const distance = Math.hypot(target.x - previous.x, target.y - previous.y);
      const travel = distance > 90 ? 120 + distance * 1.55 : 0;
      const settle = travel && edit ? 165 : edit ? 90 : 45;
      const strike = travel + settle;
      const dwell = event.kind === "finish" ? 1500 : event.kind === "rest" ? 650 : edit ? 360 : 78;
      const step = {event, key, target, from: previous, travel, strike, start: elapsed, end: elapsed + strike + dwell};
      elapsed = step.end;
      previous = target;
      return step;
    });
    return {steps, length: elapsed};
  }
  const passes = [sequence(0), sequence(1)];

  function showText(state) {
    const lo = Math.min(state.anchor, state.cursor), hi = Math.max(state.anchor, state.cursor);
    const caret = document.createElement("span");
    caret.className = "note-caret";
    const selection = document.createElement("mark");
    selection.textContent = state.text.slice(lo, hi);
    const middle = state.cursor === lo ? [caret, selection] : [selection, caret];
    paper.replaceChildren(state.text.slice(0, lo), ...middle, state.text.slice(hi));
  }

  function lightKey(board, name, pressed) {
    board.activeKey?.element.classList.remove("pressed");
    const target = board.keys.get(name);
    board.activeKey = pressed ? target : null;
    board.strike.style.display = board.activeKey ? "" : "none";
    if (board.activeKey) {
      target.element.classList.add("pressed");
      board.strike.setAttribute("x", target.x - target.width / 2);
      board.strike.setAttribute("y", target.y - 16);
      board.strike.setAttribute("width", target.width);
      board.strike.setAttribute("height", 33);
    }
  }

  let mode = 0, time = 0, solo = false, playing = !reducedMotion.matches, finished = false;
  let visible = false, started = false, request = 0, lastTime = null, lastFrame = "";
  function statusFor(index, isEdit) {
    if (index !== mode) return index === 1 && !solo ? "Up next" : "At rest";
    if (finished) return "Finished";
    if (!playing) return "Paused";
    if (mode === 1 && isEdit) return "Left Alt held";
    return solo ? "Looping" : "Playing";
  }

  function render() {
    const pass = passes[mode];
    const step = pass.steps.find(item => time < item.end) || pass.steps[pass.steps.length - 1];
    const t = time - step.start;
    const pressed = t >= step.strike;
    const moving = t < step.travel;
    const active = boards[mode];
    const progress = Math.max(0, Math.min(1, t / (step.travel || step.strike)));
    const ease = reducedMotion.matches ? 1 : progress * progress * (3 - 2 * progress);
    paintHand(active, step.from, step.target, ease);
    const stamp = [mode, step.start, pressed, moving, solo, playing, finished].join("/");
    if (stamp === lastFrame) return;
    lastFrame = stamp;
    const other = 1 - mode;
    paintHand(boards[other], rest(), rest(), 1);
    lightKey(boards[other], "", false);
    boards[other].travel.setAttribute("d", "");
    const isEdit = Boolean(editing[step.event.kind]);
    const showPath = !mode && isEdit && step.travel > 90;
    const target = keys.get(step.key);
    active.travel.setAttribute("d", showPath ? `M${step.from.x+10} ${step.from.y+20} Q${(step.from.x+target.x)/2} ${Math.min(step.from.y,target.y)-38} ${target.x} ${target.y}` : "");
    lightKey(active, step.key, pressed);
    showText(time === 0 && (!playing || !started) ? {text: note, cursor: note.length, anchor: note.length}
                                  : pressed ? step.event.after : step.event.before);
    const modifiers = [];
    if (mode && isEdit) modifiers.push("Left Alt");
    if (step.event.kind === "select") modifiers.push("Shift");
    if (step.key) modifiers.push(step.key);
    chord.hidden = !modifiers.length;
    chord.textContent = modifiers.join(" + ");
    const keyName = {"←": "the Left Arrow key", "↑": "the Up Arrow key"}[step.key] || step.key;
    if (moving && isEdit) caption.textContent = "Reach for " + keyName + ".";
    else if (moving && step.event.kind === "type") caption.textContent = "Return to the letters.";
    else caption.textContent = step.event.instruction;
    methods.forEach((button, index) => {
      button.classList.toggle("is-active", index === mode);
      button.setAttribute("aria-pressed", String(solo && index === mode));
      if (index === mode) button.setAttribute("aria-current", "step");
      else button.removeAttribute("aria-current");
      boards[index].status.textContent = statusFor(index, isEdit);
    });
    figure.classList.toggle("solo", solo);
    compareButton.hidden = !solo;
    playButton.textContent = finished ? "Replay" : playing ? "Pause" : "Play";
  }

  function frame(now) {
    request = 0;
    if (lastTime !== null) time += now - lastTime;
    lastTime = now;
    if (time >= passes[mode].length) {
      if (solo || mode === 0) {
        if (!solo) mode = 1;
        time = 0;
      } else {
        time = passes[mode].length;
        finished = true;
        playing = false;
      }
    }
    render();
    if (playing) request = requestAnimationFrame(frame);
  }

  function sync() {
    if (request) cancelAnimationFrame(request);
    lastTime = null;
    request = playing && started && visible && !document.hidden ? requestAnimationFrame(frame) : 0;
    render();
  }
  function start(index, loop) {
    mode = index;
    started = true;
    time = 0;
    solo = loop;
    playing = true;
    finished = false;
    sync();
  }
  methods.forEach((button, index) => button.addEventListener("click", () => start(index, true)));
  compareButton.addEventListener("click", () => {
    start(0, false);
    playButton.focus();
  });
  playButton.addEventListener("click", () => {
    if (finished) start(0, false);
    else {
      started = true;
      playing = !playing;
      sync();
    }
  });
  reducedMotion.addEventListener("change", () => {
    if (reducedMotion.matches) playing = false;
    sync();
  });
  document.addEventListener("visibilitychange", sync);
  const fallback = document.querySelector(".edit-example");
  fallback.replaceWith(figure);
  figure.closest(".why").classList.add("with-demo");
  new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    const availableHeight = Math.min(entry.boundingClientRect.height, entry.rootBounds?.height || innerHeight);
    if (entry.intersectionRect.height >= availableHeight * .6) started = true;
    sync();
  }, {threshold: [0, .2, .4, .6, .8, 1]}).observe(figure);
  render();
})();
