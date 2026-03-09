export type UiLang = 'en' | 'sw' | 'sheng';

type TranslationKey =
  | 'dashboardTitle'
  | 'dashboardSubtitle'
  | 'riskDistribution'
  | 'topKeywords'
  | 'toxicityTrends'
  | 'hourlyPatterns'
  | 'countyRiskAnalysis'
  | 'totalReports'
  | 'highRisk'
  | 'mediumRisk'
  | 'lowRisk'
  | 'textToVerify'
  | 'countyOptional'
  | 'verifyChecking'
  | 'verifyButton'
  | 'riskLevel'
  | 'swahili'
  | 'sheng'
  | 'prebunkingTip'
  | 'explanation';

type TranslationDict = Record<TranslationKey, string>;

type TranslationMap = Record<UiLang, TranslationDict>;

export const translations: TranslationMap = {
  en: {
    dashboardTitle: 'Political risk intelligence dashboard',
    dashboardSubtitle:
      'Monitor harmful and high-risk political content and narratives across Kenyan online spaces in near real-time.',
    riskDistribution: 'Risk distribution',
    topKeywords: 'Top keywords',
    toxicityTrends: 'Toxicity trends',
    hourlyPatterns: 'Hourly patterns',
    countyRiskAnalysis: 'County risk analysis',
    totalReports: 'Total reports',
    highRisk: 'High-risk reports',
    mediumRisk: 'Medium-risk reports',
    lowRisk: 'Low-risk reports',
    textToVerify: 'Text to verify',
    countyOptional: 'County (optional)',
    verifyChecking: 'Checking...',
    verifyButton: 'Verify text',
    riskLevel: 'Risk level',
    swahili: 'Swahili explanation',
    sheng: 'Sheng explanation',
    prebunkingTip: 'Prebunking tip',
    explanation: 'Why this content was flagged',
  },
  sw: {
    dashboardTitle: 'Dashibodi ya taarifa za hatari kisiasa',
    dashboardSubtitle:
      'Fuatilia maudhui hatarishi na hoja zenye hatari za kisiasa katika majukwaa ya mtandaoni nchini Kenya karibu na wakati halisi.',
    riskDistribution: 'Usambazaji wa hatari',
    topKeywords: 'Maneno muhimu yanayotumika sana',
    toxicityTrends: 'Mwenendo wa ukatili wa lugha',
    hourlyPatterns: 'Mwenendo kwa saa',
    countyRiskAnalysis: 'Uchambuzi wa hatari kwa kaunti',
    totalReports: 'Jumla ya taarifa',
    highRisk: 'Taarifa za hatari kubwa',
    mediumRisk: 'Taarifa za hatari ya kati',
    lowRisk: 'Taarifa za hatari ndogo',
    textToVerify: 'Maandishi ya kuhakiki',
    countyOptional: 'Kaunti (hiari)',
    verifyChecking: 'Inakaguliwa...',
    verifyButton: 'Hakikisha maandishi',
    riskLevel: 'Kiwango cha hatari',
    swahili: 'Maelezo kwa Kiswahili',
    sheng: 'Maelezo kwa Sheng',
    prebunkingTip: 'Ujumbe wa kukinga upotoshaji',
    explanation: 'Sababu ya taarifa hii kutiwa alama',
  },
  sheng: {
    dashboardTitle: 'Political risk dashboard',
    dashboardSubtitle:
      'Cheki mabonga na content za siasa zenye zinaweza kuiweka nchi kwa risk online.',
    riskDistribution: 'Viwango vya risk',
    topKeywords: 'Maneno zenye zinarudi sana',
    toxicityTrends: 'Toxicity imekuwa aje',
    hourlyPatterns: 'Vile story huspread kwa masaa',
    countyRiskAnalysis: 'Risk kwa kila county',
    totalReports: 'Reports zote',
    highRisk: 'Mabwacha noma sana',
    mediumRisk: 'Mabwacha za katikati',
    lowRisk: 'Mabwacha soft',
    textToVerify: 'Text unataka kucheck',
    countyOptional: 'County (si lazima)',
    verifyChecking: 'Ina-checkiwa...',
    verifyButton: 'Cheki hii text',
    riskLevel: 'Level ya risk',
    swahili: 'Maelezo kwa Kiswahili',
    sheng: 'Maelezo kwa Sheng',
    prebunkingTip: 'Tip ya kukaa safe na news',
    explanation: 'Kwanini hii imeflaggiwa',
  },
};

