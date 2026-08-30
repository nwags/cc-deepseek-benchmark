# Glossary page guide

## Executive summary

Glossary is the dashboard's shared language layer. It renders checked-in definitions from
`apps/dashboard/src/lib/glossary.ts`; it is not a database vocabulary dump and it does not infer
meanings from whatever values happen to be present in current runs.

## Route and implementation

- Dashboard route: `/glossary`.
- Page source: `apps/dashboard/src/app/glossary/page.tsx`.

## Data sources

- Canonical dashboard terminology is stored in `apps/dashboard/src/lib/glossary.ts`.
- Entries may link to the dashboard surface where the term is most useful.
- The separate Markdown project glossary contains broader project/evidence vocabulary and should be
  used when a term is not represented in the dashboard tooltip registry.

## Population and authority

- There is no benchmark population. The authority is checked-in terminology.
- Definitions distinguish public labels from internal compatibility fields such as logical mode and
  storage mode.

## How to read the page

- Use glossary definitions before assigning your own meaning to cost, validity, confidence, routing,
  artifact, or quality labels.
- Where a term has page links, follow those links to see the concept in its evidence context.
- Treat categorical confidence as evidence strength, not a probability or model self-assessment.

## Controls and filters

- Entries have stable anchor IDs such as `#recorded-cost` and `#execution-validity` for direct
  linking.
- There are no data filters or live queries.

## Caveats and non-inferences

- A glossary definition explains a term; it does not establish that a particular row has sufficient
  evidence for that term.
- Definitions do not supersede frozen taxonomy registries or provider-specific evidence limitations
  where those contracts are more precise.

## Common workflows

- When two dashboard pages appear to use similar words differently, resolve the canonical definition
  here and then inspect each page's population/authority notice.
- Use the glossary before changing public labels so internal IDs are not accidentally mass-renamed.

## Evidence tracing

- Tooltip or column label → Glossary anchor → related page → exact row/evidence source.

## Related documentation

- [Dashboard Research Guide](../DASHBOARD_RESEARCH_GUIDE.md) for the cross-page research workflow
  and evidence-reading order.
- [Codebase Guide](../CODEBASE_GUIDE.md) for implementation and provenance boundaries.
- [Project Glossary](../../reference/GLOSSARY.md) for canonical terminology.
