"""Multilingual explanation and UI message translation for BatchWatch.

Languages supported:
- English (en) - default
- Hindi (hi)   - हिन्दी
- Kannada (kn) - ಕನ್ನಡ

Rules:
1. Verdict decisions and verdict pill labels (FLAGGED, POSSIBLE, NOT IN ALERTS)
   remain deterministic code and are NEVER translated or altered by an LLM.
2. Only explanatory text and advice are translated.
3. Explanations must be strictly grounded in the cited alert row.
4. When Gemini is offline/unavailable, falls back to English with a clear notice.
5. Translations always carry a notice that they are machine-generated.
6. The original English lab finding is always preserved alongside the translation.
"""
import os
import re

from agent import llm

LANGUAGES = {
    "en": "English",
    "hi": "हिन्दी (Hindi)",
    "kn": "ಕನ್ನಡ (Kannada)",
}

# Machine-generated translation disclaimer
MACHINE_TRANSLATION_NOTE = {
    "en": "",
    "hi": "सूचना: यह व्याख्या मशीन द्वारा अनुवादित है और इसे किसी मूल वक्ता द्वारा सत्यापित किया जाना चाहिए।",
    "kn": "ಸೂಚನೆ: ಈ ವಿವರಣೆಯು ಯಂತ್ರ-ರಚಿತ ಅನುವಾದವಾಗಿದೆ ಮತ್ತು ಸ್ಥಳೀಯ ಭಾಷಿಕರಿಂದ ಪರಿಶೀಲಿಸಲ್ಪಡಬೇಕು.",
}

# Fallback notice when offline or translation fails
OFFLINE_NOTICE = {
    "en": "",
    "hi": "ऑफ़लाइन मोड: AI अनुवादक अनुपलब्ध होने के कारण विवरण अंग्रेजी में दिखाया जा रहा है।",
    "kn": "ಆಫ್‌ಲೈನ್ ಮೋಡ್: AI ಅನುವಾದಕ ಲಭ್ಯವಿಲ್ಲದ ಕಾರಣ ವಿವರಣೆಯನ್ನು ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ತೋರಿಸಲಾಗುತ್ತಿದೆ.",
}

# Card heading titles translated across languages
CARD_TITLES = {
    "en": {
        "FLAGGED": "This batch appears in a published CDSCO drug-quality alert",
        "POSSIBLE": "Possible match — please check the batch number on the pack",
        "CLEAR": "Not found in published CDSCO alerts",
        "RETAKE": "Batch number could not be read",
    },
    "hi": {
        "FLAGGED": "यह बैच प्रकाशित CDSCO दवा-गुणवत्ता अलर्ट में पाया गया है",
        "POSSIBLE": "संभावित मिलान — कृपया दवा पैक पर बैच नंबर की जांच करें",
        "CLEAR": "प्रकाशित CDSCO अलर्ट में नहीं मिला",
        "RETAKE": "बैच नंबर पढ़ा नहीं जा सका",
    },
    "kn": {
        "FLAGGED": "ಈ ಬ್ಯಾಚ್ ಪ್ರಕಟಿತ CDSCO ಔಷಧಿ-ಗುಣಮಟ್ಟದ ಎಚ್ಚರಿಕೆಯಲ್ಲಿ ಕಂಡುಬಂದಿದೆ",
        "POSSIBLE": "ಸಂಭವನೀಯ ಹೊಂದಾಣಿಕೆ — ದಯವಿಟ್ಟು ಪ್ಯಾಕ್‌ನಲ್ಲಿರುವ ಬ್ಯಾಚ್ ಸಂಖ್ಯೆಯನ್ನು ಪರಿಶೀಲಿಸಿ",
        "CLEAR": "ಪ್ರಕಟಿತ CDSCO ಎಚ್ಚರಿಕೆಗಳಲ್ಲಿ ಕಂಡುಬಂದಿಲ್ಲ",
        "RETAKE": "ಬ್ಯಾಚ್ ಸಂಖ್ಯೆಯನ್ನು ಓದಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ",
    },
}

