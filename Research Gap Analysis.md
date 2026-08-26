Literature Review & Research Gap Analysis
 
# ScrapLink — A Digital B2B Waste Economy Platform
 
Twenty prior-work papers reviewed against the proposed system
 
Per-paper gap statements and a consolidated novelty comparison.
 
This document reviews the twenty papers most relevant to the ScrapLink proposal and positions the system's contribution against each. For every paper it summarizes the scope, states the specific gap left open, and explains what ScrapLink adds on top of it. The reviewed work spans ten strands — industrial-symbiosis platforms, operational waste marketplaces, AI-based waste recognition, IoT-enabled collection, operations-research routing optimisation, digital governance for zero-waste cities, empirical studies of digital transformation in the circular economy, lightweight mobile reporting systems for recycling operations, informal-sector inclusion and cooperative models, and policy- and barrier-level analyses of circular-economy adoption. A consolidated feature comparison and an overall novelty statement follow the individual reviews.
 
* * *
 
Paper 1 of 20
 
## Digital Platforms for Industrial Symbiosis
 
Krom, Piscicelli & Frenken (2022)
 
### What the paper covers
 
The paper studies digital platforms that help companies identify opportunities to exchange residual resources and build industrial-symbiosis networks. It specifically investigates barriers such as limited sustainability commitment, lack of cooperation and information sharing, and technical or economic constraints.
 
### Research gap
 
The platform concept revolves primarily around finding and enabling industrial-symbiosis opportunities. The study also shows that platform design alone does not resolve the broader organisational, economic, and information-sharing barriers.
 
### What ScrapLink adds
 
ScrapLink extends the concept into an actual end-to-end B2B transaction ecosystem:
 
  * Verified businesses and recyclers through onboarding / KYC
  * Bulk waste listing with quantity, grade, and images
  * AI-based waste classification and value prediction
  * RFQ and competitive bidding
  * Pickup scheduling, tracking, and route optimisation
  * Escrow / payment and invoicing
  * Contracts and vendor management
  * Certification and chain-of-custody
  * Sustainability / ESG analytics
Gap statement for report
 
Existing industrial-symbiosis platforms primarily focus on identifying resource-exchange opportunities, whereas the proposed platform extends this concept into a complete B2B ecosystem covering discovery, valuation, bidding, logistics, payment, contracting, certification and post-transaction analytics.
 
Paper 2 of 20
 
## Hubs for Circularity: Reference Architecture of Digital Collaboration Platforms
 
Afash et al. (2026)
 
### What the paper covers
 
This paper is among the closest prior work to ScrapLink. It develops a reference architecture for digital collaboration platforms in industrial symbiosis, and identifies a major weakness in earlier systems: many focus heavily on matchmaking and synergy identification while providing little support for later phases such as implementation and monitoring.
 
### Research gap
 
The authors point to a lack of fully functional operational systems — much of the existing research consists of proof-of-concept, hypothetical, or case-specific platforms. They also note that existing platforms often provide limited decision support and do not comprehensively cover the full industrial-symbiosis lifecycle.
 
### What ScrapLink adds
 
ScrapLink moves toward a commercially oriented system across four layers:
 
  * **Marketplace & transaction layer** — RFQ, bidding, spot transactions, long-term supply agreements
  * **Commercial layer** — dynamic pricing, digital wallet, invoicing, escrow payments
  * **Operational layer** — pickup scheduling, logistics partners, route optimisation, weighbridge verification
  * **Compliance layer** — KYC, certification, chain-of-custody, audit-ready records
Note for the report: this paper does address the full industrial-symbiosis cycle conceptually and evaluates a prototype, so it should not be described as having no implementation or monitoring at all. The safer, defensible claim is that ScrapLink adds a more transaction-oriented B2B marketplace and commercial workflow on top of it.
 
Gap statement for report
 
Although existing digital collaboration platforms provide a reference architecture for industrial symbiosis, they do not fully integrate commercial transactions, dynamic pricing, logistics, payments, compliance and certification into one operational B2B marketplace.
 
Paper 3 of 20
 
## Recyclable Waste Image Recognition Based on Deep Learning
 
Zhang et al. (2021)
 
### What the paper covers
 
This research develops a deep-learning image-classification model for recyclable waste, using an improved ResNet18 architecture to classify six categories: cardboard, paper, metal, plastic, glass, and other waste.
 
### Research gap
 
The paper is fundamentally a computer-vision classification study, not an end-to-end waste-economy system. Its purpose is to improve recognition accuracy rather than manage the commercial lifecycle of the classified waste, and its classification scope is limited to six broad categories.
 
### What ScrapLink adds
 
In ScrapLink, the AI classification result becomes one input feeding the rest of the platform:
 
Image → Waste Category → Grade / Purity → Estimated Value → Marketplace → Buyer / Recycler → Logistics → Payment → Certification
 
ScrapLink specifically pairs AI classification and grading with value prediction, marketplace matching, and route optimisation. So instead of AI simply answering "what type of waste is this?", the system aims to answer what the waste is, what grade it is, what it is worth, who can buy it, how it should be transported, and how the transaction can be verified.
 
Gap statement for report
 
Existing deep-learning research focuses primarily on identifying waste categories from images, whereas ScrapLink uses AI classification as one component of a larger B2B workflow involving grading, valuation, marketplace matching, logistics and traceability.
 
Paper 4 of 20
 
## IoT-Enabled Routing Optimization for Waste Collection
 
Maciel et al. (2025)
 
### What the paper covers
 
A systematic review and meta-analysis of IoT-enabled waste-routing research. Across the included studies, IoT-based routing reduced collection distance by an average of 21.51%. The paper also highlights differences between simulated and real-world deployments.
 
### Research gap
 
The research is specifically about routing and collection efficiency; it does not create a complete marketplace or commercial ecosystem around waste. The authors also note limitations in the underlying literature: few studies provided sufficient quantitative data, there was an imbalance between simulated and real-world studies, and the overall sample was relatively small.
 
### What ScrapLink adds
 
ScrapLink's route optimiser does not operate in isolation — it draws on:
 
  * Available waste lots and generator locations
  * Recycler / buyer locations
  * Vehicle availability and pickup requests
  * Request density and traffic / dock constraints
Critically, the route is connected to the marketplace transaction. Where the underlying research asks "how can we collect waste more efficiently?", ScrapLink asks which waste should be collected, from whom, by which logistics partner, to which qualified recycler or buyer, and through what route.
 
Gap statement for report
 
Existing IoT routing research optimises waste-collection logistics independently, while the proposed platform integrates route optimisation with waste availability, marketplace matching, recycler selection and B2B transactions.
 
Paper 5 of 20
 
## Blockchain Framework for Sustainable Waste Management
 
Castiglione et al. (2023)
 
### What the paper covers
 
Proposes a blockchain-based methodology for optimising waste-management processes and supporting a circular economy, with emphasis on standardisation, stakeholder coordination, and cost reduction.
 
### Research gap
 
Blockchain is used primarily as enabling infrastructure for transparency and optimisation, not as part of a comprehensive B2B commercial marketplace with AI-based classification, market pricing, RFQs, bidding, and logistics. More broadly, blockchain-based circular-economy research still faces scalability, interoperability, data-protection, and regulatory challenges.
 
### What ScrapLink adds
 
ScrapLink's blockchain / traceability component is only one layer, combined with:
 
  * AI waste recognition and quality / grade estimation
  * Price prediction
  * Marketplace / RFQ and bidding
  * Digital contracts and escrow payments
  * Pickup verification
  * ESG analytics
The system proposes immutable chain-of-custody records while explicitly connecting them to compliance and certification workflows.
 
Gap statement for report
 
Existing blockchain-based waste-management research primarily addresses transparency and traceability, whereas ScrapLink integrates blockchain with AI, B2B marketplace functions, pricing, logistics, payments and compliance.
 
Paper 6 of 20
 
## Intelligent Waste Management System Using Deep Learning with IoT
 
Rahman, Islam, Hasan, Bithi, Hasan & Rahman (2022)
 
### What the paper covers
 
The paper couples a convolutional neural network with an IoT-instrumented smart bin. A Raspberry Pi and camera module classify waste as digestible or indigestible, with five indigestible sub-categories, reaching 95.31% classification accuracy over 34 epochs. The bin itself uses a microcontroller with an ultrasonic fill-level sensor and a load cell for weight, streaming real-time data over IoT and Bluetooth to an Android application and a web dashboard. A System Usability Scale study with 14 users returned a score of 86%.
 
### Research gap
 
The contribution stops at the bin. The authors themselves record three limitations: the model handles only five categories of indigestible waste, the prototype carries only two sensors, and fill-level readings misreport a bin as full when waste stacks unevenly. Beyond these, the work is scoped to household monitoring — once waste is classified and weighed, nothing in the system determines what the material is worth, who should receive it, or how the transfer is recorded. Recyclables are recognised but never traded.
 
### What ScrapLink adds
 
ScrapLink treats classification and bin telemetry as the first step of a commercial pipeline rather than the end product:
 
  * Industrial waste taxonomy well beyond five categories — plastic, paper, e-waste, metal, glass, organic and textile streams
  * Grade and purity estimation layered on top of category detection, because B2B price depends on contamination, not type alone
  * Value prediction that converts a classified, weighed lot into an indicative market price
  * Marketplace matching, RFQ and bidding so the classified lot reaches a verified buyer
  * Weighbridge and pickup verification cross-checking the sensor weight the paper measures at source
  * Chain-of-custody and certification records that survive after the bin is emptied
