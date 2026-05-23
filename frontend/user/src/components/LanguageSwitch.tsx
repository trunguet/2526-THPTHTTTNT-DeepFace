interface LanguageSwitchProps {
  value: "vi" | "en";
  onChange: (value: "vi" | "en") => void;
}

export default function LanguageSwitch({ value, onChange }: LanguageSwitchProps) {
  return (
    <div className="segmented-control" aria-label="Language">
      <button
        className={value === "vi" ? "active" : ""}
        onClick={() => onChange("vi")}
        type="button"
      >
        VI
      </button>
      <button
        className={value === "en" ? "active" : ""}
        onClick={() => onChange("en")}
        type="button"
      >
        EN
      </button>
    </div>
  );
}
