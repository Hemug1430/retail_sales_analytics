"""
05.24 - Run Returns Incremental Insert

Uses existing database tables:
    stg_returns
    factreturns
    rejected_records
    etl_file_log

No table creation, renaming or truncation.

All staging and merge operations are scoped by batch_id.
"""

import csv
import hashlib
import json
import uuid

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import mysql.connector

from config import DB_CONFIG


# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

CSV_PATH = (
    ROOT
    / "data"
    / "synthetic"
    / "returns_master.csv"
)

DATASET = "RETURNS"

VALID_REASONS = {
    "Damaged",
    "Wrong Product",
    "Quality Issue",
    "Size/Fit Issue",
    "Customer Changed Mind",
    "Late Delivery",
    "Other",
}

VALID_STATUSES = {
    "Requested",
    "Approved",
    "Rejected",
    "Refunded",
}

VALID_REFUND_METHODS = {
    "Original Payment",
    "Store Credit",
    "Cash",
}

ALLOWED_TRANSITIONS = {
    "Requested": {"Approved", "Rejected"},
    "Approved": {"Refunded"},
    "Rejected": set(),
    "Refunded": set(),
}


# ============================================================
# 2. HASH FUNCTIONS
# ============================================================

def sha256(value):

    return hashlib.sha256(value).hexdigest()


def calculate_record_hash(record):

    payload = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str
    )

    return sha256(payload.encode("utf-8"))


# ============================================================
# 3. STANDARDIZATION AND CONVERSION
# ============================================================

def clean(value):

    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def parse_date(value):

    value = clean(value)

    if not value:
        raise ValueError("return_date is missing")

    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):

        try:

            return datetime.strptime(
                value,
                fmt
            ).date()

        except ValueError:
            pass

    raise ValueError(
        f"Unsupported return_date format: {value}"
    )


def parse_quantity(value):

    value = clean(value)

    if not value:
        raise ValueError(
            "quantity_returned is missing"
        )

    try:

        quantity = int(value)

    except ValueError as exc:

        raise ValueError(
            "quantity_returned must be an integer"
        ) from exc

    if quantity <= 0:

        raise ValueError(
            "quantity_returned must be greater than zero"
        )

    return quantity


def parse_amount(value):

    value = clean(value)

    if not value:
        return None

    try:

        amount = Decimal(value)

    except InvalidOperation as exc:

        raise ValueError(
            "refund_amount must be numeric"
        ) from exc

    if not amount.is_finite() or amount < 0:

        raise ValueError(
            "refund_amount must be non-negative"
        )

    return amount.quantize(
        Decimal("0.01")
    )


# ============================================================
# 4. READ CSV AND GENERATE BATCH
# ============================================================

def read_source():

    raw_bytes = CSV_PATH.read_bytes()

    file_hash = sha256(raw_bytes)

    batch_id = (
        "BATCH_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + "_"
        + uuid.uuid4().hex[:8]
    )

    rows = []

    with CSV_PATH.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as handle:

        reader = csv.DictReader(handle)

        if not reader.fieldnames:

            raise ValueError(
                "CSV header is missing"
            )

        headers = {
            h.strip().lower()
            for h in reader.fieldnames
            if h
        }

        required = {
            "return_id",
            "return_date",
            "return_reason",
            "return_status",
        }

        missing = required - headers

        if missing:

            raise ValueError(
                "Missing required headers: "
                + ", ".join(sorted(missing))
            )

        if (
            "sales_line_id" not in headers
            and "order_id" not in headers
        ):

            raise ValueError(
                "CSV requires sales_line_id "
                "or legacy order_id"
            )

        for row_number, row in enumerate(
            reader,
            start=2
        ):

            normalized_row = {
                str(key).strip().lower(): value
                for key, value in row.items()
                if key
            }

            rows.append({
                "row_number": row_number,
                "raw": normalized_row,
            })

    return (
        rows,
        file_hash,
        len(raw_bytes),
        batch_id
    )


# ============================================================
# 5. NORMALIZE RECORD
# ============================================================

