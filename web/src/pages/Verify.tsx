import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ErrorNote, Loading, useLoad } from "../components";

/** Public: an auditor or regulator holding a certificate checks it here without an account. */
export function Verify() {
  const { id = "" } = useParams();
  const result = useLoad(() => api.verify(id), [id]);
  const v = result.data;

  return (
    <div className="access verify">
      <Link to="/" className="brand-large">
        ScrapLink
      </Link>
      <h1>Certificate check</h1>
      <ErrorNote message={result.error} />
      {!v && !result.error && <Loading />}
      {v && (
        <>
          <p className={v.valid ? "verdict verdict-valid" : "verdict verdict-invalid"}>
            {v.valid ? "This certificate is genuine" : "This certificate does not match the record"}
          </p>
          <p>
            {v.valid
              ? `All ${v.event_count} recorded steps of this trade are intact and end at the seal printed on the certificate.`
              : `The trade record no longer matches what was certified: ${v.reason}. Treat the certificate as unreliable.`}
          </p>
          <dl className="facts">
            <div className="fact">
              <dt>Certificate</dt>
              <dd>
                <code>{v.certificate_id}</code>
              </dd>
            </div>
            <div className="fact">
              <dt>Seal</dt>
              <dd>
                <code className="hash">{v.head_hash}</code>
              </dd>
            </div>
            <div className="fact">
              <dt>PDF fingerprint</dt>
              <dd>
                <code className="hash">{v.pdf_sha256}</code>
              </dd>
            </div>
          </dl>
          <p className="aside">
            To confirm a PDF is the one issued, compare its SHA-256 fingerprint with the one above.
          </p>
        </>
      )}
    </div>
  );
}
