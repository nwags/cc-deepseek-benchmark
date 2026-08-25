-- Cost-authority semantics for routed/custom-model harness runs.
--
-- benchmark_trials.cost_usd remains immutable harness-recorded artifact cost.
-- benchmark_trial_cost_coverage.adjusted_cost_usd is the selected adjusted-cost
-- evidence and may intentionally be NULL even when recorded_cost_usd is present.
--
-- Therefore:
--   * trial known_accounting_gap_usd is NULL when adjusted cost is unresolved;
--   * aggregate known-accounting gaps compare adjusted cost only against
--     recorded cost for rows that also have selected adjusted cost;
--   * unresolved routed harness cost is never converted into a fictitious
--     negative accounting gap.

create or replace view benchmark.v_trial_adjusted_cost_coverage as
select
    c.*,
    (c.adjusted_cost_usd is not null) as has_adjusted_cost,
    case
        when c.adjusted_cost_usd is null then null::numeric
        else
            c.adjusted_cost_usd
            - coalesce(c.recorded_cost_usd, 0::numeric)
    end as known_accounting_gap_usd
from benchmark.benchmark_trial_cost_coverage c
where not exists (
    select 1
    from benchmark.benchmark_invalid_arm_runs invalid
    where invalid.suite_id = c.suite_id
      and invalid.arm_id = c.arm_id
      and invalid.run_label = c.run_label
);

create or replace view benchmark.v_arm_adjusted_cost_coverage as
select
    suite_id,
    arm_id,
    count(distinct run_label)::integer as arm_run_count,
    count(*)::integer as trial_count,
    count(*) filter (
        where outcome_bucket in (
            'clean_success',
            'exception_with_success_signal'
        )
    )::integer as success_count,
    count(*) filter (
        where outcome_bucket = 'clean_success'
    )::integer as clean_success_count,
    count(*) filter (
        where outcome_bucket = 'exception_with_success_signal'
    )::integer as exception_success_signal_count,
    count(*) filter (
        where outcome_bucket not in (
            'clean_success',
            'exception_with_success_signal'
        )
    )::integer as failure_or_incomplete_count,
    round(
        count(*) filter (
            where outcome_bucket in (
                'clean_success',
                'exception_with_success_signal'
            )
        )::numeric
        / nullif(count(*), 0)::numeric,
        4
    ) as raw_pass_rate,
    coalesce(
        sum(recorded_cost_usd),
        0::numeric
    ) as recorded_cost_usd,
    count(*) filter (
        where recorded_cost_usd is null
    )::integer as missing_recorded_cost_count,
    count(*) filter (
        where recorded_cost_usd is null
          and (
              coalesce(input_tokens, 0)
              + coalesce(cache_tokens, 0)
              + coalesce(output_tokens, 0)
          ) > 0
    )::integer as missing_cost_with_visible_tokens_count,
    coalesce(
        sum(token_reconstructed_cost_usd),
        0::numeric
    ) as token_reconstructed_missing_cost_usd,
    coalesce(
        sum(empirical_reconstructed_cost_usd),
        0::numeric
    ) as empirical_reconstructed_missing_cost_usd,
    count(*) filter (
        where adjusted_cost_usd is null
    )::integer as unresolved_cost_count,
    coalesce(
        sum(adjusted_cost_usd),
        0::numeric
    ) as adjusted_known_cost_usd,
    (
        coalesce(
            sum(adjusted_cost_usd),
            0::numeric
        )
        -
        coalesce(
            sum(recorded_cost_usd) filter (
                where adjusted_cost_usd is not null
            ),
            0::numeric
        )
    ) as known_accounting_gap_usd,
    coalesce(
        sum(adjusted_cost_usd) filter (
            where outcome_bucket = 'clean_success'
        ),
        0::numeric
    ) as adjusted_clean_success_cost_usd,
    coalesce(
        sum(adjusted_cost_usd) filter (
            where outcome_bucket = 'exception_with_success_signal'
        ),
        0::numeric
    ) as adjusted_exception_success_signal_cost_usd,
    coalesce(
        sum(adjusted_cost_usd) filter (
            where outcome_bucket not in (
                'clean_success',
                'exception_with_success_signal'
            )
        ),
        0::numeric
    ) as adjusted_failure_or_incomplete_cost_usd,
    case
        when coalesce(sum(adjusted_cost_usd), 0::numeric) = 0
            then null
        else
            coalesce(
                sum(adjusted_cost_usd) filter (
                    where outcome_bucket <> 'clean_success'
                ),
                0::numeric
            )
            / sum(adjusted_cost_usd)
    end as nonproductive_or_unclean_spend_share,
    case
        when coalesce(sum(adjusted_cost_usd), 0::numeric) = 0
            then null
        else
            coalesce(
                sum(adjusted_cost_usd) filter (
                    where outcome_bucket not in (
                        'clean_success',
                        'exception_with_success_signal'
                    )
                ),
                0::numeric
            )
            / sum(adjusted_cost_usd)
    end as failure_or_incomplete_spend_share,
    case
        when count(*) = 0 then null
        else
            coalesce(sum(recorded_cost_usd), 0::numeric)
            / count(*)::numeric
    end as mean_recorded_cost_per_attempt,
    case
        when count(*) = 0 then null
        else
            coalesce(sum(adjusted_cost_usd), 0::numeric)
            / count(*)::numeric
    end as mean_adjusted_cost_per_attempt,
    case
        when count(*) filter (
            where outcome_bucket = 'clean_success'
        ) = 0 then null
        else
            coalesce(sum(adjusted_cost_usd), 0::numeric)
            / count(*) filter (
                where outcome_bucket = 'clean_success'
            )::numeric
    end as adjusted_cost_per_clean_success,
    case
        when count(*) filter (
            where outcome_bucket in (
                'clean_success',
                'exception_with_success_signal'
            )
        ) = 0 then null
        else
            coalesce(sum(adjusted_cost_usd), 0::numeric)
            / count(*) filter (
                where outcome_bucket in (
                    'clean_success',
                    'exception_with_success_signal'
                )
            )::numeric
    end as adjusted_cost_per_any_success,
    string_agg(
        distinct cost_source,
        ','
        order by cost_source
    ) as cost_sources_present,
    string_agg(
        distinct cost_confidence,
        ','
        order by cost_confidence
    ) as cost_confidence_present
