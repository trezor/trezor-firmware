# Review Process

- File a Pull Request with a number of well-defined clearly described commits.
  Multiple commits per PR are allowed, but please do not use reverts, etc. Use rebase.
- Do not use merge (e.g. merge trezor/master into ...). Again, use rebase.
- The general review workflow goes as follows:
  1. Someones makes a PR. They should make sure it passes lints and anything that can be run
     quickly on your computer.
  2. Reviewer reviews.
  3. In case the reviewer finds something they create a comment using the Github review system.
  4. The creator adds and pushes so called _fixup_ commit that fixes the particular commit fixing
     the reviewer's comment. This can be done by `git commit --fixup HEAD` which creates a commit
     message called "fixup! something". The "something" is the previous commit message it "fixes".
  5. The creator informs the reviewer with a simple comment "done" or similar to tell the reviewer 
     their comment was implemented. Bonus points for including a revision of the fixup commit.
  6. Reviewer reviews the modifications and when they are finally satisfied they resolve the Github
     comment.
  7. Reviewer finally approves the PR with the green tick.
  8. Creator runs `git rebase -i [main branch] --autosquash` which squashes the fixup commits into
     their respective parents. Creator force-pushes these changes.
  9. Reviewer makes a final check and merges the PR.

## Example

If you find the description too difficult here is an example to make it more clear.

Andrew tries to add number of commits very well structured and with nice and consistent commit
messages. These will _not_ be squashed together. 

![](review-1.png)

Matějčík starts to review and finds something he would like to improve:

![](review-2.png)

Andrew responds with a commit hash 55d883b informing that he has accepted and implemented the 
comment.

This commit is a fixup commit. Since it is a new commit he does not have to force-push. In the
following image he is fixing the "test: Add device tests..." commit.

![](review-3.png)

This way we can end up with number of fixup commits at the end of the review. Note that there is one commit on the following image that is _not_ a fixup commit. That's totally okay in case it makes sense and the creator indeed wants it as a separate commit.  

![](review-4.png)

Matějčík is happy and approves the PR. After that Andrew squashes his commits via `git rebase -i [main branch] --autosquash`. This command will squash the fixup commits into their respective places modifying the original commits. After this he force-pushes. As you can see the history we end up with is very nice.

![](review-5.png)

We merge the PR and that's it!

## Notes & Rationale

- If you want to fixup the latest commit just use `git commit --fixup HEAD` as written above. If you want to fixup some older commit use `git commit --fixup [commithash]`. Or any other reference for that matter.
- More good git rebase tips can be found at this [Atlassian website](https://www.atlassian.com/git/tutorials/rewriting-history/git-rebase).
- Some rationale why we avoid force pushing during code review, i.e. during the period starting with the creation of the PR until the last approval is given:
  1. Force pushing often makes it impossible to see the changes made by the author, so the reviewer has to go through the entire PR again. If it's just an amend, then GitHub can show the differences, but in more complicated situations it's unable to untangle what happened. Especially if you rebase over master, which adds lots of new changes.
  2. A fixup commit can be easily referenced in the response to the reviewer's comment.
  3. It often breaks hyperlinks, which is a real nuisance when somebody is referencing some code in their comment and you have no clue what they are talking about.
  4. It has lead to code review comments being lost on multiple occasions. I think this happens especially if you comment on a particular commit.
- What to do if you really need to rebase over master during an ongoing code review? This happens rarely, but if it's really necessary in order to implement the requested revisions, then:
  1. Try to resolve as many reviewer comments as possible before rebasing.
  2. Ask the reviewers for approval to go ahead with the rebase, i.e. give them time to confirm that the comments have been well resolved, avoiding as many of the problems mentioned above as possible.
  3. Rebase, do the stuff you need, force-push for a second round of review.