# Curated UI explanatory messages per verdict (deterministic, safe)
VERDICT_EXPLANATIONS = {
    "en": {
        "FLAGGED": "This batch matches a published CDSCO drug-quality alert. Do not dispense or use — quarantine the batch and check with a pharmacist or doctor.",
        "POSSIBLE": "Close match to a published alert — OCR uncertainty or batch found on a different product. Please physically check the batch number on the pack before any action.",
        "CLEAR": "No published CDSCO alert lists this batch. This is not a certificate of quality: only sampled batches are tested.",
        "RETAKE": "Batch number could not be read clearly. Please retake the photo in good, even light with the batch area in focus.",
        "advice": "Please speak to your pharmacist or doctor before taking more of this medicine. Don't change or stop any prescribed treatment on your own.",
        "clear_details": "No published alert lists this batch. We'll re-check automatically when new alerts are published.",
    },
    "hi": {
        "FLAGGED": "यह बैच प्रकाशित CDSCO दवा-गुणवत्ता अलर्ट से मेल खाता है। इसे वितरित या उपयोग न करें — बैच को अलग (क्वारंटीन) करें और फार्मासिस्ट या डॉक्टर से संपर्क करें।",
        "POSSIBLE": "प्रकाशित अलर्ट से संभावित मिलान — OCR अनिश्चितता या किसी अन्य उत्पाद पर पाया गया बैच। कोई भी कार्रवाई करने से पहले कृपया पैक पर बैच नंबर की जांच करें।",
        "CLEAR": "प्रकाशित CDSCO अलर्ट में यह बैच नहीं मिला। यह गुणवत्ता का प्रमाण पत्र नहीं है: केवल परीक्षण किए गए नमूनों की जांच की जाती है।",
        "RETAKE": "बैच नंबर स्पष्ट रूप से नहीं पढ़ा जा सका। कृपया अच्छी रोशनी में बैच क्षेत्र पर ध्यान केंद्रित करते हुए दोबारा फोटो लें।",
        "advice": "इस दवा को आगे लेने से पहले कृपया अपने फार्मासिस्ट या डॉक्टर से सलाह लें। अपने आप किसी भी निर्धारित उपचार को न बदलें और न ही रोकें।",
        "clear_details": "प्रकाशित अलर्ट में यह बैच नहीं मिला। जब नए अलर्ट प्रकाशित होंगे तो हम स्वचालित रूप से पुनः जांच करेंगे।",
    },
    "kn": {
        "FLAGGED": "ಈ ಬ್ಯಾಚ್ ಪ್ರಕಟಿತ CDSCO ಔಷಧಿ ಗುಣಮಟ್ಟದ ಎಚ್ಚರಿಕೆಗೆ ಹೊಂದಿಕೆಯಾಗುತ್ತದೆ. ಇದನ್ನು ನೀಡಬೇಡಿ ಅಥವಾ ಬಳಸಬೇಡಿ — ಬ್ಯಾಚ್ ಅನ್ನು ಪ್ರತ್ಯೇಕಿಸಿ (ಕ್ವಾರಂಟೈನ್ ಮಾಡಿ) ಮತ್ತು ಔಷಧಿಕಾರರು ಅಥವಾ ವೈದ್ಯರನ್ನು ಸಂಪರ್ಕಿಸಿ.",
        "POSSIBLE": "ಪ್ರಕಟಿತ ಎಚ್ಚರಿಕೆಗೆ ಸಂಭವನೀಯ ಹೊಂದಾಣಿಕೆ — OCR ಅನಿಶ್ಚಿತತೆ ಅಥವಾ ಬೇರೆ ಉತ್ಪನ್ನದಲ್ಲಿ ಕಂಡುಬಂದ ಬ್ಯಾಚ್. ಯಾವುದೇ ಕ್ರಮ ಕೈಗೊಳ್ಳುವ ಮೊದಲು ಪ್ಯಾಕ್‌ನಲ್ಲಿರುವ ಬ್ಯಾಚ್ ಸಂಖ್ಯೆಯನ್ನು ಪರಿಶೀಲಿಸಿ.",
        "CLEAR": "ಪ್ರಕಟಿತ CDSCO ಎಚ್ಚರಿಕೆಗಳಲ್ಲಿ ಈ ಬ್ಯಾಚ್ ಕಂಡುಬಂದಿಲ್ಲ. ಇದು ಗುಣಮಟ್ಟದ ಪ್ರಮಾಣಪತ್ರವಲ್ಲ: ಮಾದರಿ ಮಾಡಿದ ಬ್ಯಾಚ್‌ಗಳನ್ನು ಮಾತ್ರ ಪರೀಕ್ಷಿಸಲಾಗುತ್ತದೆ.",
        "RETAKE": "ಬ್ಯಾಚ್ ಸಂಖ್ಯೆಯನ್ನು ಸ್ಪಷ್ಟವಾಗಿ ಓದಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಉತ್ತಮ ಬೆಳಕಿನಲ್ಲಿ ಬ್ಯಾಚ್ ಭಾಗವನ್ನು ಕೇಂದ್ರೀಕರಿಸಿ ಮತ್ತೊಮ್ಮೆ ಫೋಟೋ ತೆಗೆದುಕೊಳ್ಳಿ.",
        "advice": "ಈ ಔಷಧಿಯನ್ನು ತೆಗೆದುಕೊಳ್ಳುವ ಮೊದಲು ದಯವಿಟ್ಟು ನಿಮ್ಮ ಔಷಧಿಕಾರರು ಅಥವಾ ವೈದ್ಯರೊಂದಿಗೆ ಮಾತನಾಡಿ. ನಿಮ್ಮ ಸ್ವಂತ ನಿರ್ಧಾರದಿಂದ ಯಾವುದೇ ಚಿಕಿತ್ಸೆಯನ್ನು ಬದಲಾಯಿಸಬೇಡಿ ಅಥವಾ ನಿಲ್ಲಿಸಬೇಡಿ.",
        "clear_details": "ಪ್ರಕಟಿತ ಎಚ್ಚರಿಕೆಗಳಲ್ಲಿ ಈ ಬ್ಯಾಚ್ ಕಂಡುಬಂದಿಲ್ಲ. ಹೊಸ ಎಚ್ಚರಿಕೆಗಳು ಪ್ರಕಟವಾದಾಗ ನಾವು ಸ್ವಯಂಚಾಲಿತವಾಗಿ ಮರುಪರಿಶೀಲಿಸುತ್ತೇವೆ.",
    },
}

