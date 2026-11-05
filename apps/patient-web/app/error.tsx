"use client";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="shell layout">
      <h1>Something went wrong</h1>
      <p className="lead">
        Please try again. If you were booking an appointment, check your
        appointments before submitting another request.
      </p>
      <button className="btn" onClick={reset}>
        Try again
      </button>
    </main>
  );
}