def normalize(raw):

    return {

        "return_id": clean(
            raw.get("return_id")
        ),

        "sales_line_id": clean(
            raw.get("sales_line_id")
            or raw.get("order_id")
        ),

        "return_date": parse_date(
            raw.get("return_date")
        ),

        "quantity_returned": parse_quantity(
            raw.get("quantity_returned")
            or raw.get("quantity")
        ),

        "return_reason": clean(
            raw.get("return_reason")
        ),

        "return_status": clean(
            raw.get("return_status")
            or raw.get("status")
        ),

        "refund_method": clean(
            raw.get("refund_method")
        ),

        "refund_amount": parse_amount(
            raw.get("refund_amount")
        ),

        "processed_store_id": clean(
            raw.get("processed_store_id")
            or raw.get("store_id")
        ),

    }


# ============================================================
# 6. VALIDATE RECORD
# ============================================================

def validate(record):

    required_fields = [
        "return_id",
        "sales_line_id",
        "return_date",
        "quantity_returned",
        "return_reason",
        "return_status",
    ]

    for field in required_fields:

        if record[field] is None:

            return (
                "REQ_NULL",
                f"Required field missing: {field}"
            )

    widths = {
        "return_id": 18,
        "sales_line_id": 18,
        "return_reason": 40,
        "return_status": 20,
        "refund_method": 25,
        "processed_store_id": 10,
    }

    for field, width in widths.items():

        value = record[field]

        if value is not None and len(str(value)) > width:

            return (
                "DOMAIN_INVALID",
                f"{field} exceeds maximum length {width}"
            )

    if record["return_reason"] not in VALID_REASONS:

        return (
            "DOMAIN_INVALID",
            "Invalid return_reason"
        )

    if record["return_status"] not in VALID_STATUSES:

        return (
            "DOMAIN_INVALID",
            "Invalid return_status"
        )

    if (
        record["refund_amount"] is not None
        and record["refund_amount"] >= Decimal("10000000000")
    ):

        return (
            "DOMAIN_INVALID",
            "refund_amount exceeds DECIMAL(12,2)"
        )

    if record["return_status"] == "Refunded":

        if record["refund_method"] not in VALID_REFUND_METHODS:

            return (
                "DOMAIN_INVALID",
                "Refunded status requires valid refund_method"
            )

        if record["refund_amount"] is None:

            return (
                "REQ_NULL",
                "Refunded status requires refund_amount"
            )

    elif (
        record["refund_method"] is not None
        or record["refund_amount"] is not None
    ):

        return (
            "DOMAIN_INVALID",
            "Refund fields must be blank for non-refunded returns"
        )

    return None


# ============================================================
# 7. INSERT REJECTED RECORD
# ============================================================

def insert_reject(
    cursor,
    batch_id,
    file_name,
    row_number,
    business_key,
    digest,
    code,
    message,
    raw
):

    cursor.execute("""
        INSERT INTO rejected_records (

            batch_id,
            source_file_name,
            source_row_number,
            dataset_name,
            business_key,
            record_hash,
            reject_code,
            reject_message,
            reject_timestamp,
            raw_record,
            validation_stage,
            created_at

        )

        VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,
            NOW(),%s,%s,NOW()
        )
    """, (

        batch_id,
        file_name,
        row_number,
        DATASET,
        business_key,
        digest,
        code,
        message[:1000],
        json.dumps(
            raw,
            ensure_ascii=False,
            default=str
        ),
        "05.24_RETURNS",

    ))


# ============================================================
# 8. SALES VALIDATION
# ============================================================

def get_sale(cursor, sales_line_id):

    cursor.execute("""
        SELECT
            sales_line_id,
            order_date,
            quantity,
            order_status

        FROM factsales

        WHERE sales_line_id = %s
    """, (sales_line_id,))

    return cursor.fetchone()


def get_total_returned(cursor, sales_line_id):

    cursor.execute("""
        SELECT
            COALESCE(
                SUM(quantity_returned),
                0
            ) AS total_quantity

        FROM factreturns

        WHERE sales_line_id = %s
    """, (sales_line_id,))

    return int(
        cursor.fetchone()["total_quantity"] or 0
    )


# ============================================================
# 9. EXISTING RETURN LOOKUP
# ============================================================

def get_existing(cursor, return_id):

    cursor.execute("""
        SELECT
            return_id,
            sales_line_id,
            return_date,
            quantity_returned,
            return_reason,
            return_status,
            refund_method,
            refund_amount,
            processed_store_id,
            record_hash

        FROM factreturns

        WHERE return_id = %s

        FOR UPDATE
    """, (return_id,))

    return cursor.fetchone()


