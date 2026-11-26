const tabs = [...document.querySelectorAll(".switcher a")];
const guides = tabs.map(tab => document.querySelector(tab.hash));
const switcher = document.querySelector(".switcher");
switcher.setAttribute("role", "tablist");

function selectGuide(id) {
  tabs.forEach((tab, index) => {
    const active = guides[index].id === id;
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
    guides[index].hidden = !active;
  });
}

function showAnchor() {
  const id = location.hash.slice(1);
  if (Object.hasOwn(previousLinks, id)) {
    location.replace(previousLinks[id]);
    return;
  }
  const target = document.getElementById(id);
  if (guides.includes(target)) {
    selectGuide(id);
    document.getElementById("setup").scrollIntoView();
  } else if (history.state?.platform) {
    selectGuide(history.state.platform);
  } else {
    const active = guides.find(panel => !panel.hidden);
    history.replaceState({platform: active.id}, "");
  }
}

function activateTab(tab) {
  selectGuide(tab.hash.slice(1));
  if (location.hash !== tab.hash) history.pushState({platform: tab.hash.slice(1)}, "", tab.hash);
}

tabs.forEach((tab, index) => {
  const panel = guides[index];
  tab.setAttribute("role", "tab");
  tab.setAttribute("aria-controls", panel.id);
  panel.setAttribute("role", "tabpanel");
  panel.setAttribute("aria-labelledby", tab.id);
  tab.addEventListener("click", event => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    activateTab(tab);
  });
  tab.addEventListener("keydown", event => {
    const destination = {ArrowRight: (index + 1) % tabs.length, ArrowLeft: (index + tabs.length - 1) % tabs.length,
                         Home: 0, End: tabs.length - 1}[event.key];
    if (destination === undefined) return;
    event.preventDefault();
    tabs[destination].focus();
    activateTab(tabs[destination]);
  });
});

const previousLinks = JSON.parse(document.getElementById("previous-links").textContent);
const preferredGuide = /Mac/.test(navigator.platform) ? "macos" : "linux";
selectGuide(history.state?.platform || preferredGuide);
window.addEventListener("hashchange", showAnchor);
showAnchor();

const diagram = document.querySelector(".diagram");
const svg = diagram.querySelector("svg");
const keys = JSON.parse(document.getElementById("keys").textContent);
const output = document.getElementById("key-output");
const narrow = matchMedia("(max-width: 575px)");
const originalView = svg.getAttribute("viewBox");

function resizeMap() {
  diagram.classList.toggle("mobile-map", narrow.matches);
  svg.setAttribute("viewBox", narrow.matches ? "299 62 798 320" : originalView);
  svg.style.aspectRatio = narrow.matches ? "798 / 320" : "1280 / 474";
}

function showKey(element) {
  const key = keys[element.dataset.key];
  const cap = document.createElement("kbd");
  cap.textContent = key.label;
  output.replaceChildren(cap, document.createTextNode(key.action));
  if (key.ctrl) {
    const alternate = document.createElement("span");
    alternate.className = "alt-action";
    alternate.textContent = "· Ctrl: " + key.ctrl;
    output.append(alternate);
  }
  diagram.querySelector(".touched")?.classList.remove("touched");
  element.classList.add("touched");
}

document.querySelector(".readout").hidden = false;
svg.setAttribute("role", "group");
diagram.querySelectorAll("[data-key]").forEach(element => {
  const key = keys[element.dataset.key];
  element.setAttribute("tabindex", "0");
  element.setAttribute("role", "button");
  element.setAttribute("aria-label", key.label + ", " + key.action);
  element.addEventListener("click", () => showKey(element));
  element.addEventListener("focus", () => showKey(element));
  element.addEventListener("keydown", event => {
    if (event.altKey || event.metaKey || event.ctrlKey) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      showKey(element);
      return;
    }
    const position = event.code.replace(/^Key/, "").toLowerCase().replace("quote", "apostrophe");
    if (Object.hasOwn(keys, position)) {
      event.preventDefault();
      diagram.querySelector("#key-" + position).focus();
    }
  });
});
resizeMap();
narrow.addEventListener("change", resizeMap);
