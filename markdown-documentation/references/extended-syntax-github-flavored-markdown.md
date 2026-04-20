# Extended Syntax (GitHub Flavored Markdown)

GitHub Flavored Markdown extends CommonMark with footnotes, definition lists, emoji shortcodes,
auto-linking, task lists, and `@user` / `#issue` references. These render on GitHub, GitLab (most),
and other GFM-compatible viewers.

```markdown
Footnotes:
Here's a sentence with a footnote[^1].

[^1]: This is the footnote.

Definition list:
Term
: Definition

Emoji:
:smile: :rocket: :heart:
:+1: :-1: :eyes:

Automatic URL linking:
https://github.com

Task lists in issues:

- [x] #739
- [ ] https://github.com/octo-org/repo/issues/1
- [ ] Add tests

Mentioning users and teams:
@username
@org/team-name

Referencing issues and PRs:
#123
GH-123
username/repo#123
```
