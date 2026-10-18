# Syllabus source record

**Status: PARTIALLY VERIFIED. Read this before relying on the coverage matrix.**

## Which syllabus

| Field | Value |
|---|---|
| Exam | JEE (Main), Paper 1 (B.E./B.Tech.), Mathematics |
| Syllabus year used | **2026**. This was the latest officially published syllabus at retrieval time. |
| 2027 syllabus | **Not found as an official NTA publication** on 2026-10-18. Third-party sites describe the 2027 syllabus as "expected" or "same as 2026"; none of that is treated as confirmed here. |
| Official document title | "Syllabus for JEE(Main) -2026" |
| Official URL (NTA content CDN) | https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/uploads/2025/10/202510311323551056.pdf |
| Upload date | 2025-10-31. This is inferred from the upload path `uploads/2025/10/20251031…`, not read from inside the document. |
| Companion bulletin | "Information Bulletin - 2026", https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/uploads/2025/10/202510311145384616.pdf |
| Previous year (for comparison) | "2025 Syllabus for JEE Main Paper 1 (BE/B.Tech.)", https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/uploads/2024/10/2024102841.pdf |
| Official portal | https://jeemain.nta.nic.in/ |
| Retrieval date | 2026-10-18 |

## What could and could not be verified

The production environment is a sandboxed cloud container.

* `jeemain.nta.nic.in`, `nta.ac.in` and `cdnbbsr.s3waas.gov.in` were **unreachable** from the container (egress proxy 403) and from the web-fetch tool (DNS failure). The web archive was also blocked.
* The document **titles and URLs above were confirmed through web-search indexing** of the official host.
* Search snippets of the official PDF matched the wording of Units 1, 2 and 3 and part of Unit 14 in `JEE_MAIN_2026_MATHS_TRANSCRIPTION.md`.
* **The other unit texts were transcribed from the producer's knowledge of the NTA syllabus.** That syllabus was revised for JEE Main 2024 and carried forward unchanged in wording to 2025 and 2026. They have **not** been diffed against the PDF.
* **No local copy of the official PDF could be saved.** `LOCAL_COPY_MISSING.txt` records this.

### Action needed by a human (5 minutes)
1. Download the official PDF from the URL above.
2. Save it as `docs/syllabus/JEE_Main_2026_Syllabus_official.pdf`.
3. Compare its Mathematics section line by line with `JEE_MAIN_2026_MATHS_TRANSCRIPTION.md`.
4. Change each row's `verification_status` in `docs/coverage_matrix.csv` from `transcribed-unverified` to `verified-against-pdf`.
5. If NTA publishes a 2027 syllabus, repeat the comparison against it.

## Scope notes (resolved / flagged)

These are differences from the pre-2024 syllabus that students often get wrong. The "Treatment in video" column says how each topic is handled.

| Topic | In 2026 listed text? | Treatment in video |
|---|---|---|
| Mathematical induction, Mathematical reasoning | No (removed in the 2024 revision) | Not taught. |
| Heights and distances | No | Not taught. |
| Trigonometric **equations** | Not named. The unit says "Trigonometrical identities and trigonometrical functions, inverse trigonometrical functions and their properties". | **Flagged uncertain.** Basic equations (sin x = k, general solution) are taught briefly as a *tool* for functions/inverse trig and labelled "boundary of scope". |
| Planes in 3D | No. Unit 11 lists points, distance, section formula, DRs/DCs, angle between lines, skew lines, shortest distance, equations of a line. | Not taught as assessed content. Planes appear only as a visual aid, labelled. |
| Binomial **distribution**, Bernoulli trials | No. The unit lists "probability distribution of a random variate". | Mean and variance of a discrete random variable are taught. The binomial distribution is mentioned only as "outside listed text". |
| Conditional probability | Not separately named, but it is required by "multiplication theorem" and "Bayes' theorem". | Taught as a prerequisite. |
| Limits: standard forms, L'Hospital | "Limits" is listed without detail. | Standard limits taught. L'Hospital is shown as a *checking* tool with stated conditions, not as a required method. |
| Rolle's / Mean value theorem | Not named in the 2026 text. | Not taught as assessed content. Mentioned only for context. |
| "Integration by partial functions" | Listed (NTA wording; means **partial fractions**). | Taught as partial fractions. |
| Conics: "sections of conics", "points of intersection of a line and a circle with the centre at the origin" | Listed | Taught. Tangent/normal conditions for conics are treated as applications of differentiation, labelled. |
| Mean deviation, variance, standard deviation (grouped and ungrouped) | Listed | Taught. |

Prerequisites that are **not assessed directly but needed** are listed in the coverage matrix with `row_type = prerequisite`. Examples: algebraic identities, inequalities and intervals, conditional probability, and the unit circle.

## No weightage or "most repeated" claims

This production makes **no** chapter-weightage or "most repeated" claims. No documented question-frequency analysis (years, sample, method) was carried out, so any such claim would be invented.