The distinction is one of purpose. The reviewed system answers "is this bin full, and is its contents recyclable?" ScrapLink answers "what is this material worth, which verified recycler should buy it, and how is that transaction proven?"
 
Gap statement for report
 
Existing deep-learning and IoT waste systems stop at household bin-level classification and fill-level monitoring, whereas ScrapLink carries the classified and weighed material forward through grade estimation, valuation, B2B marketplace matching, logistics, payment and chain-of-custody.
 
Paper 7 of 20
 
## Waste Management 2.0: Leveraging IoT for an Efficient and Eco-Friendly Smart City Solution
 
Addas, Khan & Naseer (2024)
 
### What the paper covers
 
An end-to-end smart-city waste framework built on ultrasonic fill-level sensors, a LoRaWAN and cellular networking layer, cloud ingestion and analytics, and route-optimisation algorithms driven by live bin data. Pilot trials across ten locations in Lahore deployed roughly 5,000 sensor units over twelve months, recording 92% sensor uptime and 89% LoRaWAN transmission success. Reported outcomes include a 20% reduction in overall waste-management cost, average annual savings of USD 410,000 per city, 15% lower carbon emissions, and a 20% increase in recyclable recovery worth USD 3.2 million per city annually.
 
### Research gap
 
The system is municipally owned and municipally optimised: value is captured as avoided cost, not as a market. The paper reports that cleaner streams increased recyclable recovery and generated revenue, but provides no mechanism for price discovery, buyer matching, contracting or traceable transfer of that material to industrial purchasers. The authors' own future-work list — blockchain, open data APIs, integrated recycling systems — identifies precisely this missing transactional layer. The architecture also assumes municipal fleet ownership, which excludes the informal and private recycling sector that handles most recoverable material in developing economies.
 
### What ScrapLink adds
 
ScrapLink builds the market layer that sits above this telemetry layer:
 
  * Sensor and weighbridge readings become supply-side inventory in a live B2B exchange rather than only a collection trigger
  * Dynamic pricing and competitive bidding replace fixed municipal disposal contracts as the mechanism for setting value
  * Verified private recyclers, scrap dealers and industrial buyers participate alongside municipal fleets, not instead of them
  * Escrow-backed settlement and invoicing close the loop the paper leaves open at "revenue generated"
  * Chain-of-custody and certification convert recovered tonnage into audit-ready ESG evidence for the buying industry
ScrapLink's route optimiser inherits the same logic validated here — fill-level-driven collection — but routes toward a matched buyer rather than toward a municipal depot.
 
Gap statement for report
 
Existing IoT smart-city platforms optimise municipal collection and quantify cost and emission savings, whereas ScrapLink converts monitored waste into priced, tradable and traceable inventory within a B2B marketplace connecting generators, verified recyclers and industrial buyers.
 
Paper 8 of 20
 
## Digital Transformation in Waste Management: Digital Governance for Zero-Waste Cities
 
Rittl, Zaman & de Oliveira (2025)
 
### What the paper covers
 
The article proposes a digital-government structure for urban solid-waste planning and management in the Global South, built on WebGIS as the integrating environment for physical and human data. It argues that analogue, data-poor management is no longer viable under the UN SDGs, and presents initial results from Florianópolis, Brazil, including the publication of open waste data and indicators. The authors cite evidence that digitising the sector can cut the municipal waste budget by 30–35% and reduce CO2 emissions by roughly 15%.
 
### Research gap
 
The work is explicitly framed as ongoing research presenting an initial conception, and it is governance-first: it plans, publishes and monitors, but does not transact. The structure informs public policy and control bodies, yet the actual exchange of material between generators, scrap dealers, recyclers and industry — the mechanism through which a circular economy actually circulates — sits outside its scope. There is no AI classification, no valuation, no bidding, and no payment or settlement capability, and the model depends on municipal initiative as the inducing agent for change.
 
### What ScrapLink adds
 
ScrapLink supplies the private-sector counterpart that a digital governance layer needs in order to have transactions to govern:
 
  * A working transaction engine — listing, valuation, bidding, settlement — rather than a planning and reporting structure
  * Market-driven participation, so adoption does not depend on a municipality acting first
  * Geospatial data used operationally for pickup routing and recycler matching, not only for planning and coverage assessment
  * Transaction-level records that can feed exactly the municipal indicators and compliance reporting this paper says are absent
  * Formal onboarding of informal scrap dealers, addressing the value-chain actors the governance model can observe but not organise
The two are complementary rather than competing: ScrapLink can be read as the marketplace that a digital waste-governance system would need to plug into, and its ESG analytics module is designed to export the indicator set such a system consumes.
 
Gap statement for report
 
Existing digital-governance and WebGIS research delivers public-sector planning, monitoring and transparency structures for zero-waste cities, whereas ScrapLink supplies the missing commercial transaction layer — AI valuation, bidding, payment and certified chain-of-custody — that turns governance data into an operating waste market.
 
Paper 9 of 20
 
## Integration of GIS, Big Data and Artificial Intelligence in Modern Waste Management Systems
 
Kochanek et al. (2026) — comprehensive review
 
### What the paper covers
 
A comprehensive review mapping GIS, Big Data and AI onto the five core management functions of a waste system: planning, organising, coordinating, leading and controlling. It surveys route planning, waste-stream forecasting, service-coverage assessment, anomaly detection and performance monitoring, and classifies the obstacles to adoption into technological, organisational and regulatory-legal barriers. Its recommendations include unified data standards and exchange protocols, regional or national repositories for interoperability, and automated reporting through IoT and RFID.
 
### Research gap
 
Being a review, it delivers no implemented or validated system — it maps what is possible rather than demonstrating it. The open problems it names remain open: data standardisation and interoperability, data quality and governance, the transferability and scalability of AI models across cities, computational cost, and cybersecurity and GDPR compliance. Critically, the entire analysis is framed around operational efficiency and public administration; the commercial dimension is absent, and none of the reviewed integration is oriented toward creating a market for recovered material.
 
### What ScrapLink adds
 
ScrapLink responds to several of the named barriers with concrete platform mechanisms rather than recommendations:
 
  * A single shared schema for waste categories, grades and quantities across every stakeholder role — the data-standardisation barrier addressed by design
  * KYC-verified listings and weighbridge confirmation, giving data provenance and quality at the point of capture
  * Immutable chain-of-custody records answering the traceability, auditability and trust gap directly
  * AI models trained on cross-city transaction data rather than a single municipality's dataset, improving the transferability the review flags as unresolved
  * Role-based access and consent-based data sharing consistent with the privacy and regulatory constraints identified
This paper is best used in the report as evidence that the gaps ScrapLink targets are independently recognised in the recent review literature, rather than as a competing system.
 
Gap statement for report
 
Existing GIS–Big Data–AI reviews catalogue technological capability and adoption barriers without delivering an operational system, whereas ScrapLink implements a working platform that standardises waste data across stakeholders and connects it to valuation, trading and auditable traceability.
 
Paper 10 of 20
 
## Digital Transformation and Green Innovation for Sustainable Waste Management
 
Tanveer & Alsharah (2026)
 
### What the paper covers
 
A quantitative study of 309 managers in Riyadh manufacturing firms, analysed with partial least squares structural equation modelling. It finds that digital transformation improves sustainable waste management performance both directly and indirectly, with green innovation and organisational circular-economy practices acting as transmission mechanisms and Vision 2030 environmental commitment shaping the relationship. The authors report an integrative framework linking digital capability to sustainability outcomes in a setting where such evidence was previously fragmented.
 
### Research gap
 
The study establishes that digital transformation improves waste outcomes, but not how. No artefact, architecture or tool is proposed — "digital transformation" remains a latent construct measured through manager perceptions. The authors list the resulting limitations: single-region data, a cross-sectional design that cannot establish causation, self-report survey data subject to respondent bias, and a restricted set of predictors. The operational question a firm actually faces — through what system does it list, price, sell and prove the disposal of its residual material — is left entirely unanswered.
 
### What ScrapLink adds
 
ScrapLink is a concrete instantiation of the construct this study validates statistically:
 
  * The platform is the digital transformation, not a proxy for it — firms perform circular practices through it rather than reporting attitudes about them
  * Circular-economy practice becomes observable behaviour: lots listed, bids accepted, material diverted, tonnage certified
  * ESG metrics are derived from completed transactions instead of self-assessment, removing the respondent bias the authors flag
  * Longitudinal transaction histories accumulate naturally, addressing the cross-sectional limitation the study identifies
  * Green innovation is embodied in specific components — AI grading, value prediction, route optimisation — rather than treated as a survey construct
For the report, this paper is the strongest available justification for why a platform like ScrapLink should exist: it supplies peer-reviewed empirical support that the intervention works, while leaving the intervention itself unbuilt.
 
Gap statement for report
 
Existing empirical research establishes a statistical association between digital transformation and sustainable waste management performance but offers no system through which firms enact it, whereas ScrapLink operationalises that association as a working B2B platform generating transaction-level circular-economy evidence.
 
Paper 11 of 20
 
## A Collaboration Platform for Enabling Industrial Symbiosis: Database Engine for Waste-to-Resource Matching
 
