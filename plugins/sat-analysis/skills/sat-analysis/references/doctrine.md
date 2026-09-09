# Doctrine catalog and enrichment

The engine uses a small, versioned reference catalog at
`sat_engine/resources/doctrine/catalog.v1.json`. This is its only catalog source;
the wheel includes it, and contract export copies its original bytes. Loading and
resolving rules requires no network access. Schema family `1` and catalog version
`1.0.0` identify contracts, not accuracy or certified compliance.

The cited editions were checked against these primary sources on 9 September
2026:

- [ODNI, ICD 203, Analytic Standards](https://archive.dni.gov/files/documents/ICD/ICD-203.pdf), signed 2 January 2015, in the linked amended compilation: D.6.e.(1), (2), (3), (4), and (6).
- [Richards J. Heuer, Jr., Psychology of Intelligence Analysis](https://www.cia.gov/resources/csi/static/Pyschology-of-Intelligence-Analysis.pdf), CIA Center for the Study of Intelligence, 1999: Chapter 8, Steps 1, 2, 5, 6, and its concluding discussion. Citations use printed page numbers, which differ from PDF page indices. The publication identifies the author's views separately from official CIA positions.

These are selected, paraphrased principles, not quotations or a claim to implement
every provision. The catalog does not adopt a minimum-contradiction-count winner
or categorical reliability weights. All severity values are local engine choices.
`BLOCKING` is policy metadata; selecting a rule does not automatically execute a
compliance check or reject an analysis. Engine validation enforces its own explicit
contracts independently of which references a caller selects.

| ID family | Interpretation | `implementation_policy` |
| --- | --- | --- |
| `ICD203-*` | Paraphrase tied to a specific directive section | `false` |
| `HEUER8-*` | Paraphrase tied to a specific book passage | `false` |
| `SAT-*` | Local safeguard or implementation decision | `true` |

Local rules cite the implementation contract with a URN. They do not borrow an
external authority's name to claim that an engine decision is mandated doctrine.
The formal falsification guard is one such local safeguard. The source principle
about examining whether evidence was observable is listed separately.

`doctrine.load_catalog()` returns a fresh, validated dictionary.
`doctrine.resolve_rules(rule_ids, catalog=None)` returns deep-copied rule objects
in sorted ID order; repeated selections are deduplicated and an empty selection
is valid. Unknown IDs raise `ValidationFailure` with code
`DOCTRINE_UNKNOWN_RULE`, a path, and remediation. IDs are exact and case-sensitive;
the engine never infers a citation from similar wording.

A caller-supplied catalog can contain a subset or reordering of the packaged
rules and additional explicitly labeled local policies. Duplicate IDs are errors.
Redefining a packaged ID raises `DOCTRINE_REFERENCE_MISMATCH`; asserting an
unpackaged external-source principle raises `DOCTRINE_UNVERIFIED_CITATION`.
Well-formed citation text or a valid URL alone cannot establish source accuracy.
The engine does not recheck source URLs at runtime or claim a newer edition has
been reviewed. Updating the packaged catalog requires a source review.

`enrich.enrich(text, rule_ids, mode="appendix")` accepts an already rendered text
string and returns another string. It does not accept or mutate canonical analysis
objects and does not edit files. No rule IDs means the text remains byte-for-byte
unchanged. Unknown rule IDs or modes fail with structured diagnostics.

- `appendix` appends a labeled reference section with summaries and citations.
- `inline` inserts compact contextual notes immediately after explicit anchors
  such as `[[doctrine:ICD203-UNCERTAINTY]]`. The original anchors remain present.
  Selected rules without anchors appear as compact context after the text.

Calling enrichment again on its output with the same mode and selection produces
the exact same string, including when selection order or duplicates differ.
Enrichment preserves the original text and adds only catalog-authored reference
context. It does not guess which prose satisfies a rule, verify free-text
citations, rewrite conclusions, or change the canonical artifact's content hash.
To select a different reference set or mode, render from the canonical artifact
again and enrich that fresh rendering. This also avoids retaining obsolete notes
from a previous reference selection.
