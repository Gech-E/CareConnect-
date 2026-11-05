"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight, X } from "lucide-react";

type Props = {
  busy: boolean;
  error: string;
  onSubmit: (
    email: string,
    password: string,
    register: boolean,
  ) => Promise<void>;
  onClose: () => void;
  onModeChange: () => void;
};

export function AuthDialog({
  busy,
  error,
  onSubmit,
  onClose,
  onModeChange,
}: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    const element = dialog.current;
    const previousFocus =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    element?.showModal();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      element?.close();
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, []);

  return (
    <dialog
      ref={dialog}
      className="modal"
      aria-labelledby="auth-heading"
      aria-describedby="auth-description"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <div className="modal-top">
        <span className="eyebrow">CARECONNECT</span>
        <button
          className="close"
          onClick={onClose}
          disabled={busy}
          aria-label="Close sign-in dialog"
        >
          <X />
        </button>
      </div>
      <h2 id="auth-heading" className="title">
        {register ? "Create account" : "Sign in"}
      </h2>
      <p id="auth-description" className="lead">
        {register
          ? "Book and manage your visits."
          : "Book and manage your visits."}
      </p>
      <form
        className="form"
        onSubmit={(event) => {
          event.preventDefault();
          void onSubmit(email, password, register);
        }}
      >
        <label>
          Email address
          <input
            className="field"
            type="email"
            autoComplete="email"
            required
            maxLength={254}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={busy}
          />
        </label>
        <label>
          Password
          <input
            className="field"
            type="password"
            autoComplete={register ? "new-password" : "current-password"}
            required
            minLength={register ? 12 : 1}
            maxLength={128}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={busy}
            aria-describedby={register ? "password-guidance" : undefined}
          />
        </label>
        {register && (
          <p id="password-guidance" className="sub">
            Use 12–128 characters.
          </p>
        )}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="btn" disabled={busy}>
          {busy ? "Please wait…" : register ? "Create account" : "Sign in"}
          <ArrowRight size={17} />
        </button>
      </form>
      <p className="center">
        <button
          className="link"
          disabled={busy}
          onClick={() => {
            setRegister(!register);
            setPassword("");
            onModeChange();
          }}
        >
          {register
            ? "Already have an account? Sign in"
            : "New here? Create an account"}
        </button>
      </p>
    </dialog>
  );
}