def same_identity(old, new):

    return (

        old["sales_line_id"] == new["sales_line_id"]

        and old["return_date"] == new["return_date"]

        and int(old["quantity_returned"])
        == new["quantity_returned"]

        and old["return_reason"] == new["return_reason"]

        and (old["processed_store_id"] or None)
        == (new["processed_store_id"] or None)

    )


# ============================================================
# 10. INSERT INTO STAGING
# ============================================================

def insert_staging(
    cursor,
    record,
    batch_id,
    file_name,
    row_number,
    digest
):

    cursor.execute("""
        INSERT INTO stg_returns (

            return_id,
            sales_line_id,
            return_date,
            quantity_returned,
            return_reason,
            return_status,
            refund_method,
            refund_amount,
            processed_store_id,
            batch_id,
            source_file_name,
            source_row_number,
            record_hash,
            load_timestamp

        )

        VALUES (
            %s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,NOW()
        )
    """, (

        record["return_id"],
        record["sales_line_id"],
        record["return_date"],
        record["quantity_returned"],
        record["return_reason"],
        record["return_status"],
        record["refund_method"],
        record["refund_amount"],
        record["processed_store_id"],
        batch_id,
        file_name,
        row_number,
        digest,

    ))


# ============================================================
# 11. MERGE INTO TRUSTED FACT TABLE
# ============================================================

def merge_return(
    cursor,
    record,
    batch_id,
    file_name,
    row_number,
    digest
):

    old = get_existing(
        cursor,
        record["return_id"]
    )

    if old is None:

        cursor.execute("""
            INSERT INTO factreturns (

                return_id,
                sales_line_id,
                return_date,
                quantity_returned,
                return_reason,
                return_status,
                refund_method,
                refund_amount,
                processed_store_id,
                batch_id,
                source_file_name,
                source_row_number,
                record_hash,
                load_timestamp,
                created_at,
                updated_at

            )

            VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,NOW(),NOW(),NOW()
            )
        """, (

            record["return_id"],
            record["sales_line_id"],
            record["return_date"],
            record["quantity_returned"],
            record["return_reason"],
            record["return_status"],
            record["refund_method"],
            record["refund_amount"],
            record["processed_store_id"],
            batch_id,
            file_name,
            row_number,
            digest,

        ))

        return "inserted"

    if old["record_hash"] == digest:

        return "duplicated"

    if not same_identity(old, record):

        return "conflict"

    old_status = old["return_status"]
    new_status = record["return_status"]

    if old_status == new_status:

        return "unchanged"

    if new_status not in ALLOWED_TRANSITIONS.get(
        old_status,
        set()
    ):

        return "conflict"

    cursor.execute("""
        UPDATE factreturns

        SET
            return_status = %s,
            refund_method = %s,
            refund_amount = %s,
            batch_id = %s,
            source_file_name = %s,
            source_row_number = %s,
            record_hash = %s,
            load_timestamp = NOW(),
            updated_at = NOW()

        WHERE return_id = %s
    """, (

        new_status,
        record["refund_method"],
        record["refund_amount"],
        batch_id,
        file_name,
        row_number,
        digest,
        record["return_id"],

    ))

    return "updated"


# ============================================================
# 12. ETL FILE LOG INSERT
# ============================================================

def create_file_log(
    cursor,
    file_id,
    batch_id,
    file_name,
    file_size,
    file_hash,
    records_read,
    started
):

    cursor.execute("""
        INSERT INTO etl_file_log (

            file_id,
            batch_id,
            file_name,
            file_type,
            file_period,
            file_size_bytes,
            sha256_hash,
            schema_fingerprint,
            records_read,
            records_staged,
            records_inserted,
            records_updated,
            records_unchanged,
            records_duplicated,
            records_rejected,
            load_start_time,
            load_status,
            correction_mode,
            retry_of_file_id,
            created_at,
            updated_at

        )

        VALUES (
            %s,%s,%s,'RETURNS',NULL,%s,%s,'RETURNS_V1',
            %s,0,0,0,0,0,0,%s,'RECEIVED',
            NULL,NULL,NOW(),NOW()
        )
    """, (

        file_id,
        batch_id,
        file_name,
        file_size,
        file_hash,
        records_read,
        started,

    ))


