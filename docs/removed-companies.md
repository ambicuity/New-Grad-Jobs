# Removed companies from `config.yml`

This log tracks employer boards that have been dropped from the scraper so future
contributors don't unknowingly re-add a dead endpoint. Each removal cites the
source (`HTTP 404`, moved ATS, defunct) and the date.

## 2026-05-16 — Greenhouse cleanup (`HTTP 404`)

39 boards removed. The `boards-api.greenhouse.io/v1/boards/<slug>/jobs` endpoint
returns `404` for each — the company has either moved off Greenhouse or wound
down. Verified by parallel head-probe of all 139 configured Greenhouse boards.

| Company | Slug | Likely reason |
|---|---|---|
| Alchemy | `alchemy` | moved ATS |
| Chainalysis | `chainalysis` | moved ATS |
| Chronosphere | `chronosphere` | moved ATS |
| Circle | `circle` | moved ATS |
| Cityblock Health | `cityblock` | moved ATS |
| Cloudinary | `cloudinary` | moved ATS |
| Coinbase | `coinbase` | moved to custom careers site |
| Color Health | `color` | moved ATS |
| Column | `column` | moved ATS |
| Cruise | `cruise` | wound down (GM shut down robotaxi unit) |
| Deel | `deel` | moved ATS |
| Devoted Health | `devotedhealth` | moved ATS |
| Getaround | `getaround` | filed bankruptcy 2024 |
| Goat | `goat` | moved ATS |
| Grammarly | `grammarly` | moved to custom site |
| Hims & Hers | `forhims` | moved ATS |
| Jam City | `jamcity` | moved ATS |
| Kraken | `kraken` | moved to custom site |
| Lever | `lever` | acquired by Employ Inc 2022 |
| LightStep | `lightstep` | acquired by ServiceNow |
| Lime | `lime` | moved ATS |
| Modern Treasury | `moderntreasury` | moved ATS |
| Niantic | `niantic` | moved ATS |
| Paxos | `paxos` | moved ATS |
| Pipe | `pipe` | shut down 2023 |
| Pulumi | `pulumi` | moved ATS |
| Railway | `railway` | moved ATS |
| Retool | `retool` | moved ATS |
| Ro | `ro` | moved ATS |
| Runway | `runwayml` | moved ATS |
| Shield AI | `shieldai` | moved ATS (now Workday — re-add candidate) |
| Skydio | `skydio` | moved ATS |
| Supercell | `supercell` | moved ATS |
| Tecton | `tecton` | moved ATS |
| Tempus | `tempus` | moved ATS |
| Veeva | `veeva` | moved ATS |
| Via | `ridewithvia` | moved ATS |
| Zoox | `zoox` | moved ATS |
| Zynga | `zynga` | acquired by Take-Two; moved ATS |

## 2026-05-16 — Lever cleanup (zero jobs returned)

3 boards removed. The Lever API responds `200 OK` but returns an empty job list,
indicating the company has migrated off Lever.

| Company | Slug | Likely new ATS |
|---|---|---|
| Netflix | `netflix` | custom (`jobs.netflix.com`) |
| Plaid | `plaid` | custom careers page |
| Atlassian | `atlassian` | custom careers page |

## 2026-05-16 — Workday cleanup (stale Site IDs)

3 boards removed. The configured Workday tenant URLs return `HTTP 404` — the
careers site IDs have changed. Re-derive the live URLs if these companies should
return.

| Company | Stale URL |
|---|---|
| Home Depot | `https://homedepot.wd5.myworkdayjobs.com/HomeDepotCareers` |
| Nike | `https://nike.wd1.myworkdayjobs.com/Search` |
| Visa | `https://visa.wd5.myworkdayjobs.com/Visa_External_Career_Site` |

## 2026-05-16 — New Greenhouse additions

13 verified-live boards added across two passes.

**First pass** (high-volume, well-known employers):

| Company | Slug | Job count (probe) |
|---|---|---|
| Anduril Industries | `andurilindustries` | 1,944 |
| Block | `block` | 161 |
| xAI | `xai` | 220 |

