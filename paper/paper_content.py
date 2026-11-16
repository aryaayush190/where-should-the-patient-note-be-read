"""Text of the TELMED 2027 paper (read by build_ieee_docx.py).

Markup: {m:macro} = number from paper/generated/numbers.tex, {c:key[,key]} = citation (numbered by first use),
*italic*, **bold**; in table cells "\n" is a line break.
"""

TITLE = ("Where Should the Patient Note Be Read? Missed Referrals, Privacy and Device Cost of LLM Pre‑Screening "
         "for Clinical Trials in Telemedicine")  # U+2011: non-breaking hyphen keeps "Pre-Screening" on one line

ABSTRACT = (
    "Many patients who could join a clinical trial are first seen at district health centres, far from the "
    "hospitals that run trials. In a telemedicine pathway, a health worker pre-screens the patient on the clinic "
    "computer and refers likely-eligible patients to a trial site by teleconsultation. Cloud large "
    "language models (LLMs) pre-screen well, but only if they receive the full patient note. We provide a measured "
    "recipe for keeping that note on the clinic device. On 270 synthetic lung cancer patient–trial pairs from 18 "
    "unseen trials, we compare four levels of patient information sent to the cloud, from the full note to "
    "nothing, running every device step on a 16 GB laptop without a GPU. Our main measure is missed eligible "
    "patients, the error the trial site cannot correct. A privacy-split design that turns criteria into rules "
    "sent no complete note sentence but missed {m:missHundredSplitDeploy} eligible pairs per 100 patients, against "
    "{m:cloudRunsMissHundredMin}–{m:cloudRunsMissHundredMax} for the cloud model, mostly through cloud judgements "
    "that saw a single fact; with the same device model, reading the note instead of the rules cut missed patients "
    "by more than half for both models we tested (the larger on hosted hardware). Open models that read the note "
    "on the laptop did not miss significantly more patients than the cloud, though with wide uncertainty, and paid "
    "instead with more unnecessary referrals and device time. Keeping the note local appears feasible, moving "
    "the cost of privacy to teleconsultation workload, but needs validation on real clinical notes.")

KEYWORDS = ("telemedicine, clinical trial pre-screening, large language models, edge computing, privacy, "
            "data minimisation")

REPO_URL = "https://github.com/aryaayush190/Clinical-Agent-System"

