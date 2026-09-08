import { createI18n } from 'vue-i18n';
import en from './locales/en';
import id from './locales/id';
import th from './locales/th';
import vi from './locales/vi';
import zh from './locales/zh';

export type SupportedLocale = 'zh' | 'en' | 'vi' | 'th' | 'id';

export const LOCALE_LABELS: Record<SupportedLocale, { name: string; native: string; flag: string }> = {
  zh: { name: '中文', native: '简体中文', flag: '🇨🇳' },
  en: { name: 'English', native: 'English', flag: '🇺🇸' },
  vi: { name: 'Vietnamese', native: 'Tiếng Việt', flag: '🇻🇳' },
  th: { name: 'Thai', native: 'ภาษาไทย', flag: '🇹🇭' },
  id: { name: 'Indonesian', native: 'Bahasa Indonesia', flag: '🇮🇩' },
};

const savedLocale = (localStorage.getItem('insightx_locale') as SupportedLocale) || 'zh';

export const i18n = createI18n({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: 'en',
  messages: {
    zh,
    en,
    vi,
    th,
    id,
  },
});

export const setLocale = (locale: SupportedLocale) => {
  i18n.global.locale.value = locale;
  localStorage.setItem('insightx_locale', locale);
};
