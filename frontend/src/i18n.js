// ponytail: tiny dictionary i18n; move to react-i18next only if languages/plurals multiply
const translations = {
  en: {
    chat: "Chat",
    stats: "Stats",
    settings: "Settings",
    admin: "Admin",
    logout: "Logout",
    newChat: "+ New chat",
    creditsLeft: "credits left",
    send: "Send",
    ask: "Ask MicroManus to research something…",
    emptyTitle: "What should we investigate?",
    emptyBody:
      "Start a new chat and give MicroManus a research task. It searches the live web, reads sources, and writes a cited report you can export as a PDF.",
    downloadPdf: "Download PDF",
    deleteChat: "Delete chat",
    deleteConfirmTitle: "Delete this chat?",
    deleteConfirmText: "The conversation and its messages will be gone for good.",
    delete: "Delete",
    outOfCredits: "Out of credits",
    outOfCreditsText: "Buy 5 more credits for $5 to keep researching.",
    buyCredits: "Buy credits",
    thinking: "working through it…",
  },
  hi: {
    chat: "चैट",
    stats: "आँकड़े",
    settings: "सेटिंग्स",
    admin: "एडमिन",
    logout: "लॉग आउट",
    newChat: "+ नई चैट",
    creditsLeft: "क्रेडिट शेष",
    send: "भेजें",
    ask: "MicroManus से कुछ रिसर्च करवाएँ…",
    emptyTitle: "आज क्या खोजें?",
    emptyBody:
      "नई चैट शुरू करें और MicroManus को रिसर्च का काम दें। यह लाइव वेब खोजता है, स्रोत पढ़ता है, और PDF में निर्यात होने वाली रिपोर्ट लिखता है।",
    downloadPdf: "PDF डाउनलोड करें",
    deleteChat: "चैट हटाएँ",
    deleteConfirmTitle: "यह चैट हटाएँ?",
    deleteConfirmText: "बातचीत और उसके संदेश हमेशा के लिए हट जाएँगे।",
    delete: "हटाएँ",
    outOfCredits: "क्रेडिट खत्म",
    outOfCreditsText: "रिसर्च जारी रखने के लिए $5 में 5 क्रेडिट खरीदें।",
    buyCredits: "क्रेडिट खरीदें",
    thinking: "सोच रहा है…",
  },
};

const LANG_KEY = "micromanus_lang";

export const LANGS = { en: "English", hi: "हिन्दी" };
export const getLang = () => localStorage.getItem(LANG_KEY) || "en";
export const setLang = (lang) => {
  localStorage.setItem(LANG_KEY, lang);
  window.location.reload(); // ponytail: reload beats context plumbing for a chrome-level language switch
};
export const t = (key) => translations[getLang()]?.[key] ?? translations.en[key] ?? key;