Low, Tjandra, Yunus, Chung, Tan, Raabe, Ng, Yeo, Bressan, Ramakrishna & Herrmann (2018)
 
### What the paper covers
 
The paper extends an earlier By-product Exchange Network collaboration platform with a database engine for waste-to-resource matching. Built on a Neo4j graph database and organised using Harmonized System classification codes, the engine stores resources, wastes and the technologies that convert one into the other, and exposes a query processor that returns and graphically visualises conversion pathways through a web interface. Two use cases demonstrate it: apple peels as a waste input, and cellulose as a target resource, for which the engine surfaces twenty possible waste-to-resource pathways with their associated processes — iodine-catalysed chemical modification of rice straw, chemical retting with steam explosion, recycled paper pulp, and others. The wider platform architecture is described in three layers (data, logic, user interface) with a game-theory-based industrial-symbiosis matching subsystem and what-if economic scenario analysis.
 
### Research gap
 
The engine answers a technical feasibility question — what _could_ this waste become, and by what process — rather than a commercial one. There is no price, no quantity, no counterparty and no transaction anywhere in the model: a firm learns that its rice straw can yield cellulose, but not who will buy it, at what rate, in what volume, or how the handover would be executed and evidenced. The authors state that the database is populated principally around paper and food wastes because those are Singapore's dominant streams, and that population is ongoing, so coverage is knowledge-limited and geographically anchored. Matching is also static and catalogue-driven: it reflects curated literature on conversion technologies rather than live supply, live demand or live pricing, and nothing in the pipeline assesses the actual grade or contamination of the material a firm holds.
 
### What ScrapLink adds
 
ScrapLink treats the knowledge layer this paper builds as an input to a market rather than as the deliverable:
 
  * Listings carry quantity, grade and purity, so a match is an executable lot rather than a theoretical pathway
  * AI classification and grading determine what the material actually is, instead of relying on the firm's own declaration into a taxonomy
  * Value prediction and competitive bidding attach a price to the pathway, which the graph engine deliberately leaves unpriced
  * Matching is driven by live counterparty inventory and verified buyer capability, not only by curated conversion-technology knowledge
  * Logistics, escrow settlement and chain-of-custody carry the match through to a completed, evidenced transfer
Read together, the two are sequential rather than competing: this paper establishes that graph-based waste-to-resource knowledge can be modelled and queried, and ScrapLink is what happens when that match is required to clear as a commercial transaction.
 
Gap statement for report
 
Existing waste-to-resource matching engines identify technically feasible conversion pathways from curated knowledge bases, whereas ScrapLink converts a feasible match into an executable transaction by attaching graded quantity, predicted value, competitive bidding, logistics and verified chain-of-custody to it.
 
Paper 12 of 20
 
## Challenges of Digital Waste Marketplace — The Upvalue Platform
 
Soares, Ribeiro, Vasconcelos, Barros, Castro, Vilarinho & Carvalho (2023)
 
### What the paper covers
 
This is the single closest prior work to ScrapLink in intent: a digital marketplace where companies buy and sell industrial waste and by-products. Developed under the Upcycle4Biz project in Portugal by a consortium of a waste valorisation centre, a university, and industry software partners, the Upvalue platform is presented alongside a detailed account of the obstacles to building such a market. The authors construct a purpose-built commercial taxonomy of fifteen main waste categories and 288 subcategories — plastics, paper and cardboard, glass, metals, organic, wood, textiles, chemicals, construction materials, packaging, used oils, used tyres, batteries and accumulators, end-of-life vehicles, and electrical and electronic materials — reconciled against European Waste List (LER) codes, hazardousness assessment under Regulation 1357/2014, and end-of-waste / by-product declassification criteria. Listings carry name, description, LER code, origin, shape and colour, and additives. The delivered platform provides a marketplace with search, favourites, a prominent "+ sell" ad-posting flow, notifications, a partners' network covering characterisation, declassification and logistics, a Media Corner, and a customer area, with purchase and sale conditions gated by user profile and the licence the user holds — developed in consultation with the Portuguese Environment Agency. The paper also documents the sector's barriers: lack of commitment to sustainable development, lack of information sharing, lack of cooperation and trust, technical infeasibility, uncertainty in environmental legislation, and economic unfeasibility, alongside a weak legal framework for industrial symbiosis and low R&D intensity in the Portuguese waste sector (0.6%).
 
### Research gap
 
Because this paper occupies the same problem space as ScrapLink, the gap it leaves is the most consequential one in this review — and it is a gap of depth rather than of direction. Upvalue is a _listing-and-search_ marketplace wrapped in a regulatory compliance framework. A seller manually classifies and describes their own waste and posts an advertisement; a buyer searches and makes contact. Everything the transaction subsequently requires sits outside the platform. There is no AI classification or verification of what the material actually is, no grade or purity estimation, no valuation or price prediction, no structured RFQ or competitive bidding mechanism, no escrow, invoicing or settlement, no pickup scheduling or route optimisation, no weighbridge verification, no blockchain or chain-of-custody record, and no ESG analytics derived from completed trades. The paper is also descriptive rather than evaluative: it presents the platform's architecture and interface but reports no deployment data, no user base, no transaction volumes and no performance metrics against which the design can be assessed. Its taxonomy, licensing logic and declassification workflow are tightly bound to the Portuguese and EU legal framework, and the authors themselves note that waste markets differ technically and legally between member states — so the model is not directly transferable. Finally, the paper identifies trust between counterparties as a primary barrier but addresses it only through licence-based registration, leaving no mechanism to verify that a delivered lot matches what was advertised.
 
### What ScrapLink adds
 
ScrapLink accepts this paper's framing of the problem and extends the platform from a listing venue into a transaction engine:
 
  * **Verified rather than declared material** — AI classification and grade/purity estimation independently characterise the lot, where Upvalue depends entirely on seller self-declaration into the LER taxonomy
  * **Price discovery instead of private negotiation** — value prediction plus structured RFQ and competitive bidding, replacing an advertisement and a contact form
  * **Settlement inside the platform** — escrow, invoicing and digital contracts, so the trade completes rather than merely being initiated
  * **Fulfilment as a first-class layer** — pickup scheduling, logistics partner assignment, route optimisation and weighbridge confirmation, where Upvalue offers logistics only as an external partner referral
  * **Trust engineered, not assumed** — immutable chain-of-custody and certification records answer the trust barrier the authors identify but resolve only through licensing checks
  * **Evidence generated as a by-product of trading** — ESG and diversion analytics computed from completed transactions, which a listings board structurally cannot produce
Note for the report: this is the paper against which ScrapLink's novelty must be argued most carefully. The claim "no digital waste marketplace exists" is not defensible — Upvalue exists, and the authors note that several other national platforms do too. The defensible claim is that existing waste marketplaces operate as regulated listing and matchmaking boards, and that ScrapLink's contribution is the AI-verified, priced, bid-cleared, logistically fulfilled and cryptographically traceable transaction layer built on top of that listing function.
 
Gap statement for report
 
Existing digital waste marketplaces provide regulated listing, taxonomy and search functionality in which sellers self-declare their material and buyers negotiate privately, whereas ScrapLink adds AI-based verification and grading, predicted valuation, competitive bidding, escrow settlement, integrated logistics and immutable chain-of-custody so that the transaction is executed, fulfilled and evidenced within the platform itself.
 
Paper 13 of 20
 
## Waste Classification and Management Using Computer Vision
 
Deng, Fan & Sun (2025) — Stanford CS231N
 
### What the paper covers
 
A controlled benchmark of three architectures — a custom baseline CNN, a pretrained ResNet34, and a Vision Transformer — on the TACO dataset of cluttered, real-world litter images, classified into 27 superclasses. The study is unusually useful because it reports honest numbers on hard data rather than headline accuracy on clean, single-object benchmarks. The baseline CNN on the raw 1,500-image dataset achieved 0.13% test F1; augmentation to 10,140 images lifted it to 12.3%; ResNet34 reached 63.4% precision, 45.0% recall and 49.8% F1; and the ViT achieved the best result at 69.1% precision, 59.7% recall and 60.7% F1. Two findings matter more than the ranking. First, architectural improvement vastly outweighed data augmentation. Second, and contrary to the authors' own hypothesis, class imbalance was _not_ the dominant limiting factor — several high-support classes performed poorly (Plastic bag & wrapper 16.3% recall at 49 samples, Bottle 17.5% at 40) while some low-support classes performed well (Lid 30% recall at 10 samples), indicating that inherent visual distinguishability varies by material regardless of sample size. On throughput, ResNet34 ran at 748.3 FPS and ViT at 384.5 FPS on a T4, both far above the 30–60 FPS threshold for industrial sorting, and the authors argue for roughly 10× hardware cost reduction through edge deployment on Jetson Nano or Coral class devices.
 
### Research gap
 
The headline result is also the limitation: the best model reaches roughly 61% F1 on realistic, cluttered waste imagery. That is a long way below the 95%-plus figures reported on clean benchmark datasets, and well below what unsupervised, fully automated valuation of a commercial lot would require. Persistent overfitting was observed across all three architectures despite regularisation, early stopping and a learning-rate scheduler. The class scheme is litter categories — bottle, bottle cap, cigarette, pop tab — not industrial grades, and the model outputs a category only: it says nothing about contamination level, purity, bale quality or moisture, which are precisely the attributes that set B2B scrap price. There is no valuation, no counterparty, no transaction and no deployment; the pipeline ends at a predicted label. The authors' own future work names multispectral imaging for finer plastic grade discrimination, active learning pipelines improving models from production feedback, and self-supervised pretraining on unlabelled waste facility footage.
 
