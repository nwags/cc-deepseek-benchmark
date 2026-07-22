--
-- PostgreSQL database dump
--

\restrict kh6BHxifo9AtAOIuEqHXgUR2eOHlAACe0qzgEWg1yg3eo7TavxChkN8sgjSUDQy

-- Dumped from database version 17.6
-- Dumped by pg_dump version 17.10 (Debian 17.10-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: benchmark; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA benchmark;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: benchmark_arms; Type: TABLE; Schema: benchmark; Owner: -
--

CREATE TABLE benchmark.benchmark_arms (
    arm_id text NOT NULL,
    display_name text,
    provider_family text,
    backend_model text,
    router_model text,
    agent_harness text,
    config_path text,
    config_sha256 text,
    active boolean DEFAULT true NOT NULL,
    notes text,
    raw_config jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: benchmark_artifacts; Type: TABLE; Schema: benchmark; Owner: -
--

CREATE TABLE benchmark.benchmark_artifacts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    run_id uuid,
    trial_id uuid,
    artifact_type text NOT NULL,
    local_path text,
    r2_uri text,
    github_uri text,
    sha256 text,
    size_bytes bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    retention_class text DEFAULT 'pilot'::text NOT NULL,
    notes text
);


--
-- Name: benchmark_models; Type: TABLE; Schema: benchmark; Owner: -
--

CREATE TABLE benchmark.benchmark_models (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    provider_family text NOT NULL,
    model_slug text NOT NULL,
    endpoint_base text,
    endpoint_region text,
    context_window integer,
    pricing_input_per_million numeric,
    pricing_output_per_million numeric,
    pricing_source_uri text,
    active boolean DEFAULT true NOT NULL,
    notes text,
    raw_metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: benchmark_runs; Type: TABLE; Schema: benchmark; Owner: -
--

CREATE TABLE benchmark.benchmark_runs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    phase text NOT NULL,
    mode text NOT NULL,
    run_label text,
    git_commit text,
    branch text,
    runner_name text,
    runner_provider text,
    runner_region text,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    status text DEFAULT 'unknown'::text NOT NULL,
    notes text,
    raw_metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: benchmark_tasks; Type: TABLE; Schema: benchmark; Owner: -
--

CREATE TABLE benchmark.benchmark_tasks (
    task_id text NOT NULL,
    benchmark text DEFAULT 'terminal-bench'::text NOT NULL,
    benchmark_version text,
    task_name text NOT NULL,
    task_source_uri text,
    contamination_notes text,
    active boolean DEFAULT true NOT NULL,
    raw_metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: benchmark_trials; Type: TABLE; Schema: benchmark; Owner: -
--

CREATE TABLE benchmark.benchmark_trials (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    run_id uuid,
    arm_id text,
    task_id text,
    attempt_index integer,
    reward numeric,
    exception_type text,
    exception_summary text,
    runtime_seconds numeric,
    input_tokens bigint,
    cache_tokens bigint,
    output_tokens bigint,
    cost_usd numeric,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    result_local_path text,
    result_artifact_uri text,
    notes text,
    raw_result jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contamination_audits; Type: TABLE; Schema: benchmark; Owner: -
--

CREATE TABLE benchmark.contamination_audits (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    run_id uuid,
    trial_id uuid,
    audit_status text NOT NULL,
    websearch_events integer DEFAULT 0 NOT NULL,
    webfetch_events integer DEFAULT 0 NOT NULL,
    forbidden_tools_available integer DEFAULT 0 NOT NULL,
    disallowed_tools text,
    audit_local_path text,
    audit_artifact_uri text,
    notes text,
    raw_audit jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: cost_forecasts; Type: TABLE; Schema: benchmark; Owner: -
--

CREATE TABLE benchmark.cost_forecasts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    forecast_name text NOT NULL,
    source_run_id uuid,
    method text NOT NULL,
    arms_included integer,
    task_count integer,
    attempts_per_task integer,
    estimated_cost_usd numeric,
    reserve_multiplier numeric,
    reserve_cost_usd numeric,
    notes text,
    raw_forecast jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: v_dashboard_arms; Type: VIEW; Schema: benchmark; Owner: -
--

CREATE VIEW benchmark.v_dashboard_arms AS
 SELECT a.arm_id,
    a.display_name,
    a.provider_family,
    a.backend_model,
    a.router_model,
    a.agent_harness,
    a.config_path,
    a.active,
    count(DISTINCT r.id) AS run_count,
    count(t.id) AS trial_count,
    count(t.id) FILTER (WHERE (COALESCE(t.reward, (0)::numeric) >= (1)::numeric)) AS success_count,
        CASE
            WHEN (count(t.id) = 0) THEN NULL::numeric
            ELSE ((count(t.id) FILTER (WHERE (COALESCE(t.reward, (0)::numeric) >= (1)::numeric)))::numeric / (count(t.id))::numeric)
        END AS pass_rate,
    sum(t.cost_usd) AS trial_cost_usd,
    count(t.cost_usd) AS cost_row_count,
    count(t.id) FILTER (WHERE (t.cost_usd IS NULL)) AS missing_cost_count,
    avg(t.runtime_seconds) AS avg_runtime_seconds,
    percentile_cont((0.5)::double precision) WITHIN GROUP (ORDER BY ((t.runtime_seconds)::double precision)) AS median_runtime_seconds
   FROM ((benchmark.benchmark_arms a
     LEFT JOIN benchmark.benchmark_trials t ON ((t.arm_id = a.arm_id)))
     LEFT JOIN benchmark.benchmark_runs r ON ((r.id = t.run_id)))
  GROUP BY a.arm_id, a.display_name, a.provider_family, a.backend_model, a.router_model, a.agent_harness, a.config_path, a.active;


--
-- Name: v_run_artifact_summary; Type: VIEW; Schema: benchmark; Owner: -
--

CREATE VIEW benchmark.v_run_artifact_summary AS
 SELECT run_id,
    count(*) AS artifact_count,
    sum(size_bytes) AS artifact_size_bytes,
    count(*) FILTER (WHERE (r2_uri IS NOT NULL)) AS r2_artifact_count
   FROM benchmark.benchmark_artifacts
  GROUP BY run_id;


--
-- Name: v_run_audit_summary; Type: VIEW; Schema: benchmark; Owner: -
--

CREATE VIEW benchmark.v_run_audit_summary AS
 SELECT run_id,
    count(*) AS audit_count,
    count(*) FILTER (WHERE (audit_status = 'pass'::text)) AS audit_pass_count,
    count(*) FILTER (WHERE (audit_status <> 'pass'::text)) AS audit_nonpass_count,
    sum(websearch_events) AS websearch_events,
    sum(webfetch_events) AS webfetch_events,
    sum(forbidden_tools_available) AS forbidden_tools_available
   FROM benchmark.contamination_audits
  GROUP BY run_id;


--
-- Name: v_run_trial_summary; Type: VIEW; Schema: benchmark; Owner: -
--

CREATE VIEW benchmark.v_run_trial_summary AS
 SELECT run_id,
    count(*) AS trial_count,
    count(*) FILTER (WHERE (COALESCE(reward, (0)::numeric) >= (1)::numeric)) AS success_count,
    count(*) FILTER (WHERE (COALESCE(reward, (0)::numeric) < (1)::numeric)) AS failure_count,
    avg(runtime_seconds) AS avg_runtime_seconds,
    percentile_cont((0.5)::double precision) WITHIN GROUP (ORDER BY ((runtime_seconds)::double precision)) AS median_runtime_seconds,
    sum(cost_usd) AS trial_cost_usd,
    count(cost_usd) AS cost_row_count,
    count(*) FILTER (WHERE (cost_usd IS NULL)) AS missing_cost_count,
    sum(input_tokens) AS input_tokens,
    sum(cache_tokens) AS cache_tokens,
    sum(output_tokens) AS output_tokens
   FROM benchmark.benchmark_trials
  GROUP BY run_id;


--
-- Name: v_dashboard_runs; Type: VIEW; Schema: benchmark; Owner: -
--

CREATE VIEW benchmark.v_dashboard_runs AS
 SELECT r.id AS run_id,
    r.phase,
    r.mode,
    r.run_label,
    r.git_commit,
    r.branch,
    r.runner_name,
    r.runner_provider,
    r.runner_region,
    r.started_at,
    r.finished_at,
    r.status,
    r.created_at,
    r.raw_metadata,
    COALESCE(ts.trial_count, (0)::bigint) AS trial_count,
    COALESCE(ts.success_count, (0)::bigint) AS success_count,
    COALESCE(ts.failure_count, (0)::bigint) AS failure_count,
        CASE
            WHEN (COALESCE(ts.trial_count, (0)::bigint) = 0) THEN NULL::numeric
            ELSE ((ts.success_count)::numeric / (ts.trial_count)::numeric)
        END AS pass_rate,
    ts.avg_runtime_seconds,
    ts.median_runtime_seconds,
    COALESCE(ts.trial_cost_usd, (0)::numeric) AS trial_cost_usd,
    COALESCE(ts.cost_row_count, (0)::bigint) AS cost_row_count,
    COALESCE(ts.missing_cost_count, (0)::bigint) AS missing_cost_count,
    COALESCE(ts.input_tokens, (0)::numeric) AS input_tokens,
    COALESCE(ts.cache_tokens, (0)::numeric) AS cache_tokens,
    COALESCE(ts.output_tokens, (0)::numeric) AS output_tokens,
    COALESCE(art.artifact_count, (0)::bigint) AS artifact_count,
    COALESCE(art.artifact_size_bytes, (0)::numeric) AS artifact_size_bytes,
    COALESCE(art.r2_artifact_count, (0)::bigint) AS r2_artifact_count,
    COALESCE(aud.audit_count, (0)::bigint) AS audit_count,
    COALESCE(aud.audit_pass_count, (0)::bigint) AS audit_pass_count,
    COALESCE(aud.audit_nonpass_count, (0)::bigint) AS audit_nonpass_count,
    COALESCE(aud.websearch_events, (0)::bigint) AS websearch_events,
    COALESCE(aud.webfetch_events, (0)::bigint) AS webfetch_events,
    COALESCE(aud.forbidden_tools_available, (0)::bigint) AS forbidden_tools_available
   FROM (((benchmark.benchmark_runs r
     LEFT JOIN benchmark.v_run_trial_summary ts ON ((ts.run_id = r.id)))
     LEFT JOIN benchmark.v_run_artifact_summary art ON ((art.run_id = r.id)))
     LEFT JOIN benchmark.v_run_audit_summary aud ON ((aud.run_id = r.id)));


--
-- Name: v_dashboard_tasks; Type: VIEW; Schema: benchmark; Owner: -
--

CREATE VIEW benchmark.v_dashboard_tasks AS
 SELECT task.task_id,
    task.benchmark,
    task.benchmark_version,
    task.task_name,
    task.active,
    count(t.id) AS trial_count,
    count(t.id) FILTER (WHERE (COALESCE(t.reward, (0)::numeric) >= (1)::numeric)) AS success_count,
        CASE
            WHEN (count(t.id) = 0) THEN NULL::numeric
            ELSE ((count(t.id) FILTER (WHERE (COALESCE(t.reward, (0)::numeric) >= (1)::numeric)))::numeric / (count(t.id))::numeric)
        END AS pass_rate,
    avg(t.runtime_seconds) AS avg_runtime_seconds,
    percentile_cont((0.5)::double precision) WITHIN GROUP (ORDER BY ((t.runtime_seconds)::double precision)) AS median_runtime_seconds,
    sum(t.cost_usd) AS trial_cost_usd,
    count(t.cost_usd) AS cost_row_count,
    count(t.id) FILTER (WHERE (t.cost_usd IS NULL)) AS missing_cost_count
   FROM (benchmark.benchmark_tasks task
     LEFT JOIN benchmark.benchmark_trials t ON ((t.task_id = task.task_id)))
  GROUP BY task.task_id, task.benchmark, task.benchmark_version, task.task_name, task.active;


--
-- Name: benchmark_arms benchmark_arms_pkey; Type: CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.benchmark_arms
    ADD CONSTRAINT benchmark_arms_pkey PRIMARY KEY (arm_id);


--
-- Name: benchmark_artifacts benchmark_artifacts_pkey; Type: CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.benchmark_artifacts
    ADD CONSTRAINT benchmark_artifacts_pkey PRIMARY KEY (id);


--
-- Name: benchmark_models benchmark_models_pkey; Type: CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.benchmark_models
    ADD CONSTRAINT benchmark_models_pkey PRIMARY KEY (id);


--
-- Name: benchmark_models benchmark_models_provider_family_model_slug_key; Type: CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.benchmark_models
    ADD CONSTRAINT benchmark_models_provider_family_model_slug_key UNIQUE (provider_family, model_slug);


--
-- Name: benchmark_runs benchmark_runs_pkey; Type: CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.benchmark_runs
    ADD CONSTRAINT benchmark_runs_pkey PRIMARY KEY (id);


--
-- Name: benchmark_tasks benchmark_tasks_pkey; Type: CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.benchmark_tasks
    ADD CONSTRAINT benchmark_tasks_pkey PRIMARY KEY (task_id);


--
-- Name: benchmark_trials benchmark_trials_pkey; Type: CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.benchmark_trials
    ADD CONSTRAINT benchmark_trials_pkey PRIMARY KEY (id);


--
-- Name: contamination_audits contamination_audits_pkey; Type: CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.contamination_audits
    ADD CONSTRAINT contamination_audits_pkey PRIMARY KEY (id);


--
-- Name: cost_forecasts cost_forecasts_pkey; Type: CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.cost_forecasts
    ADD CONSTRAINT cost_forecasts_pkey PRIMARY KEY (id);


--
-- Name: idx_benchmark_artifacts_run; Type: INDEX; Schema: benchmark; Owner: -
--

CREATE INDEX idx_benchmark_artifacts_run ON benchmark.benchmark_artifacts USING btree (run_id);


--
-- Name: idx_benchmark_runs_phase_mode; Type: INDEX; Schema: benchmark; Owner: -
--

CREATE INDEX idx_benchmark_runs_phase_mode ON benchmark.benchmark_runs USING btree (phase, mode);


--
-- Name: idx_benchmark_runs_phase_mode_run_label_unique; Type: INDEX; Schema: benchmark; Owner: -
--

CREATE UNIQUE INDEX idx_benchmark_runs_phase_mode_run_label_unique ON benchmark.benchmark_runs USING btree (phase, mode, run_label);


--
-- Name: idx_benchmark_trials_run_arm; Type: INDEX; Schema: benchmark; Owner: -
--

CREATE INDEX idx_benchmark_trials_run_arm ON benchmark.benchmark_trials USING btree (run_id, arm_id);


--
-- Name: idx_benchmark_trials_task; Type: INDEX; Schema: benchmark; Owner: -
--

CREATE INDEX idx_benchmark_trials_task ON benchmark.benchmark_trials USING btree (task_id);


--
-- Name: idx_contamination_audits_run; Type: INDEX; Schema: benchmark; Owner: -
--

CREATE INDEX idx_contamination_audits_run ON benchmark.contamination_audits USING btree (run_id);


--
-- Name: benchmark_artifacts benchmark_artifacts_run_id_fkey; Type: FK CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.benchmark_artifacts
    ADD CONSTRAINT benchmark_artifacts_run_id_fkey FOREIGN KEY (run_id) REFERENCES benchmark.benchmark_runs(id) ON DELETE CASCADE;


--
-- Name: benchmark_artifacts benchmark_artifacts_trial_id_fkey; Type: FK CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.benchmark_artifacts
    ADD CONSTRAINT benchmark_artifacts_trial_id_fkey FOREIGN KEY (trial_id) REFERENCES benchmark.benchmark_trials(id) ON DELETE CASCADE;


--
-- Name: benchmark_trials benchmark_trials_arm_id_fkey; Type: FK CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.benchmark_trials
    ADD CONSTRAINT benchmark_trials_arm_id_fkey FOREIGN KEY (arm_id) REFERENCES benchmark.benchmark_arms(arm_id);


--
-- Name: benchmark_trials benchmark_trials_run_id_fkey; Type: FK CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.benchmark_trials
    ADD CONSTRAINT benchmark_trials_run_id_fkey FOREIGN KEY (run_id) REFERENCES benchmark.benchmark_runs(id) ON DELETE CASCADE;


--
-- Name: benchmark_trials benchmark_trials_task_id_fkey; Type: FK CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.benchmark_trials
    ADD CONSTRAINT benchmark_trials_task_id_fkey FOREIGN KEY (task_id) REFERENCES benchmark.benchmark_tasks(task_id);


--
-- Name: contamination_audits contamination_audits_run_id_fkey; Type: FK CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.contamination_audits
    ADD CONSTRAINT contamination_audits_run_id_fkey FOREIGN KEY (run_id) REFERENCES benchmark.benchmark_runs(id) ON DELETE CASCADE;


--
-- Name: contamination_audits contamination_audits_trial_id_fkey; Type: FK CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.contamination_audits
    ADD CONSTRAINT contamination_audits_trial_id_fkey FOREIGN KEY (trial_id) REFERENCES benchmark.benchmark_trials(id) ON DELETE CASCADE;


--
-- Name: cost_forecasts cost_forecasts_source_run_id_fkey; Type: FK CONSTRAINT; Schema: benchmark; Owner: -
--

ALTER TABLE ONLY benchmark.cost_forecasts
    ADD CONSTRAINT cost_forecasts_source_run_id_fkey FOREIGN KEY (source_run_id) REFERENCES benchmark.benchmark_runs(id) ON DELETE SET NULL;


--
-- Name: benchmark_arms; Type: ROW SECURITY; Schema: benchmark; Owner: -
--

ALTER TABLE benchmark.benchmark_arms ENABLE ROW LEVEL SECURITY;

--
-- Name: benchmark_artifacts; Type: ROW SECURITY; Schema: benchmark; Owner: -
--

ALTER TABLE benchmark.benchmark_artifacts ENABLE ROW LEVEL SECURITY;

--
-- Name: benchmark_models; Type: ROW SECURITY; Schema: benchmark; Owner: -
--

ALTER TABLE benchmark.benchmark_models ENABLE ROW LEVEL SECURITY;

--
-- Name: benchmark_runs; Type: ROW SECURITY; Schema: benchmark; Owner: -
--

ALTER TABLE benchmark.benchmark_runs ENABLE ROW LEVEL SECURITY;

--
-- Name: benchmark_tasks; Type: ROW SECURITY; Schema: benchmark; Owner: -
--

ALTER TABLE benchmark.benchmark_tasks ENABLE ROW LEVEL SECURITY;

--
-- Name: benchmark_trials; Type: ROW SECURITY; Schema: benchmark; Owner: -
--

ALTER TABLE benchmark.benchmark_trials ENABLE ROW LEVEL SECURITY;

--
-- Name: contamination_audits; Type: ROW SECURITY; Schema: benchmark; Owner: -
--

ALTER TABLE benchmark.contamination_audits ENABLE ROW LEVEL SECURITY;

--
-- Name: cost_forecasts; Type: ROW SECURITY; Schema: benchmark; Owner: -
--

ALTER TABLE benchmark.cost_forecasts ENABLE ROW LEVEL SECURITY;

--
-- PostgreSQL database dump complete
--

\unrestrict kh6BHxifo9AtAOIuEqHXgUR2eOHlAACe0qzgEWg1yg3eo7TavxChkN8sgjSUDQy

