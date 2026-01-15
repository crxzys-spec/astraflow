import type { ChangeEvent } from "react";
import { useTranslation } from "react-i18next";

const languages = [
  { value: "en", label: "English" },
  { value: "zh-CN", label: "简体中文" },
  { value: "ja", label: "日本語" },
  { value: "ko", label: "한국어" },
];

const normalizeLanguage = (value: string): string => {
  const lower = value.toLowerCase();
  if (lower.startsWith("zh")) {
    return "zh-CN";
  }
  if (lower.startsWith("ja")) {
    return "ja";
  }
  if (lower.startsWith("ko")) {
    return "ko";
  }
  return "en";
};

const LanguageSwitcher = () => {
  const { i18n, t } = useTranslation();
  const resolved = i18n.resolvedLanguage || i18n.language || "en";
  const current = languages.some((lang) => lang.value === resolved)
    ? resolved
    : normalizeLanguage(resolved);

  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    void i18n.changeLanguage(event.target.value);
  };

  return (
    <select
      className="lang-select"
      aria-label={t("common.language")}
      value={current}
      onChange={handleChange}
    >
      {languages.map((lang) => (
        <option key={lang.value} value={lang.value}>
          {lang.label}
        </option>
      ))}
    </select>
  );
};

export default LanguageSwitcher;
