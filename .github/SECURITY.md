# Security policy

`confusable` is a security library: a look-alike it fails to flag, or an invisible
character it lets through, is a vulnerability in the projects that rely on it.

## Reporting a vulnerability

Report privately through
[GitHub security advisories](https://github.com/blip-box/confusable/security/advisories/new).
Do not open a public issue.

Useful reports include:

- two strings that UTS #39 treats as confusable but this library does not, or the
  reverse;
- invisible, bidirectional or Tag-block characters that pass a check meant to reject
  them;
- input that makes a check crash or run in more than linear time.

Please include the exact code points (for example `U+0430`), not only the rendered
text, since rendering can hide the problem.

## Supported versions

No version has been released yet. Once releases exist, only the latest release
receives security fixes.
