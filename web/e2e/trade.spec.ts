// The slice's definition of done, through the interface people actually use: three people on
// three phones take one lot from photo to a verified certificate.

import { expect, test, type Browser, type Page } from "@playwright/test";
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

async function person(browser: Browser): Promise<Page> {
  const context = await browser.newContext();
  return context.newPage();
}

async function shot(page: Page, name: string) {
  await page.screenshot({ path: join(SHOTS, `${name}.png`), fullPage: true });
}

async function register(page: Page, role: RegExp, fields: Record<string, string>) {
  await page.goto("/register");
  await page.getByRole("button", { name: role }).click();
  for (const [label, value] of Object.entries(fields)) {
    await page.getByLabel(label, { exact: true }).fill(value);
  }
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "We're checking your details" })).toBeVisible();
}

test("a lot goes from photo to verified certificate", async ({ browser, request }) => {
  const admin = await person(browser);
  const seller = await person(browser);
  const buyer = await person(browser);

  // Accounts: seller and buyer register, admin approves both.
  await register(seller, /I sell scrap/, {
    "Your name": "Ravi",
    "Phone number": "9811111111",
    Password: "seller-pass-1",
    "Business name": "Ravi Metal Traders",
  });
  await shot(seller, "01-awaiting-approval");
  await register(buyer, /I buy scrap/, {
    "Your name": "Joseph",
    "Phone number": "9844444444",
    Password: "buyer-pass-1",
    "Business name": "Periyar Non-Ferrous",
    GSTIN: gstin("AAAPJ5678D"),
  });

  await admin.goto("/signin");
  await admin.getByLabel("Phone number").fill("9999900000");
  await admin.getByLabel("Password").fill("e2e-admin-pass");
  await admin.getByRole("button", { name: "Sign in" }).click();
  await expect(admin.getByRole("heading", { name: "Approvals" })).toBeVisible();
  await shot(admin, "02-approvals");
  for (let i = 0; i < 2; i++) {
    await admin.getByRole("button", { name: "Approve" }).first().click();
  }
  await expect(admin.getByText("Nobody is waiting for approval.")).toBeVisible();

  // Seller: three screens from photo to listing.
  await seller.getByRole("button", { name: "Check again" }).click();
  await seller.getByRole("link", { name: "List a lot" }).click();
  await seller.locator('input[type="file"]').setInputFiles(join(FIXTURES, "lot.jpg"));
  await shot(seller, "03-photo");
  await seller.getByRole("button", { name: "Use this photo" }).click();

  await expect(seller.getByText(/this looks like/)).toBeVisible();
  await expect(seller.getByRole("radio", { name: /Copper/ })).toBeChecked();
  await seller.getByText("Minor contamination").click();
  await seller.getByLabel("Weight in kg").fill("180");
  await shot(seller, "04-details");
  await seller.getByRole("button", { name: "See the price" }).click();

  await expect(seller.getByText("₹93,636 – ₹1,14,444")).toBeVisible();
  await shot(seller, "05-price");
  await seller.getByRole("button", { name: "Start taking bids" }).click();
  await expect(seller.getByText("Taking bids").first()).toBeVisible();
  const lotUrl = seller.url();

  // Buyer: finds it in the market and bids.
  await buyer.getByRole("button", { name: "Check again" }).click();
  await expect(buyer.getByRole("heading", { name: "Market" })).toBeVisible();
  await shot(buyer, "06-market");
  await buyer.getByRole("link", { name: /Copper/ }).click();
  await buyer.getByLabel("Your price per kg (₹)").fill("587.50");
  await buyer.getByRole("button", { name: "Place bid" }).click();
  await expect(buyer.getByText("You bid ₹587.50/kg")).toBeVisible();
  await shot(buyer, "07-bid");

  // A day passes; bidding closes.
  await request.post(`${API}/__e2e__/advance`, { data: { hours: 25 } });

  // Buyer pays into escrow, books pickup, records the weighbridge reading.
  await buyer.reload();
  await expect(buyer.getByRole("heading", { name: "You won at ₹587.50/kg" })).toBeVisible();
  await buyer.getByRole("button", { name: "Pay ₹1,16,325" }).click();
  await expect(buyer.getByRole("button", { name: "Book pickup" })).toBeVisible();
  const pickup = new Date(Date.now() + 3 * 24 * 3600_000);
  const local = new Date(pickup.getTime() - pickup.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
  await buyer.getByLabel("Pickup time").fill(local);
  await buyer.getByRole("button", { name: "Book pickup" }).click();
  await expect(buyer.getByText(/Booked for/)).toBeVisible();
  await buyer.getByLabel("Net weight in kg").fill("176.4");
  await buyer.getByLabel("Photo of the weighbridge slip").setInputFiles(join(FIXTURES, "slip.jpg"));
  await shot(buyer, "08-weighbridge");
  await buyer.getByRole("button", { name: "Send reading" }).click();
  await expect(buyer.getByRole("heading", { name: "Waiting for the seller" })).toBeVisible();

  // Seller checks the reading against the slip and accepts.
  await seller.goto(lotUrl);
  await expect(seller.getByRole("heading", { name: "Check the weighbridge reading" })).toBeVisible();
  await expect(seller.getByText("₹1,03,635")).toBeVisible();
  await shot(seller, "09-check-weight");
  await seller.getByRole("button", { name: "Accept and get paid" }).click();
  await expect(seller.getByRole("heading", { name: "Trade complete" })).toBeVisible();
  await expect(seller.getByText("Paid out").first()).toBeVisible();
  await shot(seller, "10-complete");

  // Anyone can check the certificate.
  await seller.getByRole("link", { name: "Check certificate" }).click();
  await expect(seller.getByText("This certificate is genuine")).toBeVisible();
  await shot(seller, "11-verified");

  // Money landed where it should: seller paid for 176.4 kg, buyer refunded the rest.
  await seller.goto("/wallet");
  await expect(seller.getByText("₹1,03,635").first()).toBeVisible();
  await shot(seller, "12-wallet");
  await buyer.goto("/wallet");
  await expect(buyer.getByText("₹12,690").first()).toBeVisible();

  await seller.goto("/");
  await shot(seller, "13-my-lots");
});