**Second pass** (broader candidate sweep across AI infra, devtools, fintech, healthtech, dev infra):

| Company | Slug | Job count (probe) |
|---|---|---|
| Glean | `gleanwork` | 180 |
| BridgeBio | `bridgebio` | 93 |
| Together AI | `togetherai` | 56 |
| Cribl | `cribl` | 54 |
| Tailscale | `tailscale` | 50 |
| Sweetgreen | `sweetgreen` | 43 |
| Recursion | `recursionpharmaceuticals` | 34 |
| Maven Clinic | `mavenclinic` | 28 |
| Squarespace | `squarespace` | 27 |
| Pulley | `pulley` | 4 |

## 2026-05-16 — Ashby ATS added (new fetcher)

25 boards added in first pass after writing `fetch_ashby_jobs()`:

| Company | Slug | Job count (probe) |
|---|---|---|
| OpenAI | `openai` | 678 |
| Crusoe | `crusoe` | 324 |
| Mistral AI | `mistral` | 178 |
| Notion | `notion` | 140 |
| Cohere | `cohere` | 129 |
| Sierra | `sierra` | 126 |
| LangChain | `langchain` | 96 |
| Cursor | `cursor` | 88 |
| Lovable | `lovable` | 82 |
| Perplexity | `perplexity` | 62 |
| Baseten | `baseten` | 60 |
| Ashby | `ashby` | 60 |
| Supabase | `supabase` | 42 |
| Sentry | `sentry` | 39 |
| Modal | `modal` | 29 |
| Attio | `attio` | 29 |
| Campfire | `campfire` | 24 |
| Vapi | `vapi` | 24 |
| Linear | `linear` | 23 |
| Qualified | `qualified` | 10 |
| Browserbase | `browserbase` | 9 |
| Anyscale | `anyscale` | 7 |
| Pinecone | `pinecone` | 7 |
| Weaviate | `weaviate` | 6 |
| Turbopuffer | `turbopuffer` | 4 |

18 more added in second pass (broader probe):

| Company | Slug | Job count (probe) |
|---|---|---|
| Snowflake | `snowflake` | 423 |
| ElevenLabs | `elevenlabs` | 139 |
| Decagon | `decagon` | 108 |
| Plaid | `plaid` | 88 |
| Commure | `commure` | 85 |
| Suno | `suno` | 43 |
| Docker | `docker` | 42 |
| Astronomer | `astronomer` | 27 |
| Poolside | `poolside` | 16 |
| Cradle Bio | `cradlebio` | 11 |
| Airbyte | `airbyte` | 9 |
| Railway | `railway` | 9 |
| Warp | `warp` | 8 |
| Statsig | `statsig` | 7 |
| Reka | `reka` | 6 |
| Stytch | `stytch` | 5 |
| Prefect | `prefect` | 4 |
| Runway | `runway` | 4 |

Note: Plaid (previously removed from Lever) and Runway (previously
removed from Greenhouse as `runwayml` 404) are both alive on Ashby
and now restored.

## Not added (no public ATS, would need bespoke scraping)

These employers were requested but don't expose a public Greenhouse/Lever/Workday
endpoint as of 2026-05-16:

- **Big tech custom sites**: Apple, Meta, Google, Amazon
- **AI labs without public boards**: OpenAI (custom), Anthropic (custom),
  Cohere, Hugging Face, Mistral, Inflection, Adept, Character.AI, Perplexity
- **Quant firms**: Jane Street, Citadel, Two Sigma, Jump Trading, Hudson River
  Trading, DE Shaw, Akuna, Optiver, Five Rings, Tower Research, IMC
  (all use custom careers sites or recruiter-only flows)
- **Others**: Supabase, Sourcegraph, PostHog, Snowflake, Wiz, Snyk, Sentry

Microsoft, Oracle, Salesforce, ServiceNow, JPMorgan, Goldman Sachs, Morgan
Stanley, etc. are configured under Workday but currently fail with `HTTP 422`
— see [`docs/Workday-Investigation.md`](Workday-Investigation.md).