### What ScrapLink adds
 
This paper is best used in the report not as a competitor but as the realism benchmark that justifies how ScrapLink's AI module is designed:
 
  * **Confidence-aware classification rather than blind automation** — because roughly 61% F1 on cluttered imagery is a documented ceiling, ScrapLink treats the model output as an assisted estimate subject to confidence thresholds and seller confirmation, not as an unchallengeable verdict
  * **Verification downstream of vision** — weighbridge confirmation, buyer inspection and dispute handling close the accuracy gap that no classifier alone can close, which a pure computer-vision study has no mechanism to do
  * **Grade and purity as a distinct estimation task** — separated from category detection, addressing exactly the fine-grained plastic-grade discrimination the authors defer to future work
  * **Category becomes an input to price** — the classified label is chained to value prediction, marketplace matching and settlement rather than terminating as a metric
  * **An active-learning loop the authors could not build** — every completed ScrapLink transaction produces a confirmed label with a verified weight and a realised price, which is precisely the production-feedback training signal their future-work section calls for
The throughput result also matters operationally: sub-millisecond inference and viable edge deployment mean the classification step imposes no meaningful latency or cost on the listing workflow.
 
Gap statement for report
 
Existing computer-vision benchmarks establish that transformer and CNN architectures classify real-world cluttered waste at only around 60% F1 and stop at a predicted category, whereas ScrapLink embeds confidence-aware classification within a verified commercial workflow that adds grade estimation, weighbridge confirmation, valuation and a transaction-derived feedback loop for continual model improvement.
 
Paper 14 of 20
 
## Waste Collection Routing: A Survey on Problems and Methods
 
Hess, Dragomir, Doerner & Vigo (2024) — survey
 
### What the paper covers
 
An authoritative operations-research survey of the overlap between vehicle routing and waste collection, classifying the literature by problem type — general, node and arc routing problems, with vehicle routing problems most common, followed by arc and location routing problems — and by solution method across exact approaches and metaheuristics (ALNS, LNS, tabu search, variable neighbourhood search, simulated annealing, genetic algorithms). It gives particular attention to intermediate facilities, which are near-ubiquitous in waste collection, and to characteristics that make the domain distinctive: uncertain demand, personnel planning, alternative collection systems and vehicle types, and risk- and sustainability-related objectives such as transport risk from hazardous waste and odour timing. Roughly 23% of the surveyed literature addresses two or more objectives. The survey closes with an explicit research-gap and outlook section.
 
### Research gap
 
The authors name their open problems directly, and several map onto ScrapLink's design. AI and machine learning "ha[ve] not been applied to a waste collection context" within routing optimisation, despite clear promise for real-time re-routing and fill-level prediction. Greenhouse gas emissions should be brought more into focus as an explicit objective. Service-time estimates are usually a single constant regardless of vehicle or bin type, undermining practicability. Simultaneous pick-ups and deliveries as part of a circular economy are identified as a distinct research gap, having barely been modelled as such. Most literature ignores multi-period or periodic schedules even though real-world plans repeat. Overflow avoidance and split collections receive little attention. The survey also observes that only very few cities have equipped all their bins with sensors, so fill levels must generally be modelled as stochastic demand or predicted from historical data. Underlying all of this is a framing limitation: the objective is almost always to minimise cost, distance or time, with only a small minority of works maximising profit, revenue or tonnage collected. The material has a destination — a landfill, incinerator or sorting plant — but never a _buyer_. Demand in this literature means bins to be emptied, not industrial demand for recovered material.
 
### What ScrapLink adds
 
ScrapLink inherits the survey's methodological vocabulary while inverting its economic framing:
 
  * **Routing toward a buyer, not a depot** — the destination is a matched, verified recycler determined by the marketplace, which reframes the problem as a pickup-and-delivery problem in a circular economy: precisely the gap the authors flag as under-modelled
  * **A revenue-bearing objective** — because each lot carries a bid price, the optimiser can trade collection cost against realised material value rather than minimising cost alone
  * **AI applied inside the routing context** — demand prediction and dynamic re-routing from live listing and request data, addressing the machine-learning gap the survey names as unaddressed in this domain
  * **Realistic service times by construction** — loading time at a weighbridge-verified industrial pickup is measured per transaction and per lot type rather than assumed constant
  * **Demand that is declared, not inferred** — a listed lot states its own quantity and readiness, sidestepping the stochastic-fill-level and overflow problems that dominate municipal bin routing
  * **Emissions as reported output** — route-level carbon accounting feeds the ESG analytics module, operationalising the emissions focus the authors advocate
Note for the report: cite this survey as the authoritative statement of what waste-collection routing research currently optimises and what it leaves open. It is the strongest single source for the claim that this literature has no concept of a commercial counterparty, and its named gaps — machine learning, circular-economy pick-up-and-delivery, emissions — are three of ScrapLink's design commitments.
 
Gap statement for report
 
Existing waste-collection routing research optimises municipal cost, distance and time toward disposal facilities and has not been applied in a machine-learning or circular-economy pick-up-and-delivery context, whereas ScrapLink routes graded, priced lots from verified generators to matched industrial buyers with material value and carbon impact as explicit terms in the objective.
 
Paper 15 of 20
 
## Optimization of Vehicle Routing for Waste Collection and Transportation
 
Wu, Tao & Yang (2020)
 
### What the paper covers
 
A concrete counterpart to the preceding survey: the paper formulates a Priority Considered Green Vehicle Routing Problem (PCGVRP) for urban waste collection in China and solves it with a Local Search Hybrid Algorithm that seeds an initial solution by particle swarm optimisation and refines it by simulated annealing. Two features distinguish the model. First, it assigns high collection priority to bins containing hazardous or medical waste, motivated explicitly by the COVID-19 surge in medical waste, and penalises the "negative effect" of leaving such bins uncollected. Second, it internalises greenhouse gas emission cost alongside conventional routing cost in a single comprehensive objective, and it uses sensor-reported waste filling level (WFL) to generate dynamic routes instead of fixed schedules. Validation runs against classic CVRP benchmark instances plus a waste-collection case study. Results: a 42.3% reduction in negative effect relative to a traditional model; a WFL collection threshold between 60% and 80% delivers the highest collection and transportation efficiency; and the optimal threshold within that band depends on how many high-priority bins are present. The authors note that collection and transportation account for 60–80% of total waste-management system cost, which is what makes the optimisation worth doing.
 
### Research gap
 
The model is a municipal disposal optimiser: vehicles depart a depot, empty bins and deliver to a waste disposal centre. No recovered material is sold, no counterparty exists, and value appears only as avoided cost and avoided emissions. Priority is defined by hazard, not by material worth — a bin of clean baled aluminium and a bin of general refuse are equivalent to the objective function unless one is medically hazardous. The authors state their own limitations plainly: the results rest on benchmark CVRP instances and a case study rather than live operational data, and they recommend that "recent and real data can be used to obtain more realistic and reliable conclusions", along with multivariate statistical analysis of the model parameters. The approach also presupposes sensor-equipped bins reporting fill level, an assumption the Hess survey shows very few cities actually satisfy. There is no classification, no grading, no pricing, no marketplace and no traceability.
 
### What ScrapLink adds
 
ScrapLink adopts the two mechanisms this paper validates and re-points them at a market:
 
  * **Priority driven by value and commitment, not only hazard** — ScrapLink schedules against accepted bids, contractual pickup windows, lot value and material perishability, with hazardous-waste urgency retained as one priority class rather than the sole one
  * **Threshold logic transferred from bins to lots** — the paper's finding that a 60–80% fill threshold maximises efficiency directly informs ScrapLink's consolidation rule for when accumulated listings at a generator justify dispatching a vehicle
  * **Emissions cost carried into ESG reporting** — the same internalised GHG term becomes auditable, per-transaction carbon evidence for the buying firm, not just a line in an objective function
  * **Real operational data by construction** — the live transaction and pickup history the platform generates is exactly the "recent and real data" the authors identify as missing from their validation
  * **A destination that pays** — the terminal node is a verified recycler who has bid for the lot, converting a cost-minimisation problem into a margin-optimisation problem
Gap statement for report
 
Existing green vehicle routing models minimise combined routing and emission cost for municipal collection to disposal centres, prioritising bins by hazard and validating on benchmark rather than operational data, whereas ScrapLink applies the same fill-threshold and emission-cost logic to graded commercial lots routed to bidding buyers, with priority set by contractual commitment and material value and with live transaction data as its evidence base.
 
Paper 16 of 20
 
## Development of an Island Recycle Waste Management System Using the LINE OA Platform
 
Kemavuthanon, Yamsa-ard, Manomaivibool & Liu (2026)
 
### What the paper covers
 
A deployed digital reporting system for recycling shops on Thai islands, built not as a custom application but on top of LINE Official Account — the messaging platform already in everyday use in Thailand. Through a rich-menu interface, participating shops record waste types, quantities and transportation costs, and upload receipt and verification images that are transmitted in real time to a centralised project database. The system replaces a paper-based workflow that supported a ferry-transport subsidy scheme for moving recyclable material from islands to mainland processing facilities. Evaluation used a mixed-methods design anchored on the Technology Acceptance Model, with perceived usefulness (PU) and perceived ease of use (PEOU) as the determinants of attitude toward using (ATU) and behavioural intention (BI), administered to a pilot group of thirteen users alongside open-ended qualitative questions.
 
