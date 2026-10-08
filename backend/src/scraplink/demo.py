"""Demo dataset: three weeks of believable trading, so every screen has something to show.

    python -m scraplink.cli seed-demo

Every trade goes through the same service functions as real use (lots.py, rfqs.py,
agreements.py, ...), driven by a clock that starts three weeks ago and moves forward. Custody
records, the ledger and certificates are therefore genuine, and they verify.

Demo photos are drawn, stamped "DEMO PHOTO", and stored under demo/ in media. The training
export skips that prefix, so they can never teach the ML model anything.

Adds to whatever is already in the database, and refuses to run a second time. Where a
material's reference price only starts after the demo history does (a freshly seeded catalogue),
its earliest price is back-dated to cover it.
"""

import io
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import agreements, anchoring, compliance, lots, repricing, rfqs
from .classification import NullClassifier
from .config import Settings
from .env import Env
from .kyc import gstin_check_char
from .models import (
    JobRun,
    KycStatus,
    Lot,
    Material,
    RateSource,
    ReferenceRate,
    Transporter,
    User,
)
from .payments import SimulatedGateway
from .routing import IST
from .security import hash_password
from .storage import Storage

DEMO_PASSWORD = "demo-pass-123"
# Where each demo business is (places.PLACES), which also places its lots.
PLACE_OF = {
    "ravi": "kochi",
    "anil": "thrissur",
    "fathima": "kochi",
    "joseph": "kochi",
    "arjun": "bengaluru",
    "priya": "alappuzha",
    "suresh": "kozhikode",
    "meera": "kottayam",
}
DEMO_PREFIX = "demo"


class DemoAlreadyLoaded(Exception):
    pass


# --- people ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Person:
    key: str
    phone: str
    name: str
    role: str
    business: str
    pan: str
    state: str | None  # GST state code; None means not GST-registered
    authorisations: tuple[str, ...] = ()
    approved: bool = True

    @property
    def gstin(self) -> str | None:
        if self.state is None:
            return None
        base = f"{self.state}{self.pan}1Z"
        return base + gstin_check_char(base)


PEOPLE = [
    Person("ravi", "9000000001", "Ravi Kumar", "seller", "Ravi Metal Traders", "AAAPR4417K", "32"),
    Person("anil", "9000000002", "Anil Varghese", "seller", "Anil Scrap Yard", "AAAPV2290D", None),
    Person(
        "fathima", "9000000003", "Fathima Beevi", "seller", "Kochi E-Salvage", "AAAPB7310F", "32"
    ),
    Person(
        "joseph",
        "9000000011",
        "Joseph Mathew",
        "buyer",
        "Malabar Recycling Pvt Ltd",
        "AAACM5521R",
        "32",
        ("e_waste", "battery"),
    ),
    Person("arjun", "9000000012", "Arjun Rao", "buyer", "Deccan Metals", "AAACD8834L", "29"),
    Person(
        "priya", "9000000013", "Priya Nair", "buyer", "Coastal Paper & Plastics", "AAACC6612P", "32"
    ),
    Person(
        "suresh",
        "9000000021",
        "Suresh Pillai",
        "buyer",
        "Green Circuits Ltd",
        "AAACG3307T",
        "32",
        approved=False,
    ),
    Person(
        "meera",
        "9000000022",
        "Meera Joseph",
        "seller",
        "Meera Traders",
        "AAAPJ9145H",
        None,
        approved=False,
    ),
]


# --- drawn photos ----------------------------------------------------------------------------

# colour and the kind of shapes the photo shows
LOOKS = {
    "copper": ((182, 98, 56), "rings"),
    "brass": ((196, 156, 52), "chunks"),
    "aluminium": ((176, 186, 192), "bars"),
    "steel_hms": ((96, 104, 108), "bars"),
    "cast_iron": ((62, 64, 66), "chunks"),
    "pet_bottles": ((128, 186, 214), "bottles"),
    "hdpe": ((232, 232, 226), "bottles"),
    "occ_cardboard": ((166, 126, 80), "boxes"),
    "e_waste_boards": ((44, 118, 70), "boards"),
    "lead_acid_batteries": ((42, 42, 48), "blocks"),
}


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow older than 10.1 has one fixed size
        return ImageFont.load_default()