from benchmark.v_trial_adjusted_cost_coverage
group by suite_id, arm_id;

create or replace view benchmark.v_arm_outcome_cost_breakdown as
select
    suite_id,
    arm_id,
    outcome_bucket,
    count(*)::integer as trial_count,
    coalesce(
        sum(recorded_cost_usd),
        0::numeric
    ) as recorded_cost_usd,
    coalesce(
        sum(adjusted_cost_usd),
        0::numeric
    ) as adjusted_known_cost_usd,
    (
        coalesce(
            sum(adjusted_cost_usd),
            0::numeric
        )
        -
        coalesce(
            sum(recorded_cost_usd) filter (
                where adjusted_cost_usd is not null
            ),
            0::numeric
        )
    ) as known_accounting_gap_usd
from benchmark.v_trial_adjusted_cost_coverage
group by suite_id, arm_id, outcome_bucket;

comment on view benchmark.v_trial_adjusted_cost_coverage is
    'Adjusted-cost authority view. A recorded harness cost may exist while selected adjusted cost remains unresolved; such rows have NULL known_accounting_gap_usd.';

comment on view benchmark.v_arm_adjusted_cost_coverage is
    'Arm adjusted-cost aggregation. Known accounting gap excludes recorded harness cost from rows whose authoritative adjusted cost is unresolved.';

comment on view benchmark.v_arm_outcome_cost_breakdown is
    'Outcome adjusted-cost aggregation. Known accounting gap is computed only over rows with selected adjusted cost.';