### Research gap
 
The result is the most instructive part of the paper, and it is a negative one: 46.2% of the pilot group fell into the "not accepting" category on both ATU and BI, with only three of thirteen users accepting or highly accepting. High perceived usefulness — the system genuinely was faster and more accurate than paper — could not overcome low perceived ease of use caused by demographic and device barriers: age and digital literacy among island shop owners, complex rich-menu navigation and small typography, insufficient in-app guidance, and mobile hardware that could not run the system at full capacity. The authors also concede that objective error-rate comparisons against the paper baseline were never collected, so the efficiency claim rests on user perception rather than measurement. Functionally, the system is a data-capture and reporting tool: it records what was collected and what transport cost was incurred, but it performs no classification, assigns no grade, sets no price, matches no buyer, optimises no route and settles no payment. Its remedies are proposed rather than implemented — interface simplification, OCR for receipt scanning, multimedia guides and hands-on training.
 
### What ScrapLink adds
 
The value of this paper to ScrapLink is less about missing features than about a documented adoption failure that a B2B platform must design against from the start:
 
  * **A commercial incentive rather than an administrative obligation** — the reviewed system asks users to report data so a subsidy can be reimbursed; ScrapLink asks them to list material so it sells at a discovered price, which makes the reward for using it immediate and proportional to effort
  * **Automated capture where the pilot demanded manual entry** — AI classification from a photograph and weighbridge-fed quantities replace the typed waste-type and quantity fields that produced the cognitive burden the authors identify, and deliver the OCR-style automation they list as future work
  * **Role-appropriate interfaces** — a scrap dealer or generator-side operator sees a short listing flow rather than a deep nested menu, addressing the interface-depth barrier directly
  * **Verified transaction records rather than uploaded receipt images** — chain-of-custody entries generated by the transaction itself, so evidence does not depend on a user remembering to photograph a document
  * **Settlement in the platform** — escrow and invoicing replace an out-of-band subsidy reimbursement, closing the loop the reporting tool only documents
Note for the report: cite this paper as empirical evidence that digital waste systems fail on usability and digital literacy at least as often as on technical capability, and that a 46.2% non-adoption rate is a realistic risk for any platform onboarding small informal-sector operators. ScrapLink's onboarding, interface simplicity and assisted-capture design should be presented as a direct response to this finding, not as incidental polish.
 
Gap statement for report
 
Existing mobile waste-reporting systems digitise data capture for recycling operators but stop at recording quantities and transport costs — with documented adoption failure among low-digital-literacy users — whereas ScrapLink pairs assisted, automated capture with a direct commercial incentive, carrying the recorded material forward into valuation, buyer matching, settlement and verified traceability.
 
Paper 17 of 20
 
## Optimization of Scrap Waste Collection and Management System: An Overview Concerning Kerala, India
 
Rincy & George (2026) — regional case study
 
### What the paper covers
 
The only paper in this review addressed specifically to the scrap sector in an Indian state, and therefore the one closest to ScrapLink's operating context. It characterises scrap waste as a distinct subset of solid waste comprising metal scrap, plastic scrap and e-waste, and reviews the composition, sources and environmental and health impacts of each — PAHs, PCBs and heavy metals from metal scrap; the seven plastic resin classes with their recycling codes and impacts; and the six e-waste categories with lead, mercury, cadmium, hexavalent chromium, BFRs, arsenic, nickel and cobalt pathways. On scale it reports that India generated 160,038.9 TPD of solid waste in 2020–21, of which 152,749.5 TPD was collected, 79,956.3 TPD treated and 50,655.4 TPD (31.7%) unaccounted for; and that Kerala generates roughly 11,449 tonnes of solid waste per day. Most relevant to ScrapLink, it documents the state's scrap trade directly: more than 10,000 scrap collection centres employing around 350,000 people, handling paper, plastics, cartons, metals, e-waste, batteries, old appliances, tyres, rubber and PVC, with rejected items including sandals, rexine, thermocol, fibre and PU. It sets out the regulatory guidelines that govern them — mandatory registration with the Pollution Control Board, a comprehensive Board-maintained database, white-category consent for non-mechanised units and green-category for mechanised ones, e-waste and battery scrap routed to authorised recyclers, mandatory annual scrap-quantity records, fire precautions and permitted machinery — and notes an industry association plan to launch a mobile app and GPS-tag scrap carrying vehicles. Under Rule 15(b) of the Solid Waste Management Rules 2016, waste pickers are to be integrated into the formal collection system.
 
### Research gap
 
The paper is an environmental review, not a systems contribution: it quantifies contamination and catalogues policy, and its stated knowledge gap concerns the environmental effects of scrap collection facilities in Kerala, not the commercial mechanics of scrap trade. It states plainly that scrap waste management in the state remains fragmented, with gaps in pollution control, integration of the informal sector and collection efficiency, but proposes no mechanism to close them. Value is treated as environmental burden rather than as a market: nowhere are prices, grades, buyers, or the trading relationships between the 10,000 centres and downstream processors modelled. The digital component it reports — a proposed association mobile app and GPS vehicle tags — is aspirational, is aimed at compliance and nuisance minimisation rather than transaction, and has no classification, valuation, matching or settlement function. Record keeping is annual and submitted to a regulator, meaning there is no live view of what material exists where. The paper also notes that collected material is dispatched to processing centres mainly outside Kerala, an inter-state flow with no described coordination layer.
 
### What ScrapLink adds
 
ScrapLink addresses the fragmentation this paper documents with the exact mechanisms it says are absent:
 
  * **Formal onboarding of scrap dealers and pickup persons** — KYC-verified accounts operationalise the Rule 15(b) integration mandate and the Board registration requirement as a working directory rather than a filing obligation
  * **Continuous rather than annual records** — every listing, weighbridge reading and completed transfer produces a timestamped record, so the "comprehensive database" the guidelines require becomes a live one
  * **Category-specific handling** — separate treatment of metal, plastic and e-waste streams, with e-waste and battery lots routed only to authorised recyclers, encoding the white/green consent and authorised-recycler rules into matching logic
  * **A price and a counterparty attached to each lot** — turning the 10,000-centre network from a fragmented supply base into an addressable market, which is the gap between "material is collected" and "material is efficiently valorised"
  * **Coordinated inter-state flow** — buyer matching and route optimisation across the outbound dispatch this paper identifies but does not organise
  * **Chain-of-custody as compliance evidence** — the audit trail a Pollution Control Board submission needs, generated automatically
Note for the report: this is the strongest available source for the domestic problem statement and for the scale of the Indian informal scrap economy, and it should be cited in the motivation section rather than only in the gap analysis.
 
Gap statement for report
 
Existing regional scrap-sector studies document fragmentation, informal-sector exclusion and annual, compliance-oriented record keeping across India's scrap collection network without proposing an operational mechanism, whereas ScrapLink formalises those dealers into a verified live marketplace with graded listings, discovered prices, category-aware routing to authorised recyclers and continuously generated audit records.
 
Paper 18 of 20
 
## From Waste Pickers to Producers: An Inclusive Circular Economy Solution through Cooperatives
 
Buch, Marseille, Williams, Aggarwal & Sharma (2021)
 
### What the paper covers
 
A conceptual framework for an inclusive circular economy that treats waste pickers not as a residual social problem but as the value chain's most incentivised participants. It documents their economic position with unusual precision: the ILO estimates 15 to 20 million people work in recycling in the developing world, roughly 1% of the urban workforce; waste pickers in Mumbai earn between USD 2.71 and 3.62 per day; and, critically for a pricing platform, they receive from middlemen only about 10% of the acquired value of the materials they supply — approximately one-third of what those middlemen would pay a formal-sector actor. The paper contrasts private-sector waste contracts, which handle waste in whatever manner is most profitable including incineration (25 times the emissions of recycling), with waste pickers, who are structurally incentivised to maximise the quantity and quality of recyclable material and therefore invest effort in segregation and in connecting to appropriate buyers through local knowledge. It proposes four pillars: collaborative stakeholder networks that include waste pickers; cooperative enterprise models as the route into the formal economy; capacity strengthening for entrepreneurship; and access to technology and markets enabling upcycled manufacturing. Pune's SWaCH cooperative, with nearly 3,000 members serving 70% of the city, is its principal example.
 
### Research gap
 
The framework is organisational and pedagogical, not technological. Its instruments are training, cooperative formation, brokered arrangements with local authorities and low-cost micro-manufacturing machinery; no information system appears anywhere in the four pillars. The fourth pillar explicitly names "access to markets" as a requirement but supplies no mechanism for reaching one — the proposed answer to volatile commodity markets is to exit them by manufacturing upcycled goods rather than to trade into them on better terms. This leaves the paper's own most striking finding unaddressed: the 10%-of-value figure is a price-transparency failure, and price transparency is a solvable information problem, not one that requires cooperative formation first. The model is also dependent on external agents — international NGOs, development agencies, municipal recognition — and each cooperative it describes remains a small player negotiating individually against aggregators.
 
### What ScrapLink adds
 
