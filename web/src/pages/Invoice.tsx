import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ErrorNote, Loading, useLoad } from "../components";
import { day, kg, perKg, rupees } from "../format";

export function InvoicePage() {
  const { id = "" } = useParams();
  const invoice = useLoad(() => api.invoice(id), [id]);

  if (invoice.error) return <ErrorNote message={invoice.error} />;
  if (!invoice.data) return <Loading />;
  const inv = invoice.data;

  return (
    <>
      <Link to={`/lots/${id}`} className="back">
        Back to the lot
      </Link>
      <article className="invoice panel">
        <header>
          <p className="invoice-draft">
            {inv.draft ? "Draft, not yet a tax invoice" : "Issued automatically when the trade settled"}
          </p>
          <h1>Tax invoice</h1>
          <dl className="facts">
            <div className="fact">
              <dt>Number</dt>
              <dd>{inv.number}</dd>
            </div>
            <div className="fact">
              <dt>Date</dt>
              <dd>{day(inv.issued_at)}</dd>
            </div>
          </dl>
        </header>
        <dl className="facts">
          <div className="fact">
            <dt>From (supplier)</dt>
            <dd>
              {inv.supplier.name}
              <span className="invoice-gstin">{inv.supplier.gstin ? `GSTIN ${inv.supplier.gstin}` : "Not GST-registered"}</span>
            </dd>
          </div>
          <div className="fact">
            <dt>To (recipient)</dt>
            <dd>
              {inv.recipient.name}
              {inv.recipient.gstin && <span className="invoice-gstin">GSTIN {inv.recipient.gstin}</span>}
            </dd>
          </div>
        </dl>
        <table className="invoice-lines">
          <tbody>
            <tr>
              <th scope="row">
                {inv.description}
                <span className="invoice-item-detail">
                  {inv.hsn ? `HSN ${inv.hsn}, ` : ""}
                  {kg(inv.quantity_grams)} at {perKg(inv.rate_paise_per_kg)}
                </span>
              </th>
              <td>{rupees(inv.taxable_paise)}</td>
            </tr>
            {inv.taxes.map((tax) => (
              <tr key={tax.label}>
                <th scope="row">
                  {tax.label} at {tax.percent}%
                </th>
                <td>{rupees(tax.amount_paise)}</td>
              </tr>
            ))}
            <tr className="invoice-total">
              <th scope="row">Total</th>
              <td>{rupees(inv.total_paise)}</td>
            </tr>
          </tbody>
        </table>
        {inv.reverse_charge && (
          <p className="note">Tax payable on reverse charge: the seller isn't GST-registered, so the buyer pays the GST.</p>
        )}
        <p className="aside">
          The taxable value is what the seller was paid on the weighbridge weight. GST isn't collected through ScrapLink
          yet, and rates and HSN codes are still to be confirmed per material, so this invoice can't be filed for GST
          yet. Numbers run in one ScrapLink series per financial year, not in the seller's own GST series.
        </p>
        <button type="button" className="btn" onClick={() => window.print()}>
          Print
        </button>
      </article>
    </>
  );
}
