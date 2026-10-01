// A winner who can't go ahead: declining passes the lot to the runner-up, and a runner-up who
// doesn't pay in time lets it lapse to unsold. Setup goes through the API; the people who have
// to understand what happened use the interface.

import { expect, test, type APIRequestContext, type Browser, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const API = "http://localhost:8010";
const FIXTURES = join(import.meta.dirname, "fixtures");
const SHOTS = join(import.meta.dirname, "..", "test-results", "screens");

const CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
function gstin(pan: string): string {
  const base = `32${pan}1Z`;
  let total = 0;
  [...base].forEach((ch, i) => {
    const product = CHARS.indexOf(ch) * (i % 2 === 0 ? 1 : 2);
    total += Math.floor(product / 36) + (product % 36);
  });
  return base + CHARS[(36 - (total % 36)) % 36];
}

async function token(request: APIRequestContext, phone: string, password: string): Promise<string> {
  const response = await request.post(`${API}/auth/login`, { data: { phone, password } });
  expect(response.ok()).toBeTruthy();
  return (await response.json()).access_token;
}

async function approvedUser(request: APIRequestContext, admin: string, body: Record<string, string>) {
  const response = await request.post(`${API}/auth/register`, { data: { password: "deadline-pass-1", ...body } });
  expect(response.ok(), await response.text()).toBeTruthy();
  const user = await response.json();
  const auth = { Authorization: `Bearer ${admin}` };
  await request.post(`${API}/admin/users/${user.id}/kyc`, { headers: auth, data: { decision: "approve" } });
  return { Authorization: `Bearer ${await token(request, body.phone, "deadline-pass-1")}` };
}

async function signedIn(browser: Browser, phone: string): Promise<Page> {
  const page = await (await browser.newContext()).newPage();
  await page.goto("/signin");
  await page.getByLabel("Phone number").fill(phone);
  await page.getByLabel("Password", { exact: true }).fill("deadline-pass-1");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: /^Hello,/ })).toBeVisible();
  return page;
}

test("a declined win passes to the runner-up, and an unpaid one lapses", async ({ browser, request }) => {
  // Seller lists brass; two recyclers bid; bidding closes.
  const admin = await token(request, "9999900000", "e2e-admin-pass");
  const seller = await approvedUser(request, admin, {
    phone: "9811122222", name: "Lakshmi", role: "seller", business_name: "Lakshmi Scrap Yard",
  });
  const first = await approvedUser(request, admin, {
    phone: "9844455555", name: "Arun", role: "buyer", business_name: "Arun Alloys", gstin: gstin("AAAPA4321K"),
  });
  const second = await approvedUser(request, admin, {
    phone: "9844466666", name: "Fatima", role: "buyer", business_name: "Fatima Metals", gstin: gstin("AAAPF8765L"),
  });

  const created = await request.post(`${API}/lots`, {
    headers: seller,
    multipart: {
      photo: { name: "lot.jpg", mimeType: "image/jpeg", buffer: readFileSync(join(FIXTURES, "lot.jpg")) },
    },
  });
  const lotId = (await created.json()).id;
  await request.post(`${API}/lots/${lotId}/confirm`, {
    headers: seller,
    data: { material_code: "brass", grade: "A", declared_weight_grams: 120_000 },
  });
  await request.post(`${API}/lots/${lotId}/list`, { headers: seller, data: { auction_hours: 1 } });
  await request.post(`${API}/lots/${lotId}/bids`, { headers: first, data: { rate_paise_per_kg: 47_000 } });
  await request.post(`${API}/lots/${lotId}/bids`, { headers: second, data: { rate_paise_per_kg: 46_000 } });
  await request.post(`${API}/__e2e__/advance`, { data: { hours: 2 } });

  // Arun won, sees the deadline, and declines.
  const arun = await signedIn(browser, "9844455555");
  await arun.getByRole("region", { name: "Needs you" }).getByRole("link", { name: "Pay now" }).click();
  await expect(arun.getByRole("heading", { name: "You won at ₹470/kg" })).toBeVisible();
  await expect(arun.getByText(/^Pay by .+ After that the lot goes to the next highest bidder\.$/)).toBeVisible();
  await arun.screenshot({ path: join(SHOTS, "deadline-01-winner.png"), fullPage: true });
  await arun.getByRole("button", { name: "I can't buy this lot" }).click();
  await arun.getByRole("button", { name: "Yes, I can't buy it" }).click();
  await expect(arun.getByRole("heading", { name: "You didn't buy this lot" })).toBeVisible();
  await arun.screenshot({ path: join(SHOTS, "deadline-02-declined.png"), fullPage: true });

  // Fatima, the runner-up, now holds it at her own price.
  const fatima = await signedIn(browser, "9844466666");
  await fatima.getByRole("region", { name: "Needs you" }).getByRole("link", { name: "Pay now" }).click();
  await expect(fatima.getByRole("heading", { name: "You won at ₹460/kg" })).toBeVisible();

  // The seller is told who has it now, and by when they must pay.
  const lakshmi = await signedIn(browser, "9811122222");
  await lakshmi.goto(`/lots/${lotId}`);
  await expect(lakshmi.getByRole("heading", { name: "Sold to Fatima Metals" })).toBeVisible();
  await expect(lakshmi.getByText(/They have until .+ to pay/)).toBeVisible();
  await expect(lakshmi.getByText("Winning buyer declined. Passed to the next bidder")).toBeVisible();
  await lakshmi.screenshot({ path: join(SHOTS, "deadline-03-seller.png"), fullPage: true });

  // Fatima doesn't pay within 24 hours: nobody is left, so the lot ends unsold.
  await request.post(`${API}/__e2e__/advance`, { data: { hours: 24 } });
  await fatima.reload();
  await expect(fatima.getByRole("heading", { name: "You didn't buy this lot" })).toBeVisible();
  await lakshmi.reload();
  await expect(lakshmi.getByText("Winning buyer didn't pay in time. Not sold")).toBeVisible();
  await expect(lakshmi.getByText(/^Not sold\. Either no bid reached/)).toBeVisible();
  await lakshmi.screenshot({ path: join(SHOTS, "deadline-04-unsold.png"), fullPage: true });
});
