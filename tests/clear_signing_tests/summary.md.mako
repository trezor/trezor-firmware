<%doc>
  The summary of the nightly clear-signing tests, for $GITHUB_STEP_SUMMARY.
  Rendered by `nightly.py summarize`. Lines starting with "##" are Mako comments,
  so Markdown headings are written as ${"##"}.
</%doc>\
<%!
    def short(sha):
        return f"`{sha[:10]}`" if sha else "?"

    def baseline_link(run):
        if not run:
            return "`fixtures.json`"
        return f"[#{run['run_number']}]({run['run_url']}) ({run['created_at'][:10]})"
%>\
<%def name="capped(lines)">\
% for line in lines[:max_lines]:
${line}
% endfor
% if len(lines) > max_lines:

… and ${len(lines) - max_lines} more, see the results artifacts.
% endif
</%def>\
${"##"} Clear-signing registry tests

Definitions: \
% if inputs.get("definitions_ref"):
`${inputs["definitions_ref"]}` @ \
% endif
[${short(inputs.get("definitions_sha"))}](https://github.com/trezor/definitions/commit/${inputs.get("definitions_sha")})\
% if inputs.get("deploy_run_url"):
, [deployed ${inputs["deployed_at"]}](${inputs["deploy_run_url"]})\
% endif
 · Registry: [${short(inputs.get("registry_sha"))}](https://github.com/${inputs.get("registry_repo")}/tree/${inputs.get("registry_sha")})

${total} mainnet cases of all registry providers: ${run} run on each model, ${total - run} skipped.

| Model | Clear-signed | Blind-signed | Blind-signed, no format | Error | Not run | Text not found | UI report | Compared with |
|---|---:|---:|---:|---:|---:|---:|---|---|
% for row in rows:
| ${row.model} | ${row.counts["clear_signed"]} | ${row.counts["blind"]} | ${row.counts["blind, no format"]} | ${row.counts["error"]} | ${row.counts["not run"]} | ${row.counts["text not found"]} | [report](${row.report_url}) · [differing screens](${row.differing_url}) | ${baseline_link(row.baseline)} |
% endfor

The UI report compares the screens of each model with those of the last nightly run (`fixtures.json` when there is none). There is nothing to accept: the screens of this run are what the next one compares with.

<details><summary>Skipped cases (${sum(len(lines) for _, lines in skipped)})</summary>

% for reason, lines in skipped:
**${reason}** (${len(lines)})

${capped(lines)}
% endfor
</details>

<details><summary>Failed or not run (${len(problems)})</summary>

${capped([f"- `{test_id}`: {'; '.join(lines)}" for test_id, lines in problems])}
</details>

<details><summary>Blind-signed, no display format (${len(no_format)})</summary>

The dev definitions have no display format for the contract and function: trezor/definitions does not convert this provider, the converter dropped the format (an unsupported feature, an override by another descriptor), or the descriptor does not cover this contract on mainnet. Not a failure.

${capped([f"- `{test_id}` ({', '.join(models)})" for test_id, models in no_format])}
</details>

<details><summary>Blind-signed (${len(blind)})</summary>

The firmware fell back to blind signing although the dev definitions have a display format. Not a failure: the UI report shows when a case changes between clear and blind signing.

${capped([f"- `{test_id}` ({', '.join(models)})" for test_id, models in blind])}
</details>

<details><summary>Clear-signed, but expected text not found on screen (${len(not_found)})</summary>

The registry's `expected` texts that no page showed. The firmware formats some values differently, so this is for review, not a failure.

${capped([f"- `{test_id}` ({', '.join(models)}): {'; '.join(missing)}" for test_id, (models, missing) in not_found])}
</details>