# Localized UI chrome strings for Household Scan workflow
UI_STRINGS = {
    "en": {
        "scan_title": "Scan a medicine",
        "scan_caption": "Photograph the side of the strip or carton that shows the batch number (B.No.). Only the photo is sent to the AI, never your name, and it is discarded after reading.",
        "tab_camera": "📷 Camera",
        "tab_upload": "⬆️ Upload photo",
        "tab_demo": "🧪 Demo labels",
        "step_confirm_title": "Step 1 · Confirm what the AI read",
        "btn_confirm": "Confirm and check",
        "btn_retake": "Retake photo",
        "cabinet_title": "My medicine cabinet",
        "cabinet_empty": "Nothing saved yet. Scan a medicine above to add it to your cabinet.",
        "scan_another": "Scan another medicine",
    },
    "hi": {
        "scan_title": "दवा स्कैन करें",
        "scan_caption": "दवा की स्ट्रिप या डिब्बे के उस हिस्से की तस्वीर लें जहां बैच नंबर (B.No.) लिखा है। केवल फोटो AI को भेजी जाती है, आपका नाम कभी नहीं, और पढ़ने के तुरंत बाद इसे हटा दिया जाता है।",
        "tab_camera": "📷 कैमरा",
        "tab_upload": "⬆️ फोटो अपलोड करें",
        "tab_demo": "🧪 डेमो लेबल",
        "step_confirm_title": "चरण 1 · AI द्वारा पढ़े गए विवरण की पुष्टि करें",
        "btn_confirm": "पुष्टि करें और जांचें",
        "btn_retake": "दोबारा फोटो लें",
        "cabinet_title": "मेरी दवा अलमारी (कैबिनेट)",
        "cabinet_empty": "अभी तक कोई दवा सुरक्षित नहीं है। अपने कैबिनेट में जोड़ने के लिए ऊपर दवा स्कैन करें।",
        "scan_another": "दूसरी दवा स्कैन करें",
    },
    "kn": {
        "scan_title": "ಔಷಧಿ ಸ್ಕ್ಯಾನ್ ಮಾಡಿ",
        "scan_caption": "ಬ್ಯಾಚ್ ಸಂಖ್ಯೆ (B.No.) ಇರುವ ಸ್ಟ್ರಿಪ್ ಅಥವಾ ಪ್ಯಾಕ್‌ನ ಭಾಗದ ಫೋಟೋ ತೆಗೆದುಕೊಳ್ಳಿ. ಕೇವಲ ಫೋಟೋ ಮಾತ್ರ AI ಗೆ ಕಳುಹಿಸಲಾಗುತ್ತದೆ ಮತ್ತು ತಕ್ಷಣವೇ ಅಳಿಸಲಾಗುತ್ತದೆ.",
        "tab_camera": "📷 ಕ್ಯಾಮೆರಾ",
        "tab_upload": "⬆️ ಫೋಟೋ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ",
        "tab_demo": "🧪 ಡೆಮೊ ಲೇಬಲ್‌ಗಳು",
        "step_confirm_title": "ಹಂತ 1 · AI ಓದಿದ ವಿವರಗಳನ್ನು ದೃಢೀಕರಿಸಿ",
        "btn_confirm": "ದೃಢೀಕರಿಸಿ ಮತ್ತು ಪರಿಶೀಲಿಸಿ",
        "btn_retake": "ಮತ್ತೊಮ್ಮೆ ಫೋಟೋ ತೆಗೆದುಕೊಳ್ಳಿ",
        "cabinet_title": "ನನ್ನ ಔಷಧಿ ಪೆಟ್ಟಿಗೆ (ಕ್ಯಾಬಿನೆಟ್)",
        "cabinet_empty": "ಇನ್ನೂ ಏನೂ ಉಳಿಸಲಾಗಿಲ್ಲ. ನಿಮ್ಮ ಕ್ಯಾಬಿನೆಟ್‌ಗೆ ಸೇರಿಸಲು ಮೇಲೆ ಔಷಧಿಯನ್ನು ಸ್ಕ್ಯಾನ್ ಮಾಡಿ.",
        "scan_another": "ಮತ್ತೊಂದು ಔಷಧಿಯನ್ನು ಸ್ಕ್ಯಾನ್ ಮಾಡಿ",
    },
}