ScrapLink attacks the same value-capture problem through market infrastructure rather than institution building, and the two approaches are complementary:
 
  * **Price transparency as the direct remedy** — published, AI-predicted indicative values and competitive bidding let a supplier see what a lot is worth before selling it, addressing the 10%-of-value asymmetry at its cause
  * **Disintermediation by design** — a verified generator or dealer reaches an industrial buyer directly, removing the margin layer the paper identifies without requiring the supplier to first become a manufacturer
  * **Aggregation without institutional formation** — consolidating small lots into commercially viable volumes on the platform gives small suppliers scale that the paper can only achieve by forming a cooperative
  * **Formalisation as a by-product of transacting** — KYC onboarding, transaction history and payment records create the verifiable commercial identity that formal-sector access otherwise requires years of institutional work to establish
  * **Escrow settlement in place of dependence on buyer goodwill** — payment guaranteed on verified delivery, protecting the party with the least bargaining power
  * **Grading that pays for quality** — because ScrapLink prices grade and purity separately from category, the segregation effort this paper shows waste pickers already make is rewarded explicitly rather than absorbed by an aggregator
Note for the report: cite this paper for the social and equity dimension of ScrapLink's motivation, and specifically for the 10%-of-value figure, which is the single most compelling quantitative justification for a transparent pricing layer in the informal scrap economy. It should also temper any claim that a platform alone solves inclusion: the paper's evidence on digital and organisational barriers, read alongside Paper 16's adoption data, argues for assisted onboarding rather than self-service signup.
 
Gap statement for report
 
Existing inclusive circular-economy frameworks address waste-picker value capture through cooperative formation, training and micro-manufacturing while identifying market access as an unmet need, whereas ScrapLink supplies that market access directly as transparent pricing, competitive bidding, lot aggregation and guaranteed settlement that let small suppliers capture material value without first restructuring into new institutions.
 
Paper 19 of 20
 
## Analyzing the Interactions Among the Challenges to Circular Economy Practices
 
Bai, Ahmadi, Moktadir, Kusi-Sarpong & Liou (2021)
 
### What the paper covers
 
A multi-criteria decision analysis of why circular-economy adoption stalls in emerging economies, applied to the Bangladeshi leather industry. Eight challenges were assessed by six senior industry experts drawn from six tanneries, and their interdependencies analysed with Rough DEMATEL — chosen over fuzzy AHP/ANP because rough numbers preserve the divergence of expert opinion instead of collapsing it into a single membership function. The eight challenges are: lack of technological advancement (B1), lack of financial support from authorities (B2), absence of strong legislation toward CE (B3), lack of awareness of CE (B4), lack of communication platforms (B5), lack of reverse logistics facilities (B6), lack of pressure from social community (B7), and lack of long-term strategic goals (B8). The analysis produces both a prominence ranking — B2 > B8 > B5 > B6 > B7 > B4 > B3 > B1 — and, more usefully, a causal split: B2, B8 and B4 are net causes, while B5, B3, B1, B7 and B6 are net effects. Lack of financial support is the most pressing challenge overall; lack of communication platforms ranks first among the effect group, meaning it is a downstream symptom that the causal challenges drive.
 
### Research gap
 
This is a diagnostic study, not a solution: it identifies and ranks barriers, and its recommendations are addressed to policymakers and industry decision-makers rather than to system builders. The authors state their limitations directly — a limited set of eight challenges, a small expert panel of six, a single industry in a single country — and suggest replication in other sectors and countries and with alternative methods such as TISM. No artefact is proposed for any of the eight challenges. The finding most relevant here is also the most double-edged: "lack of communication platforms (B5)" is exactly the gap a platform like ScrapLink fills, and it is ranked third by prominence — but it is classified as an *effect*, meaning the analysis predicts that building a platform without addressing the causal challenges behind it (finance, strategic goals, awareness) will not be sufficient on its own.
 
### What ScrapLink adds
 
ScrapLink is a direct instantiation of the effect-group challenge B5, and its design touches several of the others:
 
  * **The communication platform itself (B5)** — a shared transactional environment linking generators, dealers, recyclers and industrial buyers, which the study finds absent and ranks as the leading effect-group challenge
  * **Reverse logistics as a built-in function (B6)** — pickup scheduling, logistics partner assignment and route optimisation deliver the reverse-logistics capability named as the second-ranked effect challenge, rather than requiring each firm to build it
  * **Lowered capital threshold (B2)** — because participation is a platform subscription and a transaction fee rather than plant investment, ScrapLink partially relieves the top-ranked causal challenge for the supplier side, though it cannot substitute for public financing of processing infrastructure
  * **Awareness through visible value (B4)** — realised prices, diversion tonnage and ESG dashboards make the commercial case for circular practice concrete, which is what the study argues awareness campaigns are meant to achieve
  * **Compliance-ready records supporting legislation (B3)** — chain-of-custody and certification give regulators an enforcement substrate, so stronger legislation becomes practicable rather than merely desirable
Note for the report: this paper is best used to frame the adoption strategy honestly. Its causal analysis supports a specific and defensible claim — that ScrapLink addresses the effect-group challenges (communication platform, reverse logistics) directly and the causal ones (finance, awareness, strategic goals) only partially — and it warns against claiming that a platform alone resolves circular-economy adoption. Used this way it strengthens the proposal's credibility rather than weakening it.
 
Gap statement for report
 
Existing MCDM studies rank and causally order the barriers to circular-economy adoption — identifying lack of communication platforms and lack of reverse logistics facilities as leading effect-group challenges — but deliver diagnosis rather than any system, whereas ScrapLink implements precisely those two missing capabilities as a working platform while making explicit that the causal financial and strategic barriers remain outside a single system's reach.
 
Paper 20 of 20
 
## The Management of Municipal Waste through Circular Economy in the Context of Smart Cities Development
 
Aceleanu, Șerban, Suciu & Bițoiu (2019)
 
### What the paper covers
 
A policy and indicator analysis of circular-economy transition, using Romania as a case against the EU-28 benchmark and framing the circular economy as a precondition for smart-city development — where a smart city is characterised by technological, institutional and human factors, and the EU's own definition of circular economy rests on "the use of information and communication technologies for better resource use and less emissions". The paper assembles the comparative evidence: Romania's resource productivity fell to EUR 0.33 per kg by 2017 against an EU average of EUR 2.04, a sixfold gap; domestic material consumption rose 225% from 7.7 to 25.09 tonnes per capita between 2000 and 2017; the circular material use rate — the share of recovered material fed back into the economy — stands at 1.5% in Romania against 11.7% for the EU; and the municipal waste recycling rate reached only 13.3% against an EU average of 45.3%, the lowest in the Union, with most waste landfilled or incinerated. It also establishes a positive correlation between circular material use rate and GDP across member states, and it identifies four barriers to transition: finance for both public and private sectors, the absence of an institutional framework designed to stimulate resource reuse, human capital unprepared for the skills the concept requires, and consumer behaviour.
 
### Research gap
 
The paper operates entirely at the level of aggregate indicators and policy recommendation. Its unit of analysis is the country and its evidence base is Eurostat; no firm, no transaction and no system appears anywhere in it, and the authors close by noting that their research is a stage in analysing smart-city development which they intend to extend. It measures the gap between where circularity is and where policy wants it to be, and then calls for public–private partnership, investment, education and infrastructure — but the mechanism through which a specific tonne of recovered material actually finds a buyer is not part of the analysis. The circular material use rate it treats as the headline indicator is precisely a measure of transactions that did or did not occur, yet the market where those transactions would happen is never examined. Its "need for applying modern technologies for the operationalization of this process" is stated as a requirement, not designed.
 
### What ScrapLink adds
 
ScrapLink is an operationalisation of the indicator this paper measures:
 
  * **The circular material use rate is a transaction count** — every completed ScrapLink trade is one increment of recovered material re-entering production, so the platform moves the metric rather than only reporting it
  * **Bottom-up rather than policy-led** — participation follows commercial advantage, so progress does not wait on the institutional framework the paper identifies as missing
  * **Firm-level evidence beneath national statistics** — transaction-derived ESG and diversion analytics give individual companies the circularity accounting that Eurostat provides only in aggregate, and give public bodies a data source underneath their indicators
  * **The public–private interface made concrete** — municipal fleets, private recyclers and industrial buyers transact in one verified environment, which is the partnership the paper advocates in general terms
  * **A market answer to a market-failure diagnosis** — a 1.5% circular material use rate against 11.7% is, at least in part, a matching and price-discovery failure; ScrapLink treats it as such
Note for the report: use this paper for the macroeconomic framing and for the smart-city linkage — it supplies the argument that circular-economy performance and digital infrastructure are coupled, and that recycling rates in the low tens of percent are a policy-recognised failure rather than a technical inevitability. Its EU indicator set is also the natural target schema for ScrapLink's ESG export.
 
Gap statement for report
 
Existing policy analyses quantify circular-economy underperformance through national indicators such as circular material use rate and recycling rate and recommend investment, institutional reform and technology adoption, whereas ScrapLink implements the market mechanism through which those indicators actually move, generating firm-level, transaction-derived circularity evidence beneath the aggregate statistics.
 
## The Overall Research Gap
 
Across all twenty papers reviewed, no single prior work provides the complete combination that ScrapLink proposes:
 
**AI classification** + **quality grading** + **price prediction** + **B2B marketplace** + **RFQ / bidding** + **logistics optimisation** + **payment / escrow** + **contracts** + **certification** + **chain-of-custody** + **ESG analytics**
 
