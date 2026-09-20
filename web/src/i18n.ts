/**
 * i18n — UI string dictionary + currency formatting (Indian context).
 * Add a language by adding a column; components read t(key, lang).
 */

export type Lang = "en" | "hi" | "ta" | "bn";

export const LANGS: { code: Lang; label: string }[] = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "ta", label: "தமிழ்" },
  { code: "bn", label: "বাংলা" },
];

type Dict = Record<string, Record<Lang, string>>;

const STRINGS: Dict = {
  app_title: { en: "Plan your trip", hi: "अपनी यात्रा की योजना बनाएँ", ta: "உங்கள் பயணத்தைத் திட்டமிடுங்கள்", bn: "আপনার ভ্রমণ পরিকল্পনা করুন" },
  start_planning: { en: "Start planning", hi: "योजना शुरू करें", ta: "திட்டமிடத் தொடங்கு", bn: "পরিকল্পনা শুরু করুন" },
  app_subtitle: { en: "A day-by-day itinerary that repairs itself when plans change.", hi: "एक दिन-प्रतिदिन की योजना जो बदलाव होने पर स्वयं ठीक हो जाती है।", ta: "திட்டங்கள் மாறும்போது தானாகவே சரிசெய்யும் நாள்வாரி பயணத்திட்டம்.", bn: "পরিকল্পনা বদলালে নিজেই ঠিক হয়ে যায় এমন দিন-ভিত্তিক ভ্রমণসূচি।" },
  dates: { en: "Dates", hi: "तिथियाँ", ta: "தேதிகள்", bn: "তারিখ" },
  budget: { en: "Budget", hi: "बजट", ta: "பட்ஜெட்", bn: "বাজেট" },
  interests: { en: "Interests", hi: "रुचियाँ", ta: "ஆர்வங்கள்", bn: "আগ্রহ" },
  hotel: { en: "Hotel / base", hi: "होटल / आधार", ta: "ஹோட்டல் / தளம்", bn: "হোটেল / ঘাঁটি" },
  generate: { en: "Generate itinerary", hi: "यात्रा योजना बनाएँ", ta: "பயணத்திட்டம் உருவாக்கு", bn: "ভ্রমণসূচি তৈরি করুন" },
  generating: { en: "Generating itinerary…", hi: "योजना बनाई जा रही है…", ta: "உருவாக்கப்படுகிறது…", bn: "তৈরি হচ্ছে…" },
  new_trip: { en: "New trip", hi: "नई यात्रा", ta: "புதிய பயணம்", bn: "নতুন ভ্রমণ" },
  day: { en: "Day", hi: "दिन", ta: "நாள்", bn: "দিন" },
  suggestions: { en: "Suggestions", hi: "सुझाव", ta: "பரிந்துரைகள்", bn: "পরামর্শ" },
  budget_label: { en: "Budget", hi: "बजट", ta: "பட்ஜெட்", bn: "বাজেট" },
  confirm_change: { en: "Confirm change", hi: "बदलाव पुष्टि करें", ta: "மாற்றத்தை உறுதிப்படுத்து", bn: "পরিবর্তন নিশ্চিত করুন" },
  reject: { en: "Reject", hi: "अस्वीकार करें", ta: "நிராகரி", bn: "প্রত্যাখ্যান" },
  plan_stable: { en: "plan-stable", hi: "योजना-स्थिर", ta: "திட்ட-நிலை", bn: "পরিকল্পনা-স্থিতিশীল" },
  removed: { en: "removed", hi: "हटाया गया", ta: "நீக்கப்பட்டது", bn: "সরানো হয়েছে" },
  added: { en: "added", hi: "जोड़ा गया", ta: "சேர்க்கப்பட்டது", bn: "যোগ করা হয়েছে" },
  rescheduled: { en: "rescheduled", hi: "पुनर्निर्धारित", ta: "மறுஅட்டவணை", bn: "পুনঃনির্ধারিত" },
  ask_placeholder: { en: "Ask: what should I do tomorrow morning?", hi: "पूछें: कल सुबह मुझे क्या करना चाहिए?", ta: "கேளுங்கள்: நாளை காலை என்ன செய்யலாம்?", bn: "জিজ্ঞাসা করুন: আগামীকাল সকালে কী করব?" },
  ask: { en: "Ask", hi: "पूछें", ta: "கேள்", bn: "জিজ্ঞাসা" },
  show_amenities: { en: "Show amenities", hi: "सुविधाएँ दिखाएँ", ta: "வசதிகளைக் காட்டு", bn: "সুবিধা দেখান" },
  hide_amenities: { en: "Hide amenities", hi: "सुविधाएँ छिपाएँ", ta: "வசதிகளை மறை", bn: "সুবিধা লুকান" },
  free: { en: "free", hi: "निःशुल्क", ta: "இலவசம்", bn: "বিনামূল্যে" },
  min: { en: "min", hi: "मिनट", ta: "நிமிடம்", bn: "মিনিট" },
  view_book: { en: "view & book", hi: "देखें और बुक करें", ta: "பார்க்க & பதிவு", bn: "দেখুন ও বুক করুন" },
  q_destination: { en: "Where do you want to go?", hi: "आप कहाँ जाना चाहते हैं?", ta: "நீங்கள் எங்கே செல்ல விரும்புகிறீர்கள்?", bn: "আপনি কোথায় যেতে চান?" },
  q_dates: { en: "When are you travelling?", hi: "आप कब यात्रा कर रहे हैं?", ta: "நீங்கள் எப்போது பயணிக்கிறீர்கள்?", bn: "আপনি কখন ভ্রমণ করছেন?" },
  q_starttime: { en: "What time do you start on day one?", hi: "पहले दिन आप किस समय शुरू करेंगे?", ta: "முதல் நாள் எத்தனை மணிக்குத் தொடங்குகிறீர்கள்?", bn: "প্রথম দিনে আপনি কখন শুরু করবেন?" },
  q_starttime_hint: { en: "This shapes your meal and stay suggestions.", hi: "यह आपके भोजन और ठहरने के सुझावों को आकार देता है।", ta: "இது உங்கள் உணவு மற்றும் தங்கும் பரிந்துரைகளை வடிவமைக்கிறது.", bn: "এটি আপনার খাবার ও থাকার পরামর্শ নির্ধারণ করে।" },
  q_budget: { en: "What's your budget?", hi: "आपका बजट क्या है?", ta: "உங்கள் பட்ஜெட் என்ன?", bn: "আপনার বাজেট কত?" },
  q_interests: { en: "What are you into?", hi: "आपकी रुचि किसमें है?", ta: "உங்களுக்கு எதில் ஆர்வம்?", bn: "আপনি কীসে আগ্রহী?" },
  q_pace: { en: "What pace suits you?", hi: "आपको कौन-सी गति पसंद है?", ta: "எந்த வேகம் உங்களுக்குப் பொருந்தும்?", bn: "কোন গতি আপনার জন্য উপযুক্ত?" },
  next: { en: "Next", hi: "आगे", ta: "அடுத்து", bn: "পরবর্তী" },
  back: { en: "Back", hi: "पीछे", ta: "பின்", bn: "পিছনে" },
  relaxed: { en: "Relaxed", hi: "आराम से", ta: "நிதானம்", bn: "স্বাচ্ছন্দ্য" },
  balanced: { en: "Balanced", hi: "संतुलित", ta: "சமநிலை", bn: "সুষম" },
  packed: { en: "Packed", hi: "व्यस्त", ta: "நிரம்பிய", bn: "ঠাসা" },
  gen_1: { en: "Finding the best spots near you…", hi: "आपके पास बेहतरीन जगहें ढूँढ़ रहे हैं…", ta: "உங்கள் அருகில் சிறந்த இடங்களைத் தேடுகிறோம்…", bn: "আপনার কাছে সেরা জায়গা খুঁজছি…" },
  gen_2: { en: "Plotting your route…", hi: "आपका मार्ग बना रहे हैं…", ta: "உங்கள் வழியை வரைகிறோம்…", bn: "আপনার রুট আঁকছি…" },
  gen_3: { en: "Timing your days…", hi: "आपके दिनों का समय तय कर रहे हैं…", ta: "உங்கள் நாட்களை நேரப்படுத்துகிறோம்…", bn: "আপনার দিনগুলির সময় ঠিক করছি…" },
  gen_4: { en: "Adding meal & stay picks…", hi: "भोजन और ठहरने के सुझाव जोड़ रहे हैं…", ta: "உணவு & தங்கும் தேர்வுகளைச் சேர்க்கிறோம்…", bn: "খাবার ও থাকার পছন্দ যোগ করছি…" },
  chat_title: { en: "Trip assistant", hi: "यात्रा सहायक", ta: "பயண உதவியாளர்", bn: "ভ্রমণ সহকারী" },
  chat_placeholder: { en: "Add IIT Delhi, move the fort to day 2, or ask anything…", hi: "IIT दिल्ली जोड़ें, किला दिन 2 पर ले जाएँ, या कुछ भी पूछें…", ta: "IIT டெல்லியைச் சேர், கோட்டையை நாள் 2க்கு நகர்த்து, அல்லது கேள்…", bn: "IIT দিল্লি যোগ করুন, দুর্গ দিন ২-এ সরান, বা যেকোনো প্রশ্ন করুন…" },
  chat_greeting: { en: "Hi! Tell me to add a place, move an activity, or ask about your trip.", hi: "नमस्ते! कोई जगह जोड़ने, गतिविधि हटाने, या यात्रा के बारे में पूछने को कहें।", ta: "வணக்கம்! ஒரு இடத்தைச் சேர்க்க, நடவடிக்கையை நகர்த்த, அல்லது பயணம் பற்றி கேளுங்கள்.", bn: "হাই! একটি জায়গা যোগ করতে, কার্যক্রম সরাতে, বা ভ্রমণ সম্পর্কে জিজ্ঞাসা করুন।" },
  thinking: { en: "Thinking…", hi: "सोच रहा हूँ…", ta: "யோசிக்கிறேன்…", bn: "ভাবছি…" },
  share: { en: "Share", hi: "शेयर", ta: "பங்கிடு", bn: "শেয়ার" },
  share_copied: { en: "Link copied", hi: "लिंक कॉपी हुआ", ta: "இணைப்பு நகலெடுக்கப்பட்டது", bn: "লিংক কপি হয়েছে" },
  over_budget: { en: "over budget", hi: "बजट से अधिक", ta: "பட்ஜெட்டை மீறியது", bn: "বাজেটের বেশি" },
  sug_food: { en: "Food suggestion", hi: "भोजन सुझाव", ta: "உணவு பரிந்துரை", bn: "খাবারের পরামর্শ" },
  sug_stay: { en: "Stay suggestion", hi: "ठहरने का सुझाव", ta: "தங்கும் பரிந்துரை", bn: "থাকার পরামর্শ" },
  why_this: { en: "Why this?", hi: "यह क्यों?", ta: "ஏன் இது?", bn: "কেন এটি?" },
  to_next: { en: "to next stop", hi: "अगली जगह तक", ta: "அடுத்த இடத்திற்கு", bn: "পরের স্টপ পর্যন্ত" },
  h_unit: { en: "h", hi: "घं", ta: "மணி", bn: "ঘ" },
};

export function t(key: string, lang: Lang): string {
  const row = STRINGS[key];
  if (!row) return key;
  return row[lang] ?? row.en;
}

// Currency symbol per ISO code (INR default for the Indian context).
export function currencySymbol(code: string): string {
  return ({ INR: "₹", EUR: "€", USD: "$", GBP: "£" } as Record<string, string>)[code] ?? code + " ";
}
