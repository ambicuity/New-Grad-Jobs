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
— see [`docs/operations.md`](operations.md#a-source-returns-far-fewer-jobs).

## 2026-08-12 — CSV sourcing sweep (55 boards added)

Source data: a 359-posting / 168-employer new-grad CSV export (`jobs.csv`,
columns `company,title,location,…,apply_url`) covering postings published
2026-08-01 → 2026-08-12. Each row's `apply_url` identifies the employer's ATS,
which makes the export usable as a candidate list rather than a job dump — the
scraper still fetches every listing itself, so nothing from the CSV is imported
as job data.

Method:

1. Normalized all 168 employer names and diffed them against `config.yml` —
   20 were already configured, 148 were not.
2. Derived a board endpoint from each `apply_url` on a supported ATS
   (Greenhouse / Lever / Ashby / Workday).
3. For the remainder, probed the four supported ATSes with slug guesses derived
   from the employer name, then confirmed each hit by matching the CSV's job
   titles against the titles the board returned (this is what caught Nextdoor,
   PathAI, Vorticity, Luma AI, and friends).
4. Fetched every surviving endpoint live on 2026-08-12; only boards returning a
   non-empty job list were added. Counts below are that probe's totals — total
   open reqs on the board, not new-grad matches.

### Greenhouse (17 added)

| Company | Slug | Job count (probe) | Found via |
|---|---|---|---|
| Allen Control Systems | `allencontrolsystems` | 68 | CSV apply URL |
| ATOMS | `cssmerge` | 238 | CSV apply URL |
| Bot Auto | `botauto` | 18 | CSV apply URL |
| Clarity Innovations | `clarityinnovates` | 35 | CSV apply URL |
| Cottingham & Butler | `cottinghambutlerinsuranceservicesinc` | 114 | CSV apply URL |
| DRW | `drweng` | 165 | CSV apply URL |
| Extend | `extend` | 19 | CSV apply URL |
| Jane Street | `janestreet` | 232 | CSV apply URL |
| Mobiik | `mobiik` | 16 | CSV apply URL |
| NetSage | `netsage` | 36 | slug probe |
| NewsBreak | `newsbreak` | 38 | CSV apply URL |
| Nextdoor | `nextdoor` | 17 | slug probe |
| Orion Innovation | `orioninnovation` | 85 | slug probe |
| PathAI | `pathai` | 8 | slug probe |
| Point72 | `point72` | 232 | CSV apply URL |
| Striim | `striiminc` | 9 | CSV apply URL |
| Toloka | `toloka` | 13 | slug probe |

Note: Jane Street and Point72 were listed under "Not added — quant firms use
custom careers sites" on 2026-05-16. Both run public Greenhouse boards
(`janestreet`, `point72`) as of this sweep, so that entry was wrong and is now
superseded.

### Lever (5 added)

| Company | Slug | Job count (probe) | Found via |
|---|---|---|---|
| DEUNA | `deuna` | 14 | CSV apply URL |
| Institute of Foundation Models | `ifm-us` | 44 | CSV apply URL |
| Layup Parts | `layup` | 27 | CSV apply URL |
| Welo Global | `weloglobal` | 621 | CSV apply URL |
| zaimler | `zaimler` | 12 | CSV apply URL |

This takes Lever from 2 boards to 7 — the first additions since the 2026-05-16
cleanup concluded that most Lever boards had migrated away.

### Ashby (10 added)

| Company | Slug | Job count (probe) | Found via |
|---|---|---|---|
| BJAK | `bjakcareer` | 1,331 | CSV apply URL |
| David AI | `david-ai` | 10 | slug probe |
| Luma AI | `lumaai` | 51 | slug probe |
| Netic | `netic` | 28 | CSV apply URL |
| Scientech Research LLC | `scientech-research` | 17 | CSV apply URL |
| Sunday Robotics | `sunday` | 31 | CSV apply URL |
| Tamarind Bio | `tamarindbio` | 7 | slug probe |
| Top Hat | `top-hat` | 9 | CSV apply URL |
| Truelogic | `truelogic` | 142 | CSV apply URL |
| Vorticity | `vorticity` | 2 | slug probe |

### Workday (23 added)

All 23 answered the CXS jobs API with `HTTP 200` on 2026-08-12 — none are in the
`HTTP 422` cohort described in [`docs/operations.md`](operations.md#a-source-returns-far-fewer-jobs).

| Company | Careers site | Job count (probe) |
|---|---|---|
| ALS | `alsglobal.wd103.myworkdayjobs.com/external` | 447 |
| Asurion | `asurion.wd5.myworkdayjobs.com/USExtPrivate` | 10 |
| Clio | `clio.wd3.myworkdayjobs.com/ClioCareerSite` | 154 |
| Copart | `copart.wd12.myworkdayjobs.com/Copart` | 316 |
| DataRobot | `datarobot.wd1.myworkdayjobs.com/DataRobot_External_Careers` | 25 |
| Dematic | `kiongroup.wd3.myworkdayjobs.com/KION_SCS` | 374 |
| Equifax | `equifax.wd5.myworkdayjobs.com/External` | 154 |
| Flex | `flextronics.wd1.myworkdayjobs.com/Careers` | 1,488 |
| GE Aerospace | `geaerospace.wd5.myworkdayjobs.com/GE_ExternalSite` | 438 |
| IFF | `iff.wd5.myworkdayjobs.com/IFF_Careers` | 376 |
| KBR, Inc. | `kbr.wd5.myworkdayjobs.com/KBR_Careers` | 1,658 |
| KION Group | `kiongroup.wd3.myworkdayjobs.com/KIONGroup` | 1,015 |
| Philips | `philips.wd3.myworkdayjobs.com/jobs-and-careers` | 923 |
| PPG | `ppg.wd5.myworkdayjobs.com/ppg_careers` | 775 |
| Radiance Technologies | `radiancetech.wd12.myworkdayjobs.com/Radiance_External` | 56 |
| RBC | `rbc.wd3.myworkdayjobs.com/RBCGLOBAL1` | 1,416 |
| Revvity | `revvity.wd103.myworkdayjobs.com/external` | 137 |
| The Campbell's Company | `campbellsoup.wd5.myworkdayjobs.com/ExternalCareers_GlobalSite` | 321 |
| The Home Depot | `homedepot.wd5.myworkdayjobs.com/CareerDepot` | 1,004 |
| The Kendall Group | `kendallgroup.wd503.myworkdayjobs.com/kendall_careers` | 89 |
| The Walt Disney Company | `disney.wd5.myworkdayjobs.com/disneycareer` | 650 |
| TransUnion | `transunion.wd5.myworkdayjobs.com/transunion` | 222 |
| Waystar | `waystar.wd1.myworkdayjobs.com/Waystar` | 82 |

### Not added from this CSV (93 employers)

Every remaining employer in the export runs an ATS this scraper has no fetcher
for. Grouped by ATS, with the employer count per family:

- **iCIMS** (13): Acuity, Celanese, East Penn Manufacturing, East West Bank,
  ISYS Technologies, JerseySTEM, Knowledge Services, Navitas Systems, Peraton
  (already configured via Workday), Steampunk, Waters, and others
- **Workable** (6): ALTEN MÉXICO, Accellor, Arkham Technologies, Castle Park
  Investments, Darwin AI, DataVisor
- **SmartRecruiters** (6): Agap Technologies, Alto-Shaam, Blend360, Domino's,
  Intuitive, Ubisoft
- **Oracle Fusion / Taleo** (8): Chubb, Copa Airlines, Coppel, Hexaware, Mayo
  Clinic, Nokia, Futurewei, Virtusa
- **ADP** (6): ASM Research, ECS, Gold's Gym, PMA Companies, Perdoceo Education,
  Stellantis
- **Paylocity** (5): Inadev, Meyer Distributing, Morgridge Institute, RedDrum,
  Riverhead Resources
- **UKG/UltiPro** (3), **Eightfold** (3), **Dayforce** (2), **Comeet** (2),
  **JazzHR** (2), **BrassRing** (1), **Recruitee** (1), **Recruiterflow** (1),
  **HRM Direct** (1), **Zoho Recruit** (1, AgileEngine), **YC Work at a
  Startup** (1, Silimate)
- **Custom careers sites** (~30): ByteDance (`joinbytedance.com`), Apple, Meta,
  Google, Amazon, Siemens, Teradyne, Capgemini, Munich Re, Moody's, Li Auto,
  TEK Systems, and similar

The largest single gap is ByteDance: 58 of the CSV's 359 postings, all on
`joinbytedance.com`, which exposes no public board API. TikTok's Workday tenant
(`bytedance.wd3.myworkdayjobs.com/TikTok`) has no public site (HTTP 401) and was
removed on 2026-09-24 (see below). ByteDance- and TikTok-branded reqs remain reachable only through
the JobSpy/Indeed layer, where `ByteDance new grad` and `TikTok new grad` are
already configured search terms.

Castleton Commodities International (`osv-cci.wd1.myworkdayjobs.com/CCICareers`)
is a Workday tenant but answered `HTTP 422` on every tenant-path variant tried —
same failure mode as the 422 cohort, so it was left out rather than added dead.

## 2026-09-24 — Workday cleanup (`HTTP 422` / `401`)

Every configured Workday entry was probed live. Workday answers `HTTP 422` with an
empty body when the tenant or site id in `workday_url` does not exist on that `wdN`
data centre, and `HTTP 401` when the tenant exists but has no public career site. 19
entries were corrected to their real tenant/site (Cisco, Salesforce, Capital One, PwC,
Accenture, Bank of America, Fidelity, Johnson & Johnson, Merck, Bristol Myers Squibb,
Walmart, P&G, RTX/Raytheon, GDIT, Samsung, Sony, GM, CACI, and VMware → Broadcom).
The 33 below were removed; several are still reachable through the JobSpy/Indeed layer.

| Company | Reason |
|---|---|
| Microsoft, Netflix, Oracle, SAP, ServiceNow, Amazon, IBM, Ford, Lockheed Martin, L3Harris, Deloitte, EY, McKinsey, BCG, JPMorgan, Goldman Sachs, SAIC | not on public Workday (custom careers site or other ATS) |
| AMD, Charles Schwab, PepsiCo, Peraton | moved to iCIMS |
| Morgan Stanley, Starbucks, American Express | moved to Eightfold (Amex also Oracle) |
| UnitedHealth Group | Taleo |
| Honeywell | Oracle Recruiting |
| Splunk | now part of Cisco (covered by the Cisco entry) |
| TikTok, AbbVie, Intuit, Lenovo, Dell | tenant exists but no public site (`HTTP 401`) or no site id found |
| Qualcomm | Workday site returns 0 jobs (moved off Workday) |
