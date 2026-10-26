"""Audited least-privilege operator scope command and immutable integration identities."""
from alembic import op

revision = '52b01026'
down_revision = '52a01026'
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    CREATE FUNCTION public.operator_assign_scope(p_actor text,p_target text,p_role text,
      p_scope_type text,p_scope_id text,p_enabled boolean,p_until timestamptz,p_reason text,p_request text)
    RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path = public,pg_temp AS $$
    DECLARE tenant text; binding text; prior jsonb;
    BEGIN
      IF p_actor=p_target OR NOT EXISTS(SELECT 1 FROM principals WHERE subject=p_actor AND enabled)
        OR NOT EXISTS(SELECT 1 FROM role_bindings WHERE subject=p_actor AND role='OPERATOR'
          AND scope_type='BUREAU' AND scope_id='PLATFORM' AND enabled AND valid_from<=now()
          AND (valid_until IS NULL OR valid_until>now())) THEN
        RAISE EXCEPTION 'Technical operator scope required; self-grants prohibited';
      END IF;
      IF p_role NOT IN ('REVIEWER','AUDITOR','CLEARANCE','APPROVER','ISSUER')
        OR length(trim(p_reason))<10 OR length(p_reason)>2000
        OR p_until IS NULL OR p_until<=now() OR p_until>now()+interval '90 days'
        OR NOT EXISTS(SELECT 1 FROM principals WHERE subject=p_target AND enabled) THEN
        RAISE EXCEPTION 'Invalid target, role, validity or reason';
      END IF;
      IF p_scope_type='INSTITUTION' THEN
        SELECT id INTO tenant FROM institutions WHERE id=p_scope_id;
      ELSIF p_scope_type='CASE' THEN
        SELECT institution_id INTO tenant FROM release_cases WHERE id=p_scope_id;
      ELSIF p_scope_type='BUREAU' THEN
        IF NOT ((p_role='CLEARANCE' AND p_scope_id IN ('PGRC','VIGILANCE','GRANTS')) OR
                (p_role='ISSUER' AND p_scope_id IN ('APPROVAL_BUREAU','COUNCIL'))) THEN
          RAISE EXCEPTION 'Incompatible bureau role';
        END IF;
        SELECT rb.scope_id INTO tenant FROM role_bindings rb JOIN institutions i ON i.id=rb.scope_id
          WHERE rb.subject=p_target AND rb.scope_type='INSTITUTION' AND rb.enabled AND rb.valid_from<=now()
          AND (rb.valid_until IS NULL OR rb.valid_until>now()) ORDER BY rb.id LIMIT 1;
        IF tenant IS NULL THEN
          SELECT c.institution_id INTO tenant FROM role_bindings rb JOIN release_cases c ON c.id=rb.scope_id
            WHERE rb.subject=p_target AND rb.scope_type='CASE' AND rb.enabled AND rb.valid_from<=now()
            AND (rb.valid_until IS NULL OR rb.valid_until>now()) ORDER BY rb.id LIMIT 1;
        END IF;
      END IF;
      IF tenant IS NULL THEN RAISE EXCEPTION 'Existing institution/case access scope required'; END IF;
      SELECT to_jsonb(r) INTO prior FROM role_bindings r WHERE subject=p_target AND role=p_role
        AND scope_type=p_scope_type AND scope_id=p_scope_id FOR UPDATE;
      INSERT INTO role_bindings(id,subject,role,scope_type,scope_id,enabled,valid_from,valid_until)
        VALUES(gen_random_uuid()::text,p_target,p_role,p_scope_type,p_scope_id,p_enabled,now(),p_until)
        ON CONFLICT(subject,role,scope_type,scope_id) DO UPDATE SET enabled=EXCLUDED.enabled,
          valid_until=EXCLUDED.valid_until RETURNING id INTO binding;
      INSERT INTO audit_events(id,institution_id,actor,action,aggregate_id,detail,request_id,created_at)
        VALUES(gen_random_uuid()::text,tenant,p_actor,'OPERATOR_SCOPE_CHANGED',binding,
          jsonb_build_object('subject',p_target,'role',p_role,'scope_type',p_scope_type,'scope_id',p_scope_id,
          'enabled',p_enabled,'valid_until',p_until,'reason',p_reason,'prior',prior),p_request,now());
      RETURN binding;
    END; $$;
    REVOKE ALL ON FUNCTION public.operator_assign_scope(text,text,text,text,text,boolean,timestamptz,text,text) FROM PUBLIC;
    CREATE FUNCTION public.guard_integration_identity() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.state IN ('SUCCEEDED','STALE') OR
        ROW(NEW.institution_id,NEW.deposit_id,NEW.case_id,NEW.operation,NEW.requested_by,NEW.input_revision,
            NEW.payload::jsonb,NEW.trace_context::jsonb,NEW.created_at)
        IS DISTINCT FROM
        ROW(OLD.institution_id,OLD.deposit_id,OLD.case_id,OLD.operation,OLD.requested_by,OLD.input_revision,
            OLD.payload::jsonb,OLD.trace_context::jsonb,OLD.created_at) THEN
        RAISE EXCEPTION 'Integration request identity and completed evidence are immutable';
      END IF;
      RETURN NEW;
    END; $$;
    CREATE TRIGGER integration_identity BEFORE UPDATE ON integration_requests FOR EACH ROW EXECUTE FUNCTION guard_integration_identity();
    """)


def downgrade():
    raise RuntimeError('Forward migration only; retain scope/evidence history')
