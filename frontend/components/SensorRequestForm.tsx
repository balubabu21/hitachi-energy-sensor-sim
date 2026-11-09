"use client";

import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import type { SensorSpec } from "@/lib/types";

export function SensorRequestForm({
  productId,
  productName,
  sensor,
}: {
  productId: string;
  productName: string;
  sensor: SensorSpec;
}) {
  const [submitterName, setSubmitterName] = useState("");
  const [submitterEmail, setSubmitterEmail] = useState("");
  const [approverEmail, setApproverEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSent(false);
    setSending(true);
    try {
      await api.submitSensorRequest({
        product_id: productId,
        product_name: productName,
        sensor,
        submitter_name: submitterName.trim(),
        submitter_email: submitterEmail.trim(),
        approver_email: approverEmail.trim(),
      });
      setSent(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSending(false);
    }
  }

  return (
    <form className="field-editor-form" onSubmit={submit}>
      <h4>Request permanent addition</h4>
      <p className="hint">
        This sends the sensor definition, product, and your contact details to the review mailbox. The approver
        must use a @hitachienergy.com address. Each backend instance allows up to three requests per submitter
        email per hour.
      </p>
      <div className="field-editor-grid">
        <label>
          Your name
          <input required maxLength={120} value={submitterName}
            onChange={(event) => setSubmitterName(event.target.value)} />
        </label>
        <label>
          Your email
          <input required type="email" maxLength={254} value={submitterEmail}
            onChange={(event) => setSubmitterEmail(event.target.value)} />
        </label>
        <label>
          Hitachi Energy approver email
          <input required type="email" maxLength={254} pattern="[^@\s]+@hitachienergy\.com"
            title="Use an email address ending in @hitachienergy.com"
            value={approverEmail} onChange={(event) => setApproverEmail(event.target.value)} />
        </label>
      </div>
      {error && <p className="error" role="alert">Request could not be sent: {error}</p>}
      {sent && <p className="success" role="status">Request sent for review.</p>}
      <button className="btn primary" type="submit" disabled={sending}>
        {sending ? "Sending request…" : "Send review request"}
      </button>
    </form>
  );
}
