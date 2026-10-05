"use strict";
const textElements = [...document.querySelectorAll("[data-i18n]")];
const ariaElements = [...document.querySelectorAll("[data-i18n-aria]")];
const englishText = Object.fromEntries(textElements.map(element => [element.dataset.i18n, element.textContent]));
const englishAria = Object.fromEntries(ariaElements.map(element => [element.dataset.i18nAria, element.getAttribute("aria-label")]));
const englishDescription = document.querySelector('meta[name="description"]').content;
const languageButtons = [...document.querySelectorAll("[data-language]")];

Promise.all(["data/paper-assets.json?v=7", "data/translations.zh.json?v=2"].map(url => fetch(url).then(response => {
  if (!response.ok) throw new Error("Page content unavailable");
  return response.json();
}))).then(([{items}, chinese]) => {
  function caption(item, language) {
    const english = (item.display_caption || item.caption.split(". ")[0]).replace(/\.$/, "");
    if (language === "zh") return `${item.kind === "figure" ? "图" : "表"} ${item.number} · ${chinese.captions[item.label] || english}`;
    return `${item.kind === "figure" ? "Fig." : "Table"} ${item.number}. ${english}.`;
  }
  function setLanguage(language) {
    const isChinese = language === "zh";
    document.documentElement.lang = isChinese ? "zh-CN" : "en";
    for (const element of textElements) element.textContent = isChinese ? chinese.text[element.dataset.i18n] : englishText[element.dataset.i18n];
    for (const element of ariaElements) element.setAttribute("aria-label", isChinese ? chinese.aria[element.dataset.i18nAria] : englishAria[element.dataset.i18nAria]);
    document.querySelector('meta[name="description"]').content = isChinese ? `HarnessSecurity-Bench：${chinese.text.heroDescription}` : englishDescription;
    languageButtons.forEach(button => button.setAttribute("aria-pressed", String(button.dataset.language === language)));
    for (const figure of document.querySelectorAll("[data-paper]")) {
      const item = items.find(record => record.label === figure.dataset.paper);
      if (!item) continue;
      const title = caption(item, language);
      figure.querySelector("figcaption span").textContent = title;
      figure.querySelector("img").alt = title;
    }
    const resources = document.getElementById("paper-resources");
    resources.replaceChildren();
    for (const item of items) {
      const row = document.createElement("p");
      const link = document.createElement("a");
      link.href = item.url;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = caption(item, language) + " ↗";
      row.append(link);
      resources.append(row);
    }
    try { localStorage.setItem("hsb-language", language); } catch { /* Switching also works when storage is unavailable. */ }
  }
  for (const figure of document.querySelectorAll("[data-paper]")) {
    const item = items.find(record => record.label === figure.dataset.paper);
    if (!item) continue;
    const illustration = figure.querySelector("img");
    const [, , width, height] = item.preview_viewbox.split(/\s+/).map(Number);
    illustration.width = Math.round(width);
    illustration.height = Math.round(height);
    figure.querySelector("figcaption a").href = item.url;
  }
  languageButtons.forEach(button => {
    button.disabled = false;
    button.addEventListener("click", () => setLanguage(button.dataset.language));
  });
  let language = "en";
  try { if (localStorage.getItem("hsb-language") === "zh") language = "zh"; } catch { /* Use English when storage is unavailable. */ }
  setLanguage(language);
}).catch(() => { /* English text, illustrations, and PDF links remain available. */ });
