const SunIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <circle cx="12" cy="12" r="4.2" stroke="currentColor" strokeWidth="2" />
    <path
      d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.2 5.2l1.4 1.4M17.4 17.4l1.4 1.4M18.8 5.2l-1.4 1.4M6.6 17.4l-1.4 1.4"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
    />
  </svg>
);

const MoonIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path
      d="M20 13.4A8.2 8.2 0 0 1 10.6 4a8.4 8.4 0 1 0 9.4 9.4Z"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinejoin="round"
    />
  </svg>
);

/**
 * Light and dark switcher.
 *
 * Three states, not two: "System" is the default and follows the operating
 * system, so the app matches the rest of the machine until someone expresses a
 * preference. A plain two way toggle cannot express that.
 */
export default function ThemeToggle({ theme, resolved, onChange }) {
  const options = [
    { value: null, label: "System", title: "Follow the system setting" },
    { value: "light", label: "Light", icon: <SunIcon />, title: "Always light" },
    { value: "dark", label: "Dark", icon: <MoonIcon />, title: "Always dark" },
  ];

  return (
    <div
      className="theme-toggle"
      role="group"
      aria-label={`Colour theme, currently ${resolved}`}
    >
      {options.map((o) => (
        <button
          key={o.label}
          type="button"
          className={theme === o.value ? "active" : ""}
          aria-pressed={theme === o.value}
          title={o.title}
          onClick={() => onChange(o.value)}
        >
          {o.icon}
          <span>{o.label}</span>
        </button>
      ))}
    </div>
  );
}
