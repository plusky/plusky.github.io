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

## thinking

`hardware`, `model`, `jobs` (jobs replayed), `thinking_share_of_generation` and `time_saved_share` (0..1);
`on` and `off` (thinking on, thinking off): `generated_per_turn` (tokens), `median_s`, `p90_s`, `total_s`,
`prompt_s`, `generation_s`, `class_right` (jobs); `per_job_s[]`: `on`, `off` (seconds of the same job under
both settings, no job number). Shows: most of what the model generates is thinking, and turning it off saves
time but costs right answers.

## latency

`settings`: the text of each setting id (`t8b16`, `t16b32`, `t8b16-2q`, `t16b32-2q`: threads, batch threads,
two or four questions), `chosen` (the id proposed), `timeout_s` (openQA's limit for the hook), `hardware`;
`points[]`: `setting`, `tokens` (input tokens of one request), `secs`; `fits` per setting: `intercept_s`,
`s_per_1000_tokens`, `worst_residual_s`, and `on_128` (the fit applied to the 128 confirmation jobs):
`median`, `mean`, `p90`, `max`, `over_300` (jobs over the limit); `bursts[]`: `at_once` (requests sent
together), `secs`, `alone_s` (the same request alone). Shows: the decision request takes about a minute and
grows with the prompt; requests sent together can pass the limit.

## readers

`window_days`, `jobs_with_llm_comment`, `reviewed_jobs` (of those, reviewed by a person), `reviewed_share`
(0..1), `development_jobs`, `development_reviewed_jobs`, `development_share` (jobs in development groups),
`jobs_per_day`; `groups[]`: `group` (name of a public job group), `jobs_with_llm_comment`, `reviewed_jobs`,
`development` (true for a development group); `seven_groups`: the same counts over seven groups. Shows: few
of the commented jobs are reviewed by a person, and half of the comments go to groups nobody reviews.

## prs

`read` (date the lists were read), `topics[]`, `counts`: `merged`, `open`; `prs[]`: `number`, `repo`, `title`,
`topic`, `state`, `created`, `merged` (dates). Shows: the pull requests of the work over time, by topic.

## data/results

`data/results/<id>.json` is one experiment as a table: `id`, `scope` (as above), `title`, `compared` (what
was compared), `sample` (on what), `date`, `verdict` (the outcome), optional `note` and `pr[]` (`repo`,
`number`); `columns[]`: `key`, `label`, optional `align`; `rows[]`: one object per row with the column keys.
A cell is a number, a short text, a pair `[a, b]` ("a of b") or null (not measured). A table with rows from
both instances has scope `mixed` and a column `instance` that marks each row.

## data/jobs

`data/jobs/<set>.json` holds one row per job for a set that consists of public jobs only: `set`, `scope`
(always `o3`), `date`, `jobs` (number of rows), `columns[]`, `rows[]` (arrays in column order). `job` is the
job number on openqa.opensuse.org; job pages there expire. Classes are `product`, `test`, `infra`.

- `confirmation` (128 jobs of the frozen run): `label`, `label_source` (`hindsight` if the label needed what
  happened after the failure), `posted` (class of the posted comment), `rule_three` and `rule_two` (class of
  the three-order and of the two-question decision rule), `shares_test_and_build` (the job shares a test and a
  build with a job used for tuning).
- `gold` (98 jobs whose bug reference a person set): `label`, `iq2m` and `q8` (class Gemma gave in a replay
  with each quantisation, null without an answer), `decision_label` (the decision model's most probable class),
  `decision_rule` (class of the two-question rule), `doubtful` (the ticket's class is in doubt), `ticket` (a
  running number per ticket, 1 to 27, not the reference).
- `reruns` (299 jobs with a hindsight label): `label` (may be `unclear`), `posted`, `first_failure`, `group`
  (`passed-later-same-build`, `rerun-not-passed`, `not-rerun`, `not-first-failure`), `restart` and `bisect`
  (what the posted comment advised; for `bisect` also which rule set a NO), `rerun_started_by` (for the jobs
  that passed on a rerun: `unknown`, `mass-restart`, `retry-setting`, `new-run`, `hook`).

## facts.json

`data/facts.json` maps a key to `value`, `forms` (spellings the text may use), `what` and `scope` (as above).
It holds the numbers the article and its figure descriptions quote, and nothing else; the figure files above
hold the rest. `data/facts-data.json` does the same for the data page.
