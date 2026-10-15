# Removed companies from `config.yml`

This log tracks employer boards that have been dropped from the scraper so future
contributors don't unknowingly re-add a dead endpoint. Each removal cites the
source (`HTTP 404`, moved ATS, defunct) and the date. Additions that came out of a
board audit are logged here too, so the reasoning survives.

## 2026-10-15 — iCIMS classic portals (23 added)

The iCIMS adapter now also reads classic portals (`https://<prefix>-<company>.icims.com`, #173): their
search pages, then the job pages of postings that can pass. All 61 public portal hosts found by the
careers-page audit (#419) were probed on 2026-10-15, and the 43 that list jobs were measured through the
adapter and our filters. The 23 that publish at least two curated jobs were added (211 curated jobs at
the time): Allied Universal (`securitycareers-aus`), Berkley (`careers-berkley`), Beyond New Horizons
(`careers-bnh`), Bowhead (`bowheadcareers-uicalaska`), Cotiviti (`careers-cotiviti`), Daifuku
(`careers-daifuku-america`), Everwatch (`everwatch-everwatchsolutions`), Exponent (`careers-exponent`),
ISYS Technologies (`careers-i2xisys`), Kimley-Horn (`careers-kimley-horn`), Markon (`careers-markon`),
New York University (`careers-nyu`), PeopleTec (`careers-peopletec`), Persistent Systems
(`careers-persistentsystems`), PowerSchool (`careers-powerschool`), RoviSys (`careers-rovisys`), RoviSys
Building Technologies (`careers-rovisysbuildingtechnologies`), SimVentions (`careers-simventions`),
Snap-on (`careers-snapon`), Soft Tech Consulting (`careers-softtechconsulting`), Steampunk
(`careers-steampunk`), TekSynap (`hotjobs-teksynap`) and The Tatitlek Corporation (`careers-tatitlek`).

**Not added:**

- **Already read through a career site:** the portals behind the AMD, Emory, First Citizens, Medpace,
  Noblis and PepsiCo career sites above (their `apply_url` hosts), and IDEMIA, read from SuccessFactors.
- **Duplicates:** `jobs-kimley-horn` lists the same jobs as `careers-kimley-horn`. `hotjobs-teksynap`
  is a subset of `careers-teksynap`, but only it shows real dates.
- **Posted dates hidden:** a portal that hides its dates makes one up on each job page (the request
  time two years back), so its jobs can never be recent. These are Edgewater Federal Solutions, Emory
  Healthcare (`ehccareers-emory`), MAG Aerospace, Oregon Health & Science University (three portals),
  RoviSys Europe, TekSynap (`careers-teksynap`) and Western & Southern (`careers-westernsouthern`).
- **Future roles:** `futurecareers-peopletec` lists roles for upcoming projects, not open positions.
- **Fewer than two curated jobs:** Allied Universal Canada, Berkley APAC and Spain, Cotiviti global,
  Lynker, Ryder (driver and technician portals; Ryder's Workday board is configured), and Western &
  Southern management and operations portals.
- **Employee-only or empty:** `internal*` portals, portals that redirect to a sign-in page, and portals
  with no listings.

## 2026-10-15 — iCIMS source, career sites (6 added)

The new iCIMS adapter (#423) reads iCIMS career sites (iCIMS's "Jibe" job search) on the employer's
own domain through their public `/api/jobs` search. Every unresolved employer from the careers-page
audit (#419) had its careers hosts probed for `/api/jobs` on 2026-10-15, and each site's `apply_url`
was checked to be iCIMS. Added: AMD (`careers.amd.com`), Emory University (`careers.emory.edu`),
First Citizens Bank (`jobs.firstcitizens.com`), Medpace (`careers.medpace.com`), Noblis
(`careers.noblis.org`) and PepsiCo (`www.pepsicojobs.com`; `careers.pepsico.com` redirects there).

**Not added:** S&P Global and Mount Sinai Health System run iCIMS career sites in front of Workday and
Oracle HCM, which are already configured, so they would publish duplicates. Oregon Health & Science
University (`jobs.ohsu.edu`) published no curated jobs.

**Not covered yet:** classic iCIMS portals (`careers-<company>.icims.com`, about 30 employers in the
audit) are a different product and follow in a separate change (added below).

## 2026-10-15 — SuccessFactors source (32 careers sites added)

The new SAP SuccessFactors adapter (#421) reads Career Site Builder sites on the employer's own
domain. The careers-page audit (#419) found 51 employers on SuccessFactors; 39 run Career Site
Builder, and each of those was probed live on 2026-10-15 through the adapter and our filters. The
32 sites that publish at least two curated jobs were added (767 curated jobs at the time).

**Not added (no curated jobs, or one):** NEC, Government of Nova Scotia, SES, Entergy and Consumers
Energy published none; E. & J. Gallo Winery and West Pharmaceutical Services one each.

**Not supported by this adapter:** 11 employers use the legacy `career4.successfactors.com/career?company=…`
portal (Deloitte, John Deere, Dexcom, Grainger, Hearst, SMUD, ExxonMobil, SAP, Government of Alberta,
Indra Group, Sonepar), and PG&E's careers site is a Radancy (TalentBrew) front end.

**SuccessFactors (32):** Advanced Energy (`jobs.advanced-energy.com`), ANDRITZ (`careers.andritz.com`), AVL (`jobs.avl.com`), Bank of Canada (`careers.bankofcanada.ca`), Boston Scientific (`jobs.bostonscientific.com`), Bunge (`jobs.bunge.com`), BWX Technologies (`careers.bwxt.com`), Compass Group USA (`jobs.compassgroupcareers.com`), Doosan (`jobs.doosan.com`), Duke University (`careers.duke.edu`), FlightSafety International (`careers.flightsafety.com`), Hatch (`jobs.hatch.com`), Hubbell (`careers.hubbell.com`), IDEMIA (`careers.idemia.com`), J.R. Simplot (`careers.simplot.com`), JetBlue (`careers.jetblue.com`), Lear (`jobs.lear.com`), Leonardo DRS (`careers.leonardodrs.com`), Lincoln Electric (`jobs.lincolnelectric.com`), MAPFRE (`jobs.mapfre.com`), MIT Lincoln Laboratory (`careers.ll.mit.edu`), NextEra Energy (`jobs.nexteraenergy.com`), Oak Ridge National Laboratory (`jobs.ornl.gov`), Phillips 66 (`careers.phillips66.com`), Schaeffler (`jobs.schaeffler.com`), State of Florida (`jobs.myflorida.com`), State of Illinois (`illinois.jobs2web.com`), Supermicro (`jobs.supermicro.com`), Swiss Re (`careers.swissre.com`), Teradyne (`jobs.teradyne.com`), University of Toronto (`jobs.utoronto.ca`), Westinghouse (`careers.westinghousenuclear.com`)

## 2026-10-15 — Careers-page audit (84 boards added)

A follow-up to the Foorilla audit (#419). Foorilla was re-read for unconfigured employers with at
least 10 open jobs and 3 or more recent entry-level jobs in the US, Canada or India: 440 employers,
after removing recruiters. Each employer's own website (the homepage, `/careers`, `/jobs`, `careers.`
and `jobs.` subdomains, and links labelled careers or jobs) was scanned for job-system links. Workday
tenants were confirmed through the CXS API, keeping the site with the most jobs, and other families
through their public APIs. The 84 boards whose jobs pass our filters at least twice (1,102 curated
jobs, measured with the #417 filter fix) were added.

**Not added (wrong board):** the link pointed at a different company or region. Deloitte linked
Deloitte Ireland (`deloitteie`), Toyota Automated Logistics linked Vanderlande, ETAP linked AVEVA,
Argo Group linked Brookfield, Emory University linked `hhc`, and IKEA linked IKEA Bulgaria.

**Not added (owner rule, direct employers only):** Diversified Services Network (Workable `dsn`)
describes itself as providing "staffing services to Fortune 500 companies".

**Not added (other):** Staples' Oracle HCM site answers `HTTP 403`. 13 boards publish only one
curated job and 23 publish none: Ohio State University, Premier, CAE, Sun Life, Blue Cross Blue
Shield of Arizona, Kotak Mahindra Bank, Q2, BILL, Applied Industrial Technologies, TMX, Centific,
Trident Systems and Tech Holding publish one each.

**Unsupported job systems found:** SuccessFactors (51 employers), iCIMS (37), Phenom (26), Avature
(11), Eightfold (11), Taleo (9), Dayforce (3), BrassRing (2), Jobvite (1). 146 employers showed no
job-system link. Demand is tracked in #316.

**Workday (56):** Advocate Aurora Health (`aah/External`), AeroVironment (`avav/AVAV`), Auto-Owners Insurance (`aoins/AutoOwners`), Axos Bank (`axos/axos`), Barry-Wehmiller (`barrywehmiller/BWCareers`), BDO Canada (`bdo/bdo`), BlackBerry (`bb/BlackBerry`), bp (`bpinternational/bpCareers`), Broadridge (`broadridge/careers`), Canadian Tire (`canadiantirecorporation/Enterprise_External_Careers_Site`), Cleveland Clinic (`ccf/ClevelandClinicCareers`), ConocoPhillips (`conocophillips/External`), Copeland (`copeland/Copeland_External_Careers_Page`), Crane Company (`cranecompany/Careers`), Cushman & Wakefield (`cw/External`), ERCOT (`ercot/ercot_careers`), Fannie Mae (`fanniemae/FannieMaeCareers`), Freddie Mac (`freddiemac/External`), Genworth (`gnw/GNW`), Great American Insurance Group (`gaig/GAIG_External`), Harris Computer (`harriscomputer/1`), ICF (`icf/ICFExternal_Career_Site`), Invesco (`invesco/IVZ`), Itron (`itron/Itron`), Jefferson Health (`jeffersonhealth/ThomasJeffersonExternal`), KLA (`kla/Search`), KONE (`kone/Careers`), Light & Wonder (`lnw/LightWonderExternalCareers`), Logitech (`logitech/LOGITECH`), NCR Voyix (`ncr/ext_us`), Netsmart (`ntst/Careers`), Nordstrom (`nordstrom/nordstrom_careers`), Penn State University (`psu/PSU_Staff`), Protiviti (`roberthalf/ProtivitiNA`), Regal Rexnord (`regalrexnord/careers`), Ryder (`ryder/rydercareers`), S&P Global (`spgi/SPGI_Careers`), State Street (`statestreet/Global`), T. Rowe Price (`troweprice/TROWEPRICE`), TaskUs (`taskus/careers`), The University of Texas at Austin (`utaustin/UTstaff`), Tokio Marine HCC (`tmhcc/External`), Torch Technologies (`starfish/careers`), Toyota (`toyota/TMNA`), Trellix (`trellix/EnterpriseCareers`), TSC (`tsc/TSC-Careers`), Universities of Wisconsin (`wisconsin/UW_Comprehensives`), University of Chicago (`uchicago/External`), University of Miami (`umiami/UMCareerStaff`), University of Southern California (`usc/ExternalUSCCareers`), VIAVI Solutions (`viavisolutions/careers`), Viridien (`cgg/viridiencareers`), Washington University in St. Louis (`wustl/External`), Western Governors University (`wgu/External`), Worldwide Clinical Trials (`worldwide/External`), Xylem (`xylem/xylem-careers`)

**Oracle HCM (15):** Berkshire Hathaway Energy (`fa-essf-saasfaprod1/CX_1`), Caesars Entertainment (`edmn/CX_1`), Dallas County (`fa-etvc-saasfaprod1/CX_1001`), Emerson (`hdjq/CX_1`), First Solar (`fa-esbv-saasfaprod1/CX_1`), Hearst (`eevd/CX_1`), Howmet Aerospace (`fa-exty-saasfaprod1/CX_1`), Mount Sinai Health System (`ejis/CX`), Providence (`evac/CX_1`), Sherwin-Williams (`ejhp/CX_2`), Tulane University (`tulane-ibqejb/CX_1`), UC San Francisco (`iazuqy/CX_1`), University of Tennessee (`fa-ewlq-saasfaprod1/CX_1`), Verisk (`fa-ewmy-saasfaprod1/CX_1`), Wesco (`eklm/CX`)

**SmartRecruiters (4):** Avery Dennison (`AveryDennison`), EVERSANA (`EVERSANA1`), Ramboll (`Ramboll3`), SOSi (`SOSi1`)

**UKG (3):** ARA (`APP1010ARAI`), HOPCo (`COR1016COREI`), Milliman (`MIL1017`)

**Paylocity (2):** Heartland Business Systems (`3986a99a…`), Inadev (`82c1b00b…`)

**Ashby (1):** PAR Technology (`PAR%20Technology`)

**Greenhouse (1):** D2 Consulting (`d2consulting`)

**Lever (1):** Global Lending Services (`glsllc`)

**Workable (1):** Delaware Nation Industries (`dnigov`)

## 2026-10-14 — Foorilla audit (54 boards added)

An audit of Foorilla's hiring board (#415) listed its 47,424 companies and read the page of every
unconfigured one with at least 5 open jobs. Companies with 3 or more recent entry-level jobs in the
US, Canada or India were probed on Greenhouse, Lever, Ashby, Workable and SmartRecruiters. A board
was kept only when its job titles matched the employer's Foorilla listings, and only when our own
filters publish at least one of its jobs (317 curated jobs across the 55 that do). Display names
come from the board.

**Not added:** Vailexa (Greenhouse `vailexa`) places contractors at client sites, so the
direct-employers rule (#404) excludes it. University Health Network (SmartRecruiters
`universityhealthnetwork`) is left out because some of its matching jobs are "Casual" cleaner and
aide roles, close to the part-time roles the board excludes. Pear VC (Ashby `pear-vc`) is a
portfolio job board. CGS Federal matched too, but it is already configured (Lever `cgsfederal`).
Ten matched boards published no curated jobs and were not added: Bierman Autism Centers, Energy
Solutions, Connor Clark & Lunn, JFrog, Apptronik, PMG, Roboyo, Uncommon Schools, University of
Notre Dame and Latitude.

**Unresolved:** 561 companies (about 2,700 of the counted jobs) answered on none of those job
systems. Most are large employers on Workday, such as KLA, PG&E, Walgreens, Supermicro and Sandisk.
Foorilla does not expose their careers links.

**Greenhouse (36):** AlayaCare (`alayacare`), AppDirect (`appdirect`), ARCO (`arco`), Bitwarden (`bitwarden`), CarGurus (`cargurus`), Chainguard (`chainguard`), ChargePoint (`chargepoint`), Coalition (`coalition`), Dark Wolf Solutions (`darkwolfsolutions`), DigiCert (`digicert`), Domino Data Lab (`dominodatalab`), DV Trading (`dvtrading`), ELEVI Associates (`eleviassociates`), Esri (`esri`), FanDuel (`fanduel`), Gruve (`gruve`), Inversion Space (`inversionspace`), IonQ (`ionq`), IXL Learning (`ixllearning`), Konrad (`konradgroup`), Monster Energy (`monsterenergy`), Nexla (`nexla`), North Point Technology (`northpointtechnology`), Red Ventures (`redventures`), Revolution Medicines (`revolutionmedicines`), Rhombus Power (`rhombuspower`), Roku (`roku`), RZR Global (`rzr`), Schrödinger (`schrdinger`), SMX (`smxtech`), Stratolaunch (`stratolaunch`), The New York Times (`thenewyorktimes`), TrellisWare Technologies (`trelliswaretechnologies`), Truveta (`truveta`), Ursa Major (`ursamajor`), Varda Space Industries (`vardaspace`)

**Lever (9):** Agile Defense (`agile-defense`), Field AI (`field-ai`), Hevo Data (`hevodata`), Kitware (`kitware`), Loft Orbital (`loftorbital`), Match Group (`matchgroup`), Redhorse (`redhorsecorp`), Safe Security (`safe`), Waabi (`waabi`)

**Ashby (7):** Benchling (`benchling`), Blissway (`blissway`), EliseAI (`eliseai`), Fuse (`fuse`), Handshake (`handshake`), NETGEAR (`netgear`), Radiant Industries (`radiant-industries`)

**SmartRecruiters (2):** City of Philadelphia (`CityofPhiladelphia`), Harvard University (`HarvardUniversity`)

## 2026-10-14 — Paylocity source (9 boards added, 1 left out, 5 unresolved)

The new Paylocity adapter (#413) adds the boards of 9 direct employers linked from the 30-day
applied-jobs export (#390), each probed live on 2026-10-14: Concept Solutions, CU*Answers, E&M
Technologies, Five Star Bank, Forgent Power Solutions (listed twice in the export, one board),
Interclypse, Oneida Professional Services, Trean and UNICO Group.

**Not added (owner rule, direct employers only):** the export's "Mechanical Comfort, Inc." link
resolves to the board of Abstrakt Marketing Group, which posts HVAC and sales jobs for client
companies.

**Unresolved:** CleanSlate Technology Group, Imagine, Northern Technologies Group, ES&S and Ryan
Consulting Group. Their linked postings have closed ("Job Not Found"), so the links no longer reveal
a board GUID; any live job page of theirs would (its "View All Jobs" link).

## 2026-10-14 — Amplitude moved to Ashby

The watchdog's new per-source summary (#409) showed Greenhouse's one failing company: Amplitude.
Its Greenhouse board (`amplitude`) answers `HTTP 404`, and its careers page links
`jobs.ashbyhq.com/amplitude`, whose posting API returned 38 jobs on 2026-10-14. Moved to Ashby.

## 2026-10-14 — Workable source (5 accounts added, 3 recruiters left out)

The new Workable adapter (#404) adds the direct employers among the 8 Workable accounts linked from
the applied-jobs exports (#388, #390), each probed live on 2026-10-14: Credence (`credence`),
InterImage (`interimage`), Texas Sports Academy (`texas-sports-academy-main`), TP-Link Systems
(`tp-link-usa-corp`) and Zifo (`zifo`).

**Not added (owner decision):** recruiters that post for unnamed client companies, which the board
would list as the employer. Raydar (`raydar`, a talent network; 146 curated postings that day),
Weekday AI (`weekday-1`, a hiring platform; 25) and Sapsol Technologies (`sapsol-technologies-inc-7`,
IT staffing; 6). Re-adding them needs an owner decision, not just a working endpoint.

## 2026-10-14 — ADP Workforce Now source (3 career centers)

The new ADP adapter (#402) adds the 3 ADP Workforce Now career centers linked from the 30-day
applied-jobs export (#390): Arcarithm, Moran Environmental Recovery and nou Systems. Each `cid` was
probed live on 2026-10-14 and returned postings. The 10 ADP MyJobs employers in the same export are
not covered: that API requires a per-tenant `orgoid` header (#316).

## 2026-10-14 — UKG Pro Recruiting source (19 job boards)

The new UKG adapter (#399) adds the 19 UKG Pro Recruiting (UltiPro) job boards linked from the
30-day applied-jobs export (#390). Each board was probed live on 2026-10-14 through its public
`LoadSearchResults` search and returned postings, sorted newest first: Aeroflow Health, AFL,
Alliance Technical Group, Alpha Omega, Amada, arrivia, Brown and Caldwell, Cleveland Guardians,
Community Health Center of Snohomish County, Gen II, Gray Media, Hotwire Communications, John Knox
Village, Modern Woodmen of America, PowerSecure, Rocky Brands, RubinBrown LLP, Scripps Research and
Toshiba America (the `toshibausa.rec.pro.ukg.net` board, which also lists EtaPRO).

## 2026-10-14 — Rippling source (16 boards)

The new Rippling adapter (#397) adds the 16 Rippling boards linked from the 30-day applied-jobs
export (#390). Each slug was probed live on 2026-10-14 and returned postings: Albers Aerospace
(`albers-aersopace`, the board's real spelling), Bamboo Health, Cintal, Concept Plus, Decision
Technologies, Eridu, Flourish and Thrive Labs, Kreate, Lyte, Reserv, Rippling, Sight Machine, Swoop,
ThreatDown, Veracity Insurance and Webull.

## 2026-10-14 — Oracle HCM source (21 careers sites)

The new Oracle HCM adapter (#394) adds the 21 Oracle Recruiting Cloud careers sites linked from the
30-day applied-jobs export (#390). Each host/site pair was probed live on 2026-10-14 through the
public `recruitingCEJobRequisitions` search and returned postings, sorted newest first: American
Express, Arcadis, Citco, CORE Foodservice, CSX, Diebold Nixdorf, Estes, GCI, GM Financial,
International Paper, Mayo Clinic, Nokia, Northeastern Nevada Regional Hospital, Oceaneering,
Southern Company, Texas Instruments, Trail King, Uber, Vertiv, VITAS Healthcare and WSP.

## 2026-10-14 — SmartRecruiters source (37 companies, 1 moved)

The new SmartRecruiters adapter (#392) adds 37 companies whose ids appeared in the applied-jobs
exports. Every id was probed live on 2026-10-14 and returned postings (an unknown id answers
HTTP 200 with `totalFound: 0`, so a non-empty result is the only proof an id is right).

**Moved:** LinkedIn, from Greenhouse (`linkedin` answers with 0 jobs) to SmartRecruiters (`LinkedIn3`).

## 2026-10-14 — 30-day applied-jobs export (234 boards added, 1 moved)

A 30-day applied-jobs export lists 704 employers that users applied to in the 30 days to
2026-10-14. Each posting link was matched to its ATS board. Every board not yet in
`config.yml` was probed live on 2026-10-14, and the 234 that answered with
open jobs were added. Display names come from the board (Greenhouse) or the employer, not the
URL slug.

**Moved:** Poshmark, from Greenhouse (`poshmark` answers with 0 jobs) to Ashby (`poshmark`).

**Not added:** DeepLearning.AI (Lever `aifund`, `HTTP 404`). HP `EXTEU-AC-CareerSite` is an EU-only
site; HP is already configured.

**Greenhouse (87):** 10Beauty (`10beauty`), Accenture Federal Services (`accenturefederalservices`), Advanced Space (`advancedspace`), Alo Yoga (`aloyoga`), ALTEN Technology USA (`altentechnologyusa`), Archer Aviation (`archer56`), Axon (`axon`), Baselayer (`baselayer`), BathWorks of Michigan (`bathworksmichigan`), Beyond Finance (`beyondfinance`), Black Canyon Consulting (`blackcanyonconsulting`), Blend (`blend`), C5MI Insight (`c5miinsightllc`), Cadwell (`cadwell`), Captivation Software (`captivation`), CareDx (`caredxinc`), CentralReach (`centralreach`), CHAOS Industries (`chaosindustries`), ClinChoice (`clinchoice`), Cognite (`cognite`), Crunchyroll (`crunchyroll`), Databento (`databento`), DHI Group (`dhigroupinc`), DoorDash (`doordashusa`), ExtraHop (`extrahopnetworks`), Freedom Technology Solutions Group (`freedomconsulting`), General Matter (`generalmatter`), GenScript (`genscript`), GuidePoint Security (`guidepointsecurity`), Hanwha Energy USA (`hanwhaenergyusa`), Harbinger Motors (`harbingermotors`), HeartFlow (`heartflowinc`), HexArmor (`hexarmor`), HP IQ (`hpiq`), iCapital (`icapitalnetwork`), ID.me (`idme`), Integrated Specialty Coverages (`isccareers`), K2 Space (`k2spacecorporation`), Klaviyo Campus (`klaviyocampus`), Koalafi (`koalafi`), Kodiak Robotics (`kodiak`), Launch Potato (`launch2`), LG Electronics (`lgelectronics`), Lila Sciences (`lilasciences`), May Mobility (`maymobility`), Mesh (`mesh`), Modern Health (`modernhealth`), Natera (`natera`), National Information Solutions Cooperative (NISC) (`nisc`), Neros Technologies (`nerostechnologies`), Neuralink (`neuralink`), NICE (`nice`), OneTrust (`onetrust`), OpenTeams (`openteams`), OppFi (`opploans`), Otterbein SeniorLife (`otterbein`), Outrider (`outrider`), Paperless Parts (`paperlessparts`), Perpay (`perpay`), PhysicsX (`physicsx`), Pindrop (`pindropsecurity`), Proconex (`proconex`), Prolific (`prolific`), QuEra Computing, Inc. (`queracomputinginc`), Radix Trading (University) (`radixuniversity`), Rampant Technologies (`rampanttechnologies`), Recidiviz (`recidiviz`), Relativity Space (`relativity`), Resource Environmental Solutions (`res`), Showpad (`showpad`), Sigma Computing (`sigmacomputing`), SimpliSafe (`simplisafe`), Sparksoft (`sparksoftcorporation`), Specialty1 Partners (`specialty1`), Stoke Space (`stokespacetechnologies`), Strive Health (`strivehealth`), Striveworks (`striveworks`), SupplyHouse.com (`supplyhouse`), tastytrade (`tastytrade`), Teads (`teads1`), Tenet3 (`tenet3`), Triumvirate Environmental (`triumvirateenvironmental`), True Anomaly (`trueanomalyinc`), Tubi (`tubitv`), Voyager Technologies (`voyagertechnologiesinc`), Wildlife Studios (`wildlifestudios`), Yext (`yext`)

**Lever (35):** Alloy.ai (`alloy`), ARSIEM Corporation (`arsiem`), Beghou Consulting (`beghouconsulting`), Belvedere Trading (`belvederetrading`), Centuria (`centuria`), CGS Federal (`cgsfederal`), Commonwealth Fusion Systems (`cfsenergy`), Computer World Services (`cwsc`), Dexterity (`dexterity`), Dutch (`dutch`), Electric Mind (`electricmind`), Eleos Technologies (`eleostech`), ERG (`erg`), Fehr & Peers (`fehrandpeers`), Finch (`finch`), Grant Street Group (`grantstreet`), Hermeus (`hermeus`), Hive (`hive`), Intenseye (`intenseye`), K Group Companies (`kgroupcompanies`), Laminar (`runlaminar`), Life.Church (`life`), Lightcast (`economicmodeling`), Mendix (`mendix`), Prosper (`prosper`), Protective Life (`protective`), Shield AI (`shieldai`), Skyward IT Solutions (`skywarditsolutions`), Spry Methods (`sprymethods`), SteerBridge (`steerbridge`), Telligen (`telligen`), Thea Energy (`thea.energy`), True Zero Technologies (`truezerotech`), TrueML (`trueml`), Wyetech (`wyetechllc`)

**Ashby (38):** Aescape (`aescape`), Aurelian (`aurelian`), Base Power (`base-power`), Clay (`claylabs`), Cogent Security (`cogent-security`), Dryft (`dryft`), Etched (`etched`), Fluidstack (`fluidstack`), Focused Energy (`focused`), Forward Financing (`forward%20financing`), Helion (`helion`), Hippocratic AI (`hippocratic%20ai`), Hiya (`hiya`), Jerry.ai (`jerry.ai`), Lambda (`lambda`), Legora (`legora`), LPA Design Studios (`lpadesignstudios`), MatX (`matx`), Mercor (`mercor`), Mind Robotics (`mindrobotics`), Miter (`miter`), Pivotal Health (`pivotal-health`), Promise (`promise-studios`), Quicknode (`quicknode`), Realm (`realmalliance`), REGENT (`regent`), Reliable Robotics (`reliable-robotics`), Rivian and Volkswagen Group Technologies (`rivianvw.tech`), Rox Data Corp (`rox-data-corp`), Saronic (`saronic`), Scan.com (`scan-com`), Swarm Aero (`swarmaero`), Tennr (`tennr`), Tradeify (`tradeify`), TypeSafe (`typesafe-ai`), Vola Dynamics (`voladynamics`), Vultr (`vultr`), Zello (`zello`)

**Workday (74):** 7-Eleven (`my7elevenhr/careers`), A-dec (`adec/A-dec`), Abbott (`abbott/abbottcareers2`), Academy District 20 (`asd/asd20`), Alkami (`alkami/alkami`), alliantgroup (`alliantgroup/alliantgroup`), Amentum (`pae/Amentum_Careers`), Ares Management (`aresmgmt/External`), Arrowstreet Capital (`arrowstreetcapital/Arrowstreet`), Blue Origin (`blueorigin/BlueOrigin`), BMO (`bmo/External`), BMO Campus (`bmo/campus`), Cambium Learning (`cambiumlearning/camb`), Cars Commerce (`cars/cars`), Caterpillar (`cat/caterpillarcareers`), Cboe Global Markets (`cboe/External_Career_CBOE`), Centric Software (`centricsoftware/centric`), Clark Construction (`clark/clarkexternal`), CoStar Group (`costar/CoStarCareers`), DELO (`delo/DELO-Jobs`), DPR Construction (`mydpr/11212017`), Duck Creek Technologies (`duckcreek/duckcreekcareers`), Eos Energy Enterprises (`eosenergystorage/EoS`), Ferrovial (`ferrovial/Ferrovial_Career_Site`), GAF (`gafsgi/gaf_careers`), GE Vernova (`gevernova/Vernova_ExternalSite`), GEA Group (`gea/equest`), Guidehouse (`guidehouse/External`), Hewlett Packard Enterprise (`hpe/WFMathpe`), Highmark Health (`highmarkhealth/highmark`), HNTB (`hntb/HNTB_Careers`), Humana (CenterWell) (`humana/centerwell_external_career_site`), JLL (`jll/jllcareers`), Kyndryl (`kyndryl/KyndrylProfessionalCareers`), Lennar (`lennar/Lennar_Jobs`), Little Caesars (`ilitch/LC`), London Stock Exchange Group (`lseg/Careers`), Lowe's (`lowes/LWS_External_CS`), Luma Energy (`lumaenergy/lumacareers`), Maritz (`maritz/Maritz`), Markel (`markelcorp/GlobalCareers`), McKesson (`mckesson/sourcer_on_req`), Meijer (`meijer/Meijer`), Michelin (`michelinhr/Michelin`), Mimecast (`mimecast/Mimecast-Careers`), Mosaic (`mosaic/mosaic`), Motorola Solutions (`motorolasolutions/Careers`), Nationwide (`nationwide/Nationwide_Career`), Nebraska Medicine (`nebraskamed/NM`), Nelnet (`nelnet/MyNelnet`), Nextracker (`nextracker/nextpower_careers`), Pima County (`pimacounty/pimacareers`), Plante Moran (`plantemoran/pmexternalcareers`), Prime Therapeutics (`primetherapeutics/PrimeTherapeuticsCareers`), Primient (`primient/External_Careers`), Raymond James (`raymondjames/RaymondJamesCareers`), Restaurant Brands International (`rbi/RBI_External_Career_Site`), Rio Tinto (`riotinto/riotinto_careers`), Ryan Specialty (`ryansg/Ryan_Specialty_Career_Site`), Simons Foundation (`simonsfoundation/simonsfoundationcareers`), Simpson Thacher & Bartlett LLP (`stblaw/careers`), Snap Finance (`snapfinance/Snap_External_Careers`), Symbotic (`symbotic/Symbotic`), T-Mobile (`tmobile/External`), Texas A&M University System (`tamus/system-wide_external`), Texas Rangers (`rangersmlb/Rangers`), The Cigna Group (`cigna/cignacareers`), TKO Group (WWE) (`wwecorp/tko`), TopBloc (`topbloc/TopBloc_Careers`), TreeHouse Foods (`treehouse/TreeHouseCareers`), Tyson Foods (`tysonfoods/TYIT`), U.S. Bank (`usbank/US_Bank_Careers`), Vanguard (`vanguard/vanguard_external`), Verizon (`verizon/verizon-careers`)

### Not added from this export (no fetcher for the ATS)

Employers whose links only point at an ATS without an adapter, by family (an employer
with links on several families counts in each):

**SmartRecruiters** (38), **iCIMS** (38), **Oracle HCM** (22), **UKG/UltiPro** (19), **Dayforce** (16), **Paylocity** (16), **Rippling** (16), **ADP** (13), **Workable** (8), **Taleo** (7), **Eightfold** (5), **Pinpoint** (5), **Gem** (4), **HRM Direct** (3), **Avature** (3), **Jobvite** (3), **JazzHR** (3), **Paycom** (3), **UKG** (2), **BambooHR** (2), **Dover** (1), **careers-page.com** (1), **Teamtailor** (1), **Breezy** (1), and 167 on custom career sites or other hosts.
Demand for these adapters is tracked in #316 and #173 (iCIMS).

## 2026-09-25 — 38 boards added after a live probe (Greenhouse + Ashby)

319 candidate slugs were probed against the public Greenhouse and Ashby APIs; a
board was added only if it answered and had open roles whose titles carry an
entry-level marker (new grad, graduate, junior, associate, I/II, analyst,
coordinator, 2025-2027) and no senior/intern marker. Chosen to dilute the
defense/aerospace share of the board with fintech, SaaS, trading, cloud,
health and AI employers.

**Greenhouse (28):** Sezzle (`sezzle`), AQR Capital Management (`aqr`), Astranis (`astranis`), IMC Trading (`imc`), Braze (`braze`), Pure Storage (`purestorage`), Old Mission Capital (`oldmissioncapital`), Motive (`gomotive`), SentinelOne (`sentinellabs`), Akuna Capital (`akunacapital`), DigitalOcean (`digitalocean98`), Toast (`toast`), Redwood Materials (`redwoodmaterials`), CoreWeave (`coreweave`), Adyen (`adyen`), Flow Traders (`flowtraders`), Planet Labs (`planetlabs`), Zipline (`flyzipline`), Klaviyo (`klaviyo`), Motional (`motional`), Jamf (`jamf`), Iterable (`iterable`), Zocdoc (`zocdoc`), Smartsheet (`smartsheet`), Betterment (`betterment`), Virtu Financial (`virtu`), Qualtrics (`qualtrics`), Rocket Lab (`rocketlab`)

**Ashby (10):** Harvey (`harvey`), Cognition (`cognition`), Abridge (`abridge`), Replit (`replit`), Zip (`zip`), Valon (`valon`), Lightfield (`lightfield`), N1 (`n1`), OffDeal (`offdeal`), Midjourney (`midjourney`)

Probed but not added (answered, but no entry-level titles open that day):
Wayfair, Etsy, Grammarly, Asana, Snyk, Gong, Calendly, Loom, Zapier, Box,
Coda, ClickUp, Netlify, Kong, Chainguard, Teleport, Drata, Wise, Remitly,
Circle, Anchorage, Uniswap Labs, Hudson River Trading, Optiver, Citadel,
Two Sigma, D. E. Shaw, Millennium, Bridgewater, Vanguard, Fidelity.

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

## 2026-09-24 — Greenhouse and Ashby cleanup (`HTTP 404`)

The board API returned `404` for 34 Greenhouse boards and 14 Ashby boards (verified
with curl). Twelve of those companies had moved ATS and were re-added on their new
board; the rest were removed.

| Company | Old board | Action |
|---|---|---|
| ClickHouse, Materialize, Temporal, Ramp, Deel, Vanta, Miro, Confluent, Niantic, Alchemy | Greenhouse | moved to Ashby (re-added) |
| Zoox, Kraken | Greenhouse | moved to Lever (re-added) |
| Cohere, Notion | Greenhouse | already configured on Ashby; Greenhouse duplicate removed |
| Cerebral, Magic Leap, Marqeta, Opendoor, Postman, Unity Technologies, Hugging Face, Adept AI, Character AI, Jasper, Rippling, Pipe, Navan, Retool, Canva, dbt Labs, HashiCorp, Aurora, Cruise, Chainalysis | Greenhouse | removed (board gone; no public Greenhouse/Ashby/Lever board found) |
| Anthropic, Databricks | Ashby | removed (still configured on Greenhouse, which works) |
| Cal.com, Dub, Groq, Hugging Face, Mistral AI, PlanetScale, Replicate, Scale AI, Statsig, Tinybird, Together AI, Weights & Biases | Ashby | removed (slug no longer exists) |