# ============================================================
# 13. ETL FILE LOG UPDATE
# ============================================================

def update_file_log(
    cursor,
    file_id,
    counts,
    started,
    status,
    correction_mode=None,
    error=None
):

    ended = datetime.now()

    duration = Decimal(
        str(
            (ended - started).total_seconds()
        )
    ).quantize(
        Decimal("0.001")
    )

    cursor.execute("""
        UPDATE etl_file_log

        SET
            records_staged = %s,
            records_inserted = %s,
            records_updated = %s,
            records_unchanged = %s,
            records_duplicated = %s,
            records_rejected = %s,
            load_end_time = %s,
            duration_seconds = %s,
            load_status = %s,
            correction_mode = %s,
            error_class = %s,
            error_code = %s,
            error_message = %s,
            updated_at = NOW()

        WHERE file_id = %s
    """, (

        counts["staged"],
        counts["inserted"],
        counts["updated"],
        counts["unchanged"],
        counts["duplicated"],
        counts["rejected"],
        ended,
        duration,
        status,
        correction_mode,
        type(error).__name__ if error else None,
        "RETURNS_LOAD_FAILED" if error else None,
        str(error)[:1000] if error else None,
        file_id,

    ))


# ============================================================
# 14. MAIN
# ============================================================

def main():

    connection = None
    cursor = None

    started = datetime.now()

    transaction_open = False
    file_id = None
    batch_id = None

    counts = {
        "staged": 0,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "duplicated": 0,
        "rejected": 0,
    }

    try:

        if not CSV_PATH.exists():

            raise FileNotFoundError(
                f"CSV not found: {CSV_PATH}"
            )

        (
            rows,
            file_hash,
            file_size,
            batch_id
        ) = read_source()

        file_name = CSV_PATH.name
        records_read = len(rows)

        file_id = sha256(
            f"{batch_id}|{file_name}|{file_hash}".encode()
        )

        connection = mysql.connector.connect(
            **DB_CONFIG
        )

        connection.start_transaction()
        transaction_open = True

        cursor = connection.cursor(
            dictionary=True
        )

        # ----------------------------------------------------
        # CHECK IDENTICAL PREVIOUSLY SUCCESSFUL FILE
        # ----------------------------------------------------

        cursor.execute("""
            SELECT file_id

            FROM etl_file_log

            WHERE file_name = %s
              AND sha256_hash = %s
              AND load_status = 'SUCCESS'

            ORDER BY load_start_time DESC

            LIMIT 1
        """, (
            file_name,
            file_hash
        ))

        previous_success = cursor.fetchone()

        # ----------------------------------------------------
        # CHECK DIFFERENT HASH FOR SAME FILE NAME
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total

            FROM etl_file_log

            WHERE file_name = %s
              AND sha256_hash <> %s
              AND load_status = 'SUCCESS'
        """, (
            file_name,
            file_hash
        ))

        correction_candidate = (
            int(cursor.fetchone()["total"]) > 0
        )

        create_file_log(
            cursor,
            file_id,
            batch_id,
            file_name,
            file_size,
            file_hash,
            records_read,
            started
        )

        # ----------------------------------------------------
        # SAME FILE AND SAME HASH
        # ----------------------------------------------------

        if previous_success:

            counts["duplicated"] = records_read

            update_file_log(
                cursor,
                file_id,
                counts,
                started,
                "SKIPPED_DUPLICATE"
            )

            connection.commit()
            transaction_open = False

            print(
                "Same file and SHA-256 already processed."
            )

            print(
                f"Previous file ID: {previous_success['file_id']}"
            )

            print(
                f"Batch ID: {batch_id}"
            )

            print(
                "Records duplicated: "
                f"{records_read}"
            )

            print(
                "05.24 STATUS: SKIPPED_DUPLICATE"
            )

            return

        # ----------------------------------------------------
        # CORRECTION CANDIDATE
        # ----------------------------------------------------

        if correction_candidate:

            update_file_log(
                cursor,
                file_id,
                counts,
                started,
                "CORRECTION_CANDIDATE",
                correction_mode="CORRECTION_CANDIDATE"
            )

            connection.commit()
            transaction_open = False

            print(
                "A previous successful file has the same "
                "filename but a different SHA-256."
            )

            print(
                "No staging or trusted-table changes were made."
            )

            print(
                "05.24 STATUS: CORRECTION_CANDIDATE"
            )

            return

        # ----------------------------------------------------
        # PROCESS SOURCE ROWS
        # ----------------------------------------------------

        seen = {}
        pending_quantities = {}

        for source in rows:

            row_number = source["row_number"]
            raw = source["raw"]

            digest = calculate_record_hash(raw)

            try:

                record = normalize(raw)

            except ValueError as exc:

                insert_reject(
                    cursor,
                    batch_id,
                    file_name,
                    row_number,
                    clean(raw.get("return_id")),
                    digest,
                    "TYPE_PARSE",
                    str(exc),
                    raw
                )

                counts["rejected"] += 1
                continue

            canonical = {

                key: (
                    value.isoformat()
                    if isinstance(value, date)

                    else str(value)
                    if isinstance(value, Decimal)

                    else value
                )

                for key, value in record.items()

            }

            digest = calculate_record_hash(
                canonical
            )

            validation = validate(record)

            if validation:

                code, message = validation

                insert_reject(
                    cursor,
                    batch_id,
                    file_name,
                    row_number,
                    record["return_id"],
                    digest,
                    code,
                    message,
                    raw
                )

                counts["rejected"] += 1
                continue

            # ------------------------------------------------
            # DUPLICATE BUSINESS KEY WITHIN FILE
            # ------------------------------------------------

            if record["return_id"] in seen:

                if seen[record["return_id"]] == digest:

                    counts["duplicated"] += 1

                else:

                    insert_reject(
                        cursor,
                        batch_id,
                        file_name,
                        row_number,
                        record["return_id"],
                        digest,
                        "DOMAIN_INVALID",
                        "Conflicting duplicate return_id",
                        raw
                    )

                    counts["rejected"] += 1

                continue

            seen[record["return_id"]] = digest

            # ------------------------------------------------
            # VALIDATE SALES FOREIGN KEY
            # ------------------------------------------------

            sale = get_sale(
                cursor,
                record["sales_line_id"]
            )

            if (
                sale is None
                or sale["order_status"] != "Completed"
            ):

                insert_reject(
                    cursor,
                    batch_id,
                    file_name,
                    row_number,
                    record["return_id"],
                    digest,
                    "FK_UNKNOWN",
                    (
                        "sales_line_id does not reference "
                        "an existing Completed sale"
                    ),
                    raw
                )

                counts["rejected"] += 1
                continue

            # ------------------------------------------------
            # VALIDATE RETURN DATE
            # ------------------------------------------------

            if (
                record["return_date"]
                < sale["order_date"]
            ):

                insert_reject(
                    cursor,
                    batch_id,
                    file_name,
                    row_number,
                    record["return_id"],
                    digest,
                    "DOMAIN_INVALID",
                    "return_date precedes original order_date",
                    raw
                )

                counts["rejected"] += 1
                continue

            # ------------------------------------------------
            # VALIDATE CUMULATIVE QUANTITY
            # ------------------------------------------------

            existing = get_existing(
                cursor,
                record["return_id"]
            )

            if existing is not None:

                if not same_identity(
                    existing,
                    record
                ):

                    insert_reject(
                        cursor,
                        batch_id,
                        file_name,
                        row_number,
                        record["return_id"],
                        digest,
                        "DOMAIN_INVALID",
                        (
                            "Existing return_id cannot change "
                            "its sale, date, quantity, reason or store"
                        ),
                        raw
                    )

                    counts["rejected"] += 1
                    continue

                projected = get_total_returned(
                    cursor,
                    record["sales_line_id"]
                )

            else:

                projected = (
                    get_total_returned(
                        cursor,
                        record["sales_line_id"]
                    )

                    + pending_quantities.get(
                        record["sales_line_id"],
                        0
                    )

                    + record["quantity_returned"]
                )

            if projected > int(sale["quantity"]):

                insert_reject(
                    cursor,
                    batch_id,
                    file_name,
                    row_number,
                    record["return_id"],
                    digest,
                    "RETURN_EXCEEDS_SALE",
                    (
                        "Cumulative returned quantity "
                        "exceeds sold quantity"
                    ),
                    raw
                )

                counts["rejected"] += 1
                continue

            # ------------------------------------------------
            # STAGE VALID ROW
            # ------------------------------------------------

            insert_staging(
                cursor,
                record,
                batch_id,
                file_name,
                row_number,
                digest
            )

            counts["staged"] += 1

            if existing is None:

                pending_quantities[
                    record["sales_line_id"]
                ] = (
                    pending_quantities.get(
                        record["sales_line_id"],
                        0
                    )
                    + record["quantity_returned"]
                )

        # ----------------------------------------------------
        # MERGE CURRENT BATCH ONLY
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                return_id,
                sales_line_id,
                return_date,
                quantity_returned,
                return_reason,
                return_status,
                refund_method,
                refund_amount,
                processed_store_id,
                source_file_name,
                source_row_number,
                record_hash

            FROM stg_returns

            WHERE batch_id = %s

            ORDER BY staging_id
        """, (batch_id,))

        staged_rows = cursor.fetchall()

        for row in staged_rows:

            record = {

                "return_id": row["return_id"],

                "sales_line_id": row["sales_line_id"],

                "return_date": row["return_date"],

                "quantity_returned": int(
                    row["quantity_returned"]
                ),

                "return_reason": row["return_reason"],

                "return_status": row["return_status"],

                "refund_method": row["refund_method"],

                "refund_amount": row["refund_amount"],

                "processed_store_id": (
                    row["processed_store_id"]
                ),

            }

            action = merge_return(
                cursor,
                record,
                batch_id,
                row["source_file_name"],
                row["source_row_number"],
                row["record_hash"]
            )

            if action == "inserted":

                counts["inserted"] += 1

            elif action == "updated":

                counts["updated"] += 1

            elif action == "unchanged":

                counts["unchanged"] += 1

            elif action == "duplicated":

                counts["duplicated"] += 1

            else:

                insert_reject(
                    cursor,
                    batch_id,
                    file_name,
                    row["source_row_number"],
                    row["return_id"],
                    row["record_hash"],
                    "DOMAIN_INVALID",
                    (
                        "Existing return status transition "
                        "is not permitted"
                    ),
                    record
                )

                counts["rejected"] += 1

        # ----------------------------------------------------
        # RECONCILIATION
        # ----------------------------------------------------

        classified = (
            counts["inserted"]
            + counts["updated"]
            + counts["unchanged"]
            + counts["duplicated"]
            + counts["rejected"]
        )

        if classified != records_read:

            raise RuntimeError(
                f"Reconciliation failed: "
                f"records_read={records_read}, "
                f"classified={classified}"
            )

        # ----------------------------------------------------
        # UPDATE FILE AUDIT
        # ----------------------------------------------------

        update_file_log(
            cursor,
            file_id,
            counts,
            started,
            "SUCCESS"
        )

        connection.commit()
        transaction_open = False

        # ----------------------------------------------------
        # FINAL SUMMARY
        # ----------------------------------------------------

        print("=" * 70)

        print(f"Batch ID             : {batch_id}")

        print(f"File SHA-256         : {file_hash}")

        print(f"Records read         : {records_read}")

        print(f"Records staged       : {counts['staged']}")

        print(f"Records inserted     : {counts['inserted']}")

        print(f"Records updated      : {counts['updated']}")

        print(f"Records unchanged    : {counts['unchanged']}")

        print(f"Records duplicated   : {counts['duplicated']}")

        print(f"Records rejected     : {counts['rejected']}")

        print(f"Reconciled           : {classified}")

        print("Reconciliation       : PASS")

        print("05.24 STATUS         : PASS")

    except Exception as exc:

        if (
            connection is not None
            and transaction_open
        ):

            connection.rollback()
            transaction_open = False

        # ----------------------------------------------------
        # FAILURE AUDIT
        # ----------------------------------------------------

        if (
            connection is not None
            and connection.is_connected()
            and file_id
        ):

            try:

                connection.start_transaction()

                cursor = connection.cursor(
                    dictionary=True
                )

                update_file_log(
                    cursor,
                    file_id,
                    counts,
                    started,
                    "FAILED",
                    error=exc
                )

                connection.commit()

            except Exception:

                connection.rollback()

        print(
            f"05.24 STATUS: FAILED - {exc}"
        )

        raise

    finally:

        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):

            connection.close()


if __name__ == "__main__":
    main()