# ("h1"|"h2"|"p"|"bullets"|"fig"|"table"|"box"|"ack"|"refs", payload)
BODY = [
    ("h1", "Introduction"),
    ("p", "Clinical trials are run mostly from large hospitals, while many patients are diagnosed and followed up "
          "at smaller district centres; decentralised trial designs aim to bring trials closer to these patients "
          "{c:oliver}. Telemedicine offers a practical route. At the first visit, a health worker can pre-screen "
          "the patient on the clinic laptop, refer a likely-eligible patient to a trial site by teleconsultation, "
          "and leave the full eligibility check to the site (Fig. 1a). The two possible errors at the pre-screen "
          "are not equal. An unnecessary referral costs one teleconsultation and is corrected by the site. A "
          "missed eligible patient is never referred, so this error is final. We therefore use missed eligible "
          "patients as our main measure, alongside accuracy."),
    ("fig", ("fig1_pathway.png", "(a) The telemedicine pre-screening pathway and its two errors. (b) The four "
             "privacy levels compared in this paper, defined by what the cloud receives about the patient.")),
    ("p", "LLMs can read trial criteria and patient notes and judge eligibility well {c:jin,abdallah}. In our "
          "earlier study, a single cloud LLM call per patient–trial pair reached an F1 score of 0.90 on trials it "
          "had not seen {c:indicon}. The cloud model, however, then receives the full note of every patient for "
          "every trial. This is in tension with the data-minimisation principle of India's Digital Personal Data "
          "Protection Act {c:dpdp}, and it needs a working network connection at the moment of the decision."),
    ("p", "Because trial criteria are public and only the note is private, there are two ways to keep the note in "
          "the clinic. The first *compiles the problem for a small device*: the criteria are turned into rules "
          "once in the cloud, and the clinic only extracts facts from the note and checks them, which also makes "
          "every decision traceable {c:magnini,yuan}. The second *moves the model to the data*: an open LLM runs "
          "inside the care setting and reads the note there {c:abdallah,prism}. Choosing between them needs a "
          "number that, to our knowledge, has not been measured: how many eligible patients each level of "
          "privacy costs, and what it costs the device."),
    ("p", "In this paper we measure that number and turn it into a deployment recipe. We compare four levels of "
          "information sent to the cloud (Fig. 1b) on a frozen test set whose trials were never used for "
          "development, and we run every device step on a 16 GB laptop without a GPU. For the single-facts level "
          "we built SPLIT-Match, a carefully engineered privacy-split pre-screener, and used it as a test probe. "
          "The analysis plan, including the main hypothesis, was fixed before the test data were used. Our "
          "earlier study on the same benchmark compared cloud LLMs with a hard rule-based veto, all in the cloud "
          "{c:indicon}; it did not consider what leaves the clinic, on-device models or device cost, which are the "
          "subject of this paper."),
    ("p", "Our findings are constructive. **Keeping the note on the laptop appears feasible**: open models that "
          "read the note there did not miss significantly more eligible patients than the cloud model, and the price "
          "was paid in unnecessary referrals, which the trial site corrects, and in device time. Compiling the note "
          "into rules, in contrast, missed far more eligible patients. With the device model held fixed, reading "
          "the note instead of driving the rule pipeline cut missed eligible pairs from {m:fourBvsSplitMissComp} to "
          "{m:fourBvsSplitMissRead} with a 4-billion-parameter model and from {m:twentyVsSplitMissComp} to "
          "{m:twentyVsSplitMissRead} with a 20-billion-parameter model. Most of the rule pipeline's misses came from "
          "a cloud judge that saw only a single fact, and for the larger model also from reducing the note to a "
          "fact sheet: minimising what the cloud sees can itself cost patients. These results argue against the "
          "rule-first design of our own earlier work {c:indicon}; we report the hypotheses that failed because they "
          "are the evidence behind the recipe. Our contributions are:"),
    ("bullets", [
        "**A measured deployment recipe** for on-device trial pre-screening on a 16 GB clinic laptop: which open "
        "model to run, its time and memory cost, and how many extra teleconsultations to plan for (Section VI-A).",
        "**A clinical privacy frontier**: missed eligible patients, unnecessary referrals, accuracy and data "
        "disclosure at four privacy levels, measured on a real laptop (Section V-A).",
        "**Evidence that reading beats compiling** at a fixed device model, conclusive for gpt-oss-20b and "
        "supportive for Qwen3-4B, with most losses traced to the rule pipeline and its single-fact cloud judge "
        "(Sections V-A and V-B).",
        "**An open release** of code, analysis plan, frozen system manifest and per-pair predictions, from which "
        "every number in this paper is regenerated (Section VII).",
    ]),

    ("h1", "Related Work"),
    ("h2", "LLMs for Trial Matching"),
    ("p", "TrialGPT uses an LLM to judge each eligibility criterion of a trial for a patient and ranks trials from "
          "these judgements {c:jin}. TrialMatchAI and PRISM run open or fine-tuned models on hospital servers so "
          "that patient records stay on premises {c:abdallah,prism}. Our earlier study found that a single "
          "zero-shot cloud call outperformed a hybrid system with a hard rule-based veto on unseen trials "
          "{c:indicon}. These systems target hospitals with data centres rather than primary-care devices, and "
          "they do not measure what is disclosed to an external service {c:jin,abdallah,prism}."),
    ("h2", "Compiling Criteria into Rules"),
    ("p", "Criteria2Query translates free-text criteria into database queries for cohort definition {c:yuan}. "
          "A recent neuro-symbolic system uses LLMs to turn criteria into logical constraints and verifies patient "
          "facts against them {c:qu}. In telemedicine, neuro-symbolic decision support has been proposed for "
          "chronic disease diagnosis and monitoring because its decisions can be explained {c:magnini}. We test "
          "whether this compiled route keeps its accuracy when the patient side runs on a small device "
          "(Section V-B)."),
    ("h2", "Privacy and Local Models in Telemedicine"),
    ("p", "A privacy-aware router that shares the name PRISM sends each query either to an edge model or to the "
          "cloud, depending on how sensitive the query is {c:zhan}. Earlier TELMED studies found that local open "
          "LLMs lagged cloud models as healthcare chatbots {c:montagna} and that small agentic healthcare models "
          "can leak private data {c:aguzzi}. Personal data ecosystems have been analysed as an enabler of "
          "decentralised trials {c:oliver}. We extend this line of work to trial referral and measure what local "
          "reading costs in missed patients, disclosure and device time (Section V)."),

    ("h1", "Setting and the SPLIT-Match Probe"),
    ("fig", ("fig2_splitmatch.png", "SPLIT-Match. Only public criteria and, for residual criteria, one minimal "
             "fact cross the privacy gateway, which blocks any complete note sentence or patient identifier before "
             "network access and logs every call.")),
    ("h2", "Privacy Levels and Threat Model"),
    ("p", "We describe a pre-screener by what the cloud receives about the patient (Fig. 1b): the *full note*; a "
          "*de-identified record*, i.e., structured fields extracted on the laptop with age in bands and no free "
          "text; *single facts*, each tied to one criterion; or *nothing*. Trial criteria are public, so sending "
          "them is not a disclosure. We assume a cloud provider that follows the protocol but may store everything "
          "it receives (an honest-but-curious provider), either query by query or linked across one screening "
          "session. A compromised clinic laptop is outside the scope of every design, because the note is written "
          "there."),
    ("h2", "SPLIT-Match"),
    ("p", "SPLIT-Match (Fig. 2) implements the single-facts and nothing levels. In the cloud, two LLMs from "
          "different model families, gpt-oss-120b {c:gptoss} and Qwen3.8-27B {c:qwen38}, compile each trial's "
          "criteria into typed rules; a rule is trusted only if both compilers produce it. For example, "
          "“ECOG performance status 0–1” becomes the comparison ECOG ≤ 1, and “no prior systemic therapy "
          "for metastatic disease” becomes a prior-therapy rule; other types cover lists of allowed values, "
          "washout periods, counts and conditions. Compilation happens once per trial and involves only public "
          "text. On the laptop, a 4-billion-parameter model (Qwen3-4B, 4-bit) {c:qwen3} extracts a 47-field fact "
          "sheet from the note, with a supporting quote for each value, and a rule-based reader checks each fact "
          "independently; a fact is *verified* only if both agree."),
    ("p", "Rules are evaluated with three values (true, false or unknown), so missing information never counts as "
          "a failed criterion. Because a missed referral is final, excluding a patient requires two independent "
          "pieces of evidence (two keys), and an unverified fact can never exclude a patient. Criteria that the "
          "rules cannot decide go to an on-laptop LLM judge (L1) and, if still unresolved, to a cloud judge (L2) "
          "that receives only the criterion and one minimal fact. The cloud judge's verdict can serve as the second "
          "key of an exclusion. A criterion the judges cannot settle (they disagree, or only one finds it failed) "
          "is *deferred* (*Defer*): it never excludes on its own; in forced mode it follows the cloud verdict if "
          "there is one, and offline the patient is referred. History that the note does not mention becomes a question for the health worker "
          "(*Ask*). For comparison with gold labels, a *forced* mode turns every output into eligible or not "
          "eligible; in this mode the cloud judge also settles open questions on its own, told only that the fact "
          "is not in the note. Every model call passes through one gateway function that stops the call before it "
          "reaches the network if the payload contains a complete note sentence or a patient identifier, and logs "
          "the payload for audit."),

    ("h1", "Evaluation Design"),
    ("h2", "Data"),
    ("p", "We use 400 synthetic non-small-cell lung cancer (NSCLC) patient–trial pairs over 40 real trials with "
          "verbatim criteria {c:indicon}. The pairs are split at trial level into a development set (130 pairs, "
          "26 patients, 22 trials) and a test set (270 pairs, 45 patients, 18 trials, 69 eligible pairs) that "
          "share no patients or trials; each test patient is paired with six trials. Test trials were drawn by a "
          "fixed-seed stratified procedure that did not see any system. Patient attributes were sampled without "
          "reference to any trial and written as short narratives (median 124 words). Two independent experts "
          "labelled every pair without seeing the generation details; they agreed on 98.0% of pairs and resolved "
          "the rest by discussion. Our earlier study also evaluated systems on this test split {c:indicon}; "
          "SPLIT-Match was designed after those results were known, using development data only, so we treat the "
          "test split as a previously used benchmark rather than an independent replication. No real patient data "
          "were used, so the study involved no human participants."),
    ("h2", "Compared Systems"),
    ("p", "*Full note:* gpt-oss-120b in the cloud, zero-shot (one instruction, no examples), run five times, plus "
          "few-shot, retrieval-augmented and our earlier hybrid system {c:indicon}. *Record:* gpt-oss-120b decides "
          "from the fact sheet extracted on the laptop. *Facts:* SPLIT-Match on the laptop. *Nothing:* SPLIT-Match "
          "without the cloud judge (offline), and three open models that read the full note on the laptop with "
          "the same zero-shot prompt: Qwen3-1.7B, Qwen3-4B {c:qwen3} and gpt-oss-20b, a mixture-of-experts model "
          "in which about 3.6 of its 21 billion parameters are active for each token {c:gptoss}. For the stress "
          "tests and ablations, including the offline variant, a hosted gpt-oss-20b stood in for the laptop model "
          "in a second SPLIT-Match run (the *proxy* run), because the laptop could not repeat structuring for every "
          "variant in time. *Fact sheet without rules* (exploratory): the device model decides from its own "
          "SPLIT-Match fact sheet with the zero-shot prompt. Hosted runs of gpt-oss-20b (four) and Qwen3.8-27B add "
          "reference points. All laptop runs used an Intel i5-13500H CPU (12 cores) with 16 GB of memory and no "
          "GPU, served by Ollama 0.40.15 with default CPU threading, Qwen3 models in 4-bit (Q4_K_M), gpt-oss-20b in "
          "its native MXFP4 format, a context of 8,192 tokens, temperature 0 and a fixed seed."),
    ("h2", "Analysis Plan and Measures"),
    ("p", "The analysis plan was fixed before the test run. The main hypothesis (H1) was that SPLIT-Match's forced "
          "accuracy is not worse than cloud zero-shot by more than 0.05 (non-inferiority); we chose this margin "
          "because a pre-screen is always followed by full screening at the site and because it is of the order "
          "of the run-to-run variation of hosted models. H2 stated that no patient narrative leaves the laptop, "
          "measured as zero note sentences in any cloud payload; H3–H8 covered device time, asking, uncertainty, "
          "irrelevant social cues, typed rules and noisy notes; seven ablations each removed one component. All "
          "other comparisons are exploratory. Besides accuracy we report recall (the share of eligible pairs that "
          "are referred), missed eligible pairs and unnecessary referrals, also per 100 patients screened against "
          "six trials. Every difference is written as system minus reference, so a negative value means the "
          "system scored lower. Non-inferiority is judged by whether the lower CI bound of the accuracy difference "
          "stays above −0.05; McNemar p-values test for any difference. H1 used accuracy; we adopted missed "
          "eligible patients as the main lens after the test run, so the missed-patient tests (recall with "
          "trial-resampled CIs, paired recall differences and exact McNemar tests on the 69 eligible pairs) are "
          "exploratory."),
    ("h2", "Safeguards"),
    ("p", "SPLIT-Match was developed on development data only, frozen with a SHA-256 manifest of 26 files, and run "
          "once on the test set. Confidence intervals (CIs) are 95% bootstrap intervals that resample trials, as "
          "pre-specified: we redraw the 18 test trials with replacement 5,000 times and take the middle 95% of "
          "the results; resampling patients and trials together (two-way) serves as a sensitivity check, because "
          "pairs share both. Paired comparisons use the exact McNemar test. Hosted runs were repeated to measure "
          "run-to-run noise, and every number in this paper is generated by a script from the released per-pair "
          "predictions."),

    ("h1", "Results"),
    ("h2", "Missed Eligible Patients Across Privacy Levels"),
    ("p", "Table I and Fig. 3 show three groups. Full-note cloud methods reach 0.92–0.95 accuracy (zero-shot "
          "{m:accTcloudZS}, few-shot {m:accTcloudFS}, retrieval-augmented {m:accTcloudRAG}, our earlier hybrid "
          "{m:accTindiconAdv}), and the cloud "
          "model misses {m:cloudRunsMissMin}–{m:cloudRunsMissMax} of the 69 eligible pairs across its five runs "
          "({m:cloudRunsMissHundredMin}–{m:cloudRunsMissHundredMax} per 100 patients). Compiled privacy-split "
          "methods reach only 0.77–0.79. Models that read the note on the laptop lie in between: they miss few "
          "eligible patients but refer more ineligible ones. **H1 fails:** SPLIT-Match's accuracy difference from "
          "cloud zero-shot is {m:diffTsplitDeploy} (CI [{m:diffloTsplitDeploy}, {m:diffhiTsplitDeploy}], far below "
          "the −0.05 margin), and it misses {m:missSplitDeploy} of 69 eligible pairs, the very error its design "
          "treats as final."),
    ("table", "T1"),
    ("fig", ("fig3_missed_vs_unnecessary.png", "The two errors by privacy level: missed eligible patients (never "
             "referred) against unnecessary referrals (corrected at the site), per 100 patients screened against "
             "six trials; lower left is better. Marker shape shows what the cloud receives; the shaded box spans "
             "the cloud model's five runs. SPLIT-Match offline comes from the proxy run (hosted gpt-oss-20b as device "
             "model), so its distance from the laptop SPLIT-Match point mixes the cloud judge's effect with a "
             "change of model; the matched comparison is the proxy run with and without the judge (Section V-A).")),
    ("p", "Most of these patients are lost at the cloud judge, which sees only a criterion and one minimal fact. "
          "In the proxy run, removing the judge (on the same fact sheets) left accuracy almost unchanged "
          "(difference {m:abNoLtwoDiff}, CI [{m:abNoLtwoLo}, {m:abNoLtwoHi}]) but cut missed eligible pairs from "
          "{m:ltwoProxyMiss} to {m:ltwoNoMiss}. Of the {m:ltwoExtra} extra misses with the judge, "
          "{m:ltwoExtraTwoKey} were exclusions in which its verdict supplied the second key and {m:ltwoExtraAlone} "
          "were forced-mode exclusions on its verdict alone; without it, these pairs stayed open questions or "
          "deferrals and were referred. In the laptop run, {m:ltwoDeployCloud} of the {m:ltwoDeployMiss} missed "
          "pairs had a cloud verdict as a key. Minimising what the judge sees therefore cost eligible patients, "
          "while without the judge SPLIT-Match referred almost every patient it could not exclude "
          "({m:unrefOffline} unnecessary referrals)."),
    ("p", "Tested directly on the 69 eligible pairs, SPLIT-Match's recall difference from the cloud is "
          "{m:recDSplit} (two-way CI [{m:recDSplitLoTw}, {m:recDSplitHiTw}]; {m:mcESplitB} vs. {m:mcESplitA} "
          "eligible pairs that only one of the two got right, McNemar p = {m:mcESplitP}). For the laptop readers "
          "the difference is smaller and not significant (Qwen3-4B {m:recDFour}, p = {m:mcEFourP}; gpt-oss-20b "
          "{m:recDTwLoc}, p = {m:mcETwLocP}), but the two-way intervals reach {m:recDFourLoTw} and "
          "{m:recDTwLocLoTw}, and the counts are {m:missEdgeFourB} and {m:locFullMiss} missed pairs against "
          "{m:missCloudZS} in the cloud's reference run. We therefore claim no significant difference in missed "
          "patients, not equivalence or clinical safety."),
    ("h2", "Reading Beats Compiling at a Fixed Device Model"),
    ("p", "Where are the eligible patients lost? Reading the note and running SPLIT-Match are end-to-end systems "
          "that differ in several components, so we hold the device model fixed and change one input at a time "
          "(Table II): the note; the model's own SPLIT-Match fact sheet, decided with the same zero-shot prompt but "
          "without rules; and the full pipeline of rules and judges."),
    ("table", "T3"),
    ("p", "With Qwen3-4B, the fact sheet lost no eligible patients ({m:decFourNoteMiss} missed on the note, "
          "{m:decFourFsMiss} on the fact sheet; accuracy difference {n:decFourNFAcc}, p = {m:decFourNFMcp}), and the "
          "pipeline raised misses to {m:decFourRulesMiss} (recall difference {n:decFourFRRec}; accuracy "
          "{n:decFourFRAcc}, McNemar p = {m:decFourFRMcp}). With gpt-oss-20b, the fact sheet already raised misses "
          "from {m:decTwNoteMiss} to {m:decTwFsMiss} (recall difference {n:decTwNFRec}, two-way CI "
          "[{n:decTwNFRecHiTw}, {n:decTwNFRecLoTw}]), and the pipeline raised them to {m:decTwRulesMiss} while "
          "unnecessary referrals rose from {m:decTwFsUnn} to {m:decTwRulesUnn} (accuracy difference {n:decTwFRAcc}, "
          "p = {m:decTwFRMcp}; two-way CI [{n:decTwFRAccHiTw}, {n:decTwFRAccLoTw}]). The same 4B fact sheet led the "
          "cloud model to miss {m:missRecDeploy} eligible pairs, so how a record is read matters as much as what it "
          "holds. Over the whole path, the pipeline's accuracy difference from reading the note is "
          "{n:twentyVsSplitDiff} for gpt-oss-20b ({m:twentyVsSplitMcA} vs. {m:twentyVsSplitMcB} pairs that only one "
          "got right, p = {m:twentyVsSplitMcp}; two-way CI [{n:twentyVsSplitHiTw}, {n:twentyVsSplitLoTw}], excluding "
          "zero) and {n:fourBvsSplitDiff} for Qwen3-4B (p = {m:fourBvsSplitMcp}; two-way CI [{n:fourBvsSplitHiTw}, "
          "{n:fourBvsSplitLoTw}], including zero): conclusive for the larger model, supportive for the smaller. The "
          "rule pipeline, including its single-fact cloud judging, thus cost eligible patients with both models, "
          "and the fact sheet with the larger one. Of the pre-specified one-component ablations, a single compiler "
          "outperformed agreement between two (difference {m:abSingleDiff}, p = {m:abSingleMcp}); the two-key rule, "
          "fact checking and typed rules had no significant effect."),
    ("h2", "On the Laptop: More Referrals, Not More Missed Patients"),
    ("p", "Table III compares models that read the full note. Within the Qwen family accuracy grows with size, but "
          "the error type changes: the 1.7B model refers almost everyone ({m:unrefQwenOneSeven} unnecessary "
          "referrals), while the dense 27B model refers too few (recall {m:recQwenTwentySeven}) and is less accurate "
          "than the 20B mixture of experts, so the device model must be chosen by measurement, not size. "
          "gpt-oss-20b ran on the laptop only with its weights read directly from disk (the default load needed "
          "10 GB more memory), at {m:locFullLatMed} s per pair, about {m:locFullPerPatientMin} minutes per patient "
          "for six trials, and {m:locFullPeakRamGb} GB of peak memory."),
    ("table", "T2"),
    ("p", "On all 270 pairs, gpt-oss-20b on the laptop reached {m:locFullAcc} accuracy (difference from the cloud "
          "{m:locFullDiff}, CI [{m:locFullLoTr}, {m:locFullHiTr}]), so it is not non-inferior at the 0.05 margin. "
          "It missed {m:locFullMiss} eligible pairs, within the cloud's own range across runs and not significantly "
          "more (Section V-A); its gap came mainly from unnecessary referrals ({m:locFullUnref} against "
          "{m:cloudRunsUnnMin}–{m:cloudRunsUnnMax} for the cloud). Its hosted runs scored one to two points higher, "
          "with {m:locFullAgreeMin}–{m:locFullAgreeMax} decision agreement; part of this gap may be run-to-run "
          "variation. Qwen3-4B's accuracy differed from gpt-oss-20b's by {n:locVsFourDiff} (p = {m:locVsFourMcp}); "
          "it missed a similar number of eligible pairs but made more unnecessary referrals, at a quarter of the "
          "time per pair."),
    ("p", "*Repeat runs.* Qwen3-4B was stable, while gpt-oss-20b varied by a few decisions. A fresh, uncached "
          "repeat of Qwen3-4B on all 270 pairs agreed with the first run on {m:repFourAgree} of decisions with the "
          "same accuracy ({m:repFourAccRep}), at a median of {m:repFourLatMed} s per pair (95th percentile "
          "{m:repFourLatPnf} s) and {m:repFourRamGb} GB of peak memory. A repeat of gpt-oss-20b on the 40-pair "
          "stratified subset agreed on {m:repTwAgree} of decisions (accuracy {m:repTwAccRep} vs. {m:repTwAccFirst} "
          "on those pairs); with less free memory it needed a median of {m:repTwLatMed} s per pair (95th percentile "
          "{m:repTwLatPnf} s) after a {m:repTwCold}-s cold start. These are feasibility measurements on one everyday "
          "laptop, not production benchmarks."),
    ("h2", "Robustness"),
    ("p", "*Run-to-run noise.* Over five cloud runs (mean {m:nfCloudMean}, SD {m:nfCloudSd}) and four hosted "
          "gpt-oss-20b runs (mean {m:nfEdgeMean}), the run-averaged accuracy difference is {m:nfAvgDiff} (CI "
          "[{m:nfAvgLo}, {m:nfAvgHi}]); on the laptop it is {m:locFullAvgDiff} (CI [{m:locFullAvgLo}, "
          "{m:locFullAvgHi}]). Missed eligible pairs vary more than accuracy ({m:cloudRunsMissMin}–"
          "{m:cloudRunsMissMax} across cloud runs), so differences of one or two missed pairs between single runs "
          "are not meaningful. *Long, cluttered notes.* Embedding each note in a record of "
          "{m:longWordsMin}–{m:longWordsMax} words (median {m:longWordsMed}) of label-neutral administrative, social "
          "and family history, checked by an independent model, left the cloud model's accuracy unchanged "
          "({m:longCloudDelta}) and changed it by {m:longTwentyBDelta} (CI [{m:longTwentyBLo}, {m:longTwentyBHi}]) "
          "for hosted gpt-oss-20b and {m:longFourDelta} for Qwen3-4B."),
    ("h2", "Privacy and the Network Link"),
    ("p", "**H2 holds in its pre-specified form:** no complete note sentence appeared in the {m:privCallsDeploy} "
          "fact queries ({m:privDistinctDeploy} distinct messages), and the gateway never had to block a call. The "
          "gateway catches what it is designed to catch, whole note sentences and identifiers, but not altered or "
          "encoded text. On a test set of crafted messages built from the test notes, it blocked {m:gwExactRate} "
          "of exact note sentences, {m:gwEmbedRate} of sentences embedded in a query and {m:gwPidRate} of patient "
          "identifiers, with no false blocks among the {m:gwFactOkN} real fact messages and {m:gwPubOkN} "
          "public-criteria calls; but it blocked only {m:gwHalfRate} of half-sentences, {m:gwDropRate} of "
          "sentences with one word removed and {m:gwBtsfRate} of base64-encoded sentences. In the real traffic, "
          "{m:gwRealFive} of {m:gwRealN} fact messages ({m:gwRealFiveShare}) reused a phrase of five or more "
          "consecutive note words (longest {m:gwRealMax}), such as a diagnosis and stage: facts this level is meant "
          "to send, but in the note's own wording. The gateway is a backstop, not a guarantee of privacy; its call "
          "log stays on the laptop."),
    ("p", "Sending facts is also not anonymity. In a disclosure-risk simulation over 28 record fields of the "
          "dataset's attribute generator (not a real-world re-identification test), {m:uniqRecord} of "
          "de-identified records are unique among 10⁵ synthetic patients; a single fact query is unique for "
          "{m:uniqFact} of patients, but a cloud that links one session's queries singles out {m:uniqLinked}. "
          "Round trips matter more than bytes: in a simulated link that is up half of the time in 30-minute "
          "stretches, {m:outFiftyCloud} of cloud and {m:outFiftySplit} of SPLIT-Match screenings finish within a "
          "30-minute visit, against {m:outFiftyEdgeTwenty} for on-device reading; with 5- and 120-minute stretches "
          "the cloud completes {m:outHalfFiveCloud} and {m:outHalfOneTwentyCloud}, while on-device reading is "
          "unaffected."),
    ("h2", "Other Pre-Specified Hypotheses"),
    ("p", "Of H3–H8, only H8 (no loss on noisy notes) held, and zero-shot reading met it too; the full results are "
          "in the repository."),

    ("h1", "Discussion and Limitations"),
    ("h2", "A Deployment Recipe"),
    ("p", "We condense the measurements into configuration guidance for a district clinic with a 16 GB laptop and "
          "no GPU (Box 1). It is a starting point that each site must validate on its own patients and trials, not "
          "a demonstration of clinical safety. Step 1 follows from Section V-A: no compiled design came close to "
          "the cloud on missed patients, and the single-fact cloud judge caused most of SPLIT-Match's misses. "
          "Step 2 follows from Table III: parameter count did not order the models, and hosted runs scored above "
          "the laptop run. Step 3 makes the cost of privacy explicit: about {m:locFullUnrefHundred} (gpt-oss-20b) "
          "to {m:unrefHundredEdgeFourB} (Qwen3-4B) unnecessary referrals per 100 patients screened against six "
          "trials, against {m:unrefHundredCloudZS} for the cloud model; total referrals barely change, because the "
          "cloud refers more of the eligible patients. Step 4 uses the median wall-clock time of the laptop model "
          "calls per patient (six trials, first run, cloud calls excluded): about {m:locFullPerPatientMin} minutes for gpt-oss-20b, more when memory is "
          "short, and {m:edgeFourBPerPatient} s for Qwen3-4B, against {m:edgeSplitPerPatient} s for SPLIT-Match, "
          "so compiling did not save device time. Step 5 keeps what the rule layer does well: an audit trail, a "
          "fact checker that caught all {m:extLocalWrongUnver} wrong values of the 4B extractor on 25 new "
          "patients, and an offline triage tier (proxy run) that decides {m:covTofflineSel} of pairs at "
          "{m:covOfflineAcc} accuracy, as accurate as gpt-oss-20b on the laptop abstaining to the same coverage "
          "({m:covTwentyBLocalAcc})."),
    ("p", "The health worker remains central: they answer the questions the system raises (*Ask*) during the visit "
          "and absorb the extra referrals. A study of their workload, and of clinicians' judgements of the missed "
          "patients, for which we release a review packet, is the next step."),
    ("h2", "Why Compiling Loses Eligible Patients"),
    ("p", "Most of SPLIT-Match's missed patients were excluded with a cloud verdict that saw only a criterion and "
          "one fact (Section V-A). The rule layer was also tuned on development trials and over-fitted them "
          "(accuracy difference from the cloud {m:diffDsplitProxy} there and {m:diffTsplitProxy} on unseen trials, both "
          "in the proxy run). A "
          "fixed 47-field fact sheet cost patients only for gpt-oss-20b, probably because some criteria refer to "
          "details that no fixed schema anticipates. And because an unverified fact can never exclude a patient, "
          "many decisions fall to the judges. A model that reads the note avoids these steps."),
    ("box", "BOX1"),
    ("h2", "Limitations"),
    ("p", "Patients are synthetic and written from templates, and only lung cancer trials are covered; the "
          "long-note study tests clutter, not real clinical language, and no clinician has yet reviewed note "
          "realism or the missed patients. The benchmark was used in our earlier study {c:indicon}, so later "
          "design choices could reflect knowledge of its results despite development-only tuning; a fresh set of "
          "unseen trials is the most important next test. Eighteen test trials give wide intervals, and with only "
          "69 eligible pairs the study has little power to detect a small loss of recall on the device, so “no "
          "significant difference” is not a claim of equivalence. The cloud reference is an open-weights model, "
          "chosen so that every cloud run can be repeated and compared with the same model family on the laptop; "
          "a proprietary model could raise the ceiling. Laptop results come from one machine with one repeat run; "
          "the gpt-oss-20b decomposition, the offline variant and the stress tests used hosted runs, which may be "
          "slightly optimistic for the laptop. The network and re-identification analyses are simulations. Our "
          "conclusion about compilation holds for our design; another compiled design could do better."),

    ("h1", "Conclusion"),
    ("p", "Where the patient note lives matters less than who reads it. On a benchmark with unseen trials and a "
          "real CPU-only laptop, compiling notes and criteria into rules kept complete note sentences in the clinic "
          "but missed far more eligible patients than the cloud, mostly through cloud judgements that saw a single "
          "fact, and the same models missed far fewer when they read the note instead. Open models that read the "
          "note on the laptop did not miss significantly more eligible patients than the cloud, though with wide "
          "uncertainty, at the cost of more unnecessary referrals and, for the larger model, minutes per patient. "
          "Keeping the note local therefore appears feasible for telemedicine pre-screening, but it must be "
          "validated on real notes and with clinicians before clinical use. Code, analysis plan, frozen manifest "
          "and per-pair predictions are available at " + REPO_URL + "."),

    ("ack", "This work was supported by grants from Syneos Health (IITM/CONS/SHILC-USA/VD/111), the Department of "
            "Science and Technology (IITM/DST/VD/603), the All India Council for Technical Education "
            "(IITM/IKS-MoE/VD/548), and Mr. Satish and Kamlesh Agarwal Master Account (IITM/DORA/MASTER "
            "Account/2025/03) awarded to Prof. Varun Dutt. We also thank IIT Mandi for providing the necessary "
            "infrastructure and computational resources. *Competing interests:* S. Kaushik is affiliated with "
            "Syneos Health, one of the funders of this work."),
    ("refs", None),
]