The reviewed literature divides along four fault lines.
 
**Capable technology without a market.** Deep-learning classifiers, IoT bin networks, routing optimisers, blockchain traceability frameworks and GIS–Big Data integrations are each excellent at one function and none is connected to a transaction. The two routing papers sharpen the point considerably: an entire operations-research discipline exists for moving waste efficiently, and in it the material's destination is a landfill, an incinerator or a sorting plant — never a buyer. Demand means bins to be emptied. The word "value" appears only as avoided cost.
 
**Markets and governance studied but not built.** Industrial-symbiosis platform studies, digital-governance proposals, empirical models of digital transformation, MCDM barrier analyses and national indicator studies identify what should exist and stop there. Bai et al. rank "lack of communication platforms" as a leading challenge without building one; Aceleanu et al. measure a 1.5% circular material use rate without examining the market that would raise it; Buch et al. name market access as a pillar and supply cooperatives instead. The waste-to-resource graph engine reviewed as Paper 11 sits at the boundary: it is built and it does match, but it matches technical possibility rather than commercial supply and demand, and nothing it produces carries a price.
 
**Marketplaces that list but do not transact.** This is the fault line the Upvalue paper exposes, and it is the one that matters most for ScrapLink's novelty claim. Operational B2B waste marketplaces _do_ exist. What they provide is a regulated listing board: a compliant taxonomy, self-declared listings, search, and licence-gated permission to contact a counterparty. What none of them provides is verification of what the material actually is, a predicted or competitively discovered price, settlement, fulfilment, or a tamper-evident record that the advertised lot is the lot that arrived. The trade is initiated inside the platform and completed outside it.
 
**Systems built but not adopted.** The papers added in this revision expose a fourth division that the technology-centric literature obscures. Kemavuthanon et al. deployed a working digital reporting system to real recycling shops and recorded 46.2% non-adoption, driven not by any technical deficiency but by interface depth, typography, device capability and digital literacy. Rincy & George document a Kerala scrap network of 10,000 centres and 350,000 workers whose digitisation amounts to an aspirational mobile app and annual paper records. Buch et al. show suppliers capturing 10% of the value of what they sell. Together these establish that the binding constraint on a waste platform in a developing economy is adoption by low-digital-literacy, low-margin operators — which makes assisted capture, interface simplicity, immediate commercial payoff and guaranteed settlement design requirements rather than refinements.
 
ScrapLink is designed to close all four divisions at once — connecting sensing, classification, valuation, matching, fulfilment and evidence into one digital B2B waste economy, built for the operators who actually handle the material, rather than treating waste classification, logistics, industrial symbiosis, marketplace listing, governance, policy or blockchain traceability as isolated problems.
 
## Consolidated Feature Comparison — Part A (Papers 1–5)
 
Feature | Paper 1<br>Krom et al. | Paper 2<br>Afash et al. | Paper 3<br>Zhang et al. | Paper 4<br>Maciel et al. | Paper 5<br>Castiglione et al. | ScrapLink
---|---|---|---|---|---|---
Digital stakeholder platform| ✓| ✓| ✗| ✗| ✓| ✓
Industrial / B2B resource matching| ✓| ✓| ✗| ✗| P| ✓
Waste image classification| ✗| ✗| ✓| ✗| ✗| ✓
Waste grade / purity estimation| ✗| P| ✗| ✗| ✗| ✓
Dynamic waste pricing| ✗| ✗| ✗| ✗| ✗| ✓
RFQ & bidding| ✗| ✗| ✗| ✗| ✗| ✓
IoT / real-time waste monitoring| ✗| P| ✗| ✓| ✗| P
Route optimisation| P| P| ✗| ✓| P| ✓
Digital payments / escrow| ✗| ✗| ✗| ✗| ✗| ✓
Contract / vendor management| ✗| P| ✗| ✗| ✗| ✓
Blockchain traceability| ✗| P| ✗| ✗| ✓| ✓
Certification / compliance| P| P| ✗| ✗| P| ✓
ESG / sustainability analytics| P| ✓| ✗| P| ✓| ✓
Complete end-to-end B2B ecosystem| ✗| P| ✗| ✗| ✗| ✓
 
✓ = fully addressed • P = partially addressed • ✗ = not addressed
 
## Consolidated Feature Comparison — Part B (Papers 6–10)
 
Feature | Paper 6<br>Rahman et al. | Paper 7<br>Addas et al. | Paper 8<br>Rittl et al. | Paper 9<br>Kochanek et al. | Paper 10<br>Tanveer & Alsharah | ScrapLink
---|---|---|---|---|---|---
Digital stakeholder platform| P| P| ✓| P| ✗| ✓
Industrial / B2B resource matching| ✗| ✗| P| ✗| ✗| ✓
Waste image classification| ✓| ✗| ✗| P| ✗| ✓
Waste grade / purity estimation| ✗| ✗| ✗| P| ✗| ✓
Dynamic waste pricing| ✗| ✗| ✗| ✗| ✗| ✓
RFQ & bidding| ✗| ✗| ✗| ✗| ✗| ✓
IoT / real-time waste monitoring| ✓| ✓| P| P| ✗| P
Route optimisation| ✗| ✓| P| P| ✗| ✓
Digital payments / escrow| ✗| ✗| ✗| ✗| ✗| ✓
Contract / vendor management| ✗| ✗| P| ✗| ✗| ✓
Blockchain traceability| ✗| ✗| ✗| P| ✗| ✓
Certification / compliance| ✗| ✗| P| P| P| ✓
ESG / sustainability analytics| ✗| ✓| ✓| ✓| ✓| ✓
Complete end-to-end B2B ecosystem| ✗| ✗| ✗| ✗| ✗| ✓
 
✓ = fully addressed • P = partially addressed • ✗ = not addressed
 
## Consolidated Feature Comparison — Part C (Papers 11–15)
 
Feature | Paper 11<br>Low et al. | Paper 12<br>Soares et al.<br>(Upvalue) | Paper 13<br>Deng et al. | Paper 14<br>Hess et al. | Paper 15<br>Wu et al. | ScrapLink
---|---|---|---|---|---|---
Digital stakeholder platform| ✓| ✓| ✗| ✗| ✗| ✓
Industrial / B2B resource matching| ✓| ✓| ✗| ✗| ✗| ✓
Waste image classification| ✗| ✗| ✓| ✗| ✗| ✓
Waste grade / purity estimation| P| P| P| ✗| ✗| ✓
Dynamic waste pricing| ✗| ✗| ✗| ✗| ✗| ✓
RFQ & bidding| ✗| P| ✗| ✗| ✗| ✓
IoT / real-time waste monitoring| ✗| ✗| ✗| P| ✓| P
Route optimisation| ✗| ✗| ✗| ✓| ✓| ✓
Digital payments / escrow| ✗| ✗| ✗| ✗| ✗| ✓
Contract / vendor management| ✗| P| ✗| ✗| ✗| ✓
Blockchain traceability| ✗| ✗| ✗| ✗| ✗| ✓
Certification / compliance| P| ✓| ✗| ✗| ✗| ✓
ESG / sustainability analytics| P| P| ✗| P| P| ✓
Complete end-to-end B2B ecosystem| ✗| P| ✗| ✗| ✗| ✓
 
✓ = fully addressed • P = partially addressed • ✗ = not addressed
 
## Consolidated Feature Comparison — Part D (Papers 16–20)
 
Feature | Paper 16<br>Kemavuthanon et al. | Paper 17<br>Rincy & George | Paper 18<br>Buch et al. | Paper 19<br>Bai et al. | Paper 20<br>Aceleanu et al. | ScrapLink
---|---|---|---|---|---|---
Digital stakeholder platform| ✓| ✗| ✗| ✗| ✗| ✓
Industrial / B2B resource matching| ✗| ✗| P| ✗| ✗| ✓
Waste image classification| ✗| ✗| ✗| ✗| ✗| ✓
Waste grade / purity estimation| ✗| ✗| ✗| ✗| ✗| ✓
Dynamic waste pricing| ✗| ✗| ✗| ✗| ✗| ✓
RFQ & bidding| ✗| ✗| ✗| ✗| ✗| ✓
IoT / real-time waste monitoring| P| ✗| ✗| ✗| P| P
Route optimisation| ✗| P| ✗| ✗| ✗| ✓
Digital payments / escrow| P| ✗| ✗| ✗| ✗| ✓
Contract / vendor management| P| P| P| ✗| ✗| ✓
Blockchain traceability| ✗| ✗| ✗| ✗| ✗| ✓
Certification / compliance| P| P| P| P| P| ✓
ESG / sustainability analytics| P| P| P| P| ✓| ✓
Complete end-to-end B2B ecosystem| ✗| ✗| ✗| ✗| ✗| ✓
 
✓ = fully addressed • P = partially addressed • ✗ = not addressed
 
ScrapLink is marked as partially addressing IoT / real-time waste monitoring because smart-bin and weighbridge integration is scheduled for Phase 3 of the roadmap rather than the initial build. Every other capability is in scope for the delivered system.
 
