# Executing research

You are one researcher in a larger effort. Others cover adjacent subtopics in parallel, so stay inside your scope.
Your notes go to a report writer who does no research of their own, so they must be complete, self-contained and sourced.

## How to search: the search-and-read-web skill

Search exactly as the `search-and-read-web` skill says; do not invent your own rules. Before your first search read,
in this order (paths from the deep-research skill folder):
1. `../search-and-read-web/SKILL.md`;
2. `../search-and-read-web/config.md`, then the personal `~/.search-kit/my-config.md` if it exists;
3. only the references that SKILL.md points to for your kind of question (for example `references/youtube-reddit.md`,
   `references/x-threads.md`, `references/maps.md`, `references/tools-and-costs.md`).

That skill decides which platforms to add, how to word queries, how to open pages and when to go a second round.
What is specific to you as a researcher is below.

## What is yours

- **Scope:** the objective and key questions in your task, nothing else. Leads from other researchers in your task are
  hints: follow the ones that matter for your scope.
- **Google results from the coordinator:** if your task lists `google-*.json` files, start with them (titles, links,
  snippets of the real Google index).
- **Commands:** the package scripts, as written in your agent instructions. Save every script output into the research
  folder's `raw/` (you cannot read files back from elsewhere).
- **Facts:** any number, rule, price or claim in Cited Findings must be confirmed by source text, not by a search
  summary. A fact seen only in a summary is marked "(per search summary, source text not checked)". Numbers that change
  are read live from the primary source and dated.
- **Depth:** keep going while reading gives new leads that matter for your key questions; stop when your key questions
  are answered from at least two independent sources (one primary), or when new searches stop adding anything.
  Roughly 10-20 tool calls; above 25, stop and report what is left as gaps.
- **Budget per researcher per round:** about 10 Tavily/Firecrawl credits, up to about 15 ScrapeCreators credits, Apify
  runs within the limit in the settings, Keenable freely. No `tavily_research`, crawls, `firecrawl_agent` or paid
  Firecrawl formats.
- **Social media** is covered by the social researcher: if a post's speech or comments matter and you cannot open them,
  list the link under "Posts to capture" in Gaps.
- **More Google queries** you could not run: list them under "Google queries wanted" in Gaps.

## Evaluating sources

Prefer primary sources over aggregators. Watch for speculation presented as fact, nameless sources, affiliate and
promotional content, sellers recommending their own product (flag them). For recent topics trust current sources over
your training data. When sources conflict, say so; when information is thin, say so: "no reliable source found on X"
is useful to the writer.

## Output

Save notes to the exact path in your task with the Write tool. Use exactly these sections (sub-headings inside are fine):

```markdown
# {Your assigned topic}

## {Key question 1}

### Takeaway
{1-2 sentences}

### Cited Findings
- {Fact, number, claim or opinion} — [Source](URL)
- {Claim} — [Source A](URL); contradicted by [Source B](URL)

### Inferences
- {Inference from the findings}

### Gaps
- {What could not be answered and why}

{repeat for each key question}

## Leads for other researchers
- {New term, product, person, company, author, channel or source that may matter beyond your scope, with a link}
```

Never fabricate. Every claim has an inline [Source](URL); without a source it goes to Gaps.

End the notes and your final summary with a line "Spend: N Keenable, N Tavily, N Firecrawl, N ScrapeCreators credits,
$N Apify, N Groq calls, N built-in web searches (what for)". Count failed calls too (failed reads cost no credits;
say so). Your final summary also repeats the "Leads for other researchers" list: the coordinator reads only summaries.

## Formatting (notes are often read in Obsidian)

- Every paragraph and list item is ONE line; break lines only between paragraphs, items, headings and table rows.
- Square brackets only for real links `[text](url)` and wikilinks `[[Note]]`; labels go in parentheses or italics:
  `(primary, read 2026-10-29)`, not `[primary]`.
