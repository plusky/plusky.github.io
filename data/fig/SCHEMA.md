# Figure data

One JSON file per figure. Every file has `id` (the figure id) and `scope`:

| scope | meaning |
|---|---|
| `o3` | public jobs of openqa.opensuse.org only |
| `mixed` | counts over a set that also holds jobs of a company-internal instance; aggregates only |
| `internal-aggregate` | counts over internal jobs only |
| `bench` | measurements on test hardware |
| `public-record` | public pull requests and comments |

A block inside a file can carry its own `scope`. Class order is always product, test, infra. A 3x3 table
`t` has rows = the first named thing (label, run 1) and columns = the second (answer, run 2): `t[0][1]` is
"product, answered test". A pair `[a, b]` is "a of b". Seconds are wall-clock seconds.

## chars-per-token

`n`, `median`, `p10`, `min`, `max` (characters per token), `share_below_assumed` (0..1), `assumed` 2.5,
`proposed` 1.9, `bin_width` 0.05, `bins[]`: `lo`, `hi`, `n` (half-open `[lo, hi)`). Shows: most real prompts
have fewer characters per token than the script assumed.

## labels

`human`: `failed_with_bug_reference` (failed, incomplete or timed-out jobs), `bots_or_carry_over`,
`set_by_person`, `set_by_person_public_ticket` (set by a person, ticket public: class known), `by_class` (`product`, `test`, `unknown_ticket_not_public` = a ticket in a project that is not
public, class unknown, `ticket_other_team`, `infra`), `distinct_references`, `window_days`. `gold`: `jobs`,
`by_class`, `tickets`, `tickets_by_class`, `doubtful_tickets`, `doubtful_jobs`, `clusters[]`: `jobs`, `class`,
`doubtful` (one per ticket, largest first). `silver`: `jobs`, `by_class` (with `unclear`), `with_class` (jobs
not unclear, any confidence), `confident_by_class` (labeller confidence at least 0.6), `confident_rule`.
Shows: people label few jobs, and never infrastructure where the ticket is public; the gold set is 27 tickets, one of them 18 jobs.

## detectable

`z`, `spread`; `marks[]`: `tickets`, `points`, `what`; `observed`: `tickets`, `spread`, `points`, `what`;
`curve[]`: `tickets`, `points` (percentage points, `z * spread / sqrt(tickets) * 100`). Shows: with 27
tickets only a difference of about 30 points is visible; 105 tickets bring it to 15.

## repeat

`model`; `sets[]`: `set`, `scope`, `jobs`, `same` (jobs with the same class in both runs); `o3_pair` and
`lastgood_pair`: `scope`, `jobs`, `classes`, `run1_by_run2` (3x3), `right` (`run1`, `run2`), and for
`o3_pair` the `labels` per class; `agreeing_runs_right`: `pair` (which two runs), `product`, `test` as
`[right, jobs where both runs
agree]`. Shows: an easy set repeats, a hard o3 set does not.

## confusion

`classes`, `kinds`; `gold_q8`, `gold_iq2m` (gold o3, Gemma Q8 and the production quantisation IQ2_M) and
`silver_posted` (silver o3 labels against the posted comment): `jobs`, `right`, `label_by_answer` (3x3),
`by_kind` (per kind of failure: `jobs`, `right`, `label_by_answer`); `silver_unclear_jobs`;
`gold_jobs_by_kind` (all 98, including the three Gemma did not answer). Shows: the answer follows the kind of
failure, and test issues end up as product bugs.

## screens

`jobs` (`A`, `B`, `AB`, `M`), `log_rows`, `verdicts` (counts), `rules[]`: `screen`, `rule`; `noise`: what
the one repeat on file observed, no estimate derived from it: `scope`, `what`, `temperature`, `jobs` (half A),
`answers_changed`, `right_wrong_switched` (of those, answers that went from right to wrong or back),
`only_half_a` (why there is nothing for half B), `caveats`; `a_then_b`: pairs, each a comparison that passed
its rule on half A and was then run on half B with the same candidate against the same control in a later run
(strictly later; a half-B reading of the same stored run does not count) (`definition`; `pairs`,
`pairs_failed_on_b`, `pairs_passed_on_b`; the same by idea, a distinct candidate with its "abstentions filled"
reading folded in: `ideas_passed_a`, `ideas_ran_on_b`, `ideas_failed_on_b`; `readouts_excluded`, passes on half
A whose half-B value is the same stored run read off at the same time, and `readouts_note`, that in plain words);
`on_the_halves`: `comparisons` (rows on A, B or AB with a net count over at least one job: the rows the figure
draws), `passed`, `which`; `reference`: `always_product`, `production`, `of`; `families`; `rows[]`: `time` (local time, minutes),
`screen` (`A`, `B`, `AB`, `M`, or `-` for an analysis without a run), `n` (jobs compared, null when not a
paired count), `net` (jobs gained minus lost against the control), `class_delta` (per class, null for `M`),
`verdict` (`pass`, `drop`, `drop (coverage)`), `label`, `family`, `control` (null when there was no control),
`reason` (plain words why a row whose net meets the rule's number was dropped or later overturned: class
rule, coverage, time, leakage; null otherwise), `pair` (the same integer on an A pass and its later B runs of
`a_then_b`, under the same definition; null otherwise). Shows: many ideas, a few passes, and almost every pass on A failing on B.