Reading Parts C and D together: the two rows that separate ScrapLink from the closest prior work remain _dynamic waste pricing_ and _digital payments / escrow_ — no paper in this review, including the operational Upvalue marketplace, addresses either, and the five papers added in this revision leave both rows empty as well. Upvalue is marked P for RFQ & bidding because it supports sale advertisements and buyer contact but no structured competitive bidding mechanism, and ✓ for certification / compliance because LER classification, hazardousness assessment and licence-gated trading are central to its design — the one row where a prior system is stronger than ScrapLink's initial build. Deng et al. is marked P for grade estimation on the basis of fine-grained 27-superclass discrimination, which approaches but does not constitute purity or contamination grading.
 
In Part D, Kemavuthanon et al. is marked ✓ for digital stakeholder platform because a real multi-shop system was deployed and used, P for IoT because data reaches a central database in real time without any sensing layer, and P for payments because the system records transport costs against a subsidy scheme rather than settling a trade. Rincy & George and Bai et al. are marked ✗ across the platform rows because neither builds a system; their P marks reflect regulatory registration requirements and identified-but-unbuilt capabilities respectively. Aceleanu et al. earns the only ✓ in its column for ESG analytics, since national circularity indicators are precisely what it measures — and are the schema ScrapLink's analytics module should export to.
 
## Novelty Statement
 
The strongest novelty claim is therefore not "we invented AI waste classification", "we invented digital waste management", or "we invented the digital waste marketplace" — all three already exist in the literature, and the twenty papers reviewed here demonstrate that classification, IoT monitoring, routing, traceability, governance, policy measurement and even operational B2B waste listing platforms are individually mature. The defensible claim is one of integration:
 
"ScrapLink integrates previously fragmented technologies and functions into a single B2B digital waste economy platform that manages the complete lifecycle of industrial recyclable materials — from waste generation and AI-based classification to marketplace matching, pricing, logistics, payment, compliance and traceability."
 
This framing fits the actual scope of the ScrapLink project and is defensible against the reviewed literature. The first fifteen papers sharpen it in three ways. Low et al. and Soares et al. establish that waste-exchange platforms are already built and deployed, which forces the novelty claim away from "a marketplace" and toward the verification, valuation and settlement layer those platforms lack. Hess et al. and Wu et al. supply the authoritative operations-research position on waste routing and confirm that the entire discipline optimises toward disposal facilities with no commercial counterparty in the model. Deng et al. provides the honest accuracy benchmark for computer vision on realistic cluttered waste, which justifies ScrapLink's confidence-aware, human-verified approach to AI grading rather than an overclaimed fully automated one.
 
The five papers added in this revision extend the claim in a different direction — from what the system does to whether it will be used and why it is needed here. Kemavuthanon et al. supply a deployed system with a measured 46.2% non-adoption rate, which converts usability and assisted capture from nice-to-have features into design requirements with evidence behind them. Rincy & George supply the domestic problem statement: a Kerala scrap economy of 10,000 collection centres and 350,000 workers, governed by annual paper records and fragmented across pollution control, informal-sector integration and collection efficiency. Buch et al. quantify the value asymmetry the platform is meant to correct — suppliers receiving roughly 10% of the value of the material they hand over — and establish the equity case for transparent pricing. Bai et al. rank "lack of communication platforms" and "lack of reverse logistics facilities" as the two leading effect-group challenges to circular-economy adoption, which is a peer-reviewed statement that the two capabilities ScrapLink implements are the ones the sector is missing, while their causal analysis honestly bounds what a platform alone can achieve. Aceleanu et al. place the whole exercise against national indicators, showing that a circular material use rate in the low single digits is a recognised policy failure and that the metric itself is a count of transactions that did not happen.
 
Taken together, the twenty papers support a precise four-part contribution: ScrapLink is (i) the transaction layer that existing waste marketplaces stop short of, (ii) the commercial counterparty that waste-routing optimisation has never had, (iii) the verified, evidence-generating pipeline that turns an AI classification of uncertain accuracy into a settled, auditable trade, and (iv) an adoption-aware design for the low-margin, low-digital-literacy operators who handle most recoverable material — the participants the technology literature assumes and the deployment literature shows are hardest to reach.
 
## References
 
[1] Krom, P., Piscicelli, L., & Frenken, K. (2022). Digital Platforms for Industrial Symbiosis. _Journal of Innovation Economics & Management_. Cairn.info.
 
[2] Afash et al. (2026). Hubs for Circularity: Reference Architecture of Digital Collaboration Platforms. _Circular Economy and Sustainability_. Springer Nature.
 
[3] Zhang, Q. et al. (2021). Recyclable Waste Image Recognition Based on Deep Learning. _Resources, Conservation and Recycling_. ScienceDirect.
 
[4] Maciel et al. (2025). The Impact of IoT-Enabled Routing Optimization on Waste Collection Distance: A Systematic Review and Meta-Analysis. _Logistics_ (MDPI).
 
[5] Castiglione, A. et al. (2023). A Framework for Achieving a Circular Economy Using Blockchain Technology in a Sustainable Waste Management System. _Journal of Cleaner Production_. ScienceDirect.
 
[6] Rahman, M. W., Islam, R., Hasan, A., Bithi, N. I., Hasan, M. M., & Rahman, M. M. (2022). Intelligent Waste Management System Using Deep Learning with IoT. _Journal of King Saud University – Computer and Information Sciences_, 34(5), 2072–2087. Elsevier.
 
[7] Addas, A., Khan, M. N., & Naseer, F. (2024). Waste Management 2.0 Leveraging Internet of Things for an Efficient and Eco-Friendly Smart City Solution. _PLOS ONE_, 19(7), e0307608.
 
[8] Rittl, L. G. F., Zaman, A., & de Oliveira, F. H. (2025). Digital Transformation in Waste Management: Disruptive Innovation and Digital Governance for Zero-Waste Cities in the Global South as Keys to Future Sustainable Development. _Sustainability_, 17(4), 1608. MDPI.
 
[9] Kochanek, A., Angrecka, S., Pietrucha, I., Zacłona, T., Petryk, A., Generowicz, A., Akbulut, L., & Atılgan, A. (2026). Integration of GIS, Big Data, and Artificial Intelligence in Modern Waste Management Systems — A Comprehensive Review. _Sustainability_, 18(1), 385. MDPI.
 
[10] Tanveer, M., & Tayser Alsharah, A. M. (2026). From Innovation to Sustainability: Exploring How Digital Transformation and Green Innovation Foster Sustainable Waste Management through Circular Economy Practices. _Frontiers in Sustainability_, 7:1739524.
 
[11] Low, J. S. C., Tjandra, T. B., Yunus, F., Chung, S. Y., Tan, D. Z. L., Raabe, B., Ng, Y. T., Yeo, Z., Bressan, S., Ramakrishna, S., & Herrmann, C. (2018). A Collaboration Platform for Enabling Industrial Symbiosis: Application of the Database Engine for Waste-to-Resource Matching. _Procedia CIRP_, 69, 849–854. Elsevier. doi:10.1016/j.procir.2017.11.075
 
[12] Soares, M., Ribeiro, A., Vasconcelos, T., Barros, M., Castro, C., Vilarinho, C., & Carvalho, J. (2023). Challenges of Digital Waste Marketplace — The Upvalue Platform. _Sustainability_, 15(14), 11235. MDPI. doi:10.3390/su151411235
 
[13] Deng, S., Fan, A., & Sun, J. (2025). Waste Classification and Management Using Computer Vision. CS231N Final Paper, Stanford University.
 
[14] Hess, C., Dragomir, A. G., Doerner, K. F., & Vigo, D. (2024). Waste Collection Routing: A Survey on Problems and Methods. _Central European Journal of Operations Research_, 32, 399–434. Springer. doi:10.1007/s10100-023-00892-y
 
[15] Wu, H., Tao, F., & Yang, B. (2020). Optimization of Vehicle Routing for Waste Collection and Transportation. _International Journal of Environmental Research and Public Health_, 17(14), 4963. MDPI. doi:10.3390/ijerph17144963
 
[16] Kemavuthanon, K., Yamsa-ard, S., Manomaivibool, P., & Liu, Y. (2026). Development of an Island Recycle Waste Management System Using the LINE OA Platform to Enhance the Efficiency of Waste and Recyclable Material Management Reporting on Islands for Sustainable Practices. _Journal of Mobile Multimedia_, 22(1), 63–96. River Publishers. doi:10.13052/jmm1550-4646.2213
 
[17] Rincy, A., & George, A. (2026). Optimization of Scrap Waste Collection and Management System: An Overview Concerning Kerala, India. _Journal of Material Cycles and Waste Management_. Springer. doi:10.1007/s10163-025-02472-5
 
[18] Buch, R., Marseille, A., Williams, M., Aggarwal, R., & Sharma, A. (2021). From Waste Pickers to Producers: An Inclusive Circular Economy Solution through Development of Cooperatives in Waste Management. _Sustainability_, 13(16), 8925. MDPI. doi:10.3390/su13168925
 
[19] Bai, C., Ahmadi, H. B., Moktadir, M. A., Kusi-Sarpong, S., & Liou, J. J. H. (2021). Analyzing the Interactions Among the Challenges to Circular Economy Practices. _IEEE Access_, 9, 63199–63211. doi:10.1109/ACCESS.2021.3074931
 
[20] Aceleanu, M. I., Șerban, A. C., Suciu, M.-C., & Bițoiu, T. I. (2019). The Management of Municipal Waste through Circular Economy in the Context of Smart Cities Development. _IEEE Access_, 7, 133602–133614. doi:10.1109/ACCESS.2019.2928999