_BANNED = re.compile(r"\b(stop taking|safe to (take|use)|dose|dosage|you should take|discontinue)\b", re.I)


def get_card_title(verdict: str, lang: str = "en") -> str:
    """Return the localized card title for the given verdict."""
    lang_dict = CARD_TITLES.get(lang, CARD_TITLES["en"])
    return lang_dict.get(verdict, CARD_TITLES["en"].get(verdict, verdict))


def get_ui_string(key: str, lang: str = "en") -> str:
    """Return a localized UI string for the household flow."""
    lang_dict = UI_STRINGS.get(lang, UI_STRINGS["en"])
    return lang_dict.get(key, UI_STRINGS["en"].get(key, key))


def get_verdict_summary(verdict: str, lang: str = "en") -> str:
    """Return the one-line plain explanation under each verdict in the target language."""
    lang_dict = VERDICT_EXPLANATIONS.get(lang, VERDICT_EXPLANATIONS["en"])
    return lang_dict.get(verdict, VERDICT_EXPLANATIONS["en"].get(verdict, ""))


def get_clear_details(lang: str = "en") -> str:
    """Return the clear/not-found explanation details."""
    lang_dict = VERDICT_EXPLANATIONS.get(lang, VERDICT_EXPLANATIONS["en"])
    return lang_dict.get("clear_details", VERDICT_EXPLANATIONS["en"]["clear_details"])


def translate_explanation(row: dict, en_explanation: dict, lang: str = "en") -> dict:
    """Translate an alert explanation to Hindi or Kannada.

    If lang == "en", returns the English explanation directly.
    If Gemini is available, generates a patient-friendly explanation in the target
    language grounded strictly in the row facts.
    If Gemini is offline/unavailable, falls back to English with an explanatory notice.
    """
    if not lang or lang == "en":
        return {
            "text": en_explanation.get("text", ""),
            "advice": en_explanation.get("advice", VERDICT_EXPLANATIONS["en"]["advice"]),
            "lang": "en",
            "source": en_explanation.get("source", "english"),
            "fallback": False,
            "notice": "",
            "disclaimer": "",
        }

    lang_name = "Hindi (हिन्दी)" if lang == "hi" else "Kannada (ಕನ್ನಡ)" if lang == "kn" else lang
    disclaimer = MACHINE_TRANSLATION_NOTE.get(lang, MACHINE_TRANSLATION_NOTE["hi"])
    curated_advice = VERDICT_EXPLANATIONS.get(lang, {}).get("advice", VERDICT_EXPLANATIONS["en"]["advice"])

    if llm.mode() == "gemini":
        prompt = f"""Explain this official Indian CDSCO drug-quality alert to a patient in {lang_name} in 2-3 short, calm sentences.
Use ONLY the facts below. Do not add facts, do not give medical advice, do not say whether to stop or continue the medicine, do not mention dose.
Say what failed and what that means in everyday words in {lang_name}.

Product: {row.get('product')}
Batch: {row.get('batch')}
Alert month: {row.get('alert_month')} ({row.get('list_type')} list)
Tested by: {row.get('tested_by')}
Reason recorded by the lab: {row.get('failure_reason')}
Remarks: {row.get('remarks') or '-'}"""
        try:
            text = llm._gemini_text(prompt)
            if text and not _BANNED.search(text):
                return {
                    "text": text,
                    "advice": curated_advice,
                    "lang": lang,
                    "source": f"gemini ({llm.MODEL}) translated to {lang}",
                    "fallback": False,
                    "notice": "",
                    "disclaimer": disclaimer,
                }
        except Exception:
            pass

    # Fallback to English when Gemini is unavailable or fails
    notice = OFFLINE_NOTICE.get(lang, "[Translation unavailable. Showing English.]")
    return {
        "text": en_explanation.get("text", ""),
        "advice": en_explanation.get("advice", VERDICT_EXPLANATIONS["en"]["advice"]),
        "lang": "en",
        "source": "fallback (english)",
        "fallback": True,
        "notice": notice,
        "disclaimer": disclaimer,
    }