## env

`threshold` 0.3; `confirmation`: `scope`, `jobs`, `above_by_label` (`[at or above threshold, jobs]` per
class, counted on the unrounded value), `points[]`: `label`, `env` (probability 0..1, 5 decimals, enough to
give the same counts); `read_off`: `scope`, `jobs`, `infra`, `others` (`[at or
above, jobs]`), `infra_just_below`, `chosen_after_seeing_data`. Shows: the environment answer separates
infrastructure from the rest on unseen jobs about as well as on the set the threshold was read from.

## confirm

`o3`: `jobs`, `control` (posted class), `rule` (the two questions deployed), `rule_three_orders` (the rule
frozen before the run): `right`, `of`, `mean_class_recall` (percent), `by_class` (`right`, `jobs`, `said`),
`mcnemar` (`gained`, `lost`, `p` exact two-sided, 3 significant digits, `p_printed` as the scorer prints it);
`gain_low_90` (lower end of the 90% bootstrap interval of the gain in mean class recall, percentage points).
`by_label_source`: `hindsight_rule` (the definition: the final label was given by a labelling pass that set
`hindsight_used`); `person_set` (`jobs`, `in_threshold_set`, `rule` and `production_replay` with `right`,
`product`, `test`; jobs outside the 128); the rows `hindsight_rerun_passed` (hindsight label, passed on a rerun
in the same build), `hindsight_other`, `no_hindsight` partition the 128 (`jobs`, `posted` and `rule` per
class `[right, jobs]`, `posted_right`, `rule_right`); `hindsight_total` = the first two rows, `hindsight_infra`;
`hindsight_by_other_rules` (`first_labeller_flag`, `any_pass_flag`: the same count by two other readings of the
flags); `rerun_passed_any_source` (same fields, every job of the 128 that passed on a rerun, overlapping the
rows); `infra_total`, `missed_infra`, `missed_infra_rerun_passed`. `reviewed_by_person`: jobs of the 128 a person
reviewed on o3, class taken from the person's bug reference as the gold set does: `scope`, `jobs`, `tickets`,
`largest_ticket_jobs`, `by_class`, `tickets_in_gold_set`, `tickets_resolution_checked`, `silver_label_agrees`,
`posted_right`, `rule_right`, `method`, `caveats`. `rerun_passed_with_decision`: `silver_with_decision`, `jobs`,
`posted_infra`, `rule_infra`, `both_infra`. Shows: 93 against 66 on hindsight labels, a tie on labels a person
set.

## reruns

`silver_jobs`, `first_failures` (the previous run of the same scenario did not fail), `not_first_failures`;
`groups` (`passed_later_same_build`: a later run in the same build passed, a rerun of the job or a new run of
the scenario; `rerun_not_passed`, `not_rerun`): `jobs`, `bisect_yes`, `bisect_no_model`,
`bisect_no_same_module_rule`, `bisect_no_streak_rule`, `restart_yes`, `restart_no`, `labels` and `posted` per
class; `all` (the same answer counts over all silver jobs); `who_started` (counts); `delay_median_min`
(minutes), `delay_measured` (what the delay runs from and to); `retry_rules[]`: `rule`, `retries` (jobs
retried), `covers` (jobs whose later run passed that the rule would have retried); `hook_rule_retry_passed`
(of the jobs today's hook covers, those whose own investigation retry passed); `comments_per_day` (jobs with
an LLM comment a day, four groups), `first_failures_per_day`;
`strict_note`: `records_passed` 68, `forced_pass` 1, `covers_with_68` (the `covers` column counted with 68);
`hook_investigations`: `jobs`, `clones`, `retry_passed`, `retry_softfailed`. Shows: a third of first failures
pass when simply rerun, and today's hook catches few of them.

## comment-example

`job` (o3 job id), `instance`, `created` (date), `text` (the LLM's comment, Markdown). Shows: what a comment
looks like.

## facts.json

`data/facts.json` maps a key to `value`, `forms` (spellings the text may use), `what` and `scope` (as above).
It holds the numbers the article and its figure descriptions quote, and nothing else; the figure files above
hold the rest.