def _shade(rgb, rng: random.Random, spread: int = 28):
    """Lighter or darker, all channels together, so the colour keeps its hue."""
    delta = rng.randint(-spread, spread)
    return tuple(max(0, min(255, c + delta)) for c in rgb)


def demo_photo(material: str, seed: int) -> bytes:
    """A drawn stand-in for a lot photo, clearly marked as one."""
    rng = random.Random(seed)
    colour, shape = LOOKS.get(material, ((140, 140, 140), "chunks"))
    image = Image.new("RGB", (800, 600), (124, 121, 112))
    draw = ImageDraw.Draw(image)
    for _ in range(900):  # yard gravel
        x, y = rng.randrange(800), rng.randrange(600)
        draw.point((x, y), fill=_shade((124, 121, 112), rng, 40))

    for _ in range(rng.randint(26, 40)):
        x, y = rng.randrange(-40, 800), rng.randrange(-40, 600)
        fill = _shade(colour, rng)
        if shape == "rings":
            r = rng.randint(24, 70)
            draw.ellipse((x, y, x + 2 * r, y + r), outline=fill, width=rng.randint(7, 14))
        elif shape == "bars":
            w, h = rng.randint(90, 240), rng.randint(14, 30)
            if rng.random() < 0.5:
                w, h = h, w
            draw.rectangle((x, y, x + w, y + h), fill=fill, outline=_shade(fill, rng, 50))
        elif shape == "chunks":
            pts = [(x + rng.randint(-50, 50), y + rng.randint(-40, 40)) for _ in range(6)]
            draw.polygon(pts, fill=fill, outline=_shade(fill, rng, 50))
        elif shape == "bottles":
            w, h = rng.randint(34, 52), rng.randint(110, 170)
            draw.rounded_rectangle(
                (x, y, x + w, y + h), radius=14, fill=fill, outline=(70, 90, 100)
            )
            draw.rectangle((x + w // 3, y - 14, x + 2 * w // 3, y), fill=(40, 90, 160))
        elif shape == "boxes":
            w, h = rng.randint(110, 200), rng.randint(80, 150)
            draw.rectangle((x, y, x + w, y + h), fill=fill, outline=(110, 82, 50), width=4)
            draw.line((x, y + h // 2, x + w, y + h // 2), fill=(110, 82, 50), width=3)
        elif shape == "boards":
            w, h = rng.randint(120, 200), rng.randint(80, 130)
            draw.rectangle((x, y, x + w, y + h), fill=fill, outline=(20, 60, 30), width=3)
            for _ in range(10):
                cx, cy = x + rng.randint(8, w - 16), y + rng.randint(8, h - 16)
                draw.rectangle((cx, cy, cx + 12, cy + 8), fill=(30, 30, 30))
        else:  # blocks: batteries
            w, h = rng.randint(110, 150), rng.randint(70, 95)
            draw.rectangle((x, y, x + w, y + h), fill=fill, outline=(15, 15, 18), width=3)
            for tx in (x + 18, x + w - 34):
                draw.rectangle((tx, y - 12, tx + 16, y), fill=(160, 40, 40))

    draw.rectangle((0, 548, 800, 600), fill=(28, 36, 40))
    draw.text((16, 556), "DEMO PHOTO", fill=(242, 194, 48), font=_font(32))
    out = io.BytesIO()
    image.save(out, "JPEG", quality=80)
    return out.getvalue()


def demo_slip(grams: int, seed: int) -> bytes:
    rng = random.Random(seed)
    image = Image.new("RGB", (600, 760), (250, 248, 240))
    draw = ImageDraw.Draw(image)
    tare = rng.randint(3_200, 4_800)
    net = grams / 1000
    lines = [
        ("WEIGHBRIDGE SLIP", 40),
        (f"Ticket {rng.randint(10000, 99999)}", 26),
        ("", 26),
        (f"Gross   {net + tare:,.1f} kg", 30),
        (f"Tare    {tare:,.1f} kg", 30),
        (f"Net     {net:,.1f} kg", 34),
        ("", 26),
        ("DEMO SLIP - not a real weighing", 24),
    ]
    y = 40
    for text, size in lines:
        draw.text((40, y), text, fill=(20, 20, 20), font=_font(size))
        y += size + 30
    out = io.BytesIO()
    image.save(out, "JPEG", quality=85)
    return out.getvalue()


# --- the trading history ---------------------------------------------------------------------


class _Clock:
    def __init__(self, now: datetime):
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class _DemoStorage:
    """Files the demo writes go under demo/, which the training export skips."""

    def __init__(self, inner: Storage):
        self.inner = inner

    def put(self, prefix: str, data: bytes, extension: str) -> str:
        return self.inner.put(f"{DEMO_PREFIX}/{prefix}", data, extension)

    def get(self, key: str) -> bytes:
        return self.inner.get(key)


@dataclass
class Summary:
    people: dict[str, User] = field(default_factory=dict)
    lots_by_status: dict[str, int] = field(default_factory=dict)


class _Seeder:
    def __init__(self, db: Session, settings: Settings, storage: Storage, now: datetime):
        self.db = db
        self.now = now
        self.clock = _Clock(now)
        self.env = Env(
            settings=settings,
            clock=self.clock,
            classifier=NullClassifier(),
            storage=_DemoStorage(storage),
            gateway=SimulatedGateway(),
        )
        self.people: dict[str, User] = {}
        self.photo_seed = 0

    def at(self, moment: datetime) -> None:
        self.clock.now = moment

    def later(self, **delta) -> None:
        self.clock.now += timedelta(**delta)

    # prices and people

    def backdate_rates(self, since: datetime) -> None:
        for material in self.db.scalars(select(Material)):
            if lots.current_rate(self.db, material, since) is not None:
                continue
            earliest = self.db.scalars(
                select(ReferenceRate)
                .where(ReferenceRate.material_id == material.id)
                .order_by(ReferenceRate.effective_from, ReferenceRate.id)
                .limit(1)
            ).first()
            if earliest is not None:
                self.db.add(
                    ReferenceRate(
                        material_id=material.id,
                        rate_paise_per_kg=earliest.rate_paise_per_kg,
                        effective_from=since,
                        source=RateSource.SEED,
                    )
                )
        self.db.flush()

    def add_people(self) -> None:
        for p in PEOPLE:
            user = User(
                phone=p.phone,
                name=p.name,
                password_hash=hash_password(DEMO_PASSWORD),
                role=p.role,
                business_name=p.business,
                gstin=p.gstin,
                pan=p.pan,
                kyc_status=KycStatus.APPROVED if p.approved else KycStatus.PENDING,
                # example.com never delivers mail, so demo notifications can't reach anyone.
                email=f"{p.key}@example.com",
                place=PLACE_OF[p.key],
                created_at=self.now
                - (timedelta(hours=2) if not p.approved else timedelta(days=30)),
            )
            compliance.set_held(user, list(p.authorisations))
            self.db.add(user)
            self.people[p.key] = user
        self.db.flush()

    # one lot, as far through its life as `stop`

    def trade(
        self,
        seller: str,
        material: str | None,
        kg: float = 0,
        *,
        start: datetime,
        grade: str = "A",
        hours: int = 24,
        bids: tuple[tuple[str, float], ...] = (),
        stop: str = "settled",
        weighed: float | None = None,
        pickup_at: datetime | None = None,
        location: tuple[float, float] | None = None,
        dispute: str | None = None,
        auction_format: str = "sealed",
        transporter: str | None = None,
        loaded: float | None = None,
    ) -> Lot:
        db, env = self.db, self.env
        owner = self.people[seller]
        self.photo_seed += 1
        self.at(start)
        lot = lots.create_lot(
            db,
            env,
            owner,
            photo=demo_photo(material or "copper", self.photo_seed),
            content_type="image/jpeg",
        )
        if stop == "draft":
            return lot

        self.later(minutes=4)
        grams = round(kg * 1000)
        lots.confirm_lot(
            db,
            env,
            owner,
            lot,
            material_code=material,
            grade=grade,
            declared_weight_grams=grams,
            place=owner.place,
            pickup_ready_on=(start.astimezone(IST) + timedelta(days=1)).date(),
        )
        self.later(minutes=6)
        lots.list_lot(
            db,
            env,
            owner,
            lot,
            auction_hours=hours,
            reserve_rate_paise_per_kg=None,
            auction_format=auction_format,
        )

        self.later(minutes=50)
        for buyer, factor in bids:
            rate = round(lot.estimate_rate_paise_per_kg * factor / 100) * 100
            lots.place_bid(db, env, self.people[buyer], lot, rate_paise_per_kg=rate)
            self.later(minutes=17)
        if stop == "listed":
            return lot

        self.at(lot.auction_closes_at + timedelta(minutes=1))
        lots.close_auction_if_due(db, env, lot)
        if stop in ("unsold", "awarded"):
            return lot

        buyer = db.get(User, lot.awarded_buyer_id)
        self.later(hours=2)
        intent = lots.start_escrow(db, env, buyer, lot)
        lots.capture_payment(
            db,
            env,
            intent,
            gateway_payment_id=f"demo_pay_{lot.id.hex[:12]}",
            amount_paise=intent.amount_paise,
        )
        if stop == "funded":
            return lot

        self.later(hours=1)
        when = pickup_at or self.clock.now + timedelta(days=1)
        lots.schedule_pickup(db, env, owner, lot, pickup_at=when, location=location)
        if transporter is not None:
            truck = db.scalars(select(Transporter).where(Transporter.name == transporter)).one()
            lots.assign_transporter(db, env, None, lot, transporter_id=truck.id)
        if loaded is not None:
            lots.record_pickup_weight(db, env, owner, lot, weight_grams=round(loaded * 1000))
        if stop == "pickup_scheduled":
            return lot

        self.at(when + timedelta(hours=2))
        measured = round((weighed or kg) * 1000)
        lots.record_delivery(
            db,
            env,
            buyer,
            lot,
            measured_weight_grams=measured,
            slip=demo_slip(measured, self.photo_seed),
            slip_content_type="image/jpeg",
        )
        if stop == "delivered":
            return lot

        self.later(hours=3)
        if dispute:
            lots.dispute_delivery(db, env, owner, lot, reason=dispute)
        else:
            lots.accept_delivery(db, env, owner, lot)
        return lot

    # the whole story

    def run(self) -> None:
        now = self.now

        def days(n: float) -> datetime:
            return now - timedelta(days=n)

        self.backdate_rates(days(30))
        self.add_people()

        self.db.add_all(
            [
                Transporter(
                    name=name,
                    phone=phone,
                    vehicle=vehicle,
                    capacity_grams=kg * 1000,
                    created_at=days(25),
                )
                for name, phone, vehicle, kg in (
                    ("Periyar Logistics", "9847012345", "Tata Ace, KL-07-AB-1234", 750),
                    ("Vembanad Movers", "9847023456", "Ashok Leyland Dost, KL-39-C-5521", 1_500),
                    ("Kerala Heavy Haul", "9847034567", "Tata 1109 truck, KL-07-CE-0907", 6_000),
                )
            ]
        )

        # History: three weeks of finished trades.
        self.trade(
            "ravi",
            "copper",
            250,
            grade="B",
            start=days(20),
            bids=(("joseph", 1.03), ("arjun", 1.01)),
            weighed=243.5,
        )
        self.trade(
            "ravi",
            "aluminium",
            600,
            start=days(17),
            bids=(("arjun", 1.02), ("joseph", 0.98)),
            weighed=596,
        )
        self.trade(
            "ravi",
            "copper",
            180,
            start=days(16),
            bids=(("joseph", 1.04), ("arjun", 1.02)),
            weighed=179.1,
        )
        self.trade(
            "anil",
            "steel_hms",
            2_000,
            grade="B",
            start=days(15),
            bids=(("joseph", 1.04),),
            weighed=2_040,
        )
        self.trade("anil", "brass", 120, start=days(13), bids=(("arjun", 1.01),), weighed=118.6)
        self.trade(
            "ravi", "occ_cardboard", 1_500, start=days(11), bids=(("priya", 1.05),), weighed=1_488
        )
        self.trade(
            "fathima", "e_waste_boards", 80, start=days(9), bids=(("joseph", 1.0),), weighed=79.2
        )
        self.trade("anil", "copper", 90, start=days(12), bids=(("arjun", 1.05),), weighed=90.4)
        self.trade("anil", "cast_iron", 100, start=days(8), stop="unsold")
        self.trade(
            "anil",
            "cast_iron",
            800,
            start=days(6),
            bids=(("arjun", 1.0),),
            weighed=742,
            dispute="The slip says 742 kg but we loaded 800 kg. Asking for a re-weigh.",
        )

        # The record up to here is sealed, and the scheduled job's run is on file.
        self.at(days(2) - timedelta(hours=1))
        anchor = anchoring.anchor_new_events(self.db, self.env)
        self.db.add(
            JobRun(
                name="anchor-custody",
                started_at=self.clock.now,
                finished_at=self.clock.now,
                ok=True,
                summary=f"sealed {anchor.event_count} events under root {anchor.merkle_root[:12]}…",
            )
        )

        # In progress now.
        tomorrow = (now.astimezone(IST) + timedelta(days=1)).date()

        def at_ist(hour: int, minute: int = 0) -> datetime:
            return datetime.combine(tomorrow, time(hour, minute), tzinfo=IST)

        self.trade(
            "ravi",
            "copper",
            150,
            start=days(2),
            hours=12,
            bids=(("joseph", 1.02),),
            pickup_at=now - timedelta(hours=20),
            weighed=148.2,
            stop="delivered",
        )
        self.trade(
            "ravi",
            "aluminium",
            300,
            start=days(2),
            bids=(("joseph", 1.01),),
            stop="pickup_scheduled",
            pickup_at=at_ist(10),
            location=(10.0261, 76.3086),
            transporter="Periyar Logistics",
            loaded=301.5,
        )
        self.trade(
            "anil",
            "steel_hms",
            1_200,
            grade="B",
            start=days(2),
            bids=(("arjun", 1.03),),
            stop="pickup_scheduled",
            pickup_at=at_ist(11, 30),
            location=(10.5167, 76.2167),
            transporter="Kerala Heavy Haul",
        )
        self.trade(
            "fathima",
            "e_waste_boards",
            50,
            start=days(2),
            bids=(("joseph", 1.0),),
            stop="pickup_scheduled",
            pickup_at=at_ist(14),
            location=(10.0159, 76.3419),
            transporter="Periyar Logistics",
        )
        self.trade(
            "ravi",
            "pet_bottles",
            400,
            start=days(2),
            bids=(("priya", 1.02),),
            stop="pickup_scheduled",
            pickup_at=at_ist(15),
        )
        self.trade(
            "anil",
            "brass",
            90,
            start=now - timedelta(hours=36),
            hours=12,
            bids=(("arjun", 1.02),),
            stop="funded",
        )
        self.trade(
            "ravi",
            "copper",
            200,
            start=now - timedelta(hours=10),
            hours=6,
            bids=(("arjun", 1.02), ("joseph", 1.0)),
            stop="awarded",
        )

        live = now - timedelta(hours=2)
        self.trade(
            "ravi",
            "copper",
            180,
            start=live,
            hours=8,
            bids=(("joseph", 1.01), ("arjun", 1.03)),
            stop="listed",
            auction_format="open",
        )
        self.trade(
            "anil",
            "steel_hms",
            3_000,
            grade="B",
            start=live,
            hours=32,
            bids=(("joseph", 1.0),),
            stop="listed",
        )
        self.trade("ravi", "pet_bottles", 500, start=live, hours=22, stop="listed")
        self.trade(
            "fathima",
            "lead_acid_batteries",
            300,
            start=live,
            hours=42,
            bids=(("joseph", 0.99),),
            stop="listed",
        )
        self.trade("anil", "hdpe", 250, start=live, hours=50, stop="listed")
        self.trade("ravi", None, start=now - timedelta(minutes=30), stop="draft")

        self.requests_and_agreements(days)

        # Copper has traded above its reference price, so repricing moves it. This runs at the
        # demo's present rather than in its past: a freshly seeded catalogue's own rate starts
        # inside the demo history and would otherwise override an earlier move.
        self.at(now)
        moved = repricing.summarise(repricing.reprice_all(self.db, self.env))
        self.db.add(JobRun(name="reprice", started_at=now, finished_at=now, ok=True, summary=moved))
        self.db.add(
            JobRun(
                name="close-auctions",
                started_at=now - timedelta(minutes=5),
                finished_at=now - timedelta(minutes=5),
                ok=True,
                summary="0 auctions closed, 0 unpaid awards passed on",
            )
        )

    def requests_and_agreements(self, days) -> None:
        db, env, p = self.db, self.env, self.people
        self.at(days(1))
        for buyer, material, kg, rate, in_days, note in (
            ("joseph", "steel_hms", 5_000, 3_100, 7, "HMS 1 preferred, cut to 1.5 m"),
            ("priya", "occ_cardboard", 2_000, 1_450, 10, "Dry and baled, please"),
            ("arjun", "brass", 500, None, 14, ""),
        ):
            rfqs.create_rfq(
                db,
                env,
                p[buyer],
                material_code=material,
                quantity_grams=kg * 1000,
                target_rate_paise_per_kg=rate,
                needed_by=self.now + timedelta(days=in_days),
                note=note,
            )
        closed = rfqs.create_rfq(
            db,
            env,
            p["joseph"],
            material_code="copper",
            quantity_grams=300_000,
            target_rate_paise_per_kg=None,
            needed_by=self.now + timedelta(days=3),
            note="",
        )
        rfqs.close_rfq(p["joseph"], closed)

        first_of_next_month = (self.now.date().replace(day=1) + timedelta(days=32)).replace(day=1)
        offers = []
        for buyer, seller, material, kg, rate_rupees, months in (
            ("joseph", "ravi", "copper", 500, 660, 6),
            ("priya", "ravi", "occ_cardboard", 2_000, 14.5, 12),
            ("arjun", "anil", "brass", 300, 445, 6),
            ("joseph", "anil", "steel_hms", 4_000, 30, 3),
        ):
            offers.append(
                agreements.propose(
                    db,
                    env,
                    p[buyer],
                    seller_id=p[seller].id,
                    material_code=material,
                    monthly_quantity_grams=kg * 1000,
                    rate_paise_per_kg=round(rate_rupees * 100),
                    starts_on=first_of_next_month,
                    months=months,
                )
            )
        self.later(hours=5)
        agreements.decide(db, env, p["ravi"], offers[0].id, accept=True)
        agreements.decide(db, env, p["ravi"], offers[1].id, accept=False)


def seed_demo(db: Session, settings: Settings, storage: Storage, now: datetime) -> Summary:
    """Add the demo people and history. Caller commits. Needs the catalogue seeded first."""
    phones = [p.phone for p in PEOPLE]
    if db.scalars(select(User.id).where(User.phone.in_(phones))).first() is not None:
        raise DemoAlreadyLoaded("demo data is already loaded (its phone numbers are taken)")
    seeder = _Seeder(db, settings, storage, now.astimezone(UTC))
    seeder.run()
    db.flush()

    counts: dict[str, int] = {}
    for status in db.scalars(select(Lot.status).where(Lot.photo_key.like(f"{DEMO_PREFIX}/%"))):
        counts[status] = counts.get(status, 0) + 1
    return Summary(people=seeder.people, lots_by_status=dict(sorted(counts.items())))
