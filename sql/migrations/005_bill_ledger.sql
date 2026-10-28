-- Migration 005: supplementary invoice items and payment ledger.
-- UNTESTED ON ORACLE. Stop all writers. Rehearse on a disposable backup after
-- migrations 001-004. Oracle DDL commits implicitly; recovery requires a backup.
-- Existing Bill charges remain the opening basis and legacy Paid/Pending remains
-- historical. No payment event is inferred or fabricated from the legacy label.
SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
DECLARE n NUMBER;
BEGIN
    SELECT COUNT(*) INTO n FROM user_objects WHERE object_name IN ('BILL_ITEM','BILL_PAYMENT','IX_ITEM_BILL','IX_PAYMENT_BILL');
    IF n > 0 THEN RAISE_APPLICATION_ERROR(-20130, 'Billing objects already exist; inspect partial migration.'); END IF;
END;
/
-- Additional itemized charges and actual payment events. The three legacy Bill
-- categories remain the opening charge basis; Paid/Pending is not a payment.
CREATE TABLE Bill_Item (
    item_id NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    bill_id NUMBER(10) NOT NULL,
    description VARCHAR2(200) NOT NULL,
    quantity NUMBER(8) NOT NULL,
    unit_price NUMBER(10,2) NOT NULL,
    line_total NUMBER(18,2) GENERATED ALWAYS AS (quantity * unit_price) VIRTUAL,
    CONSTRAINT pk_bill_item PRIMARY KEY (item_id),
    CONSTRAINT fk_item_bill FOREIGN KEY (bill_id) REFERENCES Bill (bill_id),
    CONSTRAINT ck_item_quantity CHECK (quantity BETWEEN 1 AND 99999999),
    CONSTRAINT ck_item_price CHECK (unit_price >= 0)
);
CREATE INDEX ix_item_bill ON Bill_Item (bill_id);

CREATE TABLE Bill_Payment (
    payment_id NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    bill_id NUMBER(10) NOT NULL,
    amount NUMBER(11,2) NOT NULL,
    payment_method VARCHAR2(20) NOT NULL,
    reference VARCHAR2(100),
    idempotency_key VARCHAR2(36) NOT NULL,
    recorded_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT pk_bill_payment PRIMARY KEY (payment_id),
    CONSTRAINT uq_payment_request UNIQUE (idempotency_key),
    CONSTRAINT fk_payment_bill FOREIGN KEY (bill_id) REFERENCES Bill (bill_id),
    CONSTRAINT ck_payment_amount CHECK (amount > 0),
    CONSTRAINT ck_payment_method CHECK (payment_method IN ('Cash', 'Card', 'Transfer', 'Other'))
);
CREATE INDEX ix_payment_bill ON Bill_Payment (bill_id);

-- Items are editable only before the first payment. Serialize all invoice
-- changes on the same parent row; direct SQL follows the same protocol.
CREATE OR REPLACE TRIGGER trg_bill_item_guard
BEFORE INSERT OR UPDATE OR DELETE ON Bill_Item
FOR EACH ROW
DECLARE
    v_bill NUMBER;
    v_lock NUMBER;
    v_payments NUMBER;
BEGIN
    IF UPDATING AND :OLD.bill_id <> :NEW.bill_id THEN
        RAISE_APPLICATION_ERROR(-20031, 'Item ownership is immutable.');
    END IF;
    IF DELETING THEN v_bill := :OLD.bill_id; ELSE v_bill := :NEW.bill_id; END IF;
    SELECT bill_id INTO v_lock FROM Bill WHERE bill_id = v_bill FOR UPDATE;
    SELECT COUNT(*) INTO v_payments FROM Bill_Payment WHERE bill_id = v_bill;
    IF v_payments > 0 THEN RAISE_APPLICATION_ERROR(-20031, 'Charges cannot change after payment.'); END IF;
END;
/

CREATE OR REPLACE TRIGGER trg_bill_charge_guard
BEFORE UPDATE OF consultation_charge, room_charge, medicine_charge ON Bill
FOR EACH ROW
DECLARE v_payments NUMBER;
BEGIN
    IF :OLD.consultation_charge <> :NEW.consultation_charge OR :OLD.room_charge <> :NEW.room_charge
       OR :OLD.medicine_charge <> :NEW.medicine_charge THEN
        SELECT COUNT(*) INTO v_payments FROM Bill_Payment WHERE bill_id = :OLD.bill_id;
        IF v_payments > 0 THEN RAISE_APPLICATION_ERROR(-20031, 'Charges cannot change after payment.'); END IF;
    END IF;
END;
/

-- Payment rows are append-only. Check totals after the DML statement, avoiding
-- a query of the mutating payment table. The bill row locks serialize inserts.
CREATE OR REPLACE TRIGGER trg_bill_payment_guard
FOR INSERT OR UPDATE OR DELETE ON Bill_Payment
COMPOUND TRIGGER
    TYPE bill_map IS TABLE OF NUMBER INDEX BY VARCHAR2(10);
    g_bills bill_map;
    BEFORE EACH ROW IS
        v_lock NUMBER;
        v_key VARCHAR2(10);
    BEGIN
        IF UPDATING OR DELETING THEN
            RAISE_APPLICATION_ERROR(-20032, 'Payment history cannot be changed or deleted.');
        END IF;
        SELECT bill_id INTO v_lock FROM Bill WHERE bill_id = :NEW.bill_id FOR UPDATE;
        v_key := LPAD(TO_CHAR(:NEW.bill_id, 'FM9999999990'), 10, '0');
        g_bills(v_key) := :NEW.bill_id;
    END BEFORE EACH ROW;
    AFTER STATEMENT IS
        v_key VARCHAR2(10);
        v_bill NUMBER;
        v_total NUMBER;
        v_paid NUMBER;
    BEGIN
        v_key := g_bills.FIRST;
        WHILE v_key IS NOT NULL LOOP
            v_bill := g_bills(v_key);
            SELECT b.total_amount + NVL((SELECT SUM(i.line_total) FROM Bill_Item i WHERE i.bill_id = b.bill_id), 0)
              INTO v_total FROM Bill b WHERE b.bill_id = v_bill;
            SELECT NVL(SUM(amount), 0) INTO v_paid FROM Bill_Payment WHERE bill_id = v_bill;
            IF v_paid > v_total THEN RAISE_APPLICATION_ERROR(-20033, 'Payment exceeds outstanding balance.'); END IF;
            v_key := g_bills.NEXT(v_key);
        END LOOP;
    END AFTER STATEMENT;
END trg_bill_payment_guard;
/

DECLARE n NUMBER;
BEGIN
    SELECT COUNT(*) INTO n FROM user_objects WHERE object_type = 'TRIGGER' AND status = 'VALID'
      AND object_name IN ('TRG_BILL_ITEM_GUARD','TRG_BILL_CHARGE_GUARD','TRG_BILL_PAYMENT_GUARD');
    IF n <> 3 THEN RAISE_APPLICATION_ERROR(-20131, 'Billing triggers invalid; inspect USER_ERRORS.'); END IF;
END;
/
