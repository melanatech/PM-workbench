# Common Pitfalls

The canonical copy of the four framing pitfalls the Product Analyst reviewer's Product Analyst agent checks for in
Mode 2 (blind review). `agents/product-analyst.md` points here instead of restating these — if
you're editing what one of these means, this is the one place to change it.

## Comparison-group homogeneity

**The claim (hypothetical, not a real number from anywhere in this repo):** "adopters converted
at 28%, non-adopters at 11.5%, so the feature works."
**The check:** is this actually a valid comparison group, or does it fail in one of two ways —
(a) the "non-adopter" bucket secretly mixes two populations (e.g. "actively uses the legacy
version of this exact job" and "never does this job at all"), so the measured gap is partly just
"does this job at all vs. doesn't," nothing to do with the feature; or (b) the comparison is
self-selected rather than assigned — adopters chose to try the new thing, so any gap may just
reflect who was already more engaged, not what the feature did.
**Concrete case (self-selection variant, (b) above):** a worked internal case's EXAMPLE-ID
advanced-filters analysis: adopters showed a
24.0% (6/25) report-request rate vs. 9.3% (157/1,688) for non-adopters — directionally positive,
but adoption was user-chosen, not randomly assigned, so the two groups aren't comparable
populations to begin with. The doc's own read: shoppers who are already heavier reports users are
more likely to discover and try a new filter feature in the first place, independent of any effect
**How to check:** pull the real split via `your approved warehouse / analytics path` rather than trusting the doc's own
framing of who's in the comparison bucket.

## Matched-window deltas

**The claim:** "usage went up 40% after the change, comparing the 90 days before to the 30 days
after."
**The check:** for a self-selected, recently-formed cohort, is the pre/post comparison using
equal-length, calendar-matched windows? A longer "before" window than "after" window mechanically
inflates any reach-type metric (did this account ever do X) purely because it had more calendar
time to accumulate a "yes" in — independent of whether the change did anything.
**How to check:** confirm both windows are the same length and cover comparable calendar periods
(same day-of-week mix, same seasonality) before trusting the delta.

## Real target vs. near-term proxy

**The claim:** treating a proxy metric's result as if it were the real target metric's result,
without saying so.
**The check:** is the doc quietly substituting something measurable-now for the thing that
actually matters, without naming the substitution? The real target metric should still be named
explicitly even when it isn't computable yet — silently swapping in a proxy is a different failure
from correctly saying "the real target isn't measurable yet, so here's a proxy and why it's a
reasonable stand-in."
**How to check:** read the doc's own metric definitions section for whether the target is named
and the proxy substitution (if any) is explicit, not inferred.

## Event precision

**The claim:** a metric built on a coarser event than the precise one actually available — e.g. a
page-path visit standing in for the specific render/impression event that would answer the
question more directly.
**The check:** is there a more precise event already firing that this metric should be using
instead? A page-path visit counts everyone who loaded the page, including people who never saw or
interacted with the specific element the metric claims to measure.
**How to check:** `your approved column-search / catalog tool` / `execute_query` against the real warehouse —
not an assumption from the tracking plan's event name alone. This exact repo's own EXAMPLE-ID/CP-5835
work found real gaps this way (`datasheet.impression` vs. a coarser page-path event materially
changed the measured adopter advantage).
