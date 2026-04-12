"""Seeds the database with the master residential dataset."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from .models.document import Document
from .models.lease import Lease
from .models.maintenance import MaintenanceRequest
from .models.payment import Payment
from .models.user import User, TenantOrg
from .models.property import Property
from .models.vendor import Vendor
from .services.auth import hash_password


def seed_db(db: Session):
    # Check if already seeded
    if db.query(User).first():
        return

    print("Seeding database with demo data...")

    # --- Tenant Org ---
    org = TenantOrg(id="t1", name="QuantumQuest Demo")
    db.add(org)

    # --- Users ---
    users = [
        User(
            id="u1", tenant_id="t1",
            email="alex.thompson@example.com",
            hashed_password=hash_password("demo1234"),
            role="owner", first_name="Alex", last_name="Thompson",
            phone="+1 (555) 012-3456", avatar_initials="AT",
        ),
        User(
            id="u2", tenant_id="t1",
            email="sarah.chen@example.com",
            hashed_password=hash_password("demo1234"),
            role="manager", first_name="Sarah", last_name="Chen",
            phone="+1 (555) 234-5678", avatar_initials="SC",
        ),
        # Real tenants — 2454 Ronald McNair Way, Sacramento (lease signed 2025-04-13)
        User(
            id="u3", tenant_id="t1",
            email="johntgregorich@gmail.com",
            hashed_password=hash_password("demo1234"),
            role="tenant", first_name="John", last_name="Gregorich",
            phone="", avatar_initials="JG",
        ),
        User(
            id="u4", tenant_id="t1",
            email="deannamgregorich@gmail.com",
            hashed_password=hash_password("demo1234"),
            role="tenant", first_name="Deanna", last_name="Gregorich",
            phone="", avatar_initials="DG",
        ),
        # Real tenants — 6670 E Madison Ave, Fresno (lease signed 2026-02-23)
        User(
            id="u7", tenant_id="t1",
            email="sawanchodri73@gmail.com",
            hashed_password=hash_password("demo1234"),
            role="tenant", first_name="Sawan Singh", last_name="Dabra",
            phone="", avatar_initials="SD",
        ),
        User(
            id="u8", tenant_id="t1",
            email="balvinder.rozara@noemail.local",
            hashed_password=hash_password("demo1234"),
            role="tenant", first_name="Balvinder", last_name="Rozara",
            phone="", avatar_initials="BR",
        ),
        User(
            id="u9", tenant_id="t1",
            email="subham.subham@noemail.local",
            hashed_password=hash_password("demo1234"),
            role="tenant", first_name="Subham", last_name="Subham",
            phone="", avatar_initials="SS",
        ),
        User(
            id="u10", tenant_id="t1",
            email="jasbir.singh@noemail.local",
            hashed_password=hash_password("demo1234"),
            role="tenant", first_name="Jasbir", last_name="Singh",
            phone="", avatar_initials="JS",
        ),
        # Real tenants — 4053 Penny Ter, Fremont (lease signed 2025-11-25)
        User(
            id="u5", tenant_id="t1",
            email="csrj0425@gmail.com",
            hashed_password=hash_password("demo1234"),
            role="tenant", first_name="Chetan Sandeep Renu", last_name="Jannu",
            phone="", avatar_initials="CJ",
        ),
        User(
            id="u6", tenant_id="t1",
            email="anoosha100@gmail.com",
            hashed_password=hash_password("demo1234"),
            role="tenant", first_name="Anoosha", last_name="Pilli",
            phone="", avatar_initials="AP",
        ),
        # Real tenants — 2580 N McArthur Ave, Fresno (Zillow lease signed 2026-01-25)
        User(
            id="u11", tenant_id="t1",
            email="chrish.vc21@gmail.com",
            hashed_password=hash_password("demo1234"),
            role="tenant", first_name="Chrishna", last_name="Cervantes",
            phone="(559) 441-3450", avatar_initials="CC",
        ),
        User(
            id="u12", tenant_id="t1",
            email="donnyxo21@gmail.com",
            hashed_password=hash_password("demo1234"),
            role="tenant", first_name="Donovon", last_name="Andersen",
            phone="(559) 349-0964", avatar_initials="DA",
        ),
        User(
            id="u13", tenant_id="t1",
            email="williamsjohnathan1000@gmail.com",
            hashed_password=hash_password("demo1234"),
            role="tenant", first_name="Johnathan", last_name="Williams",
            phone="(559) 455-8516", avatar_initials="JW",
        ),
        # Real tenant — 4008 Gunnar Dr, Roseville (C.A.R. RLMM 12/25 signed 2025-12-27)
        User(
            id="u14", tenant_id="t1",
            email="tatyanawelch1@gmail.com",
            hashed_password=hash_password("demo1234"),
            role="tenant", first_name="Tatyana", last_name="Welch",
            phone="", avatar_initials="TW",
        ),
    ]
    db.add_all(users)

    # --- Properties ---
    properties = [
        Property(
            id="p1",
            tenant_id="t1",
            owner_id="u1",
            name="2454 Ronald McNair Way",
            address="2454 Ronald McNair Way",
            city="Sacramento",
            state="CA",
            zip="95834",
            property_type="residential",
            bedrooms=4,
            bathrooms=3,
            sqft=0,
            status="occupied",
            rent_amount=3345,       # Real lease: $3,345/month (signed 2025-04-13)
            image_color="#6366f1",
        ),
        Property(
            id="p2",
            tenant_id="t1",
            owner_id="u1",
            name="2580 N McArthur Ave",
            address="2580 N McArthur Ave",
            city="Fresno",
            state="CA",
            zip="93727",
            property_type="residential",
            bedrooms=3,
            bathrooms=3,
            sqft=0,
            status="occupied",
            rent_amount=2395,
            image_color="#06b6d4",
        ),
        Property(
            id="p3",
            tenant_id="t1",
            owner_id="u1",
            name="4053 Penny Terrace",
            address="4053 Penny Terrace",
            city="Fremont",
            state="CA",
            zip="94538",
            property_type="residential",
            bedrooms=2,
            bathrooms=3,
            sqft=0,
            status="occupied",
            rent_amount=3450,
            image_color="#10b981",
        ),
        Property(
            id="p4",
            tenant_id="t1",
            owner_id="u1",
            name="4008 Gunnar Dr",
            address="4008 Gunnar Dr",
            city="Roseville",
            state="CA",
            zip="95747",
            property_type="residential",
            bedrooms=3,
            bathrooms=3,
            sqft=0,
            status="occupied",
            rent_amount=3085,
            image_color="#f59e0b",
        ),
        Property(
            id="p5",
            tenant_id="t1",
            owner_id="u1",
            name="6670 E Madison Ave",
            address="6670 E Madison Ave",
            city="Fresno",
            state="CA",
            zip="93727",
            property_type="residential",
            bedrooms=4,
            bathrooms=3,
            sqft=0,
            status="occupied",
            rent_amount=2750,
            image_color="#ef4444",
        ),
    ]
    db.add_all(properties)

    leases = [
        # Real lease: 2454 Ronald McNair Way — C.A.R. Form RLMM signed 2025-04-13
        Lease(
            id="l1",
            property_id="p1",
            tenant_user_id="u3",
            tenant_name="John Gregorich",          # Primary tenant; co-tenant: Deanna Gregorich
            start_date=date(2025, 5, 11),          # Commencement date per lease
            end_date=date(2026, 5, 31),            # Termination date per lease
            rent_amount=3345,                      # Per §3A of lease
            security_deposit=3295,                 # Per §4A of lease
            status="active",
        ),
        # Real lease: 6670 E Madison Ave, Fresno — C.A.R. Form RLMM signed 2026-02-23
        Lease(
            id="l2",
            property_id="p5",
            tenant_user_id="u7",
            tenant_name="Sawan Singh Dabra",  # Primary tenant; co-tenants: Balvinder Rozara, Subham Subham, Jasbir Singh
            start_date=date(2026, 3, 1),      # Commencement date per lease
            end_date=date(2027, 2, 28),        # Termination date per lease
            rent_amount=2750,                  # Per §3A of lease
            security_deposit=2700,             # Per §4A of lease
            status="active",
        ),
        # Real lease: 4053 Penny Ter, Fremont — C.A.R. Form RLMM signed 2025-11-25
        Lease(
            id="l3",
            property_id="p3",
            tenant_user_id="u5",
            tenant_name="Chetan Sandeep Renu Jannu",  # Primary tenant; co-tenant: Anoosha Pilli
            start_date=date(2025, 12, 1),             # Commencement date per lease
            end_date=date(2027, 5, 31),               # Termination date per lease
            rent_amount=3450,                          # Per §3A of lease
            security_deposit=3300,                     # Per §4A of lease
            status="active",
        ),
        # Real lease: 2580 N McArthur Ave, Fresno — Zillow lease signed 2026-01-25
        Lease(
            id="l4",
            property_id="p2",
            tenant_user_id="u11",
            tenant_name="Chrishna Cervantes",         # Primary tenant; co-tenants: Donovon Andersen, Johnathan Williams
            start_date=date(2026, 2, 1),              # Start date per lease §1.3
            end_date=date(2027, 1, 31),               # Expiration date per lease §1.3
            rent_amount=2395,                          # Per §1.4 of lease
            security_deposit=2745,                     # Per §1.6 of lease
            status="active",
        ),
        # Real lease: 4008 Gunnar Dr, Roseville — C.A.R. Form RLMM 12/25 signed 2025-12-27
        Lease(
            id="l5",
            property_id="p4",
            tenant_user_id="u14",
            tenant_name="Tatyana Welch",              # Primary (sole) tenant
            start_date=date(2026, 2, 1),              # Commencement date per lease
            end_date=date(2027, 1, 31),               # Termination date per lease
            rent_amount=3085,                          # Per §3A of lease
            security_deposit=2995,                     # Per §4A of lease
            status="active",
        ),
    ]
    db.add_all(leases)

    first_of_month = date.today().replace(day=1)
    previous_month = (first_of_month - timedelta(days=1)).replace(day=1)
    payments = [
        # Rent payments for 2454 Ronald McNair Way — John Gregorich
        # Late charge per lease §6A: $100 after 5-day grace period
        Payment(
            id="pay1",
            lease_id="l1",
            tenant_name="John Gregorich",
            property_name="2454 Ronald McNair Way",
            amount=3345,
            due_date=previous_month,
            paid_date=previous_month + timedelta(days=1),
            payment_method="cashier_check",
            status="paid",
            late_fee=0,
            transaction_ref="TXN-DEMO1001",
        ),
        Payment(
            id="pay2",
            lease_id="l1",
            tenant_name="John Gregorich",
            property_name="2454 Ronald McNair Way",
            amount=3345,
            due_date=first_of_month,
            paid_date=None,
            payment_method="cashier_check",
            status="late",
            late_fee=100,           # Real lease late charge per §6A
            transaction_ref="TXN-DEMO1002",
        ),
        # Rent payments for 6670 E Madison Ave — Sawan Singh Dabra
        Payment(
            id="pay3",
            lease_id="l2",
            tenant_name="Sawan Singh Dabra",
            property_name="6670 E Madison Ave",
            amount=2750,
            due_date=date(2026, 3, 1),         # First month (March 2026)
            paid_date=date(2026, 3, 1),
            payment_method="cashier_check",
            status="paid",
            late_fee=0,
            transaction_ref="TXN-DEMO1003",
        ),
        Payment(
            id="pay6",
            lease_id="l2",
            tenant_name="Sawan Singh Dabra",
            property_name="6670 E Madison Ave",
            amount=2750,
            due_date=first_of_month,
            paid_date=None,
            payment_method="cashier_check",
            status="pending",
            late_fee=0,
            transaction_ref="TXN-DEMO1006",
        ),
        # Rent payments for 4053 Penny Ter — Chetan Sandeep Renu Jannu
        Payment(
            id="pay4",
            lease_id="l3",
            tenant_name="Chetan Sandeep Renu Jannu",
            property_name="4053 Penny Terrace",
            amount=3450,
            due_date=previous_month,
            paid_date=previous_month + timedelta(days=2),
            payment_method="money_order",
            status="paid",
            late_fee=0,
            transaction_ref="TXN-DEMO1004",
        ),
        Payment(
            id="pay5",
            lease_id="l3",
            tenant_name="Chetan Sandeep Renu Jannu",
            property_name="4053 Penny Terrace",
            amount=3450,
            due_date=first_of_month,
            paid_date=None,
            payment_method="money_order",
            status="pending",
            late_fee=0,
            transaction_ref="TXN-DEMO1005",
        ),
        # Rent payments for 2580 N McArthur Ave — Chrishna Cervantes
        Payment(
            id="pay7",
            lease_id="l4",
            tenant_name="Chrishna Cervantes",
            property_name="2580 N McArthur Ave",
            amount=2395,
            due_date=date(2026, 2, 1),         # First month (February 2026)
            paid_date=date(2026, 2, 1),
            payment_method="check",
            status="paid",
            late_fee=0,
            transaction_ref="TXN-DEMO1007",
        ),
        Payment(
            id="pay8",
            lease_id="l4",
            tenant_name="Chrishna Cervantes",
            property_name="2580 N McArthur Ave",
            amount=2395,
            due_date=first_of_month,
            paid_date=None,
            payment_method="check",
            status="pending",
            late_fee=0,
            transaction_ref="TXN-DEMO1008",
        ),
        # Rent payments for 4008 Gunnar Dr — Tatyana Welch
        Payment(
            id="pay9",
            lease_id="l5",
            tenant_name="Tatyana Welch",
            property_name="4008 Gunnar Dr",
            amount=3085,
            due_date=date(2026, 2, 1),         # First month (February 2026)
            paid_date=date(2026, 2, 1),
            payment_method="cashier_check",
            status="paid",
            late_fee=0,
            transaction_ref="TXN-DEMO1009",
        ),
        Payment(
            id="pay10",
            lease_id="l5",
            tenant_name="Tatyana Welch",
            property_name="4008 Gunnar Dr",
            amount=3085,
            due_date=first_of_month,
            paid_date=None,
            payment_method="cashier_check",
            status="pending",
            late_fee=0,
            transaction_ref="TXN-DEMO1010",
        ),
    ]
    db.add_all(payments)

    maintenance_requests = [
        MaintenanceRequest(
            id="mr1",
            property_id="p5",
            tenant_user_id="u4",
            property_name="6670 E Madison Ave",
            tenant_name="Olivia Reed",
            category="HVAC",
            description="Air conditioning stopped cooling and the indoor temperature is rising in the afternoon.",
            urgency="high",
            status="assigned",
            assigned_vendor="Central Valley HVAC",
            estimated_cost=850,
        ),
        MaintenanceRequest(
            id="mr2",
            property_id="p1",
            tenant_user_id="u3",
            property_name="2454 Ronald McNair Way",
            tenant_name="John Gregorich",
            category="Plumbing",
            description="Kitchen sink drain is backing up after normal use.",
            urgency="medium",
            status="submitted",
            assigned_vendor=None,
            estimated_cost=None,
        ),
    ]
    db.add_all(maintenance_requests)

    documents = [
        # Real lease agreement — John & Deanna Gregorich, 2454 Ronald McNair Way
        # C.A.R. Form RLMM signed 2025-04-13, term: 2025-05-11 to 2026-05-31
        # Extracted text indexed at: documents/leases/lease_2454_ronald_mcnair_way.txt
        Document(
            id="d1",
            tenant_id="t1",
            uploaded_by="Laxmi Raj Reddy Prodduturi",
            document_type="lease",
            file_name="Lease_2454_Ronald_McNair_Way_Gregorich_2025.pdf",
            file_size="520 KB",
            mime_type="application/pdf",
            related_entity="2454 Ronald McNair Way",
            file_path="documents/leases/lease_2454_ronald_mcnair_way.txt",
        ),
        Document(
            id="d2",
            tenant_id="t1",
            uploaded_by="Laxmi Raj Reddy Prodduturi",
            document_type="disclosure",
            file_name="Rent_Cap_Just_Cause_Addendum_RCJC.pdf",
            file_size="96 KB",
            mime_type="application/pdf",
            related_entity="2454 Ronald McNair Way",
            file_path="documents/leases/lease_2454_ronald_mcnair_way.txt",
        ),
        Document(
            id="d3",
            tenant_id="t1",
            uploaded_by="Laxmi Raj Reddy Prodduturi",
            document_type="disclosure",
            file_name="Bed_Bug_Disclosure_BBD.pdf",
            file_size="48 KB",
            mime_type="application/pdf",
            related_entity="2454 Ronald McNair Way",
            file_path="documents/leases/lease_2454_ronald_mcnair_way.txt",
        ),
        Document(
            id="d4",
            tenant_id="t1",
            uploaded_by="Laxmi Raj Reddy Prodduturi",
            document_type="disclosure",
            file_name="Tenant_Flood_Hazard_Disclosure_TFHD.pdf",
            file_size="44 KB",
            mime_type="application/pdf",
            related_entity="2454 Ronald McNair Way",
            file_path="documents/leases/lease_2454_ronald_mcnair_way.txt",
        ),
        Document(
            id="d5",
            tenant_id="t1",
            uploaded_by="Laxmi Raj Reddy Prodduturi",
            document_type="policy",
            file_name="Fair_Housing_Discrimination_Advisory_FHDA.pdf",
            file_size="72 KB",
            mime_type="application/pdf",
            related_entity="All Properties",
            file_path="documents/shared/fair_housing_advisory.txt",
        ),
        # Real lease agreement — Chetan Sandeep Renu Jannu & Anoosha Pilli, 4053 Penny Ter, Fremont
        # C.A.R. Form RLMM signed 2025-11-25, term: 2025-12-01 to 2027-05-31
        # Extracted text indexed at: documents/leases/lease_4053_penny_ter_fremont.txt
        Document(
            id="d6",
            tenant_id="t1",
            uploaded_by="Laxmi Raj Reddy Prodduturi",
            document_type="lease",
            file_name="Lease_4053_Penny_Ter_Fremont_Chetan_2025.pdf",
            file_size="520 KB",
            mime_type="application/pdf",
            related_entity="4053 Penny Terrace",
            file_path="documents/leases/lease_4053_penny_ter_fremont.txt",
        ),
        Document(
            id="d7",
            tenant_id="t1",
            uploaded_by="Laxmi Raj Reddy Prodduturi",
            document_type="disclosure",
            file_name="Rent_Cap_Just_Cause_Addendum_RCJC_Fremont.pdf",
            file_size="96 KB",
            mime_type="application/pdf",
            related_entity="4053 Penny Terrace",
            file_path="documents/leases/lease_4053_penny_ter_fremont.txt",
        ),
        # Real lease agreement — Sawan Singh Dabra et al., 6670 E Madison Ave, Fresno
        # C.A.R. Form RLMM signed 2026-02-23, term: 2026-03-01 to 2027-02-28
        # Extracted text indexed at: documents/leases/lease_6670_e_madison_ave_fresno.txt
        Document(
            id="d8",
            tenant_id="t1",
            uploaded_by="Laxmi Raj Reddy Prodduturi",
            document_type="lease",
            file_name="Lease_6670_E_Madison_Ave_Fresno_Sawan_2026.pdf",
            file_size="540 KB",
            mime_type="application/pdf",
            related_entity="6670 E Madison Ave",
            file_path="documents/leases/lease_6670_e_madison_ave_fresno.txt",
        ),
        Document(
            id="d9",
            tenant_id="t1",
            uploaded_by="Laxmi Raj Reddy Prodduturi",
            document_type="disclosure",
            file_name="Rent_Cap_Just_Cause_Addendum_RCJC_Fresno.pdf",
            file_size="96 KB",
            mime_type="application/pdf",
            related_entity="6670 E Madison Ave",
            file_path="documents/leases/lease_6670_e_madison_ave_fresno.txt",
        ),
        # Real lease agreement — Chrishna Cervantes et al., 2580 N McArthur Ave, Fresno
        # Zillow Residential Lease signed 2026-01-25, term: 2026-02-01 to 2027-01-31
        # Extracted text indexed at: documents/leases/lease_2580_n_mcarthur_ave_fresno.txt
        Document(
            id="d10",
            tenant_id="t1",
            uploaded_by="Laxmi Raj Reddy Prodduturi",
            document_type="lease",
            file_name="Lease_2580_N_McArthur_Ave_Fresno_Chrishna_2026.pdf",
            file_size="480 KB",
            mime_type="application/pdf",
            related_entity="2580 N McArthur Ave",
            file_path="documents/leases/lease_2580_n_mcarthur_ave_fresno.txt",
        ),
        Document(
            id="d11",
            tenant_id="t1",
            uploaded_by="Laxmi Raj Reddy Prodduturi",
            document_type="disclosure",
            file_name="Tenant_Protection_Act_Exemption_McArthur.pdf",
            file_size="64 KB",
            mime_type="application/pdf",
            related_entity="2580 N McArthur Ave",
            file_path="documents/leases/lease_2580_n_mcarthur_ave_fresno.txt",
        ),
        # Real lease agreement — Tatyana Welch, 4008 Gunnar Dr, Roseville
        # C.A.R. Form RLMM 12/25 signed 2025-12-27, term: 2026-02-01 to 2027-01-31
        # Extracted text indexed at: documents/leases/lease_4008_gunnar_dr_roseville.txt
        Document(
            id="d12",
            tenant_id="t1",
            uploaded_by="Laxmi Raj Reddy Prodduturi",
            document_type="lease",
            file_name="Lease_4008_Gunnar_Dr_Roseville_Tatyana_2025.pdf",
            file_size="510 KB",
            mime_type="application/pdf",
            related_entity="4008 Gunnar Dr",
            file_path="documents/leases/lease_4008_gunnar_dr_roseville.txt",
        ),
        Document(
            id="d13",
            tenant_id="t1",
            uploaded_by="Laxmi Raj Reddy Prodduturi",
            document_type="disclosure",
            file_name="Rent_Cap_Just_Cause_Addendum_RCJC_Roseville.pdf",
            file_size="96 KB",
            mime_type="application/pdf",
            related_entity="4008 Gunnar Dr",
            file_path="documents/leases/lease_4008_gunnar_dr_roseville.txt",
        ),
    ]
    db.add_all(documents)

    # --- Vendors ---
    vendor_rows = [
        Vendor(id="vnd1", tenant_id="t1", name="CoolAir HVAC", trade="HVAC",
               email="dispatch@coolair.example.com", phone="(555) 700-1001",
               rating=4.9, response_time="2h average"),
        Vendor(id="vnd2", tenant_id="t1", name="ProPlumb Services", trade="Plumbing",
               email="jobs@proplumb.example.com", phone="(555) 700-1002",
               rating=4.7, response_time="4h average"),
        Vendor(id="vnd3", tenant_id="t1", name="QuickElec Services", trade="Electrical",
               email="service@quickelec.example.com", phone="(555) 700-1003",
               rating=4.8, response_time="2h average"),
        Vendor(id="vnd4", tenant_id="t1", name="CleanPro Janitorial", trade="Cleaning",
               email="hello@cleanpro.example.com", phone="(555) 700-1004",
               rating=4.6, response_time="24h average"),
    ]
    db.add_all(vendor_rows)

    db.commit()
    print("Database seeded successfully!")
