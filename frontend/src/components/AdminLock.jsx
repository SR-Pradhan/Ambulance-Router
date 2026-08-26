import { useState } from "react";
import { adminKey } from "../api/client";

/**
 * Unlock control for the destructive dashboard actions.
 *
 * The key is typed here and held in sessionStorage for the tab. It is never
 * compiled into the bundle, because anything in the bundle is public: the
 * deployed JavaScript can be downloaded and read by anyone.
 *
 * This component does not verify the key itself. It cannot: the browser has no
 * way to check a secret it does not hold. The server is the only thing that can
 * say whether a key is right, so an incorrect key simply produces a 401 on the
 * first admin action. Pretending to validate here would be theatre.
 */
export default function AdminLock({ unlocked, onChange }) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");

  const unlock = (e) => {
    e.preventDefault();
    const key = value.trim();
    if (!key) return;
    adminKey.set(key);
    setValue("");
    setOpen(false);
    onChange(true);
  };

  const lock = () => {
    adminKey.clear();
    onChange(false);
  };

  if (unlocked) {
    return (
      <div className="admin-lock is-unlocked">
        <span className="chip chip-good">Admin unlocked</span>
        <button type="button" className="secondary small" onClick={lock}>
          Lock
        </button>
      </div>
    );
  }

  return (
    <div className="admin-lock">
      {open ? (
        <form className="admin-lock-form" onSubmit={unlock}>
          <input
            type="password"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Admin key"
            aria-label="Admin key"
            autoFocus
          />
          <button type="submit" className="small">
            Unlock
          </button>
          <button
            type="button"
            className="secondary small"
            onClick={() => {
              setOpen(false);
              setValue("");
            }}
          >
            Cancel
          </button>
        </form>
      ) : (
        <>
          <span className="chip">Read only</span>
          <button
            type="button"
            className="secondary small"
            onClick={() => setOpen(true)}
          >
            Unlock admin
          </button>
        </>
      )}
    </div>
  );
}