BOXES = {
    "BOX1": {
        "title": "Box 1. Recipe from this benchmark for on-device trial pre-screening (16 GB laptop, no GPU); validate locally before use",
        "items": [
            "**Keep the note on the laptop.** Send nothing about the patient to the cloud; criteria may be fetched.",
            "**Choose the model by measurement**, not by size or a hosted run: on your own trials and device, "
            "count missed eligible patients, unnecessary referrals and seconds per pair.",
            "**Budget teleconsultations**: plan for about {m:locFullUnrefHundred}–{m:unrefHundredEdgeFourB} "
            "unnecessary referrals per 100 patients screened against six trials.",
            "**Budget device time**: about {m:locFullPerPatientMin} min per patient for gpt-oss-20b (more when memory "
            "is short; run it in the background) or under 4 min for Qwen3-4B.",
            "**Keep rules for audit and offline triage only**, and never let a judge that sees a single fact exclude a "
            "patient.",
        ],
    },
}

TABLES = {
    "T1": {
        "caption": "Test Results by What the Cloud Receives (270 Pairs, 69 Eligible)",
        "widths": [0.45, 1.10, 0.40, 0.94, 0.30, 0.30],
        "header": ["Cloud gets", "System", "Acc.", "Recall [95% CI]", "Miss", "Unn."],
        "rows": [
            ["Full note", "Cloud LLM, zero-shot", "{m:accTcloudZS}", "{m:recCloud} [{m:recCloudLo}, {m:recCloudHi}]",
             "{m:missCloudZS}", "{m:unrefCloudZS}"],
            ["", "  same, 5 runs (mean, range)", "{m:nfCloudMean}", "–",
             "{m:cloudRunsMissMin}–{m:cloudRunsMissMax}", "{m:cloudRunsUnnMin}–{m:cloudRunsUnnMax}"],
            ["Record", "Cloud LLM, laptop record*", "{m:accTcloudRecordDeploy}",
             "{m:recRec} [{m:recRecLo}, {m:recRecHi}]", "{m:missRecDeploy}", "{m:unrefRecDeploy}"],
            ["Facts", "SPLIT-Match", "{m:accTsplitDeploy}", "{m:recSplit} [{m:recSplitLo}, {m:recSplitHi}]",
             "{m:missSplitDeploy}", "{m:unrefSplitDeploy}"],
            ["Nothing", "SPLIT-Match offline†", "{m:accToffline}", "{m:recOff} [{m:recOffLo}, {m:recOffHi}]",
             "{m:missOffline}", "{m:unrefOffline}"],
            ["", "Qwen3-4B on laptop*", "{m:accTedgeFourB}", "{m:recFour} [{m:recFourLo}, {m:recFourHi}]",
             "{m:missEdgeFourB}", "{m:unrefEdgeFourB}"],
            ["", "gpt-oss-20b on laptop*", "{m:locFullAcc}", "{m:recTwLoc} [{m:recTwLocLo}, {m:recTwLocHi}]",
             "{m:locFullMiss}", "{m:locFullUnref}"],
        ],
        "note": "Recall CIs resample trials. Miss: eligible pairs judged not eligible; Unn.: ineligible pairs "
                "referred. Device steps ran on the 16 GB laptop, except †(proxy run, hosted stand-in for the device "
                "model). *Exploratory comparison.",
    },
    "T3": {
        "caption": "Same Device Model, Three Inputs: Note, Fact Sheet, Rules",
        "widths": [0.80, 1.05, 0.40, 0.44, 0.38, 0.42],
        "header": ["Device model", "Input", "Acc.", "Recall", "Miss", "Unn."],
        "rows": [
            ["Qwen3-4B", "note (zero-shot)", "{m:decFourNoteAcc}", "{m:decFourNoteRec}", "{m:decFourNoteMiss}",
             "{m:decFourNoteUnn}"],
            ["(laptop)", "fact sheet, no rules*", "{m:decFourFsAcc}", "{m:decFourFsRec}", "{m:decFourFsMiss}",
             "{m:decFourFsUnn}"],
            ["", "rules + judges", "{m:decFourRulesAcc}", "{m:decFourRulesRec}", "{m:decFourRulesMiss}",
             "{m:decFourRulesUnn}"],
            ["gpt-oss-20b", "note (zero-shot)", "{m:decTwNoteAcc}", "{m:decTwNoteRec}", "{m:decTwNoteMiss}",
             "{m:decTwNoteUnn}"],
            ["(hosted)", "fact sheet, no rules*", "{m:decTwFsAcc}", "{m:decTwFsRec}", "{m:decTwFsMiss}",
             "{m:decTwFsUnn}"],
            ["", "rules + judges", "{m:decTwRulesAcc}", "{m:decTwRulesRec}", "{m:decTwRulesMiss}",
             "{m:decTwRulesUnn}"],
        ],
        "note": "Each model decides from its own SPLIT-Match fact sheet (*exploratory) with the same zero-shot "
                "prompt as for the note. Rules + judges: the full SPLIT-Match pipeline, including the laptop and cloud "
                "judges. The hosted gpt-oss-20b note row is the pre-specified −compiler ablation of the proxy run, the same "
                "run as the hosted gpt-oss-20b row of Table III.",
    },
    "T2": {
        "caption": "Models Reading the Full Note (Same Zero-Shot Prompt, Test Set)",
        "widths": [0.82, 0.62, 0.42, 0.45, 0.36, 0.36, 0.46],
        "header": ["Model", "Run on", "Acc.", "Recall", "Miss", "Unn.", "s/pair"],
        "rows": [
            ["Qwen3-1.7B", "laptop", "{m:capOneSevenAcc}", "{m:recQwenOneSeven}", "{m:missQwenOneSeven}",
             "{m:unrefQwenOneSeven}", "{m:capOneSevenLat}"],
            ["Qwen3-4B", "laptop", "{m:capFourAcc}", "{m:recEdgeFourB}", "{m:missEdgeFourB}", "{m:unrefEdgeFourB}",
             "{m:capFourLat}"],
            ["gpt-oss-20b", "laptop", "{m:locFullAcc}", "{m:locFullRec}", "{m:locFullMiss}", "{m:locFullUnref}",
             "{m:locFullLatMed}"],
            ["gpt-oss-20b", "hosted", "{m:capTwentyBAcc}", "{m:recEdgeTwentyB}", "{m:missEdgeTwentyB}",
             "{m:unrefEdgeTwentyB}", "–"],
            ["Qwen3.8-27B", "hosted", "{m:capTwentySevenAcc}", "{m:recQwenTwentySeven}", "{m:missQwenTwentySeven}",
             "{m:unrefQwenTwentySeven}", "–"],
            ["gpt-oss-120b", "cloud", "{m:capOneTwentyAcc}", "{m:recCloudZS}", "{m:missCloudZS}", "{m:unrefCloudZS}",
             "–"],
        ],
        "note": "s/pair: median seconds per pair on the 16 GB CPU laptop. Hosted gpt-oss-20b: first of four hosted "
                "runs (mean accuracy {m:nfEdgeMean}), the same run as in Table II. Qwen3 models are dense; gpt-oss models are mixtures of experts.",
    },
}